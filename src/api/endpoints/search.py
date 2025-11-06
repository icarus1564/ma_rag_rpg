"""Search API endpoint."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
from ..schemas.search import SearchRequest, SearchResponse, SearchResult
from ...core.retrieval_manager import RetrievalManager
from ...utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# Global retrieval manager (will be initialized in app startup)
retrieval_manager: RetrievalManager = None


def set_retrieval_manager(manager: RetrievalManager) -> None:
    """Set the retrieval manager instance.
    
    Args:
        manager: RetrievalManager instance
    """
    global retrieval_manager
    retrieval_manager = manager


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search corpus using hybrid retrieval.
    
    Args:
        request: Search request
        
    Returns:
        SearchResponse with results
    """
    # Stub implementation
    logger.info("Search request received", query=request.query[:50], top_k=request.top_k)
    
    if retrieval_manager is None:
        raise HTTPException(status_code=503, detail="Retrieval manager not initialized")
    
    try:
        # TODO: Implement search endpoint
        # Rewrite query if enabled
        # Perform retrieval
        # Format results
        # Return response
        
        start_time = time.time()
        
        # Rewrite query if enabled
        query = request.query
        rewritten_query = None
        if request.rewrite_query:
            rewritten_query = retrieval_manager.rewrite_query(query)
            query = rewritten_query
        
        # Perform retrieval
        results = retrieval_manager.retrieve(
            query=query,
            top_k=request.top_k,
            rewrite_query=False  # Already rewritten
        )
        
        retrieval_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Format results
        search_results = [
            SearchResult(
                chunk_id=r.chunk_id,
                chunk_text=r.chunk_text,
                score=r.score,
                bm25_score=r.metadata.get("bm25_score") if r.metadata else None,
                vector_score=r.metadata.get("vector_score") if r.metadata else None,
                metadata=r.metadata or {}
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            rewritten_query=rewritten_query,
            results=search_results,
            total_results=len(search_results),
            retrieval_time_ms=retrieval_time
        )
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

