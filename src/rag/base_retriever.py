"""Base retriever interface for pluggable retrieval components."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..core.base_agent import RetrievalResult


class BaseRetriever(ABC):
    """Abstract base class for retrieval implementations."""
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional filters to apply (e.g., chunk_id, metadata)
            
        Returns:
            List of RetrievalResult objects, sorted by relevance
        """
        pass
    
    @abstractmethod
    def retrieve_with_scores(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Retrieve chunks with relevance scores.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects with scores
        """
        pass

