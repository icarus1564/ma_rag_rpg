"""Tests for core framework components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.core.config import (
    AppConfig,
    AgentConfig,
    LLMConfig,
    LLMProvider,
    SessionConfig,
    RetrievalConfig,
)
from src.core.session import GameSession, Turn
from src.core.session_manager import SessionManager
from src.core.orchestrator import GameOrchestrator
from src.core.retrieval_manager import RetrievalManager
from src.core.base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from src.rag.base_retriever import BaseRetriever


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def process(self, context: AgentContext) -> AgentOutput:
        """Mock process method."""
        return AgentOutput(
            content=f"Mock output for: {context.player_command}",
            citations=["[1]", "[2]"],
            reasoning="Mock reasoning",
        )


class TestConfig:
    """Test configuration management."""
    
    def test_llm_config_from_env(self):
        """Test LLM config loads API key from environment."""
        import os
        os.environ["OPENAI_API_KEY"] = "test-env-key"
        
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
        )
        assert config.api_key == "test-env-key"
        del os.environ["OPENAI_API_KEY"]
    
    def test_ollama_config_defaults(self):
        """Test Ollama config uses default base_url."""
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2",
        )
        assert config.provider == LLMProvider.OLLAMA
        assert config.api_key == "ollama"  # Placeholder
        assert config.base_url == "http://localhost:11434/v1"
    
    def test_ollama_config_custom_base_url(self):
        """Test Ollama config with custom base_url."""
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2",
            base_url="http://custom-host:8080/v1",
        )
        assert config.base_url == "http://custom-host:8080/v1"
    
    def test_ollama_config_from_env(self):
        """Test Ollama config loads base_url from environment."""
        import os
        os.environ["OLLAMA_BASE_URL"] = "http://env-host:11434/v1"
        
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2",
        )
        assert config.base_url == "http://env-host:11434/v1"
        del os.environ["OLLAMA_BASE_URL"]
    
    def test_app_config_from_dict(self):
        """Test creating AppConfig from dictionary."""
        import os
        # Set a test API key for OpenAI
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            config_dict = {
                "agents": {
                    "narrator": {
                        "llm": {
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "temperature": 0.7,
                        },
                        "persona_template": "You are a narrator.",
                    }
                },
                "retrieval": {
                    "bm25_weight": 0.6,
                    "vector_weight": 0.4,
                },
                "session": {
                    "memory_window_size": 10,
                },
            }
            
            config = AppConfig.from_dict(config_dict)
            assert "narrator" in config.agents
            assert config.agents["narrator"].name == "narrator"
            assert config.retrieval.bm25_weight == 0.6
            assert config.session.memory_window_size == 10
        finally:
            # Clean up
            del os.environ["OPENAI_API_KEY"]
    
    def test_app_config_with_ollama(self):
        """Test AppConfig with Ollama provider."""
        config_dict = {
            "agents": {
                "test_agent": {
                    "llm": {
                        "provider": "ollama",
                        "model": "llama2",
                        "base_url": "http://localhost:11434/v1",
                    },
                }
            },
        }
        
        config = AppConfig.from_dict(config_dict)
        assert "test_agent" in config.agents
        agent_config = config.agents["test_agent"]
        assert agent_config.llm.provider == LLMProvider.OLLAMA
        assert agent_config.llm.model == "llama2"
        assert agent_config.llm.base_url == "http://localhost:11434/v1"
    
    def test_get_agent_config(self):
        """Test getting agent configuration."""
        config = AppConfig()
        agent_config = AgentConfig(
            name="test",
            llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", api_key="test"),
        )
        config.agents["test"] = agent_config
        
        retrieved = config.get_agent_config("test")
        assert retrieved == agent_config
        assert config.get_agent_config("nonexistent") is None
    
    def test_load_agents_from_yaml(self, tmp_path):
        """Test loading agents from YAML file."""
        agents_yaml = tmp_path / "agents.yaml"
        agents_yaml.write_text("""
agents:
  TestAgent:
    name: Test Agent
    llm:
      provider: ollama
      model: llama2
      temperature: 0.8
      max_tokens: 2000
      api_key: null
      base_url: http://localhost:11434/v1
    persona_template: null
    retrieval_query_template: null
    retrieval_top_k: 10
    enabled: true
""")
        
        agents = AppConfig.load_agents_from_yaml(str(agents_yaml))
        assert "TestAgent" in agents
        assert agents["TestAgent"].name == "Test Agent"
        assert agents["TestAgent"].llm.provider == LLMProvider.OLLAMA
        assert agents["TestAgent"].llm.model == "llama2"
        assert agents["TestAgent"].llm.temperature == 0.8
        assert agents["TestAgent"].llm.max_tokens == 2000
        assert agents["TestAgent"].retrieval_top_k == 10
        assert agents["TestAgent"].enabled is True
    
    def test_load_agents_from_yaml_with_name_field(self, tmp_path):
        """Test loading agents from YAML with custom name field."""
        agents_yaml = tmp_path / "agents.yaml"
        agents_yaml.write_text("""
agents:
  Narrator:
    name: Story Narrator
    llm:
      provider: openai
      model: gpt-3.5-turbo
      api_key: test-key
""")
        
        agents = AppConfig.load_agents_from_yaml(str(agents_yaml))
        assert "Narrator" in agents
        assert agents["Narrator"].name == "Story Narrator"
        assert agents["Narrator"].llm.provider == LLMProvider.OPENAI
    
    def test_app_config_from_yaml_with_agents_yaml(self, tmp_path):
        """Test loading AppConfig from YAML with agents.yaml."""
        # Create a main config file
        main_config = tmp_path / "config.yaml"
        main_config.write_text("""
retrieval:
  bm25_weight: 0.6
  vector_weight: 0.4
session:
  memory_window_size: 15
""")
        
        # Create agents.yaml
        agents_yaml = tmp_path / "agents.yaml"
        agents_yaml.write_text("""
agents:
  Narrator:
    name: Narrator
    llm:
      provider: ollama
      model: llama2
      api_key: null
      base_url: http://localhost:11434/v1
    enabled: true
""")
        
        config = AppConfig.from_yaml(str(main_config), agents_yaml_path=str(agents_yaml))
        assert "Narrator" in config.agents
        assert config.agents["Narrator"].name == "Narrator"
        assert config.retrieval.bm25_weight == 0.6
        assert config.session.memory_window_size == 15
    
    def test_app_config_from_dict_with_name_field(self):
        """Test AppConfig from_dict handles name field correctly."""
        config_dict = {
            "agents": {
                "narrator": {
                    "name": "Custom Narrator Name",
                    "llm": {
                        "provider": "openai",
                        "model": "gpt-3.5-turbo",
                        "api_key": "test-key",
                    },
                }
            },
        }
        
        config = AppConfig.from_dict(config_dict)
        assert "narrator" in config.agents
        assert config.agents["narrator"].name == "Custom Narrator Name"
    
    def test_load_agents_from_yaml_actual_file(self):
        """Test loading agents from actual config/agents.yaml file."""
        from pathlib import Path
        import os
        
        # Get project root (assuming tests are in tests/ directory)
        project_root = Path(__file__).parent.parent
        agents_yaml_path = project_root / "config" / "agents.yaml"
        
        if agents_yaml_path.exists():
            agents = AppConfig.load_agents_from_yaml(str(agents_yaml_path))
            
            # Verify we loaded the expected agents
            expected_agents = ["Narrator", "ScenePlanner", "NPCManager", "RulesReferee"]
            for agent_name in expected_agents:
                assert agent_name in agents, f"Expected agent {agent_name} not found in loaded agents"
                assert agents[agent_name].name == agent_name or agents[agent_name].name is not None
                assert agents[agent_name].llm.provider == LLMProvider.OLLAMA
                assert agents[agent_name].enabled is True


class TestSession:
    """Test session management."""
    
    def test_session_creation(self, session_config):
        """Test creating a new session."""
        session = GameSession(
            session_id="test-123",
            config=session_config,
        )
        assert session.session_id == "test-123"
        assert session.state["current_scene"] is None
        assert session.state["active_npcs"] == []
    
    def test_add_turn(self, game_session):
        """Test adding a turn to session."""
        turn = Turn(
            turn_number=1,
            player_command="Test command",
            agent_outputs={"narrator": {"content": "Test output"}},
        )
        game_session.add_turn(turn)
        assert len(game_session.turns) == 1
        assert game_session.turns[0].turn_number == 1
    
    def test_sliding_window_memory(self, session_config):
        """Test sliding window memory application."""
        session_config.memory_window_size = 3
        session_config.max_tokens = 500
        
        session = GameSession(
            session_id="test",
            config=session_config,
        )
        
        # Add multiple turns
        for i in range(5):
            turn = Turn(
                turn_number=i + 1,
                player_command=f"Command {i+1}",
                agent_outputs={"agent": {"content": f"Output {i+1}"}},
            )
            session.add_turn(turn)
        
        # Memory should be limited
        assert len(session.state["memory"]) <= 3
    
    def test_get_memory_context(self, game_session):
        """Test getting formatted memory context."""
        turn = Turn(
            turn_number=1,
            player_command="Test command",
            agent_outputs={"narrator": {"content": "Test output"}},
        )
        game_session.add_turn(turn)
        
        context = game_session.get_memory_context()
        assert "Previous conversation:" in context
        assert "Test command" in context
    
    def test_session_to_dict(self, game_session):
        """Test session serialization."""
        session_dict = game_session.to_dict()
        assert session_dict["session_id"] == game_session.session_id
        assert "turn_count" in session_dict
        assert "current_scene" in session_dict
    
    def test_session_expiration(self, session_config):
        """Test session expiration check."""
        session_config.session_ttl_seconds = 1
        session = GameSession(
            session_id="test",
            config=session_config,
        )
        
        # Should not be expired immediately
        assert not session.is_expired()
        
        # After TTL, should be expired (but we can't easily test this without time travel)
        # This is a basic test that the method exists and works


class TestSessionManager:
    """Test session manager."""
    
    def test_create_session(self, session_config):
        """Test creating a new session."""
        manager = SessionManager(session_config)
        session = manager.create_session()
        
        assert session is not None
        assert session.session_id in manager.list_sessions()
    
    def test_get_session(self, session_config):
        """Test getting a session."""
        manager = SessionManager(session_config)
        session = manager.create_session()
        
        retrieved = manager.get_session(session.session_id)
        assert retrieved == session
    
    def test_get_nonexistent_session(self, session_config):
        """Test getting a nonexistent session."""
        manager = SessionManager(session_config)
        retrieved = manager.get_session("nonexistent")
        assert retrieved is None
    
    def test_delete_session(self, session_config):
        """Test deleting a session."""
        manager = SessionManager(session_config)
        session = manager.create_session()
        
        assert manager.delete_session(session.session_id) is True
        assert manager.get_session(session.session_id) is None
        assert manager.delete_session("nonexistent") is False
    
    def test_list_sessions(self, session_config):
        """Test listing sessions."""
        manager = SessionManager(session_config)
        session1 = manager.create_session()
        session2 = manager.create_session()
        
        sessions = manager.list_sessions()
        assert session1.session_id in sessions
        assert session2.session_id in sessions
    
    def test_session_count(self, session_config):
        """Test getting session count."""
        manager = SessionManager(session_config)
        assert manager.get_session_count() == 0
        
        manager.create_session()
        assert manager.get_session_count() == 1
        
        manager.create_session()
        assert manager.get_session_count() == 2


class TestOrchestrator:
    """Test game orchestrator."""
    
    def test_execute_turn(self, game_session, sample_retrieval_results):
        """Test executing a turn with agents."""
        mock_agent = MockAgent(
            AgentConfig(
                name="test_agent",
                llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", api_key="test"),
            )
        )
        
        agents = {"test_agent": mock_agent}
        orchestrator = GameOrchestrator(agents)
        
        result = orchestrator.execute_turn(
            session=game_session,
            player_command="Test command",
            retrieval_results=sample_retrieval_results,
        )
        
        assert "turn_number" in result
        assert "outputs" in result
        assert "test_agent" in result["outputs"]
    
    def test_orchestrator_with_disabled_agent(self, game_session, sample_retrieval_results):
        """Test orchestrator skips disabled agents."""
        agent_config = AgentConfig(
            name="disabled_agent",
            llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", api_key="test"),
            enabled=False,
        )
        mock_agent = MockAgent(agent_config)
        
        agents = {"disabled_agent": mock_agent}
        orchestrator = GameOrchestrator(agents)
        
        result = orchestrator.execute_turn(
            session=game_session,
            player_command="Test",
            retrieval_results=sample_retrieval_results,
        )
        
        # Disabled agent should not be in outputs
        assert "disabled_agent" not in result["outputs"]
    
    def test_orchestrator_error_handling(self, game_session, sample_retrieval_results):
        """Test orchestrator handles agent errors gracefully."""
        class FailingAgent(BaseAgent):
            def process(self, context: AgentContext) -> AgentOutput:
                raise Exception("Agent error")
        
        failing_agent = FailingAgent(
            AgentConfig(
                name="failing_agent",
                llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", api_key="test"),
            )
        )
        
        agents = {"failing_agent": failing_agent}
        orchestrator = GameOrchestrator(agents)
        
        result = orchestrator.execute_turn(
            session=game_session,
            player_command="Test",
            retrieval_results=sample_retrieval_results,
        )
        
        # Should have error output
        assert "failing_agent" in result["outputs"]
        assert "error" in result["outputs"]["failing_agent"]


class TestRetrievalManager:
    """Test retrieval manager."""
    
    def test_retrieve(self, mock_retriever):
        """Test retrieval operation."""
        manager = RetrievalManager(mock_retriever)
        results = manager.retrieve("test query", top_k=5)
        
        assert len(results) == 1
        assert results[0].chunk_text == "Mock chunk"
        mock_retriever.retrieve.assert_called_once_with("test query", 5)
    
    def test_retrieval_caching(self, mock_retriever):
        """Test retrieval result caching."""
        manager = RetrievalManager(mock_retriever)
        
        # First call
        results1 = manager.retrieve("test query", top_k=5)
        
        # Second call (should use cache)
        results2 = manager.retrieve("test query", top_k=5)
        
        # Should only call retriever once
        assert mock_retriever.retrieve.call_count == 1
        assert results1 == results2
    
    def test_clear_cache(self, mock_retriever):
        """Test clearing retrieval cache."""
        manager = RetrievalManager(mock_retriever)
        manager.retrieve("query1")
        manager.clear_cache()
        
        # Next call should hit retriever again
        manager.retrieve("query1")
        assert mock_retriever.retrieve.call_count == 2


class TestBaseAgent:
    """Test base agent functionality."""
    
    def test_agent_validation(self, mock_agent_config):
        """Test agent configuration validation."""
        agent = MockAgent(mock_agent_config)
        assert agent.validate_config() is True
    
    def test_agent_validation_missing_key(self):
        """Test agent validation fails with missing API key."""
        import os
        # Temporarily remove OPENAI_API_KEY if it exists
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            # This should raise ValueError during LLMConfig initialization
            # because __post_init__ will fail to find an API key
            with pytest.raises(ValueError, match="Could not set api_key"):
                config = AgentConfig(
                    name="test",
                    llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", api_key=None),
                    enabled=True,
                )
        finally:
            # Restore original key if it existed
            if original_key is not None:
                os.environ["OPENAI_API_KEY"] = original_key
    
    def test_agent_validation_ollama_no_key(self):
        """Test agent validation passes with Ollama (no API key required)."""
        config = AgentConfig(
            name="test",
            llm=LLMConfig(provider=LLMProvider.OLLAMA, model="llama2"),
            enabled=True,
        )
        # Should not raise during initialization, validation should pass
        agent = MockAgent(config)
        # Ollama doesn't require API key, so validation should pass
        assert agent.validate_config() is True
        # LLM client should be initialized (even if it won't work without Ollama running)
        assert agent.llm_client is not None
    
    def test_format_prompt(self, mock_agent_config):
        """Test prompt formatting."""
        agent = MockAgent(mock_agent_config)
        template = "Hello {name}, you are {role}."
        result = agent.format_prompt(template, name="Alice", role="narrator")
        assert result == "Hello Alice, you are narrator."
    
    def test_extract_citations(self, mock_agent_config, sample_retrieval_results):
        """Test citation extraction."""
        agent = MockAgent(mock_agent_config)
        citations = agent.extract_citations(sample_retrieval_results)
        assert len(citations) == 2
        assert citations[0] == "[1]"
        assert citations[1] == "[2]"
    
    @patch('src.core.base_agent.openai.OpenAI')
    def test_llm_client_ollama_initialization(self, mock_openai):
        """Test LLMClient initializes correctly with Ollama."""
        from src.core.base_agent import LLMClient
        
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2",
            base_url="http://localhost:11434/v1",
        )
        
        client = LLMClient(config)
        
        # Verify OpenAI client was called with correct parameters
        mock_openai.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )
        assert client.config.provider == LLMProvider.OLLAMA

