"""Comprehensive tests for all agent implementations."""

import pytest
from unittest.mock import Mock, MagicMock
from src.agents.narrator import NarratorAgent
from src.agents.rules_referee import RulesRefereeAgent, ValidationSeverity
from src.agents.scene_planner import ScenePlannerAgent
from src.agents.npc_manager import NPCManagerAgent
from src.agents.npc_persona_extractor import NPCPersonaExtractor
from src.core.base_agent import AgentContext, AgentOutput, RetrievalResult
from src.core.config import AgentConfig, LLMConfig, LLMProvider


@pytest.fixture
def mock_llm_config():
    """Create mock LLM config."""
    return AgentConfig(
        name="TestAgent",
        llm=LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="test-model",
            temperature=0.7,
            max_tokens=1000
        ),
        retrieval_top_k=5,
        enabled=True
    )


@pytest.fixture
def mock_retrieval_manager():
    """Create mock retrieval manager."""
    manager = Mock()
    manager.retrieve.return_value = [
        RetrievalResult(
            chunk_text="The tavern was dimly lit with wooden tables.",
            score=0.9,
            chunk_id="chunk_0",
            metadata={}
        ),
        RetrievalResult(
            chunk_text="Gandalf sat in the corner, smoking his pipe.",
            score=0.8,
            chunk_id="chunk_1",
            metadata={}
        ),
    ]
    return manager


@pytest.fixture
def sample_context():
    """Create sample agent context."""
    return AgentContext(
        player_command="look around the tavern",
        session_state={
            "current_scene": "tavern",
            "active_npcs": ["Gandalf"],
            "memory": []
        },
        retrieval_results=[],
        previous_turns=[]
    )


class TestNarratorAgent:
    """Test Narrator agent functionality."""

    def test_narrator_generates_description(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test narrator generates scene description."""
        # Setup mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = """DESCRIPTION: The tavern is dimly lit. You see wooden tables [1] and a wizard in the corner [2].
REASONING: Based on passages [1] and [2] describing the tavern setting."""

        narrator = NarratorAgent(mock_llm_config, mock_retrieval_manager)
        narrator.llm_client = mock_llm

        output = narrator.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert len(output.content) > 0
        assert "tavern" in output.content.lower()
        assert len(output.citations) > 0
        assert output.reasoning
        assert "scene" in output.metadata

    def test_narrator_handles_no_retrieval_results(self, mock_llm_config, sample_context):
        """Test narrator handles no retrieval results."""
        mock_retrieval_manager = Mock()
        mock_retrieval_manager.retrieve.return_value = []

        mock_llm = Mock()

        narrator = NarratorAgent(mock_llm_config, mock_retrieval_manager)
        narrator.llm_client = mock_llm

        output = narrator.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert "fallback" in output.metadata
        assert output.metadata["fallback"] == True

    def test_narrator_extracts_npcs(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test narrator extracts NPC names."""
        mock_llm = Mock()
        mock_llm.generate.return_value = """DESCRIPTION: Gandalf the wizard and Frodo the hobbit are here.
REASONING: From passages about characters."""

        narrator = NarratorAgent(mock_llm_config, mock_retrieval_manager)
        narrator.llm_client = mock_llm

        output = narrator.process(sample_context)

        assert "npcs_mentioned" in output.metadata
        # Should extract at least some NPC names
        assert len(output.metadata["npcs_mentioned"]) >= 0

    def test_narrator_handles_llm_error(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test narrator handles LLM errors gracefully."""
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM error")

        narrator = NarratorAgent(mock_llm_config, mock_retrieval_manager)
        narrator.llm_client = mock_llm

        output = narrator.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert "error" in output.metadata
        assert output.metadata["error"] == True


class TestRulesRefereeAgent:
    """Test Rules Referee agent functionality."""

    def test_rules_referee_approves_valid_action(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test rules referee approves valid action."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "approved": true,
            "reason": "Action is consistent with passages [1]",
            "severity": "none",
            "suggested_alternative": null
        }'''

        referee = RulesRefereeAgent(mock_llm_config, mock_retrieval_manager)
        referee.llm_client = mock_llm

        output = referee.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert "validation_result" in output.metadata
        assert output.metadata["validation_result"]["approved"] == True
        assert output.metadata["validation_result"]["severity"] == ValidationSeverity.NONE.value

    def test_rules_referee_rejects_invalid_action(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test rules referee rejects contradictory action."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "approved": false,
            "reason": "Action contradicts passage [1] which states dragons cannot fly",
            "severity": "blocking",
            "suggested_alternative": "Try riding the dragon on the ground"
        }'''

        referee = RulesRefereeAgent(mock_llm_config, mock_retrieval_manager)
        referee.llm_client = mock_llm

        sample_context.player_command = "fly on the dragon"
        output = referee.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert output.metadata["validation_result"]["approved"] == False
        assert output.metadata["validation_result"]["severity"] == ValidationSeverity.BLOCKING.value
        assert "rejected" in output.content.lower()

    def test_rules_referee_handles_no_retrieval(self, mock_llm_config, sample_context):
        """Test rules referee approves when no retrieval results."""
        mock_retrieval_manager = Mock()
        mock_retrieval_manager.retrieve.return_value = []

        mock_llm = Mock()

        referee = RulesRefereeAgent(mock_llm_config, mock_retrieval_manager)
        referee.llm_client = mock_llm

        output = referee.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert output.metadata["validation_result"]["approved"] == True

    def test_rules_referee_handles_json_parse_error(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test rules referee handles malformed JSON."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "This is not valid JSON at all!"

        referee = RulesRefereeAgent(mock_llm_config, mock_retrieval_manager)
        referee.llm_client = mock_llm

        output = referee.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert "validation_result" in output.metadata
        assert "parse_error" in output.metadata


class TestScenePlannerAgent:
    """Test Scene Planner agent functionality."""

    def test_scene_planner_triggers_npc_response(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test scene planner triggers NPC response."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "npc_responds": true,
            "responding_npc": "Gandalf",
            "next_scene": null,
            "reasoning": "Player is talking to Gandalf [1]",
            "fallback_to_narrator": false
        }'''

        planner = ScenePlannerAgent(mock_llm_config, mock_retrieval_manager)
        planner.llm_client = mock_llm

        sample_context.player_command = "talk to Gandalf"
        output = planner.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert "scene_plan" in output.metadata
        scene_plan = output.metadata["scene_plan"]
        assert scene_plan["npc_responds"] == True
        assert scene_plan["responding_npc"] == "Gandalf"
        assert scene_plan["fallback_to_narrator"] == False

    def test_scene_planner_fallback_to_narrator(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test scene planner falls back to narrator."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "npc_responds": false,
            "responding_npc": null,
            "next_scene": null,
            "reasoning": "No NPC interaction detected",
            "fallback_to_narrator": true
        }'''

        planner = ScenePlannerAgent(mock_llm_config, mock_retrieval_manager)
        planner.llm_client = mock_llm

        output = planner.process(sample_context)

        assert output.metadata["scene_plan"]["fallback_to_narrator"] == True
        assert output.metadata["scene_plan"]["npc_responds"] == False

    def test_scene_planner_detects_scene_transition(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test scene planner detects scene transition."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "npc_responds": false,
            "responding_npc": null,
            "next_scene": "forest",
            "reasoning": "Player is moving to the forest",
            "fallback_to_narrator": true
        }'''

        planner = ScenePlannerAgent(mock_llm_config, mock_retrieval_manager)
        planner.llm_client = mock_llm

        sample_context.player_command = "go to the forest"
        output = planner.process(sample_context)

        assert output.metadata["scene_plan"]["next_scene"] == "forest"


class TestNPCPersonaExtractor:
    """Test NPC Persona Extractor functionality."""

    def test_persona_extraction(self):
        """Test persona extraction from chunks."""
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "speaking_style": "wise and cryptic",
            "personality_traits": ["intelligent", "mysterious", "patient"],
            "background": "An ancient wizard with great knowledge",
            "knowledge_areas": ["magic", "history", "lore"],
            "dialogue_examples": ["You shall not pass!", "A wizard is never late"],
            "citations": ["1", "2"]
        }'''

        extractor = NPCPersonaExtractor(mock_llm)

        chunks = [
            RetrievalResult(
                chunk_text="Gandalf is a wise wizard who speaks cryptically.",
                score=0.9,
                chunk_id="chunk_0"
            ),
            RetrievalResult(
                chunk_text="He has vast knowledge of magic and history.",
                score=0.8,
                chunk_id="chunk_1"
            ),
        ]

        persona = extractor.extract_persona("Gandalf", chunks)

        assert persona["speaking_style"] == "wise and cryptic"
        assert len(persona["personality_traits"]) > 0
        assert "intelligent" in persona["personality_traits"]
        assert len(persona["citations"]) > 0

    def test_persona_extraction_handles_empty_chunks(self):
        """Test persona extraction with no chunks."""
        mock_llm = Mock()

        extractor = NPCPersonaExtractor(mock_llm)

        persona = extractor.extract_persona("Unknown", [])

        # Should return default persona
        assert "speaking_style" in persona
        assert "personality_traits" in persona
        assert len(persona["personality_traits"]) > 0

    def test_persona_extraction_handles_json_error(self):
        """Test persona extraction handles malformed JSON."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "Not valid JSON!"

        extractor = NPCPersonaExtractor(mock_llm)

        chunks = [
            RetrievalResult(
                chunk_text="Some text about character.",
                score=0.9,
                chunk_id="chunk_0"
            ),
        ]

        persona = extractor.extract_persona("Character", chunks)

        # Should still return a persona (fallback)
        assert "speaking_style" in persona
        assert "personality_traits" in persona

    def test_format_persona_for_prompt(self):
        """Test formatting persona for prompt."""
        persona = {
            "speaking_style": "formal",
            "personality_traits": ["wise", "kind"],
            "background": "A teacher",
            "knowledge_areas": ["history", "literature"],
            "dialogue_examples": ["Hello student", "Learn well"]
        }

        extractor = NPCPersonaExtractor(Mock())
        formatted = extractor.format_persona_for_prompt(persona)

        assert "Speaking Style: formal" in formatted
        assert "wise" in formatted
        assert "A teacher" in formatted


class TestNPCManagerAgent:
    """Test NPC Manager agent functionality."""

    def test_npc_manager_generates_dialogue(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test NPC manager generates dialogue."""
        mock_llm = Mock()
        # First call for persona extraction
        mock_llm.generate.side_effect = [
            '''{
                "speaking_style": "wise",
                "personality_traits": ["intelligent"],
                "background": "A wizard",
                "knowledge_areas": ["magic"],
                "dialogue_examples": [],
                "citations": ["1"]
            }''',
            # Second call for dialogue generation
            """DIALOGUE: "Greetings, traveler. What brings you to this place?" [1]
REASONING: Response based on character's wise personality."""
        ]

        manager = NPCManagerAgent(mock_llm_config, mock_retrieval_manager)
        manager.llm_client = mock_llm

        # Set responding NPC in context
        sample_context.session_state["responding_npc"] = "Gandalf"

        output = manager.process(sample_context)

        assert isinstance(output, AgentOutput)
        assert len(output.content) > 0
        assert "npc_name" in output.metadata
        assert output.metadata["npc_name"] == "Gandalf"

    def test_npc_manager_uses_cached_persona(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test NPC manager uses cached persona."""
        mock_llm = Mock()
        # Only one call for dialogue generation (persona already cached)
        mock_llm.generate.return_value = """DIALOGUE: "Hello again!"
REASONING: Continued conversation."""

        manager = NPCManagerAgent(mock_llm_config, mock_retrieval_manager)
        manager.llm_client = mock_llm

        # Pre-cache persona
        cached_persona = {
            "speaking_style": "friendly",
            "personality_traits": ["helpful"],
            "background": "A guide",
            "knowledge_areas": ["local area"],
            "dialogue_examples": [],
            "citations": []
        }
        sample_context.session_state["npc_persona_Gandalf"] = cached_persona
        sample_context.session_state["responding_npc"] = "Gandalf"

        output = manager.process(sample_context)

        assert output.metadata["persona_cached"] == True

    def test_npc_manager_handles_no_responding_npc(self, mock_llm_config, mock_retrieval_manager, sample_context):
        """Test NPC manager handles missing responding NPC."""
        mock_llm = Mock()

        manager = NPCManagerAgent(mock_llm_config, mock_retrieval_manager)
        manager.llm_client = mock_llm

        # No responding NPC set
        sample_context.session_state.pop("responding_npc", None)

        output = manager.process(sample_context)

        assert "fallback" in output.metadata
        assert output.metadata["fallback"] == True


class TestAgentIntegration:
    """Test integration between agents."""

    def test_narrator_to_scene_planner_flow(
        self,
        mock_llm_config,
        mock_retrieval_manager,
        sample_context
    ):
        """Test data flow from Narrator to ScenePlanner."""
        # Setup narrator
        narrator_llm = Mock()
        narrator_llm.generate.return_value = """DESCRIPTION: You are in a tavern. Gandalf is here.
REASONING: Based on passages."""

        narrator = NarratorAgent(mock_llm_config, mock_retrieval_manager)
        narrator.llm_client = narrator_llm

        # Generate narrator output
        narrator_output = narrator.process(sample_context)

        # Update context with narrator output
        sample_context.session_state["narrator_output"] = narrator_output.content

        # Setup scene planner
        planner_llm = Mock()
        planner_llm.generate.return_value = '''{
            "npc_responds": true,
            "responding_npc": "Gandalf",
            "next_scene": null,
            "reasoning": "Gandalf is mentioned in narrator output",
            "fallback_to_narrator": false
        }'''

        planner = ScenePlannerAgent(mock_llm_config, mock_retrieval_manager)
        planner.llm_client = planner_llm

        # Generate scene plan
        planner_output = planner.process(sample_context)

        # Verify flow
        assert planner_output.metadata["scene_plan"]["responding_npc"] == "Gandalf"
        assert planner_output.metadata["scene_plan"]["npc_responds"] == True
