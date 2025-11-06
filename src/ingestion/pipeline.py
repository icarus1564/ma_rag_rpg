"""Ingestion pipeline orchestrator."""

from dataclasses import dataclass
from typing import Dict, Any
import time
from pathlib import Path
from .chunker import Chunker, Chunk
from .bm25_indexer import BM25Indexer
from .embedder import Embedder
from .metadata_store import MetadataStore, ChunkMetadata
from ..rag.vector_db.base import BaseVectorDB, VectorDocument
from ..utils.logging import get_logger

logger = get_logger(__name__)


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
        """Initialize pipeline with components.
        
        Args:
            chunker: Chunker instance
            bm25_indexer: BM25Indexer instance
            embedder: Embedder instance
            vector_db: Vector DB instance
            metadata_store: MetadataStore instance
        """
        self.chunker = chunker
        self.bm25_indexer = bm25_indexer
        self.embedder = embedder
        self.vector_db = vector_db
        self.metadata_store = metadata_store
    
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
        start_time = time.time()
        logger.info("Starting ingestion pipeline", corpus_path=corpus_path, collection=collection_name)
        
        # 1. Load corpus text
        corpus_path_obj = Path(corpus_path)
        if not corpus_path_obj.exists():
            raise FileNotFoundError(f"Corpus file not found: {corpus_path}")
        
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus_text = f.read()
        
        logger.info("Corpus loaded", path=corpus_path, text_length=len(corpus_text))
        
        # 2. Chunk text
        chunks = self.chunker.chunk(
            text=corpus_text,
            strategy="sliding_window",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        logger.info("Text chunked", chunk_count=len(chunks))
        
        if not chunks:
            raise ValueError("No chunks generated from corpus text")
        
        # 3. Build BM25 index
        chunk_texts = [chunk.text for chunk in chunks]
        bm25_index = self.bm25_indexer.build_index(chunk_texts)
        
        # Save BM25 index
        bm25_index_path = f"data/indices/bm25_index_{collection_name}.pkl"
        self.bm25_indexer.save_index(bm25_index, bm25_index_path)
        logger.info("BM25 index built and saved", path=bm25_index_path)
        
        # 4. Generate embeddings
        embeddings = self.embedder.embed_batch(chunk_texts, batch_size=32)
        logger.info("Embeddings generated", count=len(embeddings))
        
        # 5. Store in vector DB
        # Create collection if it doesn't exist or overwrite is True
        if overwrite and self.vector_db.collection_exists(collection_name):
            self.vector_db.delete_collection(collection_name)
            logger.info("Existing collection deleted", collection=collection_name)
        
        if not self.vector_db.collection_exists(collection_name):
            self.vector_db.create_collection(
                collection_name=collection_name,
                embedding_dimension=self.embedder.dimension
            )
            logger.info("Collection created", collection=collection_name)
        
        # Prepare documents for vector DB
        vector_documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_documents.append(VectorDocument(
                id=chunk.id,
                text=chunk.text,
                embedding=embedding,
                metadata={
                    "start_pos": chunk.start_pos,
                    "end_pos": chunk.end_pos,
                    **chunk.metadata
                }
            ))
        
        # Add documents to vector DB
        self.vector_db.add_documents(collection_name, vector_documents)
        logger.info("Documents added to vector DB", collection=collection_name, count=len(vector_documents))
        
        # 6. Save metadata
        chunk_metadata_list = []
        for i, chunk in enumerate(chunks):
            chunk_metadata_list.append(ChunkMetadata(
                chunk_id=chunk.id,
                text=chunk.text,
                start_pos=chunk.start_pos,
                end_pos=chunk.end_pos,
                chunk_index=i,
                source=corpus_path,
                additional_metadata=chunk.metadata
            ))
        
        metadata_path = f"data/indices/chunks_{collection_name}.json"
        self.metadata_store.save_metadata(chunk_metadata_list, metadata_path)
        logger.info("Metadata saved", path=metadata_path)
        
        # 7. Validate and report statistics
        duration = time.time() - start_time
        
        # Get collection stats
        collection_stats = self.vector_db.get_collection_stats(collection_name)
        
        statistics = {
            "avg_chunk_size": sum(len(c.text) for c in chunks) / len(chunks) if chunks else 0,
            "min_chunk_size": min((len(c.text) for c in chunks), default=0),
            "max_chunk_size": max((len(c.text) for c in chunks), default=0),
            "vector_db_count": collection_stats.get("count", 0),
            "embedding_dimension": self.embedder.dimension
        }
        
        logger.info("Ingestion pipeline completed", 
                   duration=duration, 
                   total_chunks=len(chunks),
                   collection=collection_name)
        
        return IngestionResult(
            total_chunks=len(chunks),
            bm25_index_path=bm25_index_path,
            vector_db_collection=collection_name,
            metadata_path=metadata_path,
            embedding_model=self.embedder.model_name,
            embedding_dimension=self.embedder.dimension,
            duration_seconds=duration,
            statistics=statistics
        )

