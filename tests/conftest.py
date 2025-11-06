"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
from src.core.config import (
    AppConfig,
    AgentConfig,
    LLMConfig,
    LLMProvider,
    SessionConfig,
    RetrievalConfig,
)
from src.core.session import GameSession
from src.core.base_agent import RetrievalResult, AgentContext
from src.rag.base_retriever import BaseRetriever


@pytest.fixture
def mock_llm_config():
    """Mock LLM configuration."""
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1000,
        api_key="test-key",
    )


@pytest.fixture
def mock_agent_config(mock_llm_config):
    """Mock agent configuration."""
    return AgentConfig(
        name="test_agent",
        llm=mock_llm_config,
        persona_template="You are a test agent.",
        retrieval_query_template="test query: {player_command}",
        retrieval_top_k=5,
    )


@pytest.fixture
def session_config():
    """Session configuration for tests."""
    return SessionConfig(
        memory_window_size=5,
        max_tokens=2000,
        sliding_window=True,
        session_ttl_seconds=3600,
    )


@pytest.fixture
def game_session(session_config):
    """Create a test game session."""
    return GameSession(
        session_id="test-session-123",
        config=session_config,
    )


@pytest.fixture
def sample_retrieval_results():
    """Sample retrieval results for testing."""
    return [
        RetrievalResult(
            chunk_text="This is a test chunk about the story.",
            score=0.95,
            chunk_id="chunk_1",
            metadata={"source": "corpus.txt", "line": 10},
        ),
        RetrievalResult(
            chunk_text="Another relevant chunk with information.",
            score=0.85,
            chunk_id="chunk_2",
            metadata={"source": "corpus.txt", "line": 20},
        ),
    ]


@pytest.fixture
def agent_context(sample_retrieval_results):
    """Create agent context for testing."""
    return AgentContext(
        player_command="Test player command",
        session_state={"current_scene": "test_scene"},
        retrieval_results=sample_retrieval_results,
        previous_turns=[],
    )


@pytest.fixture
def mock_retriever():
    """Mock retriever implementation."""
    retriever = Mock(spec=BaseRetriever)
    retriever.retrieve = Mock(return_value=[
        RetrievalResult(
            chunk_text="Mock chunk",
            score=0.9,
            chunk_id="mock_1",
        )
    ])
    retriever.retrieve_with_scores = Mock(return_value=[
        RetrievalResult(
            chunk_text="Mock chunk",
            score=0.9,
            chunk_id="mock_1",
        )
    ])
    return retriever


@pytest.fixture
def app_config():
    """Create a minimal app configuration for testing."""
    config_dict = {
        "agents": {
            "test_agent": {
                "llm": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                },
                "persona_template": "Test persona",
            }
        },
        "retrieval": {
            "bm25_weight": 0.5,
            "vector_weight": 0.5,
        },
        "session": {
            "memory_window_size": 5,
        },
    }
    return AppConfig.from_dict(config_dict)

