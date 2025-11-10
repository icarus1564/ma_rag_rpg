"""Status API endpoints for monitoring system health and components."""

import time
import os
from typing import Dict, Any, List, Optional
from collections.abc import Iterable
from fastapi import APIRouter, HTTPException
from datetime import datetime

# psutil is optional for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from ..schemas.status_schemas import (
    SystemStatusResponse,
    SystemState,
    CorpusStatusResponse,
    AgentStatusResponse,
    RetrievalStatusResponse,
    ConnectionStatus,
)
from src.core.session_manager import SessionManager
from src.core.orchestrator import GameOrchestrator
from src.core.retrieval_manager import RetrievalManager
from src.core.config import AppConfig
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/status", tags=["status"])

# Global state (will be initialized in app startup)
_session_manager: SessionManager = None
_orchestrator: GameOrchestrator = None
_retrieval_manager: RetrievalManager = None
_app_config: AppConfig = None
_startup_time: float = time.time()
_total_turns: int = 0
_agent_stats: Dict[str, Dict[str, Any]] = {}


def set_status_dependencies(
    session_manager: SessionManager,
    orchestrator: GameOrchestrator,
    retrieval_manager: RetrievalManager,
    app_config: AppConfig,
):
    """Set dependencies for status endpoints."""
    global _session_manager, _orchestrator, _retrieval_manager, _app_config
    _session_manager = session_manager
    _orchestrator = orchestrator
    _retrieval_manager = retrieval_manager
    _app_config = app_config


def increment_turn_count():
    """Increment total turns counter."""
    global _total_turns
    _total_turns += 1


def record_agent_call(agent_name: str, success: bool, duration: float, error: Optional[str] = None):
    """Record an agent call for statistics."""
    global _agent_stats

    if agent_name not in _agent_stats:
        _agent_stats[agent_name] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration": 0.0,
            "last_call_timestamp": None,
            "last_error": None,
        }

    stats = _agent_stats[agent_name]
    stats["total_calls"] += 1
    stats["total_duration"] += duration
    stats["last_call_timestamp"] = datetime.now().isoformat()

    if success:
        stats["successful_calls"] += 1
    else:
        stats["failed_calls"] += 1
        if error:
            stats["last_error"] = error


@router.get("/system", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get overall system status.

    Returns:
        SystemStatusResponse with system-wide information
    """
    logger.debug("Getting system status")

    try:
        # Determine system state
        active_sessions = _session_manager.get_session_count() if _session_manager else 0

        # Simple state determination
        if active_sessions > 0:
            state = SystemState.READY
        else:
            state = SystemState.WAITING_FOR_USER

        # Get memory usage if possible
        memory_usage_mb = None
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                memory_usage_mb = process.memory_info().rss / 1024 / 1024  # Convert to MB
            except Exception:
                pass

        return SystemStatusResponse(
            state=state,
            uptime_seconds=time.time() - _startup_time,
            active_sessions=active_sessions,
            total_turns=_total_turns,
            memory_usage_mb=memory_usage_mb,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error("Failed to get system status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


@router.get("/corpus", response_model=CorpusStatusResponse)
async def get_corpus_status():
    """
    Get corpus and indexing status.

    Returns:
        CorpusStatusResponse with corpus information
    """
    logger.debug("Getting corpus status")

    try:
        # Get corpus info from config
        corpus_path = None
        corpus_name = None
        embedding_model = None
        embedding_dimension = None

        loaded_corpora: Optional[List[str]] = None

        if _app_config:
            corpus_path = _app_config.ingestion.corpus_path
            corpus_name = os.path.basename(corpus_path) if corpus_path else None
            embedding_model = _app_config.ingestion.embedding_model

            # Determine embedding dimension based on model
            if "MiniLM" in embedding_model:
                embedding_dimension = 384
            elif "mpnet" in embedding_model:
                embedding_dimension = 768
            elif "ada-002" in embedding_model:
                embedding_dimension = 1536

        # Check BM25 index status
        bm25_status = ConnectionStatus.UNKNOWN
        if _retrieval_manager and hasattr(_retrieval_manager, 'hybrid_retriever'):
            if _retrieval_manager.hybrid_retriever and _retrieval_manager.hybrid_retriever.bm25_retriever:
                bm25_retriever = _retrieval_manager.hybrid_retriever.bm25_retriever
                if bm25_retriever.is_loaded():
                    bm25_status = ConnectionStatus.CONNECTED

                    # Extract loaded corpus info from metadata
                    metadata = getattr(bm25_retriever, "metadata", None)
                    if metadata and isinstance(metadata, dict) and len(metadata) > 0:
                        # Get first chunk's metadata to extract source
                        first_chunk_meta = next(iter(metadata.values()), None)
                        if first_chunk_meta:
                            # Extract source from ChunkMetadata object or dict
                            actual_corpus_path = None
                            if hasattr(first_chunk_meta, "source"):
                                actual_corpus_path = first_chunk_meta.source
                            elif isinstance(first_chunk_meta, dict):
                                actual_corpus_path = first_chunk_meta.get("source")

                            if actual_corpus_path:
                                # Override config values with actual loaded corpus
                                corpus_path = str(actual_corpus_path)
                                corpus_name = os.path.basename(corpus_path)
                                loaded_corpora = [corpus_path]

                                logger.debug(
                                    "Extracted loaded corpus from metadata",
                                    corpus_name=corpus_name,
                                    corpus_path=corpus_path
                                )
                else:
                    bm25_status = ConnectionStatus.DISCONNECTED

        # Check vector DB status
        vector_db_status = ConnectionStatus.UNKNOWN
        vector_db_provider = None
        collection_name = None
        total_documents = 0

        if _retrieval_manager and hasattr(_retrieval_manager, 'hybrid_retriever'):
            if _retrieval_manager.hybrid_retriever and _retrieval_manager.hybrid_retriever.vector_retriever:
                try:
                    vector_retriever = _retrieval_manager.hybrid_retriever.vector_retriever
                    vector_db = vector_retriever.vector_db

                    # Check if collection exists
                    if _app_config:
                        collection_name = _app_config.vector_db.get_collection_name()
                        if vector_db.collection_exists(collection_name):
                            vector_db_status = ConnectionStatus.CONNECTED
                            stats = vector_db.get_collection_stats(collection_name)
                            total_documents = stats.get("count", 0)
                            vector_db_provider = _app_config.vector_db.provider
                        else:
                            vector_db_status = ConnectionStatus.DISCONNECTED
                except Exception as e:
                    logger.warning("Failed to check vector DB status", error=str(e))
                    vector_db_status = ConnectionStatus.ERROR

        # Get total chunks from metadata or BM25 index
        total_chunks = 0
        if bm25_status == ConnectionStatus.CONNECTED and _retrieval_manager:
            try:
                total_chunks = len(_retrieval_manager.hybrid_retriever.bm25_retriever.chunks)
            except Exception:
                pass

        return CorpusStatusResponse(
            corpus_name=corpus_name,
            corpus_path=corpus_path,
            loaded_corpora=loaded_corpora,
            total_chunks=total_chunks,
            bm25_status=bm25_status,
            vector_db_status=vector_db_status,
            vector_db_provider=vector_db_provider,
            collection_name=collection_name,
            total_documents=total_documents,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            last_ingestion=None,  # TODO: Track this in ingestion pipeline
            ingestion_stats=None,
        )

    except Exception as e:
        logger.error("Failed to get corpus status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get corpus status: {str(e)}")


@router.get("/agents", response_model=List[AgentStatusResponse])
async def get_agents_status():
    """
    Get status of all agents.

    Returns:
        List of AgentStatusResponse for each agent
    """
    logger.debug("Getting agents status")

    try:
        if _orchestrator is None:
            return []

        agent_statuses = []

        for agent_name, agent in _orchestrator.agents.items():
            # Get agent stats
            stats = _agent_stats.get(agent_name, {})

            # Determine LLM status
            llm_status = ConnectionStatus.UNKNOWN
            if stats.get("total_calls", 0) > 0:
                if stats.get("failed_calls", 0) == stats.get("total_calls", 0):
                    llm_status = ConnectionStatus.ERROR
                elif stats.get("last_call_timestamp"):
                    llm_status = ConnectionStatus.CONNECTED
                else:
                    llm_status = ConnectionStatus.DISCONNECTED

            # Calculate average response time
            avg_response_time = None
            if stats.get("total_calls", 0) > 0:
                avg_response_time = stats.get("total_duration", 0) / stats["total_calls"]

            agent_status = AgentStatusResponse(
                agent_name=agent_name,
                enabled=agent.config.enabled,
                llm_status=llm_status,
                llm_provider=agent.config.llm.provider.value,
                llm_model=agent.config.llm.model,
                last_call_timestamp=stats.get("last_call_timestamp"),
                total_calls=stats.get("total_calls", 0),
                successful_calls=stats.get("successful_calls", 0),
                failed_calls=stats.get("failed_calls", 0),
                average_response_time=avg_response_time,
                last_error=stats.get("last_error"),
                config_summary={
                    "temperature": agent.config.llm.temperature,
                    "max_tokens": agent.config.llm.max_tokens,
                    "retrieval_top_k": agent.config.retrieval_top_k,
                },
            )

            agent_statuses.append(agent_status)

        return agent_statuses

    except Exception as e:
        logger.error("Failed to get agents status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agents status: {str(e)}")


@router.get("/retrieval", response_model=RetrievalStatusResponse)
async def get_retrieval_status():
    """
    Get retrieval system status.

    Returns:
        RetrievalStatusResponse with retrieval system information
    """
    logger.debug("Getting retrieval status")

    try:
        # Check retrieval manager
        if _retrieval_manager is None:
            raise HTTPException(status_code=500, detail="Retrieval manager not initialized")

        # Get BM25 status
        bm25_status = ConnectionStatus.UNKNOWN
        if hasattr(_retrieval_manager, 'hybrid_retriever') and _retrieval_manager.hybrid_retriever:
            if _retrieval_manager.hybrid_retriever.bm25_retriever:
                if _retrieval_manager.hybrid_retriever.bm25_retriever.is_loaded():
                    bm25_status = ConnectionStatus.CONNECTED
                else:
                    bm25_status = ConnectionStatus.DISCONNECTED

        # Get vector status
        vector_status = ConnectionStatus.UNKNOWN
        if hasattr(_retrieval_manager, 'hybrid_retriever') and _retrieval_manager.hybrid_retriever:
            if _retrieval_manager.hybrid_retriever.vector_retriever:
                try:
                    # Try to check if vector DB is accessible
                    vector_db = _retrieval_manager.hybrid_retriever.vector_retriever.vector_db
                    if _app_config:
                        collection_name = _app_config.vector_db.get_collection_name()
                        if vector_db.collection_exists(collection_name):
                            vector_status = ConnectionStatus.CONNECTED
                        else:
                            vector_status = ConnectionStatus.DISCONNECTED
                except Exception:
                    vector_status = ConnectionStatus.ERROR

        # Get config
        fusion_strategy = "unknown"
        query_rewriting_enabled = False
        if _app_config:
            fusion_strategy = _app_config.retrieval.fusion_strategy
            query_rewriting_enabled = _app_config.retrieval.query_rewriter_enabled

        # Get cache stats
        cache_enabled = hasattr(_retrieval_manager, 'cache')
        cache_hit_rate = None
        cached_queries = 0
        total_retrievals = 0

        if cache_enabled and _retrieval_manager.cache:
            cached_queries = len(_retrieval_manager.cache)
            # Calculate hit rate if we track it
            # For now, just count cached queries

        return RetrievalStatusResponse(
            hybrid_retrieval_enabled=True,
            bm25_status=bm25_status,
            vector_status=vector_status,
            fusion_strategy=fusion_strategy,
            query_rewriting_enabled=query_rewriting_enabled,
            cache_enabled=cache_enabled,
            cache_hit_rate=cache_hit_rate,
            cached_queries=cached_queries,
            total_retrievals=total_retrievals,
        )

    except Exception as e:
        logger.error("Failed to get retrieval status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval status: {str(e)}")


@router.get("/config")
async def get_config():
    """
    Get current application configuration.

    Returns:
        Dictionary with full application configuration
    """
    logger.debug("Getting application configuration")

    try:
        if _app_config is None:
            raise HTTPException(status_code=500, detail="Configuration not loaded")

        # Build config response
        config_response = {
            "agents": {},
            "retrieval": {
                "bm25_weight": _app_config.retrieval.bm25_weight,
                "vector_weight": _app_config.retrieval.vector_weight,
                "chunk_size": _app_config.retrieval.chunk_size,
                "chunk_overlap": _app_config.retrieval.chunk_overlap,
                "top_k": _app_config.retrieval.top_k,
                "fusion_strategy": _app_config.retrieval.fusion_strategy,
                "rrf_k": _app_config.retrieval.rrf_k,
                "query_rewriter_enabled": _app_config.retrieval.query_rewriter_enabled,
            },
            "session": {
                "memory_window_size": _app_config.session.memory_window_size,
                "max_tokens": _app_config.session.max_tokens,
                "sliding_window": _app_config.session.sliding_window,
                "session_ttl_seconds": _app_config.session.session_ttl_seconds,
            },
            "ingestion": {
                "corpus_path": _app_config.ingestion.corpus_path,
                "corpus_filename": os.path.basename(_app_config.ingestion.corpus_path),
                "chunk_size": _app_config.ingestion.chunk_size,
                "chunk_overlap": _app_config.ingestion.chunk_overlap,
                "embedding_model": _app_config.ingestion.embedding_model,
                "bm25_index_path": _app_config.ingestion.bm25_index_path,
                "vector_index_path": _app_config.ingestion.vector_index_path,
                "chunk_metadata_path": _app_config.ingestion.chunk_metadata_path,
            },
            "vector_db": {
                "provider": _app_config.vector_db.provider,
                "collection_name": _app_config.vector_db.get_collection_name(),
            },
            "api": {
                "log_level": _app_config.log_level,
                "host": _app_config.api_host,
                "port": _app_config.api_port,
            },
        }

        # Add agent configs
        for agent_name, agent_config in _app_config.agents.items():
            config_response["agents"][agent_name] = {
                "name": agent_config.name,
                "enabled": agent_config.enabled,
                "llm": {
                    "provider": agent_config.llm.provider.value,
                    "model": agent_config.llm.model,
                    "temperature": agent_config.llm.temperature,
                    "max_tokens": agent_config.llm.max_tokens,
                    "base_url": agent_config.llm.base_url,
                },
                "retrieval_top_k": agent_config.retrieval_top_k,
            }

        return config_response

    except Exception as e:
        logger.error("Failed to get configuration", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.post("/agents/{agent_name}/test")
async def test_agent_connection(agent_name: str):
    """
    Test connection to a specific agent's LLM provider.

    Args:
        agent_name: Name of the agent to test

    Returns:
        Dictionary with connection test results
    """
    logger.info(f"Testing connection for agent: {agent_name}")

    try:
        if _orchestrator is None:
            raise HTTPException(status_code=500, detail="Orchestrator not initialized")

        # Get the agent
        agent = _orchestrator.agents.get(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")

        # Test connection
        success, error_message = agent.test_connection()

        # Record the test result
        import time
        start_time = time.time()
        duration = time.time() - start_time

        record_agent_call(agent_name, success, duration, error_message)

        return {
            "agent_name": agent_name,
            "success": success,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test agent connection: {agent_name}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {str(e)}")
