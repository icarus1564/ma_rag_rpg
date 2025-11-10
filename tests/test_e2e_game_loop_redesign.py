"""End-to-end tests for the refactored game loop with mocked LLM responses.

These tests validate all decision paths through the redesigned game loop:
1. Happy path - successful NPC interaction
2. User disqualification - invalid user prompt
3. Agent disqualification - agent response contradicts corpus (player wins)
4. Scene description path - narrator-only interaction
5. Persona caching - repeated NPC interaction
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.core.game_loop import (
    GameLoop,
    TurnPhase,
    TurnProgress,
    TurnResult,
    ValidationResult,
    ScenePlanOutput,
)
from src.core.orchestrator import GameOrchestrator
from src.core.session import GameSession
from src.core.config import SessionConfig
from src.core.base_agent import AgentOutput, RetrievalResult


class TestE2EGameLoopRedesign:
    """End-to-end tests for game loop with correct orchestration flow."""

    @pytest.fixture
    def mock_retrieval_manager(self):
        """Create mock retrieval manager."""
        manager = Mock()
        manager.retrieve.return_value = [
            RetrievalResult(
                chunk_id="chunk_1",
                chunk_text="Gandalf is a wise wizard who guides the Fellowship.",
                score=0.9,
                metadata={"source": "lotr"}
            ),
            RetrievalResult(
                chunk_id="chunk_2",
                chunk_text="The Shire is a peaceful land of hobbits.",
                score=0.85,
                metadata={"source": "lotr"}
            ),
        ]
        return manager

    @pytest.fixture
    def game_session(self):
        """Create a test game session."""
        config = SessionConfig(
            memory_window_size=5,
            max_tokens=1000,
            sliding_window=True,
            session_ttl_seconds=3600
        )
        return GameSession(session_id="test-session-e2e", config=config)

    def create_mock_agent(self, name, response_fn):
        """Create a mock agent with custom response function."""
        agent = Mock()
        agent.config.enabled = True
        agent.config.name = name
        agent.process = response_fn
        return agent

    def test_e2e_happy_path_npc_interaction(self, mock_retrieval_manager, game_session):
        """Test successful NPC interaction flow."""

        # Mock RulesReferee - approves user prompt
        def rules_referee_user_validation(context):
            return AgentOutput(
                content="User prompt is valid - Gandalf exists in LOTR corpus.",
                citations=[],
                reasoning="Found references to Gandalf",
                metadata={
                    "validation_result": {
                        "approved": True,
                        "reason": "Valid query about existing character",
                        "confidence": 0.95,
                        "relevant_chunks": ["chunk_1"],
                        "citations": [1],
                    }
                }
            )

        # Mock ScenePlanner - routes to NPC
        def scene_planner_response(context):
            return AgentOutput(
                content="Player wants to talk to Gandalf",
                citations=[],
                reasoning="Direct NPC engagement requested",
                metadata={
                    "scene_plan": {
                        "next_action": "engage_npc",
                        "target": "Gandalf",
                        "reasoning": "Player directly addressing Gandalf",
                        "retrieval_quality": 0.9,
                        "validation_status": "approved",
                    }
                }
            )

        # Mock NPCPersonaExtractor
        def persona_extractor_response(context):
            return AgentOutput(
                content="Extracted Gandalf's persona",
                citations=[],
                reasoning="",
                metadata={
                    "persona": {
                        "speaking_style": "wise and cryptic",
                        "personality_traits": ["intelligent", "mysterious", "patient"],
                        "background": "Ancient wizard of great power",
                    }
                }
            )

        # Mock NPCManager - generates Gandalf's response
        def npc_manager_response(context):
            return AgentOutput(
                content="A wizard is never late, Frodo Baggins. Nor is he early.",
                citations=[1],
                reasoning="Responding in Gandalf's characteristic style",
                metadata={"npc_name": "Gandalf"}
            )

        # Mock RulesReferee - approves agent response
        def rules_referee_agent_validation(context):
            # Check if this is agent validation (has validation_mode)
            if context.session_state.get("validation_mode") == "agent_response":
                return AgentOutput(
                    content="Agent response matches corpus",
                    citations=[],
                    reasoning="Gandalf's quote is accurate",
                    metadata={
                        "validation_result": {
                            "approved": True,
                            "reason": "Accurate quote from corpus",
                            "confidence": 0.98,
                            "relevant_chunks": ["chunk_1"],
                            "citations": [1],
                        }
                    }
                )
            else:
                # User validation
                return rules_referee_user_validation(context)

        # Create orchestrator with mocked agents
        orchestrator = GameOrchestrator(agents={
            "rules_referee": self.create_mock_agent("rules_referee", rules_referee_agent_validation),
            "scene_planner": self.create_mock_agent("scene_planner", scene_planner_response),
            "npc_persona_extractor": self.create_mock_agent("npc_persona_extractor", persona_extractor_response),
            "npc_manager": self.create_mock_agent("npc_manager", npc_manager_response),
        })

        game_loop = GameLoop(orchestrator, mock_retrieval_manager)

        # Execute turn
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Talk to Gandalf about the quest"
        )

        # Assertions
        assert result.success is True
        assert result.player_wins is False
        assert result.player_loses is False
        assert result.turn_ended_early is False

        # Check validations
        assert result.user_validation is not None
        assert result.user_validation.approved is True
        assert result.agent_validation is not None
        assert result.agent_validation.approved is True

        # Check scene plan
        assert result.scene_plan is not None
        assert result.scene_plan.next_action == "engage_npc"
        assert result.scene_plan.target == "Gandalf"

        # Check NPC output
        assert result.npc_output is not None
        assert "wizard is never late" in result.npc_output["content"]
        assert result.narrator_output is None

        # Check persona cache
        assert "Gandalf" in game_session.persona_cache
        assert game_session.persona_cache["Gandalf"]["speaking_style"] == "wise and cryptic"

        # Check session state
        assert "Gandalf" in game_session.state["active_npcs"]
        assert game_session.wins == 0
        assert game_session.losses == 0

    def test_e2e_user_disqualification(self, mock_retrieval_manager, game_session):
        """Test user prompt disqualification - player loses."""

        # Mock RulesReferee - rejects user prompt
        def rules_referee_response(context):
            return AgentOutput(
                content="User prompt is invalid - quantum physics not in LOTR",
                citations=[],
                reasoning="No corpus support for quantum physics",
                metadata={
                    "validation_result": {
                        "approved": False,
                        "reason": "Query about quantum physics not relevant to Middle-earth",
                        "confidence": 0.99,
                        "relevant_chunks": [],
                        "suggestions": ["Ask about magic instead", "Inquire about the Ring"],
                        "citations": [],
                    }
                }
            )

        # Mock ScenePlanner - sees rejection and sets disqualify
        def scene_planner_response(context):
            validation = context.session_state.get("validation_result", {})
            if not validation.get("approved", True):
                return AgentOutput(
                    content="Cannot proceed - invalid prompt",
                    citations=[],
                    reasoning="User validation failed",
                    metadata={
                        "scene_plan": {
                            "next_action": "disqualify",
                            "target": None,
                            "reasoning": "User prompt doesn't match corpus",
                            "retrieval_quality": 0.1,
                            "validation_status": "rejected",
                            "alternative_suggestions": [
                                "Ask about wizardry and magic",
                                "Explore the Shire",
                                "Learn about the One Ring"
                            ],
                        }
                    }
                )

        # Mock Narrator - generates disqualification message
        def narrator_response(context):
            mode = context.session_state.get("mode")
            if mode == "disqualification":
                return AgentOutput(
                    content=(
                        "Your question about quantum physics doesn't fit in Middle-earth. "
                        "Perhaps you meant to ask about the ancient magic of wizards?"
                    ),
                    citations=[],
                    reasoning="Gentle redirection to corpus-appropriate topics",
                    metadata={}
                )

        orchestrator = GameOrchestrator(agents={
            "rules_referee": self.create_mock_agent("rules_referee", rules_referee_response),
            "scene_planner": self.create_mock_agent("scene_planner", scene_planner_response),
            "narrator": self.create_mock_agent("narrator", narrator_response),
        })

        game_loop = GameLoop(orchestrator, mock_retrieval_manager)

        # Execute turn
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Ask Gandalf about quantum physics"
        )

        # Assertions
        assert result.success is True  # Turn completed successfully
        assert result.player_wins is False
        assert result.player_loses is True  # User was disqualified
        assert result.turn_ended_early is True  # Turn ended at validation

        # Check user validation
        assert result.user_validation is not None
        assert result.user_validation.approved is False
        assert "quantum physics" in result.user_validation.reason

        # Check scene plan
        assert result.scene_plan is not None
        assert result.scene_plan.next_action == "disqualify"

        # Check narrator output
        assert result.narrator_output is not None
        assert "doesn't fit in Middle-earth" in result.narrator_output["content"]
        assert result.npc_output is None

        # Check session state
        assert game_session.losses == 1
        assert game_session.wins == 0

        # Check metadata structure (for API compatibility)
        assert "timestamp" in result.metadata, "metadata should include timestamp"
        assert "retrieval" in result.metadata, "metadata should include retrieval"
        assert "agents_executed" in result.metadata, "metadata should include agents_executed"
        assert "disqualification_reason" in result.metadata
        assert "alternative_suggestions" in result.metadata

    def test_e2e_agent_disqualification_player_wins(self, mock_retrieval_manager, game_session):
        """Test agent response disqualification - player wins."""

        # Mock RulesReferee - approves user prompt, rejects agent response
        def rules_referee_response(context):
            mode = context.session_state.get("validation_mode")
            if mode == "agent_response":
                # Agent validation - reject
                return AgentOutput(
                    content="Agent response contradicts corpus",
                    citations=[],
                    reasoning="Gandalf never said that in the books",
                    metadata={
                        "validation_result": {
                            "approved": False,
                            "reason": "Response contains inaccurate information not in corpus",
                            "confidence": 0.92,
                            "relevant_chunks": ["chunk_1"],
                            "citations": [],
                        }
                    }
                )
            else:
                # User validation - approve
                return AgentOutput(
                    content="User prompt is valid",
                    citations=[],
                    reasoning="",
                    metadata={
                        "validation_result": {
                            "approved": True,
                            "reason": "Valid query",
                            "confidence": 0.9,
                            "relevant_chunks": ["chunk_1"],
                            "citations": [1],
                        }
                    }
                )

        # Mock ScenePlanner
        def scene_planner_response(context):
            return AgentOutput(
                content="Route to narrator",
                citations=[],
                reasoning="",
                metadata={
                    "scene_plan": {
                        "next_action": "narrator_scene",
                        "target": None,
                        "reasoning": "Scene description needed",
                        "retrieval_quality": 0.8,
                        "validation_status": "approved",
                    }
                }
            )

        # Mock Narrator - first call returns bad response, second call is correction
        narrator_call_count = [0]
        def narrator_response(context):
            narrator_call_count[0] += 1
            mode = context.session_state.get("mode")

            if mode == "correction":
                # Correction mode
                return AgentOutput(
                    content=(
                        "The previous response was inaccurate. "
                        "According to the corpus, Gandalf actually said..."
                    ),
                    citations=[1],
                    reasoning="Providing accurate corpus-based correction",
                    metadata={}
                )
            else:
                # First call - narration mode (will be rejected)
                return AgentOutput(
                    content="Gandalf says: 'I love quantum mechanics!' (This is wrong)",
                    citations=[],
                    reasoning="Made up response",
                    metadata={}
                )

        orchestrator = GameOrchestrator(agents={
            "rules_referee": self.create_mock_agent("rules_referee", rules_referee_response),
            "scene_planner": self.create_mock_agent("scene_planner", scene_planner_response),
            "narrator": self.create_mock_agent("narrator", narrator_response),
        })

        game_loop = GameLoop(orchestrator, mock_retrieval_manager)

        # Execute turn
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Look around"
        )

        # Assertions
        assert result.success is True
        assert result.player_wins is True  # Agent was disqualified
        assert result.player_loses is False

        # Check validations
        assert result.user_validation is not None, "assert user_validation not None"
        assert result.user_validation.approved is True
        assert result.agent_validation is not None, "assert agent_validation not None"
        assert result.agent_validation.approved is False

        # Check narrator output (should be correction)
        assert result.narrator_output is not None, "assert narrator_output not None"
        # The narrator should have been called twice: once for bad response, once for correction
        assert narrator_call_count[0] == 2
        # The result should contain the correction OR metadata about original response
        assert ("previous response was inaccurate" in result.narrator_output["content"] or
                "original_agent_response" in result.metadata)

        # Check session state
        assert game_session.wins == 1
        assert game_session.losses == 0

        # Check metadata structure (for API compatibility)
        assert "timestamp" in result.metadata, "metadata should include timestamp"
        assert "retrieval" in result.metadata, "metadata should include retrieval"
        assert "agents_executed" in result.metadata, "metadata should include agents_executed"
        assert "original_agent_response" in result.metadata
        assert "disqualification_reason" in result.metadata

    def test_e2e_scene_description_path(self, mock_retrieval_manager, game_session):
        """Test scene description with narrator-only interaction."""

        # Mock RulesReferee - approves
        def rules_referee_response(context):
            mode = context.session_state.get("validation_mode")
            return AgentOutput(
                content="Valid",
                citations=[],
                reasoning="",
                metadata={
                    "validation_result": {
                        "approved": True,
                        "reason": "Valid scene query",
                        "confidence": 0.9,
                        "relevant_chunks": ["chunk_2"],
                        "citations": [2],
                    }
                }
            )

        # Mock ScenePlanner - routes to narrator
        def scene_planner_response(context):
            return AgentOutput(
                content="Scene description needed",
                citations=[],
                reasoning="No NPC mentioned",
                metadata={
                    "scene_plan": {
                        "next_action": "narrator_scene",
                        "target": None,
                        "reasoning": "Player wants scene description, no NPC interaction",
                        "retrieval_quality": 0.85,
                        "validation_status": "approved",
                    }
                }
            )

        # Mock Narrator
        def narrator_response(context):
            return AgentOutput(
                content="The Shire stretches before you, with rolling green hills and cozy hobbit-holes.",
                citations=[2],
                reasoning="Describing the Shire",
                metadata={"scene": "Shire"}
            )

        orchestrator = GameOrchestrator(agents={
            "rules_referee": self.create_mock_agent("rules_referee", rules_referee_response),
            "scene_planner": self.create_mock_agent("scene_planner", scene_planner_response),
            "narrator": self.create_mock_agent("narrator", narrator_response),
        })

        game_loop = GameLoop(orchestrator, mock_retrieval_manager)

        # Execute turn
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Look around the Shire"
        )

        # Assertions
        assert result.success is True
        assert result.player_wins is False
        assert result.player_loses is False

        # Check scene plan
        assert result.scene_plan is not None, "assert scene_plan not None"
        assert result.scene_plan.next_action == "narrator_scene"
        assert result.scene_plan.target is None

        # Check narrator output
        assert result.narrator_output is not None, "assert narrator_output not None"
        assert "Shire stretches" in result.narrator_output["content"]
        assert result.npc_output is None

        # Check no NPCs added
        assert len(game_session.state["active_npcs"]) == 0

    def test_e2e_persona_caching(self, mock_retrieval_manager, game_session):
        """Test that persona is cached after first NPC interaction."""

        # Setup same as happy path test
        def rules_referee_response(context):
            return AgentOutput(
                content="Valid",
                citations=[],
                reasoning="",
                metadata={
                    "validation_result": {
                        "approved": True,
                        "reason": "Valid",
                        "confidence": 0.9,
                        "relevant_chunks": ["chunk_1"],
                        "citations": [1],
                    }
                }
            )

        def scene_planner_response(context):
            return AgentOutput(
                content="Engage NPC",
                citations=[],
                reasoning="",
                metadata={
                    "scene_plan": {
                        "next_action": "engage_npc",
                        "target": "Gandalf",
                        "reasoning": "Player addressing Gandalf",
                        "retrieval_quality": 0.9,
                        "validation_status": "approved",
                    }
                }
            )

        persona_extractor_calls = [0]
        def persona_extractor_response(context):
            persona_extractor_calls[0] += 1
            return AgentOutput(
                content="Persona extracted",
                citations=[],
                reasoning="",
                metadata={
                    "persona": {
                        "speaking_style": "wise",
                        "personality_traits": ["wise"],
                        "background": "wizard",
                    }
                }
            )

        def npc_manager_response(context):
            return AgentOutput(
                content="Gandalf responds",
                citations=[1],
                reasoning="",
                metadata={"npc_name": "Gandalf"}
            )

        orchestrator = GameOrchestrator(agents={
            "rules_referee": self.create_mock_agent("rules_referee", rules_referee_response),
            "scene_planner": self.create_mock_agent("scene_planner", scene_planner_response),
            "npc_persona_extractor": self.create_mock_agent("npc_persona_extractor", persona_extractor_response),
            "npc_manager": self.create_mock_agent("npc_manager", npc_manager_response),
        })

        game_loop = GameLoop(orchestrator, mock_retrieval_manager)

        # First turn - should extract persona
        result1 = game_loop.execute_turn(
            session=game_session,
            player_command="Talk to Gandalf"
        )

        assert result1.success is True
        assert "Gandalf" in game_session.persona_cache
        assert persona_extractor_calls[0] == 1

        # Second turn - should use cached persona
        result2 = game_loop.execute_turn(
            session=game_session,
            player_command="Ask Gandalf again"
        )

        assert result2.success is True
        assert persona_extractor_calls[0] == 1  # Still 1 - not called again
        assert "Gandalf" in game_session.persona_cache
