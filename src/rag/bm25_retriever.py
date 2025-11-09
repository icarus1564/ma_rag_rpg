"""BM25-based retriever implementation."""

from typing import List, Optional, Dict, Any
from rank_bm25 import BM25Okapi
import pickle
from pathlib import Path
from .base_retriever import BaseRetriever
from ..core.base_agent import RetrievalResult
from ..ingestion.metadata_store import MetadataStore, ChunkMetadata
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)


class BM25Retriever(BaseRetriever):
    """BM25-based retriever."""
    
    def __init__(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None, lazy_load: bool = False):
        """Initialize BM25 retriever.

        Args:
            index_path: Path to BM25 index file
            metadata_path: Path to chunk metadata file
            lazy_load: If True, don't load indices immediately (default: False)
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata_store = MetadataStore()
        self.metadata = {}
        self.chunks = []
        self.index_to_chunk_id = {}

        if not lazy_load and index_path and metadata_path:
            self._load_index()
            self._load_metadata()
            self._load_chunks()
    
    def _load_index(self) -> None:
        """Load BM25 index from disk."""
        logger.info("Loading BM25 index", path=self.index_path)
        
        if not Path(self.index_path).exists():
            raise FileNotFoundError(f"BM25 index file not found: {self.index_path}")
        
        with open(self.index_path, "rb") as f:
            self.index = pickle.load(f)
        
        logger.info("BM25 index loaded successfully", path=self.index_path)
    
    def _load_metadata(self) -> None:
        """Load chunk metadata from disk."""
        logger.info("Loading chunk metadata", path=self.metadata_path)
        self.metadata = self.metadata_store.load_metadata(self.metadata_path)
        logger.info("Chunk metadata loaded successfully", 
                   path=self.metadata_path, 
                   count=len(self.metadata))
    
    def _load_chunks(self) -> None:
        """Load chunk texts from metadata."""
        logger.info("Loading chunk texts")
        # Sort metadata by chunk_index to match BM25 index order
        sorted_metadata = sorted(self.metadata.values(), key=lambda m: m.chunk_index)
        self.chunks = [meta.text for meta in sorted_metadata]
        # Create mapping from chunk_index to chunk_id
        self.index_to_chunk_id = {meta.chunk_index: meta.chunk_id for meta in sorted_metadata}
        logger.info("Chunk texts loaded", count=len(self.chunks))

    @debug_log_method
    def load_index(self, index_path: str, metadata_path: str) -> None:
        """Load BM25 index and metadata.

        Args:
            index_path: Path to BM25 index file
            metadata_path: Path to chunk metadata file
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self._load_index()
        self._load_metadata()
        self._load_chunks()

    def is_loaded(self) -> bool:
        """Check if index is loaded.

        Returns:
            True if index is loaded, False otherwise
        """
        return self.index is not None and len(self.chunks) > 0
    
    @debug_log_method
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using BM25.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of RetrievalResult objects
        """
        logger.debug("BM25 retrieval", query=query[:50], top_k=top_k)
        
        if self.index is None:
            raise ValueError("BM25 index not loaded")
        
        if not self.chunks:
            logger.warning("No chunks available for BM25 retrieval")
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get scores from BM25
        scores = self.index.get_scores(tokenized_query)
        
        # Create list of (score, index) pairs
        scored_chunks = list(enumerate(scores))
        
        # Sort by score (descending)
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Apply filters if provided
        filtered_results = []
        for chunk_idx, score in scored_chunks:
            # Map chunk index to chunk_id
            chunk_id = self.index_to_chunk_id.get(chunk_idx)
            if chunk_id is None:
                continue
            
            metadata = self.metadata.get(chunk_id)
            if metadata is None:
                continue
            
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if key in metadata.additional_metadata:
                        if metadata.additional_metadata[key] != value:
                            match = False
                            break
                    elif hasattr(metadata, key):
                        if getattr(metadata, key) != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if not match:
                    continue
            
            filtered_results.append((chunk_idx, score, metadata))
        
        # Normalize scores (optional - BM25 scores can be negative, so we normalize to 0-1)
        if filtered_results:
            max_score = max(score for _, score, _ in filtered_results)
            min_score = min(score for _, score, _ in filtered_results)
            score_range = max_score - min_score if max_score != min_score else 1.0
            
            normalized_results = []
            for chunk_idx, score, metadata in filtered_results[:top_k]:
                normalized_score = (score - min_score) / score_range if score_range > 0 else 0.5
                normalized_results.append(RetrievalResult(
                    chunk_text=metadata.text,
                    score=normalized_score,
                    chunk_id=metadata.chunk_id,
                    metadata={
                        "start_pos": metadata.start_pos,
                        "end_pos": metadata.end_pos,
                        "chunk_index": metadata.chunk_index,
                        "source": metadata.source,
                        **metadata.additional_metadata
                    }
                ))
            
            logger.debug("BM25 retrieval completed", 
                        query=query[:50], 
                        results_count=len(normalized_results))
            return normalized_results
        
        return []
    
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
        logger.debug("BM25 retrieval with scores", query=query[:50], top_k=top_k)
        # TODO: Implement BM25 retrieval with explicit scores
        # Similar to retrieve but with explicit scores
        return self.retrieve(query, top_k)

