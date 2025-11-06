"""BM25 index building and management."""

from typing import List
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BM25Indexer:
    """Build and manage BM25 index."""
    
    def __init__(self):
        """Initialize BM25 indexer."""
        self.index = None
    
    def build_index(self, chunks: List[str]) -> BM25Okapi:
        """Build BM25 index from chunks.
        
        Args:
            chunks: List of chunk texts
            
        Returns:
            BM25Okapi index object
        """
        logger.info("Building BM25 index", chunk_count=len(chunks))
        
        if not chunks:
            raise ValueError("Cannot build BM25 index from empty chunk list")
        
        # Tokenize chunks (simple whitespace tokenization)
        tokenized_chunks = [chunk.lower().split() for chunk in chunks]
        
        # Build BM25 index
        self.index = BM25Okapi(tokenized_chunks)
        logger.info("BM25 index built successfully", chunk_count=len(chunks))
        
        return self.index
    
    def save_index(self, index: BM25Okapi, path: str) -> None:
        """Save index to disk.
        
        Args:
            index: BM25 index to save
            path: File path to save to
        """
        logger.info("Saving BM25 index", path=path)
        
        # Create directory if needed
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Save index using pickle
        with open(path, "wb") as f:
            pickle.dump(index, f)
        
        logger.info("BM25 index saved successfully", path=path)
    
    def load_index(self, path: str) -> BM25Okapi:
        """Load index from disk.
        
        Args:
            path: File path to load from
            
        Returns:
            BM25Okapi index object
        """
        logger.info("Loading BM25 index", path=path)
        
        if not Path(path).exists():
            raise FileNotFoundError(f"BM25 index file not found: {path}")
        
        # Load index from pickle file
        with open(path, "rb") as f:
            index = pickle.load(f)
        
        self.index = index
        logger.info("BM25 index loaded successfully", path=path)
        
        return index

