"""FastAPI application setup."""

import os
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .endpoints import ingestion, search, game, status
from src.core.config import AppConfig
from src.core.retrieval_manager import RetrievalManager
from src.core.session_manager import SessionManager
from src.core.orchestrator import GameOrchestrator
from src.core.game_loop import GameLoop
from src.agents.narrator import NarratorAgent
from src.agents.scene_planner import ScenePlannerAgent
from src.agents.npc_manager import NPCManagerAgent
from src.agents.rules_referee import RulesRefereeAgent
from src.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

# Global application state
_app_config: Optional[AppConfig] = None
_retrieval_manager: Optional[RetrievalManager] = None
_session_manager: Optional[SessionManager] = None
_orchestrator: Optional[GameOrchestrator] = None
_game_loop: Optional[GameLoop] = None
_startup_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events using the modern lifespan pattern.
    """
    global _app_config, _retrieval_manager, _session_manager, _orchestrator, _game_loop, _startup_time

    # Startup
    _startup_time = time.time()
    logger.info("Starting Multi-Agent RAG RPG API")

    # Setup logging
    setup_logging()

    try:
        # Load configuration
        logger.info("Loading configuration")
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        agents_config_path = os.getenv("AGENTS_CONFIG_PATH", "config/agents.yaml")

        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}, using defaults")
            _app_config = AppConfig()
        else:
            _app_config = AppConfig.from_yaml(config_path, agents_config_path)

        logger.info("Configuration loaded successfully")

        # Initialize retrieval manager
        logger.info("Initializing retrieval manager")
        _retrieval_manager = RetrievalManager(_app_config)

        # Try to load indices if they exist
        try:
            bm25_path = Path(_app_config.ingestion.bm25_index_path)
            metadata_path = Path(_app_config.ingestion.chunk_metadata_path)

            if bm25_path.exists() and metadata_path.exists():
                logger.info("Loading existing indices")
                _retrieval_manager.load_indices(
                    str(bm25_path),
                    str(metadata_path),
                    _app_config.vector_db.get_collection_name()
                )
                logger.info("Indices loaded successfully")
            else:
                logger.warning("No existing indices found - run ingestion first")
        except Exception as e:
            logger.warning(f"Could not load indices: {e}")

        # Initialize session manager
        logger.info("Initializing session manager")
        _session_manager = SessionManager(_app_config.session)

        # Initialize agents
        logger.info("Initializing agents")
        agents = {}

        try:
            if "narrator" in _app_config.agents:
                agents["narrator"] = NarratorAgent(
                    _app_config.agents["narrator"],
                    _retrieval_manager
                )

            if "scene_planner" in _app_config.agents:
                agents["scene_planner"] = ScenePlannerAgent(
                    _app_config.agents["scene_planner"],
                    _retrieval_manager
                )

            if "npc_manager" in _app_config.agents:
                agents["npc_manager"] = NPCManagerAgent(
                    _app_config.agents["npc_manager"],
                    _retrieval_manager
                )

            if "rules_referee" in _app_config.agents:
                agents["rules_referee"] = RulesRefereeAgent(
                    _app_config.agents["rules_referee"],
                    _retrieval_manager
                )

            logger.info(f"Initialized {len(agents)} agents: {list(agents.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}", exc_info=True)
            # Continue with empty agents dict if agent initialization fails

        # Initialize orchestrator
        logger.info("Initializing orchestrator")
        _orchestrator = GameOrchestrator(agents)

        # Initialize game loop
        logger.info("Initializing game loop")
        _game_loop = GameLoop(_orchestrator, _retrieval_manager)

        # Set dependencies in endpoints
        game.set_game_dependencies(_session_manager, _game_loop)
        status.set_status_dependencies(
            _session_manager,
            _orchestrator,
            _retrieval_manager,
            _app_config
        )

        logger.info("Multi-Agent RAG RPG API startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    # Yield control to the application
    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent RAG RPG API")

    try:
        # Close vector DB connections
        if _retrieval_manager and hasattr(_retrieval_manager, 'hybrid_retriever'):
            if _retrieval_manager.hybrid_retriever and _retrieval_manager.hybrid_retriever.vector_retriever:
                try:
                    _retrieval_manager.hybrid_retriever.vector_retriever.vector_db.close()
                    logger.info("Vector DB connections closed")
                except Exception as e:
                    logger.warning(f"Error closing vector DB: {e}")

        # Cleanup sessions
        if _session_manager:
            session_count = _session_manager.get_session_count()
            logger.info(f"Cleaning up {session_count} active sessions")

        logger.info("Shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


app = FastAPI(
    title="Multi-Agent RAG RPG API",
    description="API for the Multi-Agent RAG RPG Game",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/ui", StaticFiles(directory=str(static_path), html=True), name="ui")
    logger.info(f"Static files mounted at /ui from {static_path}")
else:
    logger.warning(f"Static files directory not found at {static_path}")

# Include routers
app.include_router(ingestion.router)
app.include_router(search.router)
app.include_router(game.router)
app.include_router(status.router)


@app.get("/")
async def root():
    """
    Root endpoint - redirects to the UI.

    Returns:
        Redirect response to /ui/index.html
    """
    return RedirectResponse(url="/ui/index.html")


@app.get("/health")
async def health():
    """
    Health check endpoint with real component status.

    Returns:
        Health status with component details
    """
    logger.debug("Health check requested")

    components = {}
    overall_healthy = True

    # Check BM25 index
    try:
        if _retrieval_manager and hasattr(_retrieval_manager, 'hybrid_retriever'):
            if _retrieval_manager.hybrid_retriever and _retrieval_manager.hybrid_retriever.bm25_retriever:
                if _retrieval_manager.hybrid_retriever.bm25_retriever.is_loaded():
                    components["bm25_index"] = "loaded"
                else:
                    components["bm25_index"] = "not_loaded"
                    overall_healthy = False
            else:
                components["bm25_index"] = "not_initialized"
                overall_healthy = False
        else:
            components["bm25_index"] = "not_available"
            overall_healthy = False
    except Exception as e:
        components["bm25_index"] = f"error: {str(e)}"
        overall_healthy = False

    # Check vector DB
    total_documents = 0
    collection_name = "unknown"
    try:
        if _retrieval_manager and hasattr(_retrieval_manager, 'hybrid_retriever'):
            if _retrieval_manager.hybrid_retriever and _retrieval_manager.hybrid_retriever.vector_retriever:
                vector_db = _retrieval_manager.hybrid_retriever.vector_retriever.vector_db
                if _app_config:
                    collection_name = _app_config.vector_db.get_collection_name()
                    if vector_db.collection_exists(collection_name):
                        components["vector_db"] = "connected"
                        stats = vector_db.get_collection_stats(collection_name)
                        total_documents = stats.get("count", 0)
                    else:
                        components["vector_db"] = "collection_not_found"
                        overall_healthy = False
                else:
                    components["vector_db"] = "config_not_loaded"
                    overall_healthy = False
            else:
                components["vector_db"] = "not_initialized"
                overall_healthy = False
        else:
            components["vector_db"] = "not_available"
            overall_healthy = False
    except Exception as e:
        components["vector_db"] = f"error: {str(e)}"
        overall_healthy = False

    # Check session manager
    try:
        if _session_manager:
            components["session_manager"] = "active"
            components["active_sessions"] = _session_manager.get_session_count()
        else:
            components["session_manager"] = "not_initialized"
            overall_healthy = False
    except Exception as e:
        components["session_manager"] = f"error: {str(e)}"
        overall_healthy = False

    # Check agents
    try:
        if _orchestrator:
            components["agents"] = f"{len(_orchestrator.agents)}_agents_loaded"
        else:
            components["agents"] = "not_initialized"
            overall_healthy = False
    except Exception as e:
        components["agents"] = f"error: {str(e)}"
        overall_healthy = False

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "components": components,
        "collection": collection_name,
        "total_documents": total_documents,
        "uptime_seconds": time.time() - _startup_time if _startup_time > 0 else 0,
    }

