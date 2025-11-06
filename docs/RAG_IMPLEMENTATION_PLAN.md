# RAG Infrastructure Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for the RAG infrastructure. Each phase includes specific tasks, file structures, code interfaces, and test requirements.

## Prerequisites

- Python 3.11+ virtual environment activated
- All dependencies from `requirements.txt` installed
- Test corpus available in `data/corpus.txt`
- Configuration files in place

## Phase 1: Vector Database Abstraction Layer

### Goal
Create a provider-agnostic abstraction layer for vector databases, enabling easy swapping between ChromaDB, Pinecone, and future providers.

### Tasks

#### Task 1.1: Create Base Vector DB Interface

**File: `src/rag/vector_db/base.py`**

**Deliverables:**
- `BaseVectorDB` abstract class
- `VectorDocument` dataclass
- `VectorSearchResult` dataclass
- Complete type hints and docstrings

**Interface Specification:**
```python
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
```

**Tests:**
- `tests/test_rag/test_vector_db/test_base.py`
  - Test abstract class cannot be instantiated
  - Test interface methods are abstract

#### Task 1.2: Implement ChromaDB Provider

**File: `src/rag/vector_db/chroma_provider.py`**

**Deliverables:**
- `ChromaVectorDB` class implementing `BaseVectorDB`
- Full ChromaDB integration
- Error handling and logging
- Thread-safe operations

**Implementation Notes:**
- Use `chromadb.Client` for local persistence
- Support both persistent and in-memory modes
- Handle collection creation and document addition
- Implement similarity search with metadata filtering
- Add proper error handling for missing collections

**Key Methods:**
```python
class ChromaVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any]):
        """Initialize ChromaDB client."""
        self.persist_directory = config.get("persist_directory", "data/vector_db")
        self.in_memory = config.get("in_memory", False)
        self.client = chromadb.Client(
            chromadb.config.Settings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            )
        ) if not self.in_memory else chromadb.Client()
    
    def create_collection(
        self,
        collection_name: str,
        embedding_dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create ChromaDB collection."""
        # Implementation with error handling
        pass
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> None:
        """Add documents to ChromaDB collection."""
        # Batch add with proper formatting
        pass
    
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search ChromaDB collection."""
        # Convert filters to ChromaDB where clause format
        # Return results with scores
        pass
```

**Tests:**
- `tests/test_rag/test_vector_db/test_chroma_provider.py`
  - Test initialization (persistent and in-memory)
  - Test collection creation
  - Test document addition
  - Test search functionality
  - Test metadata filtering
  - Test collection deletion
  - Test error handling (missing collection, etc.)

#### Task 1.3: Implement Pinecone Provider (Stub)

**File: `src/rag/vector_db/pinecone_provider.py`**

**Deliverables:**
- `PineconeVectorDB` class implementing `BaseVectorDB`
- Basic Pinecone integration (stub for future implementation)
- API key authentication
- Index management

**Implementation Notes:**
- Use `pinecone.Pinecone` client
- Handle index creation and connection
- Implement upsert for document addition
- Implement query for similarity search
- Add proper error handling

**Tests:**
- `tests/test_rag/test_vector_db/test_pinecone_provider.py`
  - Test initialization with API key
  - Test index creation (mock)
  - Test document addition (mock)
  - Test search functionality (mock)
  - Test error handling

#### Task 1.4: Create Provider Factory

**File: `src/rag/vector_db/factory.py`**

**Deliverables:**
- `VectorDBFactory` class
- Provider creation logic
- Configuration validation

**Implementation:**
```python
from typing import Dict, Any
from .base import BaseVectorDB
from .chroma_provider import ChromaVectorDB
from .pinecone_provider import PineconeVectorDB

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
        if provider == "chroma":
            return ChromaVectorDB(config)
        elif provider == "pinecone":
            return PineconeVectorDB(config)
        else:
            raise ValueError(f"Unsupported vector DB provider: {provider}")
```

**Tests:**
- `tests/test_rag/test_vector_db/test_factory.py`
  - Test factory creates correct provider
  - Test factory raises error for unsupported provider
  - Test configuration passing

#### Task 1.5: Update Configuration

**File: `src/core/config.py`**

**Deliverables:**
- Add `VectorDBConfig` dataclass
- Update `AppConfig` to include vector DB config
- Add configuration loading from YAML

**Configuration Schema:**
```python
@dataclass
class VectorDBConfig:
    """Configuration for vector database."""
    provider: str = "chroma"  # chroma, pinecone, etc.
    chroma: Dict[str, Any] = field(default_factory=lambda: {
        "persist_directory": "data/vector_db",
        "collection_name": "corpus_embeddings",
        "in_memory": False
    })
    pinecone: Dict[str, Any] = field(default_factory=lambda: {
        "api_key": None,
        "environment": "us-west1-gcp",
        "index_name": "ma-rag-rpg-index",
        "dimension": 384
    })
```

**Tests:**
- `tests/test_core/test_config.py` (update existing)
  - Test vector DB config loading
  - Test default values
  - Test provider-specific config

---

## Phase 2: Ingestion Pipeline

### Goal
Implement a complete ingestion pipeline that processes corpus text, creates BM25 index, generates embeddings, and stores them in the vector database.

### Tasks

#### Task 2.1: Implement Chunker

**File: `src/ingestion/chunker.py`**

**Deliverables:**
- `Chunker` class with multiple strategies
- Sentence-based chunking
- Paragraph-based chunking
- Sliding window chunking
- Chunk metadata generation

**Interface:**
```python
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class Chunk:
    """Represents a text chunk."""
    id: str
    text: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]

class Chunker:
    """Text chunking with multiple strategies."""
    
    def chunk(
        self,
        text: str,
        strategy: Literal["sentence", "paragraph", "sliding_window"] = "sliding_window",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Chunk]:
        """Split text into chunks.
        
        Args:
            text: Input text to chunk
            strategy: Chunking strategy to use
            chunk_size: Target chunk size (characters or tokens)
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of Chunk objects
        """
        pass
```

**Tests:**
- `tests/test_ingestion/test_chunker.py`
  - Test sentence-based chunking
  - Test paragraph-based chunking
  - Test sliding window chunking
  - Test chunk size and overlap
  - Test edge cases (empty text, very short text)

#### Task 2.2: Implement BM25 Indexer

**File: `src/ingestion/bm25_indexer.py`**

**Deliverables:**
- `BM25Indexer` class
- Index building from chunks
- Index persistence (pickle)
- Index loading
- Tokenization and preprocessing

**Interface:**
```python
from rank_bm25 import BM25Okapi
from typing import List
import pickle

class BM25Indexer:
    """Build and manage BM25 index."""
    
    def __init__(self):
        """Initialize BM25 indexer."""
        pass
    
    def build_index(self, chunks: List[str]) -> BM25Okapi:
        """Build BM25 index from chunks.
        
        Args:
            chunks: List of chunk texts
            
        Returns:
            BM25Okapi index object
        """
        pass
    
    def save_index(self, index: BM25Okapi, path: str) -> None:
        """Save index to disk.
        
        Args:
            index: BM25 index to save
            path: File path to save to
        """
        pass
    
    def load_index(self, path: str) -> BM25Okapi:
        """Load index from disk.
        
        Args:
            path: File path to load from
            
        Returns:
            BM25Okapi index object
        """
        pass
```

**Tests:**
- `tests/test_ingestion/test_bm25_indexer.py`
  - Test index building
  - Test index persistence and loading
  - Test tokenization
  - Test retrieval from index

#### Task 2.3: Implement Embedder

**File: `src/ingestion/embedder.py`**

**Deliverables:**
- `Embedder` class
- Support for sentence-transformers models
- Support for OpenAI embeddings (optional)
- Batch processing
- Caching (optional)

**Interface:**
```python
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import openai  # Optional

class Embedder:
    """Generate embeddings for text."""
    
    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        """Initialize embedder with model.
        
        Args:
            model_name: Name of embedding model
            cache_dir: Optional cache directory for models
        """
        pass
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
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
        pass
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass
```

**Tests:**
- `tests/test_ingestion/test_embedder.py`
  - Test embedding generation
  - Test embedding dimensions
  - Test batch processing
  - Test different models
  - Test caching (if implemented)

#### Task 2.4: Implement Metadata Store

**File: `src/ingestion/metadata_store.py`**

**Deliverables:**
- `MetadataStore` class
- JSON-based storage
- Fast lookup by chunk ID
- Metadata schema

**Interface:**
```python
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    chunk_id: str
    text: str
    start_pos: int
    end_pos: int
    chunk_index: int
    source: str
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

class MetadataStore:
    """Store and retrieve chunk metadata."""
    
    def save_metadata(
        self,
        chunks: List[ChunkMetadata],
        path: str
    ) -> None:
        """Save chunk metadata to disk.
        
        Args:
            chunks: List of chunk metadata
            path: File path to save to
        """
        pass
    
    def load_metadata(self, path: str) -> Dict[str, ChunkMetadata]:
        """Load chunk metadata from disk.
        
        Args:
            path: File path to load from
            
        Returns:
            Dictionary mapping chunk_id to metadata
        """
        pass
    
    def get_chunk_metadata(
        self,
        chunk_id: str,
        metadata_path: str
    ) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk.
        
        Args:
            chunk_id: ID of the chunk
            metadata_path: Path to metadata file
            
        Returns:
            ChunkMetadata if found, None otherwise
        """
        pass
```

**Tests:**
- `tests/test_ingestion/test_metadata_store.py`
  - Test metadata saving and loading
  - Test chunk lookup
  - Test metadata schema validation

#### Task 2.5: Implement Ingestion Pipeline

**File: `src/ingestion/pipeline.py`**

**Deliverables:**
- `IngestionPipeline` class
- Full pipeline orchestration
- Progress tracking
- Error handling
- Statistics generation

**Interface:**
```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class IngestionResult:
    """Result from ingestion pipeline."""
    total_chunks: int
    bm25_index_path: str
    vector_db_collection: str
    metadata_path: str
    embedding_model: str
    embedding_dimension: int
    duration_seconds: float
    statistics: Dict[str, Any]

class IngestionPipeline:
    """Orchestrates the ingestion pipeline."""
    
    def __init__(
        self,
        chunker: Chunker,
        bm25_indexer: BM25Indexer,
        embedder: Embedder,
        vector_db: BaseVectorDB,
        metadata_store: MetadataStore
    ):
        """Initialize pipeline with components."""
        pass
    
    def ingest(
        self,
        corpus_path: str,
        collection_name: str = "corpus_embeddings",
        overwrite: bool = False,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> IngestionResult:
        """Run full ingestion pipeline.
        
        Args:
            corpus_path: Path to corpus text file
            collection_name: Name of vector DB collection
            overwrite: Whether to overwrite existing collection
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            IngestionResult with statistics
        """
        pass
```

**Tests:**
- `tests/test_ingestion/test_pipeline.py`
  - Test full ingestion pipeline
  - Test overwrite behavior
  - Test error handling
  - Test statistics generation
  - Test progress tracking

#### Task 2.6: Create Ingestion CLI Script

**File: `scripts/ingest.py`**

**Deliverables:**
- Command-line script for ingestion
- Argument parsing
- Configuration loading
- Progress reporting

**Interface:**
```python
#!/usr/bin/env python3
"""CLI script for corpus ingestion."""

import argparse
from pathlib import Path
from src.core.config import AppConfig
from src.ingestion.pipeline import IngestionPipeline
# ... imports ...

def main():
    parser = argparse.ArgumentParser(description="Ingest corpus for RAG")
    parser.add_argument(
        "--corpus",
        type=str,
        default="data/corpus.txt",
        help="Path to corpus file"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing indices"
    )
    # ... more arguments ...
    
    args = parser.parse_args()
    
    # Load config
    config = AppConfig.from_yaml(args.config)
    
    # Initialize components
    # ... component initialization ...
    
    # Run pipeline
    pipeline = IngestionPipeline(...)
    result = pipeline.ingest(
        corpus_path=args.corpus,
        collection_name=config.ingestion.vector_index_path,
        overwrite=args.overwrite
    )
    
    # Print results
    print(f"Ingestion complete: {result.total_chunks} chunks processed")
    # ...

if __name__ == "__main__":
    main()
```

**Tests:**
- `tests/test_scripts/test_ingest.py`
  - Test CLI argument parsing
  - Test script execution
  - Test error handling

---

## Phase 3: Retrieval System

### Goal
Implement BM25 retriever, vector retriever, hybrid retriever with fusion strategies, and query rewriter.

### Tasks

#### Task 3.1: Implement BM25 Retriever

**File: `src/rag/bm25_retriever.py`**

**Deliverables:**
- `BM25Retriever` class implementing `BaseRetriever`
- Index loading
- Query preprocessing
- Score normalization
- Top-k retrieval

**Implementation:**
```python
from .base_retriever import BaseRetriever, RetrievalResult
from rank_bm25 import BM25Okapi
import pickle
from typing import List, Optional, Dict, Any

class BM25Retriever(BaseRetriever):
    """BM25-based retriever."""
    
    def __init__(self, index_path: str, metadata_path: str):
        """Initialize BM25 retriever.
        
        Args:
            index_path: Path to BM25 index file
            metadata_path: Path to chunk metadata file
        """
        self.index = self._load_index(index_path)
        self.metadata = self._load_metadata(metadata_path)
        self.chunks = self._load_chunks()
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using BM25."""
        # Tokenize query
        # Get scores from BM25
        # Normalize scores
        # Apply filters if provided
        # Return top_k results
        pass
    
    def retrieve_with_scores(
        self,
        query: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """Retrieve with scores."""
        # Similar to retrieve but with explicit scores
        pass
```

**Tests:**
- `tests/test_rag/test_bm25_retriever.py`
  - Test retrieval with various queries
  - Test score ordering
  - Test filtering
  - Test top_k limiting

#### Task 3.2: Implement Vector Retriever

**File: `src/rag/vector_retriever.py`**

**Deliverables:**
- `VectorRetriever` class implementing `BaseRetriever`
- Vector DB integration via abstraction layer
- Query embedding generation
- Similarity search
- Metadata filtering

**Implementation:**
```python
from .base_retriever import BaseRetriever, RetrievalResult
from .vector_db.base import BaseVectorDB
from ..ingestion.embedder import Embedder
from typing import List, Optional, Dict, Any

class VectorRetriever(BaseRetriever):
    """Vector-based retriever."""
    
    def __init__(
        self,
        vector_db: BaseVectorDB,
        collection_name: str,
        embedder: Embedder
    ):
        """Initialize vector retriever."""
        self.vector_db = vector_db
        self.collection_name = collection_name
        self.embedder = embedder
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using vector search."""
        # Generate query embedding
        # Search vector DB
        # Convert results to RetrievalResult
        pass
```

**Tests:**
- `tests/test_rag/test_vector_retriever.py`
  - Test vector search
  - Test similarity scores
  - Test metadata filtering
  - Test top_k limiting

#### Task 3.3: Implement Hybrid Retriever

**File: `src/rag/hybrid_retriever.py`**

**Deliverables:**
- `HybridRetriever` class implementing `BaseRetriever`
- RRF fusion strategy
- Weighted score fusion strategy
- Score normalization
- Result deduplication

**Implementation:**
```python
from .base_retriever import BaseRetriever, RetrievalResult
from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever
from typing import List, Optional, Dict, Any, Literal

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
        """Initialize hybrid retriever."""
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
        """Retrieve using hybrid approach."""
        # Get results from both retrievers
        # Apply fusion strategy
        # Deduplicate results
        # Return top_k
        pass
    
    def _fuse_rrf(
        self,
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Fuse results using Reciprocal Rank Fusion."""
        # RRF formula: score = 1 / (k + rank)
        pass
    
    def _fuse_weighted(
        self,
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Fuse results using weighted score combination."""
        # Normalize scores
        # Combine: final = bm25_weight * bm25_score + vector_weight * vector_score
        pass
```

**Tests:**
- `tests/test_rag/test_hybrid_retriever.py`
  - Test RRF fusion
  - Test weighted fusion
  - Test result diversity
  - Test score normalization
  - Test deduplication

#### Task 3.4: Implement Query Rewriter

**File: `src/rag/query_rewriter.py`**

**Deliverables:**
- `QueryRewriter` class
- Query expansion (synonyms)
- Query normalization
- Optional LLM-based rewriting

**Implementation:**
```python
from typing import Optional
from nltk.corpus import wordnet
import nltk
from ..core.base_agent import LLMClient

class QueryRewriter:
    """Rewrite queries for better retrieval."""
    
    def __init__(
        self,
        enable_expansion: bool = True,
        enable_decomposition: bool = False,
        enable_llm_rewriting: bool = False,
        llm_client: Optional[LLMClient] = None
    ):
        """Initialize query rewriter."""
        self.enable_expansion = enable_expansion
        self.enable_decomposition = enable_decomposition
        self.enable_llm_rewriting = enable_llm_rewriting
        self.llm_client = llm_client
        self._download_nltk_data()
    
    def rewrite(self, query: str) -> str:
        """Rewrite query for better retrieval."""
        rewritten = query
        
        if self.enable_expansion:
            rewritten = self.expand(rewritten)
        
        if self.enable_llm_rewriting and self.llm_client:
            rewritten = self.llm_rewrite(rewritten)
        
        return rewritten
    
    def expand(self, query: str) -> str:
        """Expand query with synonyms."""
        # Extract keywords
        # Find synonyms using WordNet
        # Add synonyms to query
        pass
    
    def llm_rewrite(self, query: str) -> str:
        """Rewrite query using LLM."""
        # Use LLM to rewrite query for better retrieval
        pass
```

**Tests:**
- `tests/test_rag/test_query_rewriter.py`
  - Test query expansion
  - Test query normalization
  - Test LLM rewriting (mock)
  - Test edge cases

#### Task 3.5: Update Retrieval Manager

**File: `src/core/retrieval_manager.py`**

**Deliverables:**
- Update `RetrievalManager` to use `HybridRetriever`
- Integrate query rewriter
- Maintain existing interface

**Changes:**
- Replace `BaseRetriever` with `HybridRetriever`
- Add query rewriting before retrieval
- Update logging

**Tests:**
- `tests/test_core/test_retrieval_manager.py` (update existing)
  - Test hybrid retrieval
  - Test query rewriting integration
  - Test caching

---

## Phase 4: API Endpoints

### Goal
Implement FastAPI endpoints for ingestion and search with proper schemas, validation, and error handling.

### Tasks

#### Task 4.1: Create API Schemas

**File: `src/api/schemas/ingestion.py`**

**Deliverables:**
- Pydantic models for ingestion requests/responses
- Validation rules
- Type hints

**Schemas:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class IngestionRequest(BaseModel):
    """Request schema for ingestion endpoint."""
    corpus_path: str = Field(..., description="Path to corpus file")
    collection_name: str = Field(
        default="corpus_embeddings",
        description="Name of vector DB collection"
    )
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing collection")

class IngestionResponse(BaseModel):
    """Response schema for ingestion endpoint."""
    status: str = Field(..., description="Status: success or error")
    result: Optional[dict] = None
    error: Optional[str] = None
    code: Optional[str] = None
```

**File: `src/api/schemas/search.py`**

**Deliverables:**
- Pydantic models for search requests/responses

**Schemas:**
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SearchRequest(BaseModel):
    """Request schema for search endpoint."""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=10, ge=1, le=100)
    use_hybrid: bool = Field(default=True, description="Use hybrid retrieval")
    fusion_strategy: str = Field(default="rrf", pattern="^(rrf|weighted)$")
    rewrite_query: bool = Field(default=True, description="Rewrite query before search")
    filters: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    """Individual search result."""
    chunk_id: str
    chunk_text: str
    score: float
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None
    metadata: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    """Response schema for search endpoint."""
    query: str
    rewritten_query: Optional[str] = None
    results: List[SearchResult]
    total_results: int
    retrieval_time_ms: float
```

**Tests:**
- `tests/test_api/test_schemas.py`
  - Test schema validation
  - Test default values
  - Test error cases

#### Task 4.2: Implement Ingestion Endpoint

**File: `src/api/endpoints/ingestion.py`**

**Deliverables:**
- `POST /ingest` endpoint
- Request validation
- Pipeline execution
- Error handling
- Response formatting

**Implementation:**
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..schemas.ingestion import IngestionRequest, IngestionResponse
from ...ingestion.pipeline import IngestionPipeline
from ...core.config import AppConfig
import time

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/", response_model=IngestionResponse)
async def ingest(
    request: IngestionRequest,
    background_tasks: BackgroundTasks
):
    """Ingest corpus and create indices."""
    try:
        # Load config
        config = AppConfig.from_yaml("config/config.yaml")
        
        # Initialize components
        # ... component initialization ...
        
        # Create pipeline
        pipeline = IngestionPipeline(...)
        
        # Run ingestion
        start_time = time.time()
        result = pipeline.ingest(
            corpus_path=request.corpus_path,
            collection_name=request.collection_name,
            overwrite=request.overwrite,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        duration = time.time() - start_time
        
        return IngestionResponse(
            status="success",
            result={
                "total_chunks": result.total_chunks,
                "bm25_index_path": result.bm25_index_path,
                "vector_db_collection": result.vector_db_collection,
                "metadata_path": result.metadata_path,
                "embedding_model": result.embedding_model,
                "embedding_dimension": result.embedding_dimension,
                "duration_seconds": duration,
                "statistics": result.statistics
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Tests:**
- `tests/test_api/test_ingestion_endpoint.py`
  - Test successful ingestion
  - Test error handling
  - Test validation
  - Test overwrite behavior

#### Task 4.3: Implement Search Endpoint

**File: `src/api/endpoints/search.py`**

**Deliverables:**
- `POST /search` endpoint
- Query rewriting integration
- Hybrid retrieval
- Response formatting

**Implementation:**
```python
from fastapi import APIRouter, HTTPException
from ..schemas.search import SearchRequest, SearchResponse, SearchResult
from ...core.retrieval_manager import RetrievalManager
import time

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search corpus using hybrid retrieval."""
    try:
        # Get retrieval manager (from app state or dependency injection)
        retrieval_manager = get_retrieval_manager()
        
        # Rewrite query if enabled
        query = request.query
        rewritten_query = None
        if request.rewrite_query:
            # Apply query rewriting
            rewritten_query = retrieval_manager.rewrite_query(query)
            query = rewritten_query
        
        # Perform retrieval
        start_time = time.time()
        results = retrieval_manager.retrieve(
            query=query,
            top_k=request.top_k,
            use_hybrid=request.use_hybrid
        )
        retrieval_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Format results
        search_results = [
            SearchResult(
                chunk_id=r.chunk_id,
                chunk_text=r.chunk_text,
                score=r.score,
                bm25_score=r.metadata.get("bm25_score"),
                vector_score=r.metadata.get("vector_score"),
                metadata=r.metadata
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            rewritten_query=rewritten_query,
            results=search_results,
            total_results=len(search_results),
            retrieval_time_ms=retrieval_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Tests:**
- `tests/test_api/test_search_endpoint.py`
  - Test search with various queries
  - Test query rewriting
  - Test hybrid retrieval
  - Test filtering
  - Test error handling

#### Task 4.4: Create FastAPI Application

**File: `src/api/app.py`**

**Deliverables:**
- FastAPI application setup
- Router registration
- Dependency injection
- Health check endpoint
- Error handling middleware

**Implementation:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import ingestion, search
from ...core.config import AppConfig
from ...core.retrieval_manager import RetrievalManager
from ...utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Multi-Agent RAG RPG API",
    description="API for RAG infrastructure",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router)
app.include_router(search.router)

# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

# Application state
@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("Starting RAG API")
    # Initialize retrieval manager, etc.

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down RAG API")
    # Cleanup resources
```

**Tests:**
- `tests/test_api/test_app.py`
  - Test application startup
  - Test health check
  - Test CORS
  - Test error handling

---

## Phase 5: Test Data and Integration Tests

### Goal
Create comprehensive test data and integration tests demonstrating the full ingestion → search flow.

### Tasks

#### Task 5.1: Create Test Corpus

**File: `tests/data/test_corpus.txt`**

**Deliverables:**
- Small, focused test corpus (e.g., first chapter of a book)
- Or synthetic test data with known structure
- Include various entities, locations, and dialogue

**Requirements:**
- At least 1000 words
- Multiple characters/entities
- Dialogue sections
- Location descriptions
- Action sequences

#### Task 5.2: Create Test Queries

**File: `tests/data/test_queries.json`**

**Deliverables:**
- Test queries with expected results
- Ground truth chunk IDs
- Expected keywords
- Minimum relevant results

**Format:**
```json
{
  "queries": [
    {
      "id": "q1",
      "query": "Arthur Dent lies in front of bulldozer",
      "expected_chunk_ids": ["chunk_123", "chunk_124"],
      "expected_keywords": ["Arthur", "Dent", "bulldozer", "lies"],
      "min_relevant_results": 2,
      "description": "Test query for character action"
    }
  ]
}
```

#### Task 5.3: Implement Test Data Generator

**File: `tests/fixtures/test_data_generator.py`**

**Deliverables:**
- Synthetic corpus generator
- Test query generator from corpus
- Ground truth generation

**Implementation:**
```python
class TestDataGenerator:
    """Generate test data for RAG infrastructure."""
    
    def generate_test_corpus(self, num_chapters: int = 5) -> str:
        """Generate synthetic test corpus."""
        pass
    
    def generate_test_queries(
        self,
        corpus: str,
        num_queries: int = 10
    ) -> List[TestQuery]:
        """Generate test queries from corpus."""
        pass
```

**Tests:**
- `tests/test_fixtures/test_data_generator.py`
  - Test corpus generation
  - Test query generation

#### Task 5.4: Write Integration Tests

**File: `tests/test_integration/test_ingestion_to_search.py`**

**Deliverables:**
- End-to-end test: ingestion → search
- Verify results match expectations
- Test with test corpus and queries

**Test Cases:**
1. Ingest test corpus
2. Search with test queries
3. Verify results contain expected chunks
4. Verify scores are reasonable
5. Test hybrid retrieval improves results

**File: `tests/test_integration/test_hybrid_retrieval.py`**

**Deliverables:**
- Compare BM25-only, vector-only, and hybrid results
- Verify hybrid improves recall
- Test fusion strategies

---

## Phase 6: Docker and Documentation

### Goal
Update Docker configuration, Makefile, and documentation for easy installation and deployment.

### Tasks

#### Task 6.1: Update Dockerfile

**File: `Dockerfile`**

**Deliverables:**
- Multi-stage build
- Data directory setup
- Health check
- Proper permissions

**Key Changes:**
- Create data directories
- Set proper permissions
- Add health check endpoint
- Install NLTK data

#### Task 6.2: Create Docker Compose (Optional)

**File: `docker-compose.yml`**

**Deliverables:**
- Docker Compose configuration
- Volume mounts for data
- Environment variables
- Health checks

#### Task 6.3: Update Makefile

**File: `Makefile`**

**Deliverables:**
- Add ingestion target
- Add search test target
- Add evaluation target
- Update existing targets

**New Targets:**
```makefile
ingest:
	@echo "Running ingestion pipeline..."
	$(PYTHON) scripts/ingest.py

test-search:
	@echo "Testing search API..."
	$(PYTHON) -m pytest tests/test_api/test_search_endpoint.py -v

test-ingestion:
	@echo "Testing ingestion API..."
	$(PYTHON) -m pytest tests/test_api/test_ingestion_endpoint.py -v

test-integration:
	@echo "Running integration tests..."
	$(PYTHON) -m pytest tests/test_integration/ -v
```

#### Task 6.4: Update README

**File: `README.md`**

**Deliverables:**
- Add RAG infrastructure section
- Add ingestion instructions
- Add search API documentation
- Add Docker instructions
- Add configuration examples

#### Task 6.5: Create API Documentation

**File: `docs/API.md`**

**Deliverables:**
- API endpoint documentation
- Request/response examples
- Error codes
- Authentication (if applicable)

#### Task 6.6: Create Configuration Documentation

**File: `docs/CONFIGURATION.md`**

**Deliverables:**
- Configuration schema
- Vector DB provider configuration
- Ingestion configuration
- Retrieval configuration
- Examples for each provider

---

## Testing Strategy

### Unit Tests

- **Coverage Target**: > 80% for all components
- **Focus Areas**:
  - Vector DB abstraction layer
  - Ingestion components
  - Retrieval components
  - Query rewriting
  - API endpoints

### Integration Tests

- **Focus Areas**:
  - Ingestion → Search flow
  - Hybrid retrieval comparison
  - End-to-end API tests

### Test Execution

```bash
# Run all tests
make test

# Run specific test suite
pytest tests/test_ingestion/ -v
pytest tests/test_rag/ -v
pytest tests/test_api/ -v
pytest tests/test_integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Success Criteria

### Functional Requirements

1. ✅ **Ingestion API**: Successfully ingest corpus and create indices
2. ✅ **Search API**: Return relevant results using hybrid retrieval
3. ✅ **Query Rewriting**: Improve retrieval quality with query expansion
4. ✅ **Provider Swapping**: Change vector DB provider via configuration only
5. ✅ **Docker Support**: Full functionality in containerized environment

### Performance Requirements

1. **Ingestion**: Process 10,000 chunks in < 5 minutes (local)
2. **Search**: Return results in < 200ms (p95)
3. **Memory**: < 2GB RAM for local ChromaDB with 10K chunks

### Test Coverage

1. **Unit Tests**: > 80% coverage for all components
2. **Integration Tests**: Full ingestion → search flow tested
3. **API Tests**: All endpoints tested with various inputs

---

## Dependencies

### New Dependencies

**Add to `requirements.txt`:**

```txt
# Vector Database
chromadb>=0.4.0
pinecone-client>=2.2.0  # Optional, for Pinecone support

# BM25
rank-bm25>=0.2.2

# Embeddings
sentence-transformers>=2.2.0

# Text Processing
nltk>=3.8.0

# Query Expansion
wordnet>=0.0.1  # Via nltk
```

---

## Timeline Estimate

- **Phase 1**: Vector DB Abstraction Layer - 2-3 days
- **Phase 2**: Ingestion Pipeline - 3-4 days
- **Phase 3**: Retrieval System - 2-3 days
- **Phase 4**: API Endpoints - 2 days
- **Phase 5**: Test Data and Integration Tests - 2 days
- **Phase 6**: Docker and Documentation - 1-2 days

**Total**: 12-16 days

---

## Notes

- All code must follow Python best practices (type hints, docstrings, error handling)
- Use virtual environment for all development
- Test each phase before moving to the next
- Update documentation as you implement
- Keep components loosely coupled for easy swapping

