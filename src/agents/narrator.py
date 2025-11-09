"""Narrator agent for generating scene descriptions."""

import re
from typing import List, Optional
from ..core.base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from ..core.config import AgentConfig
from ..core.retrieval_manager import RetrievalManager
from .prompt_templates import PromptTemplateManager
from .response_parsers import ResponseParser
from .citation_utils import CitationMapper
from ..utils.debug_logging import debug_log_method


class NarratorAgent(BaseAgent):
    """Generates immersive scene descriptions grounded in corpus."""

    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        """Initialize Narrator agent.

        Args:
            config: Agent configuration
            retrieval_manager: Retrieval manager for RAG operations
        """
        super().__init__(config)
        self.retrieval_manager = retrieval_manager

    @debug_log_method
    def process(self, context: AgentContext) -> AgentOutput:
        """Process context and return scene description.

        Args:
            context: Agent context with player command and session state

        Returns:
            AgentOutput with scene description and citations
        """
        try:
            # 1. Build retrieval query
            query = self._build_query(context)
            self.logger.debug("Built retrieval query", query=query[:100])

            # 2. Retrieve relevant context
            retrieval_results = self.retrieval_manager.retrieve(
                query=query,
                top_k=self.config.retrieval_top_k,
                agent_name=self.config.name
            )

            if not retrieval_results:
                self.logger.warning("No retrieval results found")
                return self._fallback_response(context)

            # 3. Build prompt
            prompt = self._build_prompt(context, retrieval_results)

            # 4. Generate output
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt()
            )

            # 5. Parse response and extract citations
            output = self._parse_response(response, retrieval_results, context)

            self.logger.info("Narrator output generated",
                           content_length=len(output.content),
                           citations_count=len(output.citations))

            return output

        except Exception as e:
            self.logger.error("Narrator processing failed", error=str(e), exc_info=True)
            return AgentOutput(
                content=f"Error generating scene description: {str(e)}",
                citations=[],
                reasoning="LLM generation failed",
                metadata={"error": True}
            )

    def _build_query(self, context: AgentContext) -> str:
        """Build retrieval query from context.

        Args:
            context: Agent context

        Returns:
            Query string for retrieval
        """
        query_parts = []

        # Add current scene if available
        current_scene = context.session_state.get("current_scene", "")
        if current_scene:
            query_parts.append(f"location {current_scene}")

        # Add player command
        if context.player_command:
            query_parts.append(f"scene {context.player_command}")

        # Extract keywords from previous narrator output
        if context.previous_turns:
            last_turn = context.previous_turns[-1] if context.previous_turns else None
            if last_turn and "outputs" in last_turn:
                narrator_output = last_turn["outputs"].get("narrator", {})
                if isinstance(narrator_output, dict) and "content" in narrator_output:
                    # Extract location/NPC names from previous description
                    prev_content = narrator_output["content"]
                    # Simple keyword extraction (could be enhanced)
                    keywords = self._extract_keywords(prev_content)
                    if keywords:
                        query_parts.extend(keywords[:2])  # Add top 2 keywords

        # Default query if nothing specific
        if not query_parts:
            return "scene description location setting"

        return " ".join(query_parts)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords
        """
        # Remove common words and citations
        text = re.sub(r'\[\d+\]', '', text)  # Remove citations
        words = text.lower().split()

        # Simple stopword list
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'can', 'it', 'you', 'he',
                    'she', 'they', 'we', 'i', 'this', 'that', 'these', 'those'}

        # Filter and return unique keywords
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return list(set(keywords))[:5]  # Return unique keywords

    def _build_prompt(self, context: AgentContext, results: List[RetrievalResult]) -> str:
        """Build LLM prompt from context and retrieval results.

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

        # Format prompt using template
        return PromptTemplateManager.format_template(
            "narrator_user",
            retrieved_chunks=retrieved_chunks,
            player_command=context.player_command,
            current_scene=current_scene,
            memory_context=memory_context
        )

    def _build_memory_context(self, context: AgentContext) -> str:
        """Build memory context from previous turns.

        Args:
            context: Agent context

        Returns:
            Formatted memory context string
        """
        if not context.previous_turns:
            return "This is the beginning of the story."

        # Get last 2 turns for context
        recent_turns = context.previous_turns[-2:] if len(context.previous_turns) >= 2 else context.previous_turns

        context_parts = []
        for turn in recent_turns:
            turn_num = turn.get("turn_number", "?")
            player_cmd = turn.get("player_command", "")
            outputs = turn.get("outputs", {})

            if player_cmd:
                context_parts.append(f"Turn {turn_num}: Player: {player_cmd}")

            # Add narrator output if available
            if "narrator" in outputs and isinstance(outputs["narrator"], dict):
                narrator_content = outputs["narrator"].get("content", "")
                if narrator_content:
                    # Truncate to avoid too much context
                    short_content = narrator_content[:150] + "..." if len(narrator_content) > 150 else narrator_content
                    context_parts.append(f"  Narrator: {short_content}")

        return "\n".join(context_parts) if context_parts else "This is the beginning of the story."

    def _get_system_prompt(self) -> str:
        """Get system prompt for narrator.

        Returns:
            System prompt string
        """
        return PromptTemplateManager.get_template("narrator_system")

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
        # Parse sectioned response
        sections = ResponseParser.parse_sectioned_response(response)

        # Extract description and reasoning
        description = sections.get("description", response)
        reasoning = sections.get("reasoning", "")

        # If no sections found, use full response as description
        if not sections:
            description = response
            reasoning = "Direct narration"

        # Extract citations
        citation_markers = ResponseParser.extract_citations(description + " " + reasoning)
        chunk_ids = CitationMapper.map_citations(citation_markers, results)

        # Extract NPCs and locations mentioned
        npcs_mentioned = self._extract_npcs(description)
        locations_mentioned = self._extract_locations(description)

        # Determine scene name
        scene_name = self._determine_scene_name(description, context)

        return AgentOutput(
            content=description,
            citations=chunk_ids,
            reasoning=reasoning,
            metadata={
                "scene": scene_name,
                "npcs_mentioned": npcs_mentioned,
                "locations_mentioned": locations_mentioned,
                "keywords": self._extract_keywords(description)
            }
        )

    def _extract_npcs(self, text: str) -> List[str]:
        """Extract NPC names from description.

        Args:
            text: Description text

        Returns:
            List of NPC names found
        """
        # Simple heuristic: capitalized words that appear multiple times
        # or are preceded by character indicators
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        # Filter out common non-NPC capitalized words
        non_npcs = {'The', 'A', 'An', 'In', 'On', 'At', 'To', 'From', 'You', 'He', 'She', 'They'}

        npcs = []
        for word in words:
            if word not in non_npcs and len(word) > 2:
                npcs.append(word)

        # Return unique NPCs
        return list(set(npcs))[:5]  # Limit to 5

    def _extract_locations(self, text: str) -> List[str]:
        """Extract location names from description.

        Args:
            text: Description text

        Returns:
            List of location names found
        """
        # Look for phrases that indicate locations
        location_patterns = [
            r'in (?:the )?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'at (?:the )?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:room|hall|chamber|area|place) (?:called|named) ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]

        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            locations.extend(matches)

        return list(set(locations))[:3]  # Limit to 3

    def _determine_scene_name(self, description: str, context: AgentContext) -> str:
        """Determine scene name from description and context.

        Args:
            description: Scene description
            context: Agent context

        Returns:
            Scene name
        """
        # Check if scene is already set
        current_scene = context.session_state.get("current_scene")
        if current_scene:
            return current_scene

        # Try to extract from locations
        locations = self._extract_locations(description)
        if locations:
            return locations[0]

        # Default scene name
        return "Unknown Location"

    def _fallback_response(self, context: AgentContext) -> AgentOutput:
        """Generate fallback response when no retrieval results.

        Args:
            context: Agent context

        Returns:
            Fallback AgentOutput
        """
        return AgentOutput(
            content="You find yourself in an uncertain place. The details are unclear.",
            citations=[],
            reasoning="No relevant passages found in corpus",
            metadata={
                "scene": context.session_state.get("current_scene", "Unknown"),
                "npcs_mentioned": [],
                "locations_mentioned": [],
                "keywords": [],
                "fallback": True
            }
        )
