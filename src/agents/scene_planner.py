"""Scene planner agent for determining story flow and NPC responses."""

import re
from typing import List, Optional, Dict, Any
from ..core.base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from ..core.config import AgentConfig
from ..core.retrieval_manager import RetrievalManager
from .prompt_templates import PromptTemplateManager
from .response_parsers import ResponseParser
from .citation_utils import CitationMapper
from ..utils.debug_logging import debug_log_method


class ScenePlannerAgent(BaseAgent):
    """Determines scene flow and which NPC should respond."""

    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        """Initialize ScenePlanner agent.

        Args:
            config: Agent configuration
            retrieval_manager: Retrieval manager for RAG operations
        """
        super().__init__(config)
        self.retrieval_manager = retrieval_manager

    @debug_log_method
    def process(self, context: AgentContext) -> AgentOutput:
        """Process context and determine scene flow.

        Args:
            context: Agent context with player command and session state

        Returns:
            AgentOutput with scene plan
        """
        try:
            # 1. Build retrieval query
            query = self._build_query(context)
            self.logger.debug("Built scene planning query", query=query[:100])

            # 2. Retrieve relevant context
            retrieval_results = self.retrieval_manager.retrieve(
                query=query,
                top_k=self.config.retrieval_top_k,
                agent_name=self.config.name
            )

            # 3. Build prompt
            prompt = self._build_prompt(context, retrieval_results)

            # 4. Generate scene plan
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt()
            )

            # 5. Parse response
            output = self._parse_response(response, retrieval_results, context)

            scene_plan = output.metadata.get("scene_plan", {})
            self.logger.info("Scene plan generated",
                           npc_responds=scene_plan.get("npc_responds"),
                           responding_npc=scene_plan.get("responding_npc"),
                           next_scene=scene_plan.get("next_scene"))

            return output

        except Exception as e:
            self.logger.error("Scene planning failed", error=str(e), exc_info=True)
            # Fallback to narrator
            return self._fallback_to_narrator(str(e))

    @debug_log_method
    def _build_query(self, context: AgentContext) -> str:
        """Build retrieval query for scene planning.

        Args:
            context: Agent context

        Returns:
            Query string for retrieval
        """
        query_parts = []

        # Add "character" and "NPC" keywords for NPC-focused retrieval
        query_parts.append("character NPC dialogue")

        # Add player command
        if context.player_command:
            query_parts.append(context.player_command)

        # Add current scene
        current_scene = context.session_state.get("current_scene", "")
        if current_scene:
            query_parts.append(current_scene)

        # Add active NPCs
        active_npcs = context.session_state.get("active_npcs", [])
        if active_npcs:
            query_parts.extend(active_npcs[:3])  # Top 3 active NPCs

        # Extract potential NPC names from player command
        npc_mentions = self._extract_npc_mentions(context.player_command)
        if npc_mentions:
            query_parts.extend(npc_mentions)

        return " ".join(query_parts)

    def _extract_npc_mentions(self, command: str) -> List[str]:
        """Extract potential NPC names from command.

        Args:
            command: Player command

        Returns:
            List of potential NPC names
        """
        # Look for capitalized words that might be NPC names
        potential_npcs = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', command)

        # Filter out common words
        common_words = {'I', 'You', 'He', 'She', 'They', 'We', 'The', 'A', 'An'}
        npcs = [npc for npc in potential_npcs if npc not in common_words]

        return npcs[:3]  # Limit to 3

    @debug_log_method
    def _build_prompt(self, context: AgentContext, results: List[RetrievalResult]) -> str:
        """Build LLM prompt for scene planning.

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

        # Get active NPCs
        active_npcs = context.session_state.get("active_npcs", [])
        active_npcs_str = ", ".join(active_npcs) if active_npcs else "None"

        # Build previous turn summary
        previous_turn_summary = self._build_previous_turn_summary(context)

        # Format prompt using template
        return PromptTemplateManager.format_template(
            "scene_planner_user",
            retrieved_chunks=retrieved_chunks,
            player_command=context.player_command,
            current_scene=current_scene,
            active_npcs=active_npcs_str,
            previous_turn_summary=previous_turn_summary
        )

    def _build_previous_turn_summary(self, context: AgentContext) -> str:
        """Build summary of previous turn.

        Args:
            context: Agent context

        Returns:
            Summary string
        """
        if not context.previous_turns:
            return "This is the first turn."

        last_turn = context.previous_turns[-1]
        turn_num = last_turn.get("turn_number", "?")
        player_cmd = last_turn.get("player_command", "")
        outputs = last_turn.get("outputs", {})

        summary_parts = [f"Turn {turn_num}: Player said/did: {player_cmd}"]

        # Add narrator summary if available
        if "narrator" in outputs and isinstance(outputs["narrator"], dict):
            narrator_content = outputs["narrator"].get("content", "")
            if narrator_content:
                short_content = narrator_content[:100] + "..." if len(narrator_content) > 100 else narrator_content
                summary_parts.append(f"Narrator: {short_content}")

        return "\n".join(summary_parts)

    def _get_system_prompt(self) -> str:
        """Get system prompt for scene planner.

        Returns:
            System prompt string
        """
        return PromptTemplateManager.get_template("scene_planner_system")

    @debug_log_method
    def _parse_response(
        self,
        response: str,
        results: List[RetrievalResult],
        context: AgentContext
    ) -> AgentOutput:
        """Parse LLM response into AgentOutput.

        Args:
            response: Raw LLM response
            results: Retrieved chunks used
            context: Agent context

        Returns:
            Parsed AgentOutput
        """
        try:
            # Parse JSON response
            plan_data = ResponseParser.parse_json_response(response)

            # Extract fields
            npc_responds = plan_data.get("npc_responds", False)
            responding_npc = plan_data.get("responding_npc")
            next_scene = plan_data.get("next_scene")
            reasoning = plan_data.get("reasoning", "")
            fallback_to_narrator = plan_data.get("fallback_to_narrator", not npc_responds)

            # Extract citations from reasoning
            citation_markers = ResponseParser.extract_citations(reasoning)
            chunk_ids = CitationMapper.map_citations(citation_markers, results)

            # Build content message
            if npc_responds and responding_npc:
                content = f"{responding_npc} will respond to the player."
            else:
                content = "Narrator will describe the scene."

            if next_scene:
                content += f" Scene transition to: {next_scene}"

            return AgentOutput(
                content=content,
                citations=chunk_ids,
                reasoning=reasoning,
                metadata={
                    "scene_plan": {
                        "npc_responds": npc_responds,
                        "responding_npc": responding_npc,
                        "next_scene": next_scene,
                        "fallback_to_narrator": fallback_to_narrator
                    }
                }
            )

        except (ValueError, KeyError) as e:
            # If parsing fails, try to extract NPC mentions from text
            self.logger.warning("Failed to parse scene plan JSON", error=str(e))

            # Try to find NPC names in response
            npc_names = self._extract_npc_from_passages(results)
            responding_npc = npc_names[0] if npc_names else None

            # Check if response suggests NPC interaction
            response_lower = response.lower()
            npc_responds = responding_npc is not None and (
                "respond" in response_lower or
                "speak" in response_lower or
                "say" in response_lower or
                "dialogue" in response_lower
            )

            # Extract citations
            citation_markers = ResponseParser.extract_citations(response)
            chunk_ids = CitationMapper.map_citations(citation_markers, results)

            return AgentOutput(
                content=f"{responding_npc} will respond." if npc_responds else "Narrator will describe the scene.",
                citations=chunk_ids,
                reasoning=response,
                metadata={
                    "scene_plan": {
                        "npc_responds": npc_responds,
                        "responding_npc": responding_npc,
                        "next_scene": None,
                        "fallback_to_narrator": not npc_responds
                    },
                    "parse_error": True
                }
            )

    def _extract_npc_from_passages(self, results: List[RetrievalResult]) -> List[str]:
        """Extract NPC names from retrieved passages.

        Args:
            results: Retrieved chunks

        Returns:
            List of potential NPC names
        """
        all_text = " ".join([r.chunk_text for r in results])

        # Extract capitalized words
        potential_npcs = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', all_text)

        # Filter and count occurrences
        npc_counts = {}
        common_words = {'The', 'A', 'An', 'In', 'On', 'At', 'To', 'From', 'You', 'He', 'She', 'They', 'I'}

        for npc in potential_npcs:
            if npc not in common_words and len(npc) > 2:
                npc_counts[npc] = npc_counts.get(npc, 0) + 1

        # Sort by frequency
        sorted_npcs = sorted(npc_counts.items(), key=lambda x: x[1], reverse=True)

        return [npc for npc, count in sorted_npcs[:5]]  # Top 5

    def _should_scene_transition(self, command: str) -> bool:
        """Determine if player command indicates scene transition.

        Args:
            command: Player command

        Returns:
            True if scene transition detected
        """
        transition_keywords = ['go', 'move', 'walk', 'run', 'enter', 'leave', 'exit',
                             'travel', 'head', 'return', 'climb', 'descend', 'ascend']

        command_lower = command.lower()
        return any(keyword in command_lower for keyword in transition_keywords)

    def _fallback_to_narrator(self, error_msg: str) -> AgentOutput:
        """Create fallback output when planning fails.

        Args:
            error_msg: Error message

        Returns:
            Fallback AgentOutput
        """
        return AgentOutput(
            content="Narrator will describe the scene.",
            citations=[],
            reasoning=f"Scene planning failed: {error_msg}. Falling back to narrator.",
            metadata={
                "scene_plan": {
                    "npc_responds": False,
                    "responding_npc": None,
                    "next_scene": None,
                    "fallback_to_narrator": True
                },
                "error": True
            }
        )
