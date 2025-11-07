"""Rules referee agent for validating player actions against corpus."""

import re
from typing import List, Optional, Dict, Any
from enum import Enum
from ..core.base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from ..core.config import AgentConfig
from ..core.retrieval_manager import RetrievalManager
from .prompt_templates import PromptTemplateManager
from .response_parsers import ResponseParser
from .citation_utils import CitationMapper


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    BLOCKING = "blocking"     # Clear contradiction, action cannot proceed
    WARNING = "warning"       # Questionable but allowable
    NONE = "none"            # No issues, action approved


class RulesRefereeAgent(BaseAgent):
    """Validates player actions against corpus facts."""

    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        """Initialize RulesReferee agent.

        Args:
            config: Agent configuration
            retrieval_manager: Retrieval manager for RAG operations
        """
        super().__init__(config)
        self.retrieval_manager = retrieval_manager

    def process(self, context: AgentContext) -> AgentOutput:
        """Process context and validate player action.

        Args:
            context: Agent context with player command and session state

        Returns:
            AgentOutput with validation result
        """
        try:
            # 1. Build retrieval query
            query = self._build_query(context)
            self.logger.debug("Built validation query", query=query[:100])

            # 2. Retrieve relevant facts
            retrieval_results = self.retrieval_manager.retrieve(
                query=query,
                top_k=self.config.retrieval_top_k,
                agent_name=self.config.name
            )

            # If no retrieval results, approve by default (benefit of doubt)
            if not retrieval_results:
                self.logger.info("No retrieval results, approving by default")
                return self._approve_action(
                    "No relevant facts found in corpus to contradict this action.",
                    []
                )

            # 3. Build prompt
            prompt = self._build_prompt(context, retrieval_results)

            # 4. Generate validation
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt()
            )

            # 5. Parse response
            output = self._parse_response(response, retrieval_results)

            self.logger.info("Validation completed",
                           approved=output.metadata.get("validation_result", {}).get("approved"),
                           severity=output.metadata.get("validation_result", {}).get("severity"))

            return output

        except Exception as e:
            self.logger.error("Validation failed", error=str(e), exc_info=True)
            # On error, approve with warning
            return AgentOutput(
                content="Validation system error. Action approved by default.",
                citations=[],
                reasoning=f"Error during validation: {str(e)}",
                metadata={
                    "validation_result": {
                        "approved": True,
                        "reason": f"Validation error: {str(e)}",
                        "severity": ValidationSeverity.WARNING.value,
                        "suggested_alternative": None
                    },
                    "error": True
                }
            )

    def _build_query(self, context: AgentContext) -> str:
        """Build retrieval query for fact validation.

        Args:
            context: Agent context

        Returns:
            Query string for retrieval
        """
        query_parts = []

        # Add player command (the action to validate)
        if context.player_command:
            query_parts.append(context.player_command)

        # Add current scene
        current_scene = context.session_state.get("current_scene", "")
        if current_scene:
            query_parts.append(current_scene)

        # Extract action keywords
        action_keywords = self._extract_action_keywords(context.player_command)
        query_parts.extend(action_keywords)

        # Add context from narrator if available
        narrator_output = context.session_state.get("narrator_output", "")
        if narrator_output:
            # Extract key entities
            entities = self._extract_entities(narrator_output[:200])
            query_parts.extend(entities[:2])

        return " ".join(query_parts) if query_parts else "rules facts"

    def _extract_action_keywords(self, command: str) -> List[str]:
        """Extract key action verbs and objects from command.

        Args:
            command: Player command

        Returns:
            List of action keywords
        """
        # Common action verbs
        action_verbs = ['use', 'take', 'get', 'pick', 'open', 'close', 'attack', 'talk',
                       'speak', 'say', 'go', 'move', 'walk', 'run', 'fly', 'swim',
                       'cast', 'drink', 'eat', 'wear', 'remove', 'climb', 'jump']

        words = command.lower().split()
        keywords = []

        # Extract verbs
        for verb in action_verbs:
            if verb in words:
                keywords.append(verb)

        # Extract capitalized words (potential objects/NPCs)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', command)
        keywords.extend(capitalized)

        return keywords[:5]  # Limit to 5 keywords

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity names from text.

        Args:
            text: Text to extract from

        Returns:
            List of entities
        """
        # Extract capitalized words
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        # Filter common words
        common_words = {'The', 'A', 'An', 'In', 'On', 'At', 'To', 'From', 'You'}
        entities = [e for e in entities if e not in common_words]

        return list(set(entities))[:5]

    def _build_prompt(self, context: AgentContext, results: List[RetrievalResult]) -> str:
        """Build LLM prompt for validation.

        Args:
            context: Agent context
            results: Retrieved chunks

        Returns:
            Formatted prompt string
        """
        # Format retrieved chunks
        retrieved_chunks = CitationMapper.format_chunks_for_prompt(results, include_scores=False)

        # Get current scene
        current_scene = context.session_state.get("current_scene", "Unknown")

        # Build memory context
        memory_context = self._build_memory_context(context)

        # Get narrator and NPC outputs if available
        narrator_output = context.session_state.get("narrator_output", "None")
        npc_output = context.session_state.get("npc_manager_output", "None")

        # Format prompt using template
        return PromptTemplateManager.format_template(
            "rules_referee_user",
            retrieved_chunks=retrieved_chunks,
            player_command=context.player_command,
            current_scene=current_scene,
            memory_context=memory_context,
            narrator_output=narrator_output,
            npc_output=npc_output
        )

    def _build_memory_context(self, context: AgentContext) -> str:
        """Build memory context from previous turns.

        Args:
            context: Agent context

        Returns:
            Formatted memory context string
        """
        if not context.previous_turns:
            return "Beginning of story."

        # Get last turn
        last_turn = context.previous_turns[-1] if context.previous_turns else None
        if not last_turn:
            return "Beginning of story."

        turn_num = last_turn.get("turn_number", "?")
        player_cmd = last_turn.get("player_command", "")

        return f"Last action (Turn {turn_num}): {player_cmd}"

    def _get_system_prompt(self) -> str:
        """Get system prompt for rules referee.

        Returns:
            System prompt string
        """
        return PromptTemplateManager.get_template("rules_referee_system")

    def _parse_response(self, response: str, results: List[RetrievalResult]) -> AgentOutput:
        """Parse LLM response into AgentOutput.

        Args:
            response: Raw LLM response
            results: Retrieved chunks used

        Returns:
            Parsed AgentOutput
        """
        try:
            # Try to parse JSON response
            validation_data = ResponseParser.parse_json_response(response)

            # Extract fields
            approved = validation_data.get("approved", True)  # Default approve
            reason = validation_data.get("reason", "")
            severity = validation_data.get("severity", ValidationSeverity.NONE.value)
            suggested_alternative = validation_data.get("suggested_alternative")

            # Extract citations from reason
            citation_markers = ResponseParser.extract_citations(reason)
            chunk_ids = CitationMapper.map_citations(citation_markers, results)

            # Build content message
            if approved:
                content = "Action approved."
            else:
                content = f"Action rejected: {reason}"
                if suggested_alternative:
                    content += f"\nSuggested alternative: {suggested_alternative}"

            return AgentOutput(
                content=content,
                citations=chunk_ids,
                reasoning=reason,
                metadata={
                    "validation_result": {
                        "approved": approved,
                        "reason": reason,
                        "severity": severity,
                        "suggested_alternative": suggested_alternative
                    }
                }
            )

        except (ValueError, KeyError) as e:
            # If parsing fails, try to extract approval from text
            self.logger.warning("Failed to parse validation JSON", error=str(e))

            # Look for approval/rejection keywords
            response_lower = response.lower()
            if "reject" in response_lower or "not allowed" in response_lower or "contradiction" in response_lower:
                approved = False
                severity = ValidationSeverity.BLOCKING.value
            else:
                approved = True
                severity = ValidationSeverity.NONE.value

            # Extract citations
            citation_markers = ResponseParser.extract_citations(response)
            chunk_ids = CitationMapper.map_citations(citation_markers, results)

            return AgentOutput(
                content="Action approved." if approved else "Action rejected.",
                citations=chunk_ids,
                reasoning=response,
                metadata={
                    "validation_result": {
                        "approved": approved,
                        "reason": response,
                        "severity": severity,
                        "suggested_alternative": None
                    },
                    "parse_error": True
                }
            )

    def _approve_action(self, reason: str, chunk_ids: List[str]) -> AgentOutput:
        """Create approval output.

        Args:
            reason: Reason for approval
            chunk_ids: Citation chunk IDs

        Returns:
            AgentOutput for approval
        """
        return AgentOutput(
            content="Action approved.",
            citations=chunk_ids,
            reasoning=reason,
            metadata={
                "validation_result": {
                    "approved": True,
                    "reason": reason,
                    "severity": ValidationSeverity.NONE.value,
                    "suggested_alternative": None
                }
            }
        )
