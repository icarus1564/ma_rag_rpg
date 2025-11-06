#!/usr/bin/env python3
"""CLI script for corpus ingestion."""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import AppConfig
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.chunker import Chunker
from src.ingestion.bm25_indexer import BM25Indexer
from src.ingestion.embedder import Embedder
from src.ingestion.metadata_store import MetadataStore
from src.rag.vector_db.factory import VectorDBFactory
from src.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for ingestion script."""
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
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size (overrides config)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Chunk overlap (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Load config
    try:
        config = AppConfig.from_yaml(args.config)
    except Exception as e:
        logger.error("Failed to load config", error=str(e))
        sys.exit(1)
    
    # Initialize components
    try:
        # Initialize chunker
        chunker = Chunker()
        
        # Initialize BM25 indexer
        bm25_indexer = BM25Indexer()
        
        # Initialize embedder
        embedder = Embedder(
            model_name=config.ingestion.embedding_model
        )
        
        # Initialize vector DB
        vector_db_config = config.vector_db.chroma if config.vector_db.provider == "chroma" else config.vector_db.pinecone
        vector_db = VectorDBFactory.create(
            provider=config.vector_db.provider,
            config=vector_db_config
        )
        
        # Initialize metadata store
        metadata_store = MetadataStore()
        
        # Create pipeline
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        # Run ingestion
        chunk_size = args.chunk_size or config.ingestion.chunk_size
        chunk_overlap = args.chunk_overlap or config.ingestion.chunk_overlap
        
        result = pipeline.ingest(
            corpus_path=args.corpus,
            collection_name=config.vector_db.chroma.get("collection_name", "corpus_embeddings"),
            overwrite=args.overwrite,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Print results
        logger.info("Ingestion complete", **{
            "total_chunks": result.total_chunks,
            "duration_seconds": result.duration_seconds,
            "embedding_model": result.embedding_model,
            "embedding_dimension": result.embedding_dimension
        })
        print(f"Ingestion complete: {result.total_chunks} chunks processed in {result.duration_seconds:.2f}s")
        
    except Exception as e:
        logger.error("Ingestion failed", error=str(e))
        sys.exit(1)
    finally:
        # Cleanup
        if 'vector_db' in locals():
            vector_db.close()


if __name__ == "__main__":
    main()

