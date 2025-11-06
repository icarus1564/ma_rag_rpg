"""Factory for creating vector DB provider instances."""

from typing import Dict, Any
from .base import BaseVectorDB
from .chroma_provider import ChromaVectorDB
from .pinecone_provider import PineconeVectorDB
from ...utils.logging import get_logger

logger = get_logger(__name__)


class VectorDBFactory:
    """Factory for creating vector DB provider instances."""
    
    @staticmethod
    def create(provider: str, config: Dict[str, Any]) -> BaseVectorDB:
        """Create a vector DB provider instance.
        
        Args:
            provider: Provider name ("chroma", "pinecone", etc.)
            config: Provider-specific configuration
            
        Returns:
            Initialized vector DB provider instance
            
        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        
        if provider == "chroma":
            logger.info("Creating ChromaDB provider")
            return ChromaVectorDB(config)
        elif provider == "pinecone":
            logger.info("Creating Pinecone provider")
            return PineconeVectorDB(config)
        else:
            raise ValueError(f"Unsupported vector DB provider: {provider}")

