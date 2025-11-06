"""FastAPI application setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import ingestion, search
from ...core.config import AppConfig
from ...core.retrieval_manager import RetrievalManager
from ...utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Multi-Agent RAG RPG API",
    description="API for RAG infrastructure",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router)
app.include_router(search.router)


@app.get("/health")
async def health():
    """Health check endpoint.
    
    Returns:
        Health status
    """
    # Stub implementation
    logger.debug("Health check requested")
    # TODO: Implement health check
    # Check BM25 index loaded
    # Check vector DB connected
    # Check collection exists
    return {
        "status": "healthy",
        "components": {
            "bm25_index": "loaded",
            "vector_db": "connected",
            "collection": "corpus_embeddings",
            "total_documents": 0
        }
    }


@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("Starting RAG API")
    # TODO: Implement startup initialization
    # Setup logging
    # Load config
    # Initialize retrieval manager
    # Initialize vector DB
    # Load BM25 index
    # Set retrieval manager in search endpoint
    setup_logging()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down RAG API")
    # TODO: Implement shutdown cleanup
    # Close vector DB connections
    # Cleanup resources

