"""Retrieval manager coordinates retrieval for agents."""

from typing import List, Optional, Dict, Any
from .base_agent import RetrievalResult
from ..rag.base_retriever import BaseRetriever
from ..rag.query_rewriter import QueryRewriter
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RetrievalManager:
    """Manages retrieval operations for agents."""
    
    def __init__(
        self,
        retriever: BaseRetriever,
        query_rewriter: Optional[QueryRewriter] = None
    ):
        """
        Initialize retrieval manager.
        
        Args:
            retriever: The retriever instance to use (should be HybridRetriever)
            query_rewriter: Optional query rewriter instance
        """
        self.retriever = retriever
        self.query_rewriter = query_rewriter
        self.logger = get_logger(__name__)
        # Cache for retrieval results per query
        self._cache: Dict[str, List[RetrievalResult]] = {}
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        agent_name: Optional[str] = None,
        use_cache: bool = True,
        rewrite_query: bool = True,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            agent_name: Optional agent name for logging
            use_cache: Whether to use cached results
            rewrite_query: Whether to rewrite query before retrieval
            
        Returns:
            List of RetrievalResult objects
        """
        # Rewrite query if enabled
        original_query = query
        if rewrite_query and self.query_rewriter:
            query = self.query_rewriter.rewrite(query)
            if query != original_query:
                self.logger.debug("Query rewritten", original=original_query[:50], rewritten=query[:50])
        
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
    
    def rewrite_query(self, query: str) -> str:
        """Rewrite query for better retrieval.
        
        Args:
            query: Original query
            
        Returns:
            Rewritten query
        """
        if self.query_rewriter:
            return self.query_rewriter.rewrite(query)
        return query
    
    def clear_cache(self) -> None:
        """Clear the retrieval cache."""
        self._cache.clear()
        self.logger.debug("Retrieval cache cleared")

