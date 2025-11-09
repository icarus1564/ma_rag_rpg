"""Retrieval manager coordinates retrieval for agents."""

from typing import List, Optional, Dict, Any
from pathlib import Path
from .base_agent import RetrievalResult
from ..rag.base_retriever import BaseRetriever
from ..rag.query_rewriter import QueryRewriter
from ..rag.bm25_retriever import BM25Retriever
from ..rag.vector_retriever import VectorRetriever
from ..rag.hybrid_retriever import HybridRetriever
from ..rag.vector_db.factory import VectorDBFactory
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

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
        self.hybrid_retriever = retriever if isinstance(retriever, HybridRetriever) else None
        self.query_rewriter = query_rewriter
        self.logger = get_logger(__name__)
        # Cache for retrieval results per query
        self._cache: Dict[str, List[RetrievalResult]] = {}

    @classmethod
    def from_config(cls, config: "AppConfig") -> "RetrievalManager":
        """
        Create RetrievalManager from AppConfig.

        Args:
            config: Application configuration

        Returns:
            Initialized RetrievalManager
        """
        # Import here to avoid circular dependency
        from .config import AppConfig

        # Initialize BM25 retriever with lazy loading
        bm25_retriever = BM25Retriever(lazy_load=True)

        # Initialize vector retriever
        # Get provider-specific config
        if config.vector_db.provider == "chroma":
            vector_db_config = config.vector_db.chroma
        elif config.vector_db.provider == "pinecone":
            vector_db_config = config.vector_db.pinecone
        else:
            raise ValueError(f"Unsupported vector DB provider: {config.vector_db.provider}")

        vector_db = VectorDBFactory.create(config.vector_db.provider, vector_db_config)

        # Initialize embedder
        from ..ingestion.embedder import Embedder
        embedder = Embedder(model_name=config.ingestion.embedding_model)

        # Get collection name
        collection_name = config.vector_db.get_collection_name()

        vector_retriever = VectorRetriever(
            vector_db=vector_db,
            collection_name=collection_name,
            embedder=embedder
        )

        # Initialize hybrid retriever
        hybrid_retriever = HybridRetriever(
            bm25_retriever=bm25_retriever,
            vector_retriever=vector_retriever,
            fusion_strategy=config.retrieval.fusion_strategy,
            bm25_weight=config.retrieval.bm25_weight,
            vector_weight=config.retrieval.vector_weight,
            rrf_k=config.retrieval.rrf_k
        )

        # Initialize query rewriter if enabled
        query_rewriter = None
        if config.retrieval.query_rewriter_enabled:
            query_rewriter = QueryRewriter()

        return cls(retriever=hybrid_retriever, query_rewriter=query_rewriter)

    def load_indices(
        self,
        bm25_index_path: str,
        metadata_path: str,
        collection_name: str
    ) -> None:
        """
        Load pre-existing indices.

        Args:
            bm25_index_path: Path to BM25 index file
            metadata_path: Path to chunks metadata file
            collection_name: Vector DB collection name
        """
        if not self.hybrid_retriever:
            raise ValueError("HybridRetriever not initialized")

        # Load BM25 index
        if Path(bm25_index_path).exists() and Path(metadata_path).exists():
            self.hybrid_retriever.bm25_retriever.load_index(
                bm25_index_path,
                metadata_path
            )
            self.logger.info("BM25 index loaded", path=bm25_index_path)

        # Vector DB collection should already exist, just verify
        if self.hybrid_retriever.vector_retriever:
            vector_db = self.hybrid_retriever.vector_retriever.vector_db
            if vector_db.collection_exists(collection_name):
                self.logger.info("Vector DB collection verified", collection=collection_name)
            else:
                self.logger.warning("Vector DB collection not found", collection=collection_name)
    
    @debug_log_method
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

