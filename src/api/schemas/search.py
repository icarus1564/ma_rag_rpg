"""Pydantic models for search endpoint."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SearchRequest(BaseModel):
    """Request schema for search endpoint."""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    use_hybrid: bool = Field(default=True, description="Use hybrid retrieval")
    fusion_strategy: str = Field(default="rrf", pattern="^(rrf|weighted)$", description="Fusion strategy")
    rewrite_query: bool = Field(default=True, description="Rewrite query before search")
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Individual search result."""
    chunk_id: str
    chunk_text: str
    score: float
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response schema for search endpoint."""
    query: str
    rewritten_query: Optional[str] = None
    results: List[SearchResult]
    total_results: int
    retrieval_time_ms: float

