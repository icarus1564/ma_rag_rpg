"""Tests for status API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock

from src.api.app import app
from src.api.endpoints import status
from src.core.session_manager import SessionManager
from src.core.orchestrator import GameOrchestrator
from src.core.retrieval_manager import RetrievalManager
from src.core.config import AppConfig, AgentConfig, LLMConfig, LLMProvider


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    manager = Mock(spec=SessionManager)
    manager.get_session_count.return_value = 2
    return manager


@pytest.fixture
def mock_agent():
    """Create a mock agent with config."""
    agent = Mock()
    agent.config = AgentConfig(
        name="test_agent",
        llm=LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="test-model",
            temperature=0.7,
            max_tokens=1000
        ),
        retrieval_top_k=5,
        enabled=True
    )
    return agent


@pytest.fixture
def mock_orchestrator(mock_agent):
    """Create mock orchestrator."""
    orchestrator = Mock(spec=GameOrchestrator)
    orchestrator.agents = {
        "narrator": mock_agent,
        "scene_planner": mock_agent,
    }
    return orchestrator


@pytest.fixture
def mock_retrieval_manager():
    """Create mock retrieval manager."""
    manager = Mock(spec=RetrievalManager)

    # Mock BM25 retriever
    bm25_retriever = Mock()
    bm25_retriever.is_loaded.return_value = True
    bm25_retriever.chunks = ["chunk1", "chunk2", "chunk3"]

    # Mock vector retriever
    vector_retriever = Mock()
    vector_db = Mock()
    vector_db.collection_exists.return_value = True
    vector_db.get_collection_stats.return_value = {"count": 100}
    vector_retriever.vector_db = vector_db

    # Mock hybrid retriever
    hybrid_retriever = Mock()
    hybrid_retriever.bm25_retriever = bm25_retriever
    hybrid_retriever.vector_retriever = vector_retriever

    manager.hybrid_retriever = hybrid_retriever
    manager.cache = {"query1": "result1", "query2": "result2"}

    return manager


@pytest.fixture
def mock_app_config():
    """Create mock app config."""
    config = Mock()

    # Ingestion config
    config.ingestion = Mock()
    config.ingestion.corpus_path = "data/test_data/test_corpus2.txt"
    config.ingestion.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector DB config
    config.vector_db = Mock()
    config.vector_db.provider = "chroma"
    config.vector_db.get_collection_name = Mock(return_value="test_collection")

    # Retrieval config
    config.retrieval = Mock()
    config.retrieval.fusion_strategy = "rrf"
    config.retrieval.query_rewriter_enabled = True

    return config


@pytest.fixture
def client(mock_session_manager, mock_orchestrator, mock_retrieval_manager, mock_app_config):
    """Create test client with mocked dependencies."""
    # Set mock dependencies
    status.set_status_dependencies(
        mock_session_manager,
        mock_orchestrator,
        mock_retrieval_manager,
        mock_app_config
    )

    return TestClient(app)


class TestStatusEndpoints:
    """Test status API endpoints."""

    def test_get_system_status(self, client):
        """Test getting system status."""
        response = client.get("/api/status/system")

        assert response.status_code == 200
        data = response.json()

        assert "state" in data
        assert "uptime_seconds" in data
        assert "active_sessions" in data
        assert data["active_sessions"] == 2
        assert "total_turns" in data
        assert "timestamp" in data

    def test_get_corpus_status(self, client, mock_app_config):
        """Test getting corpus status."""
        response = client.get("/api/status/corpus")

        assert response.status_code == 200
        data = response.json()

        assert data["corpus_name"] == "test_corpus2.txt"
        assert data["corpus_path"] == "data/test_data/test_corpus2.txt"
        assert data["loaded_corpora"] is None
        assert data["total_chunks"] == 3  # From mock BM25 retriever
        assert data["bm25_status"] == "connected"
        assert data["vector_db_status"] == "connected"
        assert data["vector_db_provider"] == "chroma"
        assert data["collection_name"] == "test_collection"
        assert data["total_documents"] == 100
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["embedding_dimension"] == 384  # MiniLM dimension

    def test_get_corpus_status_bm25_not_loaded(self, client, mock_retrieval_manager):
        """Test corpus status when BM25 index is not loaded."""
        mock_retrieval_manager.hybrid_retriever.bm25_retriever.is_loaded.return_value = False

        response = client.get("/api/status/corpus")

        assert response.status_code == 200
        data = response.json()
        assert data["bm25_status"] == "disconnected"

    def test_get_corpus_status_vector_db_error(self, client, mock_retrieval_manager):
        """Test corpus status when vector DB has an error."""
        mock_retrieval_manager.hybrid_retriever.vector_retriever.vector_db.collection_exists.side_effect = Exception("Connection error")

        response = client.get("/api/status/corpus")

        assert response.status_code == 200
        data = response.json()
        assert data["vector_db_status"] == "error"

    def test_get_agents_status(self, client):
        """Test getting agents status."""
        # Record some agent stats
        status.record_agent_call("narrator", success=True, duration=1.5)
        status.record_agent_call("narrator", success=True, duration=2.0)
        status.record_agent_call("narrator", success=False, duration=0.5, error="Timeout")

        response = client.get("/api/status/agents")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 2  # narrator and scene_planner

        # Find narrator in results
        narrator_status = next((a for a in data if a["agent_name"] == "narrator"), None)
        assert narrator_status is not None
        assert narrator_status["enabled"] is True
        assert narrator_status["llm_provider"] == "ollama"
        assert narrator_status["llm_model"] == "test-model"
        assert narrator_status["total_calls"] == 3
        assert narrator_status["successful_calls"] == 2
        assert narrator_status["failed_calls"] == 1
        assert narrator_status["last_error"] == "Timeout"
        assert narrator_status["average_response_time"] is not None

    def test_get_agents_status_no_orchestrator(self):
        """Test agents status when orchestrator is not initialized."""
        # Create client without orchestrator
        status.set_status_dependencies(None, None, None, None)
        client = TestClient(app)

        response = client.get("/api/status/agents")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_retrieval_status(self, client):
        """Test getting retrieval status."""
        response = client.get("/api/status/retrieval")

        assert response.status_code == 200
        data = response.json()

        assert data["hybrid_retrieval_enabled"] is True
        assert data["bm25_status"] == "connected"
        assert data["vector_status"] == "connected"
        assert data["fusion_strategy"] == "rrf"
        assert data["query_rewriting_enabled"] is True
        assert data["cache_enabled"] is True
        assert data["cached_queries"] == 2

    def test_get_retrieval_status_not_initialized(self):
        """Test retrieval status when not initialized."""
        status.set_status_dependencies(None, None, None, None)
        client = TestClient(app)

        response = client.get("/api/status/retrieval")

        assert response.status_code == 500

    def test_increment_turn_count(self):
        """Test incrementing turn count."""
        initial_count = status._total_turns

        status.increment_turn_count()
        status.increment_turn_count()

        assert status._total_turns == initial_count + 2

    def test_record_agent_call_stats(self):
        """Test recording agent call statistics."""
        status._agent_stats.clear()

        # Record successful call
        status.record_agent_call("test_agent", success=True, duration=1.0)

        assert "test_agent" in status._agent_stats
        stats = status._agent_stats["test_agent"]
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["total_duration"] == 1.0

        # Record failed call
        status.record_agent_call("test_agent", success=False, duration=0.5, error="Test error")

        stats = status._agent_stats["test_agent"]
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1
        assert stats["last_error"] == "Test error"

    def test_corpus_status_with_different_embedding_models(self, client, mock_app_config):
        """Test corpus status reports correct dimensions for different models."""
        # Test mpnet model
        mock_app_config.ingestion.embedding_model = "sentence-transformers/all-mpnet-base-v2"

        response = client.get("/api/status/corpus")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_dimension"] == 768

        # Test OpenAI model
        mock_app_config.ingestion.embedding_model = "text-embedding-ada-002"

        response = client.get("/api/status/corpus")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_dimension"] == 1536

    def test_agents_status_disabled_agent(self, client, mock_orchestrator):
        """Test status of disabled agent."""
        # Make one agent disabled
        disabled_agent = Mock()
        disabled_agent.config = AgentConfig(
            name="disabled_agent",
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4",
                temperature=0.5,
                max_tokens=500,
                api_key="test-key"  # Provide API key
            ),
            enabled=False
        )

        mock_orchestrator.agents["disabled_agent"] = disabled_agent

        response = client.get("/api/status/agents")

        assert response.status_code == 200
        data = response.json()

        disabled_status = next((a for a in data if a["agent_name"] == "disabled_agent"), None)
        assert disabled_status is not None
        assert disabled_status["enabled"] is False
