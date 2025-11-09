"""Integration tests for retrieval system initialization."""

import pytest
from pathlib import Path
from src.core.config import AppConfig
from src.core.retrieval_manager import RetrievalManager


class TestRetrievalManagerInitialization:
    """Test RetrievalManager initialization from config."""

    @pytest.fixture
    def app_config(self):
        """Load application configuration."""
        config_path = "config/config.yaml"
        agents_config_path = "config/agents.yaml"
        return AppConfig.from_yaml(config_path, agents_config_path)

    def test_retrieval_manager_from_config(self, app_config):
        """Test creating RetrievalManager from AppConfig."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)

        # Assert
        assert retrieval_manager is not None
        assert retrieval_manager.retriever is not None
        assert retrieval_manager.hybrid_retriever is not None
        assert retrieval_manager.hybrid_retriever.bm25_retriever is not None
        assert retrieval_manager.hybrid_retriever.vector_retriever is not None

    def test_bm25_retriever_lazy_loading(self, app_config):
        """Test BM25Retriever supports lazy loading."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)
        bm25_retriever = retrieval_manager.hybrid_retriever.bm25_retriever

        # Assert - should not be loaded initially
        assert not bm25_retriever.is_loaded()

    def test_load_indices(self, app_config):
        """Test loading indices after initialization."""
        # Arrange
        retrieval_manager = RetrievalManager.from_config(app_config)
        bm25_path = app_config.ingestion.bm25_index_path
        metadata_path = app_config.ingestion.chunk_metadata_path
        collection_name = app_config.vector_db.get_collection_name()

        # Only test if indices exist
        if Path(bm25_path).exists() and Path(metadata_path).exists():
            # Act
            retrieval_manager.load_indices(bm25_path, metadata_path, collection_name)

            # Assert
            bm25_retriever = retrieval_manager.hybrid_retriever.bm25_retriever
            assert bm25_retriever.is_loaded()
            assert bm25_retriever.index is not None
            assert len(bm25_retriever.chunks) > 0

    def test_vector_retriever_initialization(self, app_config):
        """Test VectorRetriever is properly initialized."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)
        vector_retriever = retrieval_manager.hybrid_retriever.vector_retriever

        # Assert
        assert vector_retriever is not None
        assert vector_retriever.vector_db is not None
        assert vector_retriever.embedder is not None
        assert vector_retriever.collection_name == app_config.vector_db.get_collection_name()

    def test_embedder_initialization(self, app_config):
        """Test Embedder is properly initialized."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)
        embedder = retrieval_manager.hybrid_retriever.vector_retriever.embedder

        # Assert
        assert embedder is not None
        assert embedder.model_name == app_config.ingestion.embedding_model
        assert embedder.model is not None

    def test_hybrid_retriever_configuration(self, app_config):
        """Test HybridRetriever is configured correctly."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)
        hybrid_retriever = retrieval_manager.hybrid_retriever

        # Assert
        assert hybrid_retriever.fusion_strategy == app_config.retrieval.fusion_strategy
        assert hybrid_retriever.bm25_weight == app_config.retrieval.bm25_weight
        assert hybrid_retriever.vector_weight == app_config.retrieval.vector_weight
        assert hybrid_retriever.rrf_k == app_config.retrieval.rrf_k

    def test_query_rewriter_initialization(self, app_config):
        """Test QueryRewriter is initialized when enabled."""
        # Act
        retrieval_manager = RetrievalManager.from_config(app_config)

        # Assert
        if app_config.retrieval.query_rewriter_enabled:
            assert retrieval_manager.query_rewriter is not None
        else:
            assert retrieval_manager.query_rewriter is None
