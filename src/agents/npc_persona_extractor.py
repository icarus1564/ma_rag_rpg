"""NPC persona extractor for just-in-time character profile extraction."""

import re
from typing import Dict, Any, List
from ..core.base_agent import RetrievalResult, LLMClient
from .prompt_templates import PromptTemplateManager
from .response_parsers import ResponseParser
from .citation_utils import CitationMapper
from ..utils.logging import get_logger

logger = get_logger(__name__)


class NPCPersonaExtractor:
    """Extracts NPC persona from corpus chunks."""

    def __init__(self, llm_client: LLMClient):
        """Initialize persona extractor.

        Args:
            llm_client: LLM client for persona extraction
        """
        self.llm_client = llm_client

    def extract_persona(
        self,
        npc_name: str,
        chunks: List[RetrievalResult]
    ) -> Dict[str, Any]:
        """Extract persona from retrieved chunks.

        Args:
            npc_name: Name of the NPC
            chunks: Retrieved chunks about the NPC

        Returns:
            Dictionary with persona information:
            {
                "speaking_style": "...",
                "personality_traits": ["trait1", "trait2"],
                "background": "...",
                "knowledge_areas": ["area1", "area2"],
                "dialogue_examples": ["example1", "example2"],
                "citations": ["chunk_1", "chunk_3"]
            }
        """
        if not chunks:
            logger.warning("No chunks provided for persona extraction", npc_name=npc_name)
            return self._default_persona(npc_name)

        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(npc_name, chunks)

            # Use LLM to extract structured persona
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_extraction_system_prompt()
            )

            # Parse JSON response
            persona = self._parse_persona_response(response, chunks)

            logger.info("Persona extracted successfully",
                       npc_name=npc_name,
                       traits_count=len(persona.get("personality_traits", [])),
                       citations_count=len(persona.get("citations", [])))

            return persona

        except Exception as e:
            logger.error("Persona extraction failed", npc_name=npc_name, error=str(e))
            return self._default_persona(npc_name)

    def _build_extraction_prompt(self, npc_name: str, chunks: List[RetrievalResult]) -> str:
        """Build persona extraction prompt.

        Args:
            npc_name: Name of the NPC
            chunks: Retrieved chunks

        Returns:
            Formatted prompt string
        """
        # Format chunks with citations
        retrieved_chunks = CitationMapper.format_chunks_for_prompt(chunks, include_scores=False)

        # Use template
        return PromptTemplateManager.format_template(
            "npc_persona_extraction_user",
            npc_name=npc_name,
            retrieved_chunks=retrieved_chunks
        )

    def _get_extraction_system_prompt(self) -> str:
        """Get system prompt for persona extraction.

        Returns:
            System prompt string
        """
        return PromptTemplateManager.get_template("npc_persona_extraction_system")

    def _parse_persona_response(self, response: str, chunks: List[RetrievalResult]) -> Dict[str, Any]:
        """Parse LLM response into persona dictionary.

        Args:
            response: Raw LLM response
            chunks: Retrieved chunks used

        Returns:
            Parsed persona dictionary
        """
        try:
            # Parse JSON response
            persona_data = ResponseParser.parse_json_response(response)

            # Extract and validate fields
            speaking_style = persona_data.get("speaking_style", "neutral")
            personality_traits = persona_data.get("personality_traits", [])
            background = persona_data.get("background", "Unknown background")
            knowledge_areas = persona_data.get("knowledge_areas", [])
            dialogue_examples = persona_data.get("dialogue_examples", [])
            citation_markers = persona_data.get("citations", [])

            # Map citations to chunk IDs
            if citation_markers:
                # Convert markers to strings if they're integers
                citation_markers = [str(m) for m in citation_markers]
                chunk_ids = CitationMapper.map_citations(citation_markers, chunks)
            else:
                # If no citations provided, use all chunks
                chunk_ids = CitationMapper.extract_chunk_ids(chunks)

            # Ensure lists are actually lists
            if not isinstance(personality_traits, list):
                personality_traits = [str(personality_traits)]
            if not isinstance(knowledge_areas, list):
                knowledge_areas = [str(knowledge_areas)]
            if not isinstance(dialogue_examples, list):
                dialogue_examples = [str(dialogue_examples)]

            return {
                "speaking_style": speaking_style,
                "personality_traits": personality_traits[:5],  # Limit to 5
                "background": background,
                "knowledge_areas": knowledge_areas[:5],  # Limit to 5
                "dialogue_examples": dialogue_examples[:3],  # Limit to 3
                "citations": chunk_ids
            }

        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse persona JSON", error=str(e))

            # Fallback: Try to extract information from text
            return self._extract_persona_from_text(response, chunks)

    def _extract_persona_from_text(self, text: str, chunks: List[RetrievalResult]) -> Dict[str, Any]:
        """Extract persona information from unstructured text.

        Args:
            text: Response text
            chunks: Retrieved chunks

        Returns:
            Extracted persona dictionary
        """
        # Extract speaking style
        speaking_style_match = re.search(r'speaking style[:\s]+([^.]+)', text, re.IGNORECASE)
        speaking_style = speaking_style_match.group(1).strip() if speaking_style_match else "neutral"

        # Extract traits (look for lists or comma-separated items)
        traits_match = re.search(r'personality trait[s]*[:\s]+([^.]+)', text, re.IGNORECASE)
        if traits_match:
            traits_text = traits_match.group(1)
            personality_traits = [t.strip() for t in re.split(r'[,;]', traits_text) if t.strip()]
        else:
            personality_traits = ["mysterious"]

        # Extract background
        background_match = re.search(r'background[:\s]+([^.]+(?:\.[^.]+)*)', text, re.IGNORECASE)
        background = background_match.group(1).strip() if background_match else "Unknown background"

        # Extract citations
        citation_markers = ResponseParser.extract_citations(text)
        chunk_ids = CitationMapper.map_citations(citation_markers, chunks) if citation_markers else CitationMapper.extract_chunk_ids(chunks)

        return {
            "speaking_style": speaking_style,
            "personality_traits": personality_traits[:5],
            "background": background,
            "knowledge_areas": ["general"],
            "dialogue_examples": [],
            "citations": chunk_ids
        }

    def _default_persona(self, npc_name: str) -> Dict[str, Any]:
        """Generate default persona when extraction fails.

        Args:
            npc_name: Name of the NPC

        Returns:
            Default persona dictionary
        """
        return {
            "speaking_style": "neutral and polite",
            "personality_traits": ["mysterious", "knowledgeable"],
            "background": f"{npc_name} is a character in this story.",
            "knowledge_areas": ["general knowledge"],
            "dialogue_examples": [],
            "citations": []
        }

    def format_persona_for_prompt(self, persona: Dict[str, Any]) -> str:
        """Format persona dictionary for use in prompts.

        Args:
            persona: Persona dictionary

        Returns:
            Formatted persona string
        """
        parts = []

        if persona.get("speaking_style"):
            parts.append(f"Speaking Style: {persona['speaking_style']}")

        if persona.get("personality_traits"):
            traits = ", ".join(persona["personality_traits"])
            parts.append(f"Personality Traits: {traits}")

        if persona.get("background"):
            parts.append(f"Background: {persona['background']}")

        if persona.get("knowledge_areas"):
            knowledge = ", ".join(persona["knowledge_areas"])
            parts.append(f"Knowledge Areas: {knowledge}")

        if persona.get("dialogue_examples"):
            examples = "\n".join([f"  - \"{ex}\"" for ex in persona["dialogue_examples"]])
            parts.append(f"Dialogue Examples:\n{examples}")

        return "\n\n".join(parts) if parts else "No specific persona information available."
