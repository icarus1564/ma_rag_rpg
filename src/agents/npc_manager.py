"""NPC manager agent for generating character dialogue."""

from typing import List, Optional, Dict, Any
from ..core.base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from ..core.config import AgentConfig
from ..core.retrieval_manager import RetrievalManager
from .prompt_templates import PromptTemplateManager
from .response_parsers import ResponseParser
from .citation_utils import CitationMapper
from .npc_persona_extractor import NPCPersonaExtractor


class NPCManagerAgent(BaseAgent):
    """Generates NPC dialogue with just-in-time persona extraction."""

    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        """Initialize NPCManager agent.

        Args:
            config: Agent configuration
            retrieval_manager: Retrieval manager for RAG operations
        """
        super().__init__(config)
        self.retrieval_manager = retrieval_manager
        self.persona_extractor = NPCPersonaExtractor(self.llm_client)

    def process(self, context: AgentContext) -> AgentOutput:
        """Process context and generate NPC dialogue.

        Args:
            context: Agent context with player command and session state

        Returns:
            AgentOutput with NPC dialogue
        """
        try:
            # 1. Determine which NPC should respond
            npc_name = self._get_responding_npc(context)

            if not npc_name:
                self.logger.warning("No responding NPC determined")
                return self._fallback_response("No NPC available to respond")

            self.logger.debug("Generating dialogue for NPC", npc_name=npc_name)

            # 2. Get or extract persona
            persona = self._get_or_extract_persona(npc_name, context)

            # 3. Retrieve dialogue context
            dialogue_context = self._retrieve_dialogue_context(npc_name, context)

            # 4. Build prompt
            prompt = self._build_prompt(npc_name, persona, context, dialogue_context)

            # 5. Generate dialogue
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt(npc_name, persona)
            )

            # 6. Parse response
            output = self._parse_response(response, dialogue_context, npc_name, persona, context)

            self.logger.info("NPC dialogue generated",
                           npc_name=npc_name,
                           dialogue_length=len(output.content),
                           citations_count=len(output.citations))

            return output

        except Exception as e:
            self.logger.error("NPC dialogue generation failed", error=str(e), exc_info=True)
            return AgentOutput(
                content=f"Error generating dialogue: {str(e)}",
                citations=[],
                reasoning="LLM generation failed",
                metadata={"error": True}
            )

    def _get_responding_npc(self, context: AgentContext) -> Optional[str]:
        """Determine which NPC should respond.

        Args:
            context: Agent context

        Returns:
            NPC name or None
        """
        # Check if scene planner specified an NPC
        scene_plan = context.session_state.get("scene_planner_output", {})
        if isinstance(scene_plan, dict):
            scene_plan_metadata = scene_plan.get("metadata", {})
            if isinstance(scene_plan_metadata, dict):
                plan = scene_plan_metadata.get("scene_plan", {})
                if isinstance(plan, dict):
                    responding_npc = plan.get("responding_npc")
                    if responding_npc:
                        return responding_npc

        # Fallback: check session state directly
        responding_npc = context.session_state.get("responding_npc")
        if responding_npc:
            return responding_npc

        # No NPC determined
        return None

    def _get_or_extract_persona(self, npc_name: str, context: AgentContext) -> Dict[str, Any]:
        """Get cached persona or extract just-in-time.

        Args:
            npc_name: Name of the NPC
            context: Agent context

        Returns:
            Persona dictionary
        """
        # Check cache in session state
        persona_cache_key = f"npc_persona_{npc_name}"
        if persona_cache_key in context.session_state:
            self.logger.debug("Using cached persona", npc_name=npc_name)
            return context.session_state[persona_cache_key]

        # Extract persona
        self.logger.info("Extracting persona for NPC", npc_name=npc_name)
        persona_chunks = self._retrieve_persona(npc_name, context)
        persona = self.persona_extractor.extract_persona(npc_name, persona_chunks)

        # Cache for session (Note: This modifies session state, which is acceptable for caching)
        context.session_state[persona_cache_key] = persona

        return persona

    def _retrieve_persona(self, npc_name: str, context: AgentContext) -> List[RetrievalResult]:
        """Retrieve chunks for persona extraction.

        Args:
            npc_name: Name of the NPC
            context: Agent context

        Returns:
            List of retrieval results
        """
        query = f"{npc_name} character personality speaking style dialogue"

        return self.retrieval_manager.retrieve(
            query=query,
            top_k=10,  # More chunks for comprehensive persona
            agent_name=f"{self.config.name}_persona"
        )

    def _retrieve_dialogue_context(self, npc_name: str, context: AgentContext) -> List[RetrievalResult]:
        """Retrieve chunks for dialogue generation.

        Args:
            npc_name: Name of the NPC
            context: Agent context

        Returns:
            List of retrieval results
        """
        query = f"{npc_name} dialogue conversation {context.player_command}"

        return self.retrieval_manager.retrieve(
            query=query,
            top_k=self.config.retrieval_top_k,
            agent_name=self.config.name
        )

    def _build_prompt(
        self,
        npc_name: str,
        persona: Dict[str, Any],
        context: AgentContext,
        dialogue_chunks: List[RetrievalResult]
    ) -> str:
        """Build LLM prompt for dialogue generation.

        Args:
            npc_name: Name of the NPC
            persona: NPC persona dictionary
            context: Agent context
            dialogue_chunks: Retrieved chunks for dialogue context

        Returns:
            Formatted prompt string
        """
        # Format dialogue context chunks
        retrieved_chunks = CitationMapper.format_chunks_for_prompt(dialogue_chunks, include_scores=False)

        # Get current scene
        current_scene = context.session_state.get("current_scene", "Unknown")

        # Build memory context
        memory_context = self._build_memory_context(context)

        # Use template
        return PromptTemplateManager.format_template(
            "npc_manager_user",
            retrieved_chunks=retrieved_chunks,
            player_command=context.player_command,
            current_scene=current_scene,
            memory_context=memory_context,
            npc_name=npc_name
        )

    def _build_memory_context(self, context: AgentContext) -> str:
        """Build memory context from previous turns.

        Args:
            context: Agent context

        Returns:
            Formatted memory context string
        """
        if not context.previous_turns:
            return "This is the beginning of the conversation."

        # Get last 2-3 turns
        recent_turns = context.previous_turns[-3:] if len(context.previous_turns) >= 3 else context.previous_turns

        context_parts = []
        for turn in recent_turns:
            turn_num = turn.get("turn_number", "?")
            player_cmd = turn.get("player_command", "")
            outputs = turn.get("outputs", {})

            if player_cmd:
                context_parts.append(f"Turn {turn_num}: Player: {player_cmd}")

            # Add NPC response if available
            if "npc_manager" in outputs and isinstance(outputs["npc_manager"], dict):
                npc_content = outputs["npc_manager"].get("content", "")
                if npc_content:
                    short_content = npc_content[:150] + "..." if len(npc_content) > 150 else npc_content
                    context_parts.append(f"  NPC: {short_content}")

        return "\n".join(context_parts) if context_parts else "This is the beginning of the conversation."

    def _get_system_prompt(self, npc_name: str, persona: Dict[str, Any]) -> str:
        """Get system prompt for NPC dialogue.

        Args:
            npc_name: Name of the NPC
            persona: NPC persona dictionary

        Returns:
            System prompt string
        """
        # Format persona for prompt
        persona_text = self.persona_extractor.format_persona_for_prompt(persona)

        return PromptTemplateManager.format_template(
            "npc_manager_system",
            npc_name=npc_name,
            persona=persona_text
        )

    def _parse_response(
        self,
        response: str,
        dialogue_chunks: List[RetrievalResult],
        npc_name: str,
        persona: Dict[str, Any],
        context: AgentContext
    ) -> AgentOutput:
        """Parse LLM response into AgentOutput.

        Args:
            response: Raw LLM response
            dialogue_chunks: Retrieved chunks used
            npc_name: Name of the NPC
            persona: NPC persona used
            context: Agent context

        Returns:
            Parsed AgentOutput
        """
        # Parse sectioned response
        sections = ResponseParser.parse_sectioned_response(response)

        # Extract dialogue and reasoning
        dialogue = sections.get("dialogue", response)
        reasoning = sections.get("reasoning", "")

        # If no sections found, use full response as dialogue
        if not sections:
            dialogue = response
            reasoning = f"Response as {npc_name}"

        # Extract citations
        citation_markers = ResponseParser.extract_citations(dialogue + " " + reasoning)
        chunk_ids = CitationMapper.map_citations(citation_markers, dialogue_chunks)

        # Include persona citations
        persona_citations = persona.get("citations", [])
        all_citations = list(set(chunk_ids + persona_citations))  # Remove duplicates

        return AgentOutput(
            content=dialogue,
            citations=all_citations,
            reasoning=reasoning,
            metadata={
                "npc_name": npc_name,
                "persona_used": {
                    "speaking_style": persona.get("speaking_style"),
                    "traits": persona.get("personality_traits", [])
                },
                "persona_cached": f"npc_persona_{npc_name}" in context.session_state,
                "dialogue_context_chunks": len(dialogue_chunks)
            }
        )

    def _fallback_response(self, reason: str) -> AgentOutput:
        """Generate fallback response when dialogue generation fails.

        Args:
            reason: Reason for fallback

        Returns:
            Fallback AgentOutput
        """
        return AgentOutput(
            content="[Character remains silent]",
            citations=[],
            reasoning=reason,
            metadata={
                "npc_name": None,
                "fallback": True
            }
        )
