"""Pydantic models for ingestion endpoint."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class IngestionRequest(BaseModel):
    """Request schema for ingestion endpoint."""
    corpus_path: str = Field(..., description="Path to corpus file")
    collection_name: str = Field(
        default="corpus_embeddings",
        description="Name of vector DB collection"
    )
    chunk_size: int = Field(default=500, ge=100, le=2000, description="Chunk size in characters")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="Chunk overlap in characters")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing collection")


class IngestionResponse(BaseModel):
    """Response schema for ingestion endpoint."""
    status: str = Field(..., description="Status: success or error")
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    code: Optional[str] = None

