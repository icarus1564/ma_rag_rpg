# Debug Logging Instrumentation Checklist

## Quick Reference by Phase and Priority

---

## PHASE 1A: CORE MODULE (18 methods)

### src/core/session.py
- [ ] `GameSession.add_turn()` - CRITICAL
- [ ] `GameSession._apply_sliding_window()` - CRITICAL
- [ ] `GameSession.get_memory_context()` - IMPORTANT
- [ ] `GameSession.is_expired()` - IMPORTANT

### src/core/base_agent.py
- [ ] `LLMClient._initialize_client()` - CRITICAL
- [ ] `LLMClient.generate()` - **CRITICAL**
- [ ] `BaseAgent.__init__()` - IMPORTANT
- [ ] `BaseAgent.validate_config()` - IMPORTANT
- [ ] `BaseAgent.format_prompt()` - USEFUL
- [ ] `BaseAgent.test_connection()` - IMPORTANT
- [ ] `BaseAgent.extract_citations()` - USEFUL

### src/core/orchestrator.py
- [ ] `GameOrchestrator.execute_turn()` - **CRITICAL**
- [ ] `GameOrchestrator._update_session_state()` - IMPORTANT

### src/core/session_manager.py
- [ ] `SessionManager.create_session()` - IMPORTANT
- [ ] `SessionManager.get_session()` - IMPORTANT
- [ ] `SessionManager.delete_session()` - IMPORTANT
- [ ] `SessionManager.cleanup_expired_sessions()` - IMPORTANT
- [ ] `SessionManager.list_sessions()` - USEFUL

---

## PHASE 2: COMPLETE AGENTS (18 methods)

### src/agents/scene_planner.py
- [ ] `ScenePlannerAgent.process()` - **CRITICAL**
- [ ] `ScenePlannerAgent._build_query()` - IMPORTANT
- [ ] `ScenePlannerAgent._build_prompt()` - IMPORTANT
- [ ] `ScenePlannerAgent._parse_response()` - IMPORTANT
- [ ] `ScenePlannerAgent._should_scene_transition()` - USEFUL

### src/agents/npc_manager.py
- [ ] `NPCManagerAgent.process()` - **CRITICAL**
- [ ] `NPCManagerAgent._get_responding_npc()` - IMPORTANT
- [ ] `NPCManagerAgent._get_or_extract_persona()` - **CRITICAL**
- [ ] `NPCManagerAgent._retrieve_persona()` - IMPORTANT
- [ ] `NPCManagerAgent._retrieve_dialogue_context()` - IMPORTANT
- [ ] `NPCManagerAgent._build_prompt()` - IMPORTANT
- [ ] `NPCManagerAgent._parse_response()` - IMPORTANT

### src/agents/rules_referee.py
- [ ] `RulesRefereeAgent.process()` - **CRITICAL**
- [ ] `RulesRefereeAgent._build_query()` - IMPORTANT
- [ ] `RulesRefereeAgent._extract_action_keywords()` - USEFUL
- [ ] `RulesRefereeAgent._extract_entities()` - USEFUL
- [ ] `RulesRefereeAgent._build_prompt()` - IMPORTANT
- [ ] `RulesRefereeAgent._parse_response()` - IMPORTANT

---

## PHASE 3: RAG RETRIEVAL SYSTEM (18 methods)

### src/rag/hybrid_retriever.py
- [ ] `HybridRetriever.retrieve()` - **CRITICAL**
- [ ] `HybridRetriever.retrieve_with_scores()` - IMPORTANT
- [ ] `HybridRetriever._fuse_rrf()` - **CRITICAL**
- [ ] `HybridRetriever._fuse_weighted()` - **CRITICAL**

### src/rag/vector_retriever.py
- [ ] `VectorRetriever.retrieve()` - **CRITICAL**
- [ ] `VectorRetriever.retrieve_with_scores()` - IMPORTANT

### src/rag/bm25_retriever.py
- [ ] `BM25Retriever._load_index()` - IMPORTANT
- [ ] `BM25Retriever._load_metadata()` - IMPORTANT
- [ ] `BM25Retriever._load_chunks()` - IMPORTANT
- [ ] `BM25Retriever.load_index()` - IMPORTANT
- [ ] `BM25Retriever.is_loaded()` - USEFUL
- [ ] `BM25Retriever.retrieve()` - **CRITICAL**
- [ ] `BM25Retriever.retrieve_with_scores()` - IMPORTANT

### src/rag/query_rewriter.py
- [ ] `QueryRewriter.rewrite()` - **CRITICAL**
- [ ] `QueryRewriter.expand()` - IMPORTANT
- [ ] `QueryRewriter.llm_rewrite()` - IMPORTANT

---

## PHASE 4: INGESTION PIPELINE (13 methods)

### src/ingestion/pipeline.py
- [ ] `IngestionPipeline.ingest()` - **CRITICAL**

### src/ingestion/chunker.py
- [ ] `Chunker.chunk()` - **CRITICAL**
- [ ] `Chunker._chunk_by_sentence()` - IMPORTANT
- [ ] `Chunker._chunk_by_paragraph()` - IMPORTANT
- [ ] `Chunker._chunk_sliding_window()` - IMPORTANT

### src/ingestion/embedder.py
- [ ] `Embedder._initialize_model()` - IMPORTANT
- [ ] `Embedder.embed()` - **CRITICAL**
- [ ] `Embedder.embed_batch()` - **CRITICAL**

### src/ingestion/bm25_indexer.py
- [ ] `BM25Indexer.build_index()` - **CRITICAL**
- [ ] `BM25Indexer.save_index()` - IMPORTANT
- [ ] `BM25Indexer.load_index()` - IMPORTANT

### src/ingestion/metadata_store.py
- [ ] `MetadataStore.save_metadata()` - IMPORTANT
- [ ] `MetadataStore.load_metadata()` - IMPORTANT

---

## PHASE 5: VECTOR DB PROVIDERS (9 methods)

### src/rag/vector_db/chroma_provider.py
- [ ] `ChromaVectorDB.initialize()` - IMPORTANT
- [ ] `ChromaVectorDB.create_collection()` - IMPORTANT
- [ ] `ChromaVectorDB.add_documents()` - IMPORTANT
- [ ] `ChromaVectorDB.search()` - **CRITICAL**

### src/rag/vector_db/pinecone_provider.py
- [ ] `PineconeVectorDB.initialize()` - IMPORTANT
- [ ] `PineconeVectorDB.create_collection()` - IMPORTANT
- [ ] `PineconeVectorDB.add_documents()` - IMPORTANT
- [ ] `PineconeVectorDB.search()` - **CRITICAL**

### src/rag/vector_db/factory.py
- [ ] `VectorDBFactory.create()` - IMPORTANT

---

## SUMMARY STATISTICS

| Phase | File Count | Method Count | Critical | Important | Useful |
|-------|-----------|--------------|----------|-----------|--------|
| 1A: Core | 4 | 18 | 4 | 10 | 4 |
| 2: Agents | 3 | 18 | 4 | 10 | 4 |
| 3: RAG | 4 | 18 | 8 | 8 | 2 |
| 4: Ingestion | 5 | 13 | 6 | 5 | 2 |
| 5: VectorDB | 3 | 9 | 2 | 6 | 1 |
| **TOTAL** | **19** | **76** | **24** | **39** | **13** |

---

## IMPLEMENTATION TIPS

### For @debug_log_method (recommended for 70% of methods)
- Automatically logs all parameters (truncated to 25 chars)
- Logs return value
- Logs exceptions
- Minimal code changes

### For @debug_log_calls (recommended for 20% of methods)
- Only logs method entry/exit
- Good for high-frequency, low-parameter methods
- Lower overhead

### Skip Decorators For (10% of methods)
- Properties
- `__init__` in dataclasses
- Abstract methods
- Pure utility functions with simple logic

### Best Practices
1. Add imports at top of file:
   ```python
   from ..utils.debug_logging import debug_log_method, debug_log_calls
   ```

2. Place decorator immediately before method:
   ```python
   @debug_log_method
   def my_method(self, param1: str) -> str:
   ```

3. Test before committing:
   ```bash
   source .venv/bin/activate
   pytest tests/ -v
   ```

4. Verify logging output:
   ```bash
   LOG_LEVEL=DEBUG python -m src.module_name
   ```

---

## TESTING RECOMMENDATIONS

After each phase, run:
```bash
# Activate venv
source .venv/bin/activate

# Run unit tests
pytest tests/test_core.py -v

# Run with debug logging
LOG_LEVEL=DEBUG pytest tests/ -v -s

# Check for import errors
python -c "from src.core import game_loop; from src.agents import scene_planner"
```

