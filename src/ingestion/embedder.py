"""Embedding generation for text chunks."""

from typing import List, Optional
from sentence_transformers import SentenceTransformer
from ..utils.logging import get_logger

logger = get_logger(__name__)


class Embedder:
    """Generate embeddings for text."""
    
    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        """Initialize embedder with model.
        
        Args:
            model_name: Name of embedding model
            cache_dir: Optional cache directory for models
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        logger.info("Initializing embedder", model=self.model_name, cache_dir=self.cache_dir)
        try:
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=self.cache_dir
            )
            logger.info("Embedder initialized successfully", model=self.model_name)
        except Exception as e:
            logger.error("Failed to initialize embedder", error=str(e), model=self.model_name)
            raise
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        logger.debug("Generating embeddings", text_count=len(texts))
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=False, show_progress_bar=False)
            return [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
        except Exception as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """Generate embeddings in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        logger.debug("Generating embeddings in batches", text_count=len(texts), batch_size=batch_size)
        all_embeddings = []
        
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = self.model.encode(batch, convert_to_numpy=False, show_progress_bar=False)
                batch_embeddings = [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
                all_embeddings.extend(batch_embeddings)
            return all_embeddings
        except Exception as e:
            logger.error("Failed to generate batch embeddings", error=str(e))
            raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self.model is None:
            # Default dimension for all-MiniLM-L6-v2
            return 384
        return self.model.get_sentence_embedding_dimension()

