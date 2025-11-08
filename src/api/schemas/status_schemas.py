"""Pydantic schemas for status API endpoints."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SystemState(str, Enum):
    """Overall system state."""
    READY = "ready"
    PROCESSING_CORPUS = "processing_corpus"
    PROCESSING_REQUEST = "processing_request"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"


class ConnectionStatus(str, Enum):
    """Connection status for components."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class ComponentStatus(BaseModel):
    """Status of a system component."""
    name: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    message: Optional[str] = Field(None, description="Status message")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details"
    )


class SystemStatusResponse(BaseModel):
    """System-wide status information."""
    state: SystemState = Field(..., description="Overall system state")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    active_sessions: int = Field(..., description="Number of active sessions")
    total_turns: int = Field(..., description="Total turns processed")
    memory_usage_mb: Optional[float] = Field(
        None,
        description="Memory usage in megabytes"
    )
    timestamp: str = Field(..., description="Status timestamp")


class CorpusStatusResponse(BaseModel):
    """Corpus and indexing status."""
    corpus_name: Optional[str] = Field(None, description="Corpus name or title")
    corpus_path: Optional[str] = Field(None, description="Path to corpus file")
    total_chunks: int = Field(..., description="Total number of chunks indexed")
    bm25_status: ConnectionStatus = Field(
        ...,
        description="BM25 index status"
    )
    vector_db_status: ConnectionStatus = Field(
        ...,
        description="Vector database connection status"
    )
    vector_db_provider: Optional[str] = Field(
        None,
        description="Vector database provider"
    )
    collection_name: Optional[str] = Field(
        None,
        description="Vector database collection name"
    )
    total_documents: int = Field(
        ...,
        description="Total documents in vector database"
    )
    embedding_model: Optional[str] = Field(
        None,
        description="Embedding model used"
    )
    embedding_dimension: Optional[int] = Field(
        None,
        description="Embedding dimension"
    )
    last_ingestion: Optional[str] = Field(
        None,
        description="Last ingestion timestamp"
    )
    ingestion_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Statistics from last ingestion"
    )


class AgentStatusResponse(BaseModel):
    """Status of a single agent."""
    agent_name: str = Field(..., description="Agent name")
    enabled: bool = Field(..., description="Whether agent is enabled")
    llm_status: ConnectionStatus = Field(
        ...,
        description="LLM connection status"
    )
    llm_provider: str = Field(..., description="LLM provider (OpenAI, Gemini, Ollama)")
    llm_model: str = Field(..., description="LLM model name")
    last_call_timestamp: Optional[str] = Field(
        None,
        description="Timestamp of last successful call"
    )
    total_calls: int = Field(
        default=0,
        description="Total calls since startup"
    )
    successful_calls: int = Field(
        default=0,
        description="Number of successful calls"
    )
    failed_calls: int = Field(
        default=0,
        description="Number of failed calls"
    )
    average_response_time: Optional[float] = Field(
        None,
        description="Average response time in seconds"
    )
    last_error: Optional[str] = Field(
        None,
        description="Last error message if any"
    )
    config_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent configuration summary"
    )


class RetrievalStatusResponse(BaseModel):
    """Retrieval system status."""
    hybrid_retrieval_enabled: bool = Field(
        ...,
        description="Whether hybrid retrieval is enabled"
    )
    bm25_status: ConnectionStatus = Field(
        ...,
        description="BM25 retriever status"
    )
    vector_status: ConnectionStatus = Field(
        ...,
        description="Vector retriever status"
    )
    fusion_strategy: str = Field(..., description="Fusion strategy (RRF, weighted)")
    query_rewriting_enabled: bool = Field(
        ...,
        description="Whether query rewriting is enabled"
    )
    cache_enabled: bool = Field(..., description="Whether caching is enabled")
    cache_hit_rate: Optional[float] = Field(
        None,
        description="Cache hit rate (0-1)"
    )
    cached_queries: int = Field(
        default=0,
        description="Number of cached queries"
    )
    total_retrievals: int = Field(
        default=0,
        description="Total retrievals since startup"
    )
