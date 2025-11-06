"""Configuration management for Multi-Agent RAG RPG."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any
from enum import Enum
import yaml
import os
from pathlib import Path


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: LLMProvider
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama or custom OpenAI-compatible endpoints
    
    def __post_init__(self):
        """Load API key and base URL from environment if not provided."""
        if self.api_key is None:
            match self.provider:
                case LLMProvider.OPENAI:
                    self.api_key = os.getenv("OPENAI_API_KEY")
                case LLMProvider.GEMINI:
                    self.api_key = os.getenv("GEMINI_API_KEY")
                case LLMProvider.OLLAMA:
                    # Ollama doesn't require an API key, but we can use a dummy value
                    self.api_key = "ollama"  # Placeholder, not actually used
        
        if self.api_key is None:
            #should never happen, but don't want to leave loose ends
            raise ValueError(f"LLMConfig: Could not set api_key due to invalid provider ${self.provider}")

        # Set default base_url for Ollama if not provided
        if self.provider == LLMProvider.OLLAMA and self.base_url is None:
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


@dataclass
class AgentConfig:
    """Configuration for an individual agent."""
    name: str
    llm: LLMConfig
    persona_template: Optional[str] = None
    retrieval_query_template: Optional[str] = None
    retrieval_top_k: int = 5
    enabled: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for retrieval system."""
    bm25_weight: float = 0.5
    vector_weight: float = 0.5
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 10
    fusion_strategy: Literal["rrf", "weighted"] = "rrf"
    rrf_k: int = 60  # For Reciprocal Rank Fusion
    query_rewriter_enabled: bool = True


@dataclass
class SessionConfig:
    """Configuration for game sessions."""
    memory_window_size: int = 10  # Number of turns to keep
    max_tokens: int = 8000  # Maximum tokens in session memory
    sliding_window: bool = True
    session_ttl_seconds: int = 3600  # 1 hour default


@dataclass
class IngestionConfig:
    """Configuration for data ingestion."""
    corpus_path: str = "data/corpus.txt"
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    bm25_index_path: str = "data/indices/bm25_index.pkl"
    vector_index_path: str = "data/indices/vector_index"
    chunk_metadata_path: str = "data/indices/chunks.json"


@dataclass
class VectorDBConfig:
    """Configuration for vector database."""
    provider: str = "chroma"  # chroma, pinecone, etc.
    chroma: Dict[str, Any] = field(default_factory=lambda: {
        "persist_directory": "data/vector_db",
        "collection_name": "corpus_embeddings",
        "in_memory": False
    })
    pinecone: Dict[str, Any] = field(default_factory=lambda: {
        "api_key": None,
        "environment": "us-west1-gcp",
        "index_name": "ma-rag-rpg-index",
        "dimension": 384
    })


@dataclass
class AppConfig:
    """Main application configuration."""
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    @classmethod
    def from_yaml(cls, config_path: str, agents_yaml_path: Optional[str] = None) -> "AppConfig":
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to main config YAML file
            agents_yaml_path: Optional path to agents.yaml file. If provided, agents will be loaded from this file.
                             If not provided and config_path doesn't contain agents, will try to load from config/agents.yaml.example
        """
        path = Path(config_path)
        if not path.exists():
            # Try relative to project root if absolute path doesn't exist
            project_root = Path(__file__).parent.parent.parent
            path = project_root / config_path
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        
        # Load agents from agents.yaml if specified or if not in main config
        # Note: If agents are loaded from agents.yaml, they will be loaded directly in from_dict
        # For now, we'll handle it by loading agents.yaml content and merging into config_dict
        if agents_yaml_path or "agents" not in config_dict:
            agents_path = agents_yaml_path or "config/agents.yaml.example"
            try:
                # Load agents.yaml as raw dict and merge into config_dict
                agents_yaml_path_obj = Path(agents_path)
                if not agents_yaml_path_obj.exists():
                    project_root = Path(__file__).parent.parent.parent
                    agents_yaml_path_obj = project_root / agents_path
                
                if agents_yaml_path_obj.exists():
                    with open(agents_yaml_path_obj, "r") as f:
                        agents_yaml_dict = yaml.safe_load(f)
                    
                    # Handle both structures: agents.yaml might have "agents:" root or "config:" root
                    if "config" in agents_yaml_dict and "agents" not in agents_yaml_dict:
                        agents_dict = agents_yaml_dict.get("config", {})
                    elif "agents" in agents_yaml_dict:
                        agents_dict = agents_yaml_dict["agents"]
                    else:
                        agents_dict = agents_yaml_dict
                    
                    # Merge agents into config_dict
                    if "agents" not in config_dict:
                        config_dict["agents"] = {}
                    config_dict["agents"].update(agents_dict)
            except FileNotFoundError:
                # If agents.yaml doesn't exist, continue with existing agents or empty dict
                if "agents" not in config_dict:
                    config_dict["agents"] = {}
        
        return cls.from_dict(config_dict)
    
    @classmethod
    def load_agents_from_yaml(cls, agents_yaml_path: str = "config/agents.yaml.example") -> Dict[str, AgentConfig]:
        """Load agent configurations from agents.yaml file.
        
        Args:
            agents_yaml_path: Path to agents.yaml file (relative to project root or absolute)
            
        Returns:
            Dictionary mapping agent keys to AgentConfig objects
        """
        path = Path(agents_yaml_path)
        if not path.exists():
            # Try relative to project root if absolute path doesn't exist
            project_root = Path(__file__).parent.parent.parent
            path = project_root / agents_yaml_path
            if not path.exists():
                raise FileNotFoundError(f"Agents config file not found: {agents_yaml_path}")
        
        with open(path, "r") as f:
            agents_dict = yaml.safe_load(f)
        
        # Handle both structures: agents.yaml might have "agents:" root or "config:" root
        if "config" in agents_dict and "agents" not in agents_dict:
            # If config.yaml structure, extract agents from config key
            agents_dict = agents_dict.get("config", {})
        elif "agents" in agents_dict:
            agents_dict = agents_dict["agents"]
        else:
            # Assume the root is the agents dict
            pass
        
        agents = {}
        for agent_key, agent_dict in agents_dict.items():
            llm_dict = agent_dict.get("llm", {})
            # Use name from agent_dict if provided, otherwise use the key
            agent_name = agent_dict.get("name", agent_key)
            
            llm_config = LLMConfig(
                provider=LLMProvider(llm_dict.get("provider", "openai")),
                model=llm_dict.get("model", "gpt-3.5-turbo"),
                temperature=llm_dict.get("temperature", 0.7),
                max_tokens=llm_dict.get("max_tokens", 1000),
                api_key=llm_dict.get("api_key") if llm_dict.get("api_key") is not None else None,
                base_url=llm_dict.get("base_url"),
            )
            agents[agent_key] = AgentConfig(
                name=agent_name,
                llm=llm_config,
                persona_template=agent_dict.get("persona_template") if agent_dict.get("persona_template") is not None else None,
                retrieval_query_template=agent_dict.get("retrieval_query_template") if agent_dict.get("retrieval_query_template") is not None else None,
                retrieval_top_k=agent_dict.get("retrieval_top_k", 5),
                enabled=agent_dict.get("enabled", True),
            )
        
        return agents
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "AppConfig":
        """Create configuration from dictionary."""
        # Build agent configs
        agents = {}
        if "agents" in config_dict:
            for agent_name, agent_dict in config_dict["agents"].items():
                llm_dict = agent_dict.get("llm", {})
                # Use name from agent_dict if provided, otherwise use the key
                agent_name_value = agent_dict.get("name", agent_name)
                
                llm_config = LLMConfig(
                    provider=LLMProvider(llm_dict.get("provider", "openai")),
                    model=llm_dict.get("model", "gpt-3.5-turbo"),
                    temperature=llm_dict.get("temperature", 0.7),
                    max_tokens=llm_dict.get("max_tokens", 1000),
                    api_key=llm_dict.get("api_key") if llm_dict.get("api_key") is not None else None,
                    base_url=llm_dict.get("base_url"),
                )
                agents[agent_name] = AgentConfig(
                    name=agent_name_value,
                    llm=llm_config,
                    persona_template=agent_dict.get("persona_template") if agent_dict.get("persona_template") is not None else None,
                    retrieval_query_template=agent_dict.get("retrieval_query_template") if agent_dict.get("retrieval_query_template") is not None else None,
                    retrieval_top_k=agent_dict.get("retrieval_top_k", 5),
                    enabled=agent_dict.get("enabled", True),
                )
        
        # Build retrieval config
        retrieval_dict = config_dict.get("retrieval", {})
        retrieval_config = RetrievalConfig(
            bm25_weight=retrieval_dict.get("bm25_weight", 0.5),
            vector_weight=retrieval_dict.get("vector_weight", 0.5),
            chunk_size=retrieval_dict.get("chunk_size", 500),
            chunk_overlap=retrieval_dict.get("chunk_overlap", 50),
            top_k=retrieval_dict.get("top_k", 10),
            fusion_strategy=retrieval_dict.get("fusion_strategy", "rrf"),
            rrf_k=retrieval_dict.get("rrf_k", 60),
            query_rewriter_enabled=retrieval_dict.get("query_rewriter_enabled", True),
        )
        
        # Build session config
        session_dict = config_dict.get("session", {})
        session_config = SessionConfig(
            memory_window_size=session_dict.get("memory_window_size", 10),
            max_tokens=session_dict.get("max_tokens", 8000),
            sliding_window=session_dict.get("sliding_window", True),
            session_ttl_seconds=session_dict.get("session_ttl_seconds", 3600),
        )
        
        # Build ingestion config
        ingestion_dict = config_dict.get("ingestion", {})
        ingestion_config = IngestionConfig(
            corpus_path=ingestion_dict.get("corpus_path", "data/corpus.txt"),
            chunk_size=ingestion_dict.get("chunk_size", 500),
            chunk_overlap=ingestion_dict.get("chunk_overlap", 50),
            embedding_model=ingestion_dict.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            bm25_index_path=ingestion_dict.get("bm25_index_path", "data/indices/bm25_index.pkl"),
            vector_index_path=ingestion_dict.get("vector_index_path", "data/indices/vector_index"),
            chunk_metadata_path=ingestion_dict.get("chunk_metadata_path", "data/indices/chunks.json"),
        )
        
        # Build vector DB config
        vector_db_dict = config_dict.get("vector_db", {})
        vector_db_config = VectorDBConfig(
            provider=vector_db_dict.get("provider", "chroma"),
            chroma=vector_db_dict.get("chroma", {
                "persist_directory": "data/vector_db",
                "collection_name": "corpus_embeddings",
                "in_memory": False
            }),
            pinecone=vector_db_dict.get("pinecone", {
                "api_key": os.getenv("PINECONE_API_KEY"),
                "environment": "us-west1-gcp",
                "index_name": "ma-rag-rpg-index",
                "dimension": 384
            })
        )
        
        return cls(
            agents=agents,
            retrieval=retrieval_config,
            session=session_config,
            ingestion=ingestion_config,
            vector_db=vector_db_config,
            log_level=config_dict.get("log_level", "INFO"),
            api_host=config_dict.get("api_host", "0.0.0.0"),
            api_port=config_dict.get("api_port", 8000),
        )
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)

