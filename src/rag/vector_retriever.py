"""Vector-based retriever implementation."""

from typing import List, Optional, Dict, Any
from .base_retriever import BaseRetriever
from ..core.base_agent import RetrievalResult
from .vector_db.base import BaseVectorDB
from ..ingestion.embedder import Embedder
from ..utils.logging import get_logger

logger = get_logger(__name__)


class VectorRetriever(BaseRetriever):
    """Vector-based retriever."""
    
    def __init__(
        self,
        vector_db: BaseVectorDB,
        collection_name: str,
        embedder: Embedder
    ):
        """Initialize vector retriever.
        
        Args:
            vector_db: Vector DB instance
            collection_name: Name of the collection
            embedder: Embedder instance
        """
        self.vector_db = vector_db
        self.collection_name = collection_name
        self.embedder = embedder
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using vector search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of RetrievalResult objects
        """
        logger.debug("Vector retrieval", query=query[:50], top_k=top_k)
        
        # Generate query embedding
        query_embeddings = self.embedder.embed([query])
        if not query_embeddings:
            logger.warning("Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]
        
        # Search vector DB
        results = self.vector_db.search(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )
        
        # Convert results to RetrievalResult
        retrieval_results = [
            RetrievalResult(
                chunk_text=result.text,
                score=result.score,
                chunk_id=result.document_id,
                metadata=result.metadata
            )
            for result in results
        ]
        
        logger.debug("Vector retrieval completed", 
                    query=query[:50], 
                    results_count=len(retrieval_results))
        
        return retrieval_results
    
    def retrieve_with_scores(
        self,
        query: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """Retrieve with scores.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects with scores
        """
        # Stub implementation
        return self.retrieve(query, top_k)

