"""Tests for game loop implementation."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.core.game_loop import GameLoop, TurnPhase, TurnProgress, TurnResult
from src.core.orchestrator import GameOrchestrator
from src.core.session import GameSession
from src.core.config import SessionConfig
from src.core.base_agent import AgentOutput, RetrievalResult


class TestGameLoop:
    """Test GameLoop functionality."""

    @pytest.fixture
    def mock_retrieval_manager(self):
        """Create mock retrieval manager."""
        manager = Mock()
        manager.retrieve.return_value = [
            RetrievalResult(
                chunk_id="chunk_0",
                chunk_text="Test chunk content",
                score=0.9,
                metadata={}
            )
        ]
        return manager

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = Mock()
        agent.config.enabled = True
        agent.config.name = "test_agent"
        agent.process.return_value = AgentOutput(
            content="Test response",
            citations=["chunk_0"],
            reasoning="Test reasoning",
            metadata={"test": "data"}
        )
        return agent

    @pytest.fixture
    def mock_orchestrator(self, mock_agent):
        """Create mock orchestrator."""
        orchestrator = Mock(spec=GameOrchestrator)
        orchestrator.agents = {
            "narrator": mock_agent,
            "scene_planner": mock_agent,
            "npc_manager": mock_agent,
            "rules_referee": mock_agent,
        }
        return orchestrator

    @pytest.fixture
    def game_session(self):
        """Create a test game session."""
        config = SessionConfig(
            memory_window_size=5,
            max_tokens=1000,
            sliding_window=True,
            session_ttl_seconds=3600
        )
        return GameSession(session_id="test-session", config=config)

    @pytest.fixture
    def game_loop(self, mock_orchestrator, mock_retrieval_manager):
        """Create game loop instance."""
        return GameLoop(mock_orchestrator, mock_retrieval_manager)

    def test_execute_turn_basic(self, game_loop, game_session):
        """Test basic turn execution."""
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Look around"
        )

        assert isinstance(result, TurnResult)
        assert result.turn_number == 1
        assert result.session_id == "test-session"
        assert result.player_command == "Look around"
        assert result.success is True
        assert result.error is None

    def test_execute_turn_with_initial_context(self, game_loop, game_session):
        """Test turn execution with initial context."""
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Start adventure",
            initial_context="You are in a tavern"
        )

        assert result.success is True
        assert game_session.state.get("initial_context") == "You are in a tavern"

    def test_execute_turn_retrieval(self, game_loop, game_session, mock_retrieval_manager):
        """Test that retrieval is performed during turn."""
        game_loop.execute_turn(
            session=game_session,
            player_command="Talk to wizard"
        )

        # Verify retrieval was called
        mock_retrieval_manager.retrieve.assert_called_once()
        call_args = mock_retrieval_manager.retrieve.call_args
        assert "Talk to wizard" in call_args.kwargs["query"]

    def test_execute_turn_agents_called(self, game_loop, game_session, mock_orchestrator):
        """Test that agents are executed during turn."""
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Test command"
        )

        # Verify agents were called (through mocked process calls)
        for agent in mock_orchestrator.agents.values():
            agent.process.assert_called()

    def test_execute_turn_updates_session(self, game_loop, game_session):
        """Test that turn updates session state."""
        initial_turn_count = len(game_session.turns)

        game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        # Session should have one more turn
        assert len(game_session.turns) == initial_turn_count + 1
        assert game_session.turns[-1].player_command == "Test"

    def test_execute_turn_progress_tracking(self, game_loop, game_session):
        """Test progress tracking during turn execution."""
        progress_updates = []

        def progress_callback(progress: TurnProgress):
            progress_updates.append(progress.phase)

        game_loop.progress_callback = progress_callback

        game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        # Should have received progress updates
        assert len(progress_updates) > 0
        # Check that we progressed through the phases
        assert TurnPhase.STARTED in progress_updates
        assert TurnPhase.RETRIEVAL in progress_updates
        assert TurnPhase.COMPLETED in progress_updates

    def test_execute_turn_error_handling(self, game_loop, game_session, mock_retrieval_manager):
        """Test error handling during turn execution."""
        # Make retrieval raise an error
        mock_retrieval_manager.retrieve.side_effect = Exception("Retrieval failed")

        result = game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        assert result.success is False
        assert "Retrieval failed" in result.error

    def test_execute_turn_agent_failure_continues(self, game_loop, game_session, mock_orchestrator):
        """Test that turn continues even if one agent fails."""
        # Make narrator fail
        narrator = mock_orchestrator.agents["narrator"]
        narrator.process.side_effect = Exception("Narrator failed")

        result = game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        # Turn should still complete
        assert result.success is True
        # Other agents should still be called
        mock_orchestrator.agents["scene_planner"].process.assert_called()

    def test_get_progress(self, game_loop, game_session):
        """Test getting progress for a session."""
        # No progress initially
        progress = game_loop.get_progress("test-session")
        assert progress is None

        # Execute a turn
        game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        # Should have progress now
        progress = game_loop.get_progress("test-session")
        assert progress is not None
        assert progress.session_id == "test-session"

    def test_turn_result_to_dict(self):
        """Test TurnResult serialization."""
        result = TurnResult(
            turn_number=1,
            session_id="test",
            player_command="test command",
            narrator_output={"content": "test"},
            duration_seconds=1.5,
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["turn_number"] == 1
        assert result_dict["session_id"] == "test"
        assert result_dict["player_command"] == "test command"
        assert result_dict["duration_seconds"] == 1.5
        assert result_dict["success"] is True

    def test_turn_progress_to_dict(self):
        """Test TurnProgress serialization."""
        progress = TurnProgress(
            turn_number=1,
            session_id="test",
            phase=TurnPhase.NARRATOR,
            current_agent="narrator",
            message="Processing narrator",
        )

        progress_dict = progress.to_dict()

        assert progress_dict["turn_number"] == 1
        assert progress_dict["session_id"] == "test"
        assert progress_dict["phase"] == "narrator"
        assert progress_dict["current_agent"] == "narrator"

    def test_multiple_turns(self, game_loop, game_session):
        """Test executing multiple turns in sequence."""
        commands = ["Look around", "Talk to wizard", "Pick up item"]

        for i, command in enumerate(commands, 1):
            result = game_loop.execute_turn(
                session=game_session,
                player_command=command
            )

            assert result.turn_number == i
            assert result.success is True

        # Session should have all turns
        assert len(game_session.turns) == 3

    def test_turn_metadata_includes_retrieval_info(self, game_loop, game_session):
        """Test that turn result metadata includes retrieval information."""
        result = game_loop.execute_turn(
            session=game_session,
            player_command="Test"
        )

        assert "retrieval" in result.metadata
        assert "num_chunks" in result.metadata["retrieval"]
        assert result.metadata["retrieval"]["num_chunks"] > 0

    def test_turn_updates_scene_from_scene_planner(self, game_loop, game_session, mock_orchestrator):
        """Test that scene is updated from scene planner output."""
        scene_planner = mock_orchestrator.agents["scene_planner"]
        scene_planner.process.return_value = AgentOutput(
            content="Scene planned",
            citations=[],
            reasoning="",
            metadata={
                "scene_plan": {
                    "next_scene": "forest",
                    "responding_npc": "Gandalf"
                }
            }
        )

        game_loop.execute_turn(
            session=game_session,
            player_command="Go to forest"
        )

        assert game_session.state.get("current_scene") == "forest"
        assert "Gandalf" in game_session.state.get("active_npcs", [])
