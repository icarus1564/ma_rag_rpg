"""ChromaDB vector database provider implementation."""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from ...utils.logging import get_logger
from ...utils.debug_logging import debug_log_method
from .base import BaseVectorDB, VectorDocument, VectorSearchResult

logger = get_logger(__name__)


class ChromaVectorDB(BaseVectorDB):
    """ChromaDB implementation of vector database interface."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ChromaDB client.
        
        Args:
            config: Configuration dictionary with:
                - persist_directory: Directory for persistent storage
                - in_memory: Whether to use in-memory mode
        """
        self.persist_directory = config.get("persist_directory", "data/vector_db")
        self.in_memory = config.get("in_memory", False)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize ChromaDB client."""
        if self.in_memory:
            self.client = chromadb.Client()
        else:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
        logger.info("ChromaDB client initialized", in_memory=self.in_memory)
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the vector database connection.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        # Already initialized in __init__, but update config if needed
        self.persist_directory = config.get("persist_directory", self.persist_directory)
        self.in_memory = config.get("in_memory", self.in_memory)
        if self.client is None:
            self._initialize_client()

    @debug_log_method
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
        if self.collection_exists(collection_name):
            logger.warning("Collection already exists", collection=collection_name)
            return
        
        # ChromaDB doesn't require explicit dimension specification
        # but we can store it in metadata
        collection_metadata = metadata or {}
        collection_metadata["embedding_dimension"] = embedding_dimension
        
        self.client.create_collection(
            name=collection_name,
            metadata=collection_metadata
        )
        logger.info("Collection created", collection=collection_name, dimension=embedding_dimension)

    @debug_log_method
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
        if not self.collection_exists(collection_name):
            raise ValueError(f"Collection does not exist: {collection_name}")
        
        collection = self.client.get_collection(collection_name)
        
        # Prepare data for ChromaDB
        ids = [doc.id for doc in documents]
        texts = [doc.text for doc in documents]
        embeddings = [doc.embedding for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info("Documents added", collection=collection_name, count=len(documents))

    @debug_log_method
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
        if not self.collection_exists(collection_name):
            raise ValueError(f"Collection does not exist: {collection_name}")
        
        collection = self.client.get_collection(collection_name)
        
        # Convert filters to ChromaDB where clause format
        where_clause = None
        if filters:
            where_clause = filters
        
        # Perform search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )
        
        # Convert to VectorSearchResult format
        search_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                # ChromaDB returns distances, convert to similarity scores
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = 1.0 / (1.0 + distance)  # Convert distance to similarity
                
                search_results.append(VectorSearchResult(
                    document_id=results["ids"][0][i],
                    text=results["documents"][0][i] if results.get("documents") else "",
                    score=score,
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else {}
                ))
        
        logger.debug("Search completed", collection=collection_name, results=len(search_results))
        return search_results
    
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
        """
        if not self.collection_exists(collection_name):
            logger.warning("Collection does not exist", collection=collection_name)
            return
        
        self.client.delete_collection(collection_name)
        logger.info("Collection deleted", collection=collection_name)
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.list_collections()
            return any(col.name == collection_name for col in collections)
        except Exception as e:
            logger.error("Error checking collection existence", error=str(e))
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection statistics (count, dimension, etc.)
        """
        if not self.collection_exists(collection_name):
            raise ValueError(f"Collection does not exist: {collection_name}")
        
        collection = self.client.get_collection(collection_name)
        count = collection.count()
        
        # Get dimension from metadata or sample embedding
        dimension = None
        if collection.metadata and "embedding_dimension" in collection.metadata:
            dimension = collection.metadata["embedding_dimension"]
        else:
            # Try to get dimension from a sample document
            sample = collection.peek(limit=1)
            if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                dimension = len(sample["embeddings"][0])
        
        return {
            "count": count,
            "dimension": dimension,
            "metadata": collection.metadata or {}
        }
    
    def close(self) -> None:
        """Close connections and cleanup resources."""
        # ChromaDB persistent client doesn't need explicit close
        # but we can reset the client reference
        self.client = None
        logger.info("ChromaDB client closed")

