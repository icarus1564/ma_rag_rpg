"""Retrieval manager coordinates retrieval for agents."""

from typing import List, Optional, Dict, Any
from .base_agent import RetrievalResult
from ..rag.base_retriever import BaseRetriever
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RetrievalManager:
    """Manages retrieval operations for agents."""
    
    def __init__(self, retriever: BaseRetriever):
        """
        Initialize retrieval manager.
        
        Args:
            retriever: The retriever instance to use (should be HybridRetriever)
        """
        self.retriever = retriever
        self.logger = get_logger(__name__)
        # Cache for retrieval results per query
        self._cache: Dict[str, List[RetrievalResult]] = {}
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        agent_name: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            agent_name: Optional agent name for logging
            use_cache: Whether to use cached results
            
        Returns:
            List of RetrievalResult objects
        """
        cache_key = f"{agent_name}:{query}:{top_k}" if agent_name else f"{query}:{top_k}"
        
        if use_cache and cache_key in self._cache:
            self.logger.debug("Using cached retrieval results", query=query[:50])
            return self._cache[cache_key]
        
        try:
            results = self.retriever.retrieve(query, top_k)
            self.logger.debug(
                "Retrieval completed",
                query=query[:50],
                results_count=len(results),
                agent=agent_name,
            )
            
            if use_cache:
                self._cache[cache_key] = results
            
            return results
        
        except Exception as e:
            self.logger.error("Retrieval failed", error=str(e), query=query[:50])
            return []
    
    def clear_cache(self) -> None:
        """Clear the retrieval cache."""
        self._cache.clear()
        self.logger.debug("Retrieval cache cleared")

