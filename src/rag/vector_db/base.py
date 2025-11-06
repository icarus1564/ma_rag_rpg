"""Abstract interface for vector database providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VectorDocument:
    """Represents a document with vector embedding."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class VectorSearchResult:
    """Result from vector search."""
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class BaseVectorDB(ABC):
    """Abstract interface for vector database providers."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the vector database connection.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        pass
    
    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a new collection/index.
        
        Args:
            collection_name: Name of the collection to create
            embedding_dimension: Dimension of embeddings (e.g., 384, 768)
            metadata: Optional metadata for the collection
        """
        pass
    
    @abstractmethod
    def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> None:
        """Add documents to the collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of documents to add
        """
        pass
    
    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar documents.
        
        Args:
            collection_name: Name of the collection to search
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results sorted by relevance
        """
        pass
    
    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
        """
        pass
    
    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if collection exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection statistics (count, dimension, etc.)
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connections and cleanup resources."""
        pass

