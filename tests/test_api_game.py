"""Tests for game API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from src.api.app import app
from src.api.endpoints import game
from src.core.session_manager import SessionManager
from src.core.game_loop import GameLoop, TurnResult
from src.core.config import SessionConfig


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    manager = Mock(spec=SessionManager)

    # Mock create_session
    mock_session = Mock()
    mock_session.session_id = "test-session-123"
    mock_session.created_at.isoformat.return_value = "2025-01-01T00:00:00"
    mock_session.state = {}
    mock_session.turns = []
    mock_session.last_accessed.isoformat.return_value = "2025-01-01T00:00:00"
    mock_session.to_dict.return_value = {
        "session_id": "test-session-123",
        "turn_count": 0,
        "current_scene": None,
        "active_npcs": [],
        "memory_size": 0,
        "created_at": "2025-01-01T00:00:00",
        "last_accessed": "2025-01-01T00:00:00",
        "state": {}
    }

    manager.create_session.return_value = mock_session
    manager.get_session.return_value = mock_session
    manager.delete_session.return_value = True
    manager.get_session_count.return_value = 1

    return manager


@pytest.fixture
def mock_game_loop():
    """Create mock game loop."""
    loop = Mock(spec=GameLoop)

    # Mock execute_turn
    result = TurnResult(
        turn_number=1,
        session_id="test-session-123",
        player_command="Look around",
        narrator_output={
            "content": "You see a tavern",
            "citations": ["chunk_0"],
            "reasoning": "Based on location",
            "metadata": {"scene": "tavern"}
        },
        scene_planner_output={
            "content": "Scene continues",
            "citations": [],
            "reasoning": "",
            "metadata": {"scene_plan": {"fallback_to_narrator": True}}
        },
        metadata={
            "retrieval": {"num_chunks": 5, "chunks": []},
            "agents_executed": ["narrator", "scene_planner"],
            "timestamp": "2025-01-01T00:00:00"
        },
        duration_seconds=1.5,
        success=True
    )

    loop.execute_turn.return_value = result
    loop.get_progress.return_value = None

    return loop


@pytest.fixture
def client(mock_session_manager, mock_game_loop):
    """Create test client with mocked dependencies."""
    # Set mock dependencies
    game.set_game_dependencies(mock_session_manager, mock_game_loop)

    return TestClient(app)


class TestGameEndpoints:
    """Test game API endpoints."""

    def test_new_game_success(self, client, mock_session_manager):
        """Test creating a new game."""
        response = client.post(
            "/api/new_game",
            json={"initial_context": "You are in a tavern"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        assert "message" in data
        assert "created_at" in data

        # Verify session was created
        mock_session_manager.create_session.assert_called_once()

    def test_new_game_no_context(self, client, mock_session_manager):
        """Test creating a new game without initial context."""
        response = client.post(
            "/api/new_game",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_new_game_error(self, client, mock_session_manager):
        """Test error handling in new game."""
        mock_session_manager.create_session.side_effect = Exception("Database error")

        response = client.post(
            "/api/new_game",
            json={}
        )

        assert response.status_code == 500
        assert "Failed to create game session" in response.json()["detail"]

    def test_process_turn_success(self, client, mock_game_loop):
        """Test processing a player turn."""
        response = client.post(
            "/api/turn",
            json={
                "session_id": "test-session-123",
                "player_command": "Look around"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["turn_number"] == 1
        assert data["session_id"] == "test-session-123"
        assert data["player_command"] == "Look around"
        assert data["success"] is True
        assert "narrator_output" in data
        assert data["narrator_output"]["content"] == "You see a tavern"

        # Verify game loop was called
        mock_game_loop.execute_turn.assert_called_once()

    def test_process_turn_session_not_found(self, client, mock_session_manager):
        """Test processing turn with invalid session."""
        mock_session_manager.get_session.return_value = None

        response = client.post(
            "/api/turn",
            json={
                "session_id": "invalid-session",
                "player_command": "Test"
            }
        )

        assert response.status_code == 404
        assert "not found or expired" in response.json()["detail"]

    def test_process_turn_validation_error(self, client):
        """Test turn request validation."""
        # Missing required field
        response = client.post(
            "/api/turn",
            json={"session_id": "test"}
        )

        assert response.status_code == 422  # Validation error

        # Empty player command
        response = client.post(
            "/api/turn",
            json={"session_id": "test", "player_command": ""}
        )

        assert response.status_code == 422

    def test_process_turn_with_errors(self, client, mock_game_loop):
        """Test turn processing with agent errors."""
        # Return a result with errors
        error_result = TurnResult(
            turn_number=1,
            session_id="test-session-123",
            player_command="Test",
            narrator_output={
                "content": "Error occurred",
                "citations": [],
                "error": True,
                "error_message": "LLM timeout"
            },
            metadata={
                "retrieval": {"num_chunks": 0, "chunks": []},
                "agents_executed": ["narrator"],
                "timestamp": "2025-01-01T00:00:00"
            },
            duration_seconds=5.0,
            success=True  # Turn completes even with agent errors
        )

        mock_game_loop.execute_turn.return_value = error_result

        response = client.post(
            "/api/turn",
            json={
                "session_id": "test-session-123",
                "player_command": "Test"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["narrator_output"]["error"] is True

    def test_get_game_state_success(self, client, mock_session_manager):
        """Test getting game state."""
        response = client.get("/api/state/test-session-123")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "test-session-123"
        assert "turn_count" in data
        assert "current_scene" in data
        assert "active_npcs" in data
        assert "memory_size" in data

    def test_get_game_state_not_found(self, client, mock_session_manager):
        """Test getting state for non-existent session."""
        mock_session_manager.get_session.return_value = None

        response = client.get("/api/state/invalid-session")

        assert response.status_code == 404

    def test_get_turn_progress(self, client, mock_game_loop):
        """Test getting turn progress."""
        from src.core.game_loop import TurnProgress, TurnPhase

        progress = TurnProgress(
            turn_number=1,
            session_id="test-session-123",
            phase=TurnPhase.NARRATOR,
            current_agent="narrator",
            message="Processing narrator"
        )

        mock_game_loop.get_progress.return_value = progress

        response = client.get("/api/progress/test-session-123")

        assert response.status_code == 200
        data = response.json()

        assert data["turn_number"] == 1
        assert data["phase"] == "narrator"
        assert data["current_agent"] == "narrator"

    def test_get_turn_progress_no_progress(self, client, mock_game_loop, mock_session_manager):
        """Test getting progress when no turn is active."""
        mock_game_loop.get_progress.return_value = None

        response = client.get("/api/progress/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "idle"

    def test_delete_session_success(self, client, mock_session_manager):
        """Test deleting a session."""
        response = client.delete("/api/session/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

        mock_session_manager.delete_session.assert_called_once_with("test-session-123")

    def test_delete_session_not_found(self, client, mock_session_manager):
        """Test deleting non-existent session."""
        mock_session_manager.delete_session.return_value = False

        response = client.delete("/api/session/invalid-session")

        assert response.status_code == 404

    def test_multiple_turns_sequence(self, client, mock_game_loop, mock_session_manager):
        """Test processing multiple turns in sequence."""
        # First turn
        response1 = client.post(
            "/api/turn",
            json={
                "session_id": "test-session-123",
                "player_command": "Look around"
            }
        )

        assert response1.status_code == 200

        # Update mock for second turn
        result2 = TurnResult(
            turn_number=2,
            session_id="test-session-123",
            player_command="Talk to wizard",
            metadata={
                "retrieval": {"num_chunks": 5, "chunks": []},
                "agents_executed": ["narrator", "npc_manager"],
                "timestamp": "2025-01-01T00:00:01"
            },
            duration_seconds=2.0,
            success=True
        )
        mock_game_loop.execute_turn.return_value = result2

        # Second turn
        response2 = client.post(
            "/api/turn",
            json={
                "session_id": "test-session-123",
                "player_command": "Talk to wizard"
            }
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["turn_number"] == 2
