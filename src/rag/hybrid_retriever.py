"""Hybrid retriever combining BM25 and vector search."""

from typing import List, Optional, Dict, Any, Literal
from .base_retriever import BaseRetriever
from ..core.base_agent import RetrievalResult
from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever
from ..utils.logging import get_logger

logger = get_logger(__name__)


class HybridRetriever(BaseRetriever):
    """Hybrid retriever combining BM25 and vector search."""
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        fusion_strategy: Literal["rrf", "weighted"] = "rrf",
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60
    ):
        """Initialize hybrid retriever.
        
        Args:
            bm25_retriever: BM25 retriever instance
            vector_retriever: Vector retriever instance
            fusion_strategy: Fusion strategy ("rrf" or "weighted")
            bm25_weight: Weight for BM25 scores (for weighted fusion)
            vector_weight: Weight for vector scores (for weighted fusion)
            rrf_k: RRF constant (for RRF fusion)
        """
        self.bm25_retriever = bm25_retriever
        self.vector_retriever = vector_retriever
        self.fusion_strategy = fusion_strategy
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.rrf_k = rrf_k
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using hybrid approach.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of RetrievalResult objects
        """
        logger.debug("Hybrid retrieval", query=query[:50], top_k=top_k, strategy=self.fusion_strategy)
        
        # Get results from both retrievers
        bm25_results = self.bm25_retriever.retrieve(query, top_k=top_k * 2, filters=filters)
        vector_results = self.vector_retriever.retrieve(query, top_k=top_k * 2, filters=filters)
        
        if self.fusion_strategy == "rrf":
            fused_results = self._fuse_rrf(bm25_results, vector_results, top_k)
        else:
            fused_results = self._fuse_weighted(bm25_results, vector_results, top_k)
        
        logger.debug("Hybrid retrieval completed", 
                    query=query[:50], 
                    results_count=len(fused_results),
                    strategy=self.fusion_strategy)
        
        return fused_results[:top_k]
    
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
    
    def _fuse_rrf(
        self,
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Fuse results using Reciprocal Rank Fusion.
        
        Args:
            bm25_results: BM25 retrieval results
            vector_results: Vector retrieval results
            top_k: Number of results to return
            
        Returns:
            Fused results sorted by score
        """
        logger.debug("Fusing results with RRF", bm25_count=len(bm25_results), vector_count=len(vector_results))
        
        # RRF formula: score = 1 / (k + rank)
        # Create score dictionary mapping chunk_id to RRF score
        rrf_scores: Dict[str, float] = {}
        chunk_data: Dict[str, RetrievalResult] = {}
        
        # Add BM25 results
        for rank, result in enumerate(bm25_results, start=1):
            rrf_score = 1.0 / (self.rrf_k + rank)
            if result.chunk_id in rrf_scores:
                rrf_scores[result.chunk_id] += rrf_score
            else:
                rrf_scores[result.chunk_id] = rrf_score
                chunk_data[result.chunk_id] = result
        
        # Add vector results
        for rank, result in enumerate(vector_results, start=1):
            rrf_score = 1.0 / (self.rrf_k + rank)
            if result.chunk_id in rrf_scores:
                rrf_scores[result.chunk_id] += rrf_score
            else:
                rrf_scores[result.chunk_id] = rrf_score
                chunk_data[result.chunk_id] = result
        
        # Sort by combined RRF score
        sorted_chunks = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create fused results
        fused_results = []
        for chunk_id, rrf_score in sorted_chunks[:top_k]:
            result = chunk_data[chunk_id]
            # Create new result with RRF score
            fused_results.append(RetrievalResult(
                chunk_text=result.chunk_text,
                score=rrf_score,
                chunk_id=result.chunk_id,
                metadata=result.metadata
            ))
        
        return fused_results
    
    def _fuse_weighted(
        self,
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Fuse results using weighted score combination.
        
        Args:
            bm25_results: BM25 retrieval results
            vector_results: Vector retrieval results
            top_k: Number of results to return
            
        Returns:
            Fused results sorted by score
        """
        logger.debug("Fusing results with weighted scores", bm25_count=len(bm25_results), vector_count=len(vector_results))
        
        # Normalize scores to 0-1 range for both result sets
        def normalize_scores(results: List[RetrievalResult]) -> List[RetrievalResult]:
            if not results:
                return []
            
            scores = [r.score for r in results]
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score if max_score != min_score else 1.0
            
            normalized = []
            for result in results:
                normalized_score = (result.score - min_score) / score_range if score_range > 0 else 0.5
                normalized.append(RetrievalResult(
                    chunk_text=result.chunk_text,
                    score=normalized_score,
                    chunk_id=result.chunk_id,
                    metadata=result.metadata
                ))
            return normalized
        
        normalized_bm25 = normalize_scores(bm25_results)
        normalized_vector = normalize_scores(vector_results)
        
        # Combine scores: final = bm25_weight * bm25_score + vector_weight * vector_score
        combined_scores: Dict[str, float] = {}
        chunk_data: Dict[str, RetrievalResult] = {}
        
        # Add BM25 scores
        for result in normalized_bm25:
            combined_scores[result.chunk_id] = self.bm25_weight * result.score
            chunk_data[result.chunk_id] = result
        
        # Add vector scores
        for result in normalized_vector:
            if result.chunk_id in combined_scores:
                combined_scores[result.chunk_id] += self.vector_weight * result.score
            else:
                combined_scores[result.chunk_id] = self.vector_weight * result.score
                chunk_data[result.chunk_id] = result
        
        # Sort by combined score
        sorted_chunks = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create fused results
        fused_results = []
        for chunk_id, combined_score in sorted_chunks[:top_k]:
            result = chunk_data[chunk_id]
            fused_results.append(RetrievalResult(
                chunk_text=result.chunk_text,
                score=combined_score,
                chunk_id=result.chunk_id,
                metadata=result.metadata
            ))
        
        return fused_results

