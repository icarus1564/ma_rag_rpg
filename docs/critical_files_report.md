# Critical Files for Debug Logging Instrumentation

## Summary
This report identifies all critical classes and their key methods that should be instrumented with debug logging decorators across the RAG RPG codebase.

Total Python files in src: 50
Codebase modules:
- Core game logic (6 files)
- Agents (9 files)
- RAG/Retrieval (7 files)
- Ingestion pipeline (6 files)
- Vector DB providers (4 files)
- API endpoints (5 files)
- Utilities (3 files)

---

## PHASE 1: CORE MODULE (ALREADY PARTIALLY COMPLETE)

Already instrumented:
- ✅ src/core/game_loop.py: execute_turn, _perform_retrieval, _execute_agents
- ✅ src/core/retrieval_manager.py: retrieve
- ✅ src/agents/narrator.py: process

### Phase 1A: Complete Core Module

#### 1. src/core/session.py
File: /home/matthew/dev/ma_rag_rpg/src/core/session.py
Class: GameSession (dataclass)

Key methods to instrument:
- `add_turn(turn: Turn) -> None` - Critical: Adds turn to session and applies sliding window
- `_apply_sliding_window() -> None` - Critical: Memory management
- `get_memory_context() -> str` - Important: Builds memory for agents
- `is_expired() -> bool` - Important: Session lifecycle management

Class: Turn (dataclass)
- No methods to decorate (data class)

#### 2. src/core/base_agent.py
File: /home/matthew/dev/ma_rag_rpg/src/core/base_agent.py

Class: LLMClient
Key methods:
- `_initialize_client()` - Critical: Initializes LLM provider connections
- `generate(prompt: str, system_prompt: Optional[str] = None) -> str` - **CRITICAL**: All LLM calls

Class: BaseAgent
Key methods:
- `__init__(config: AgentConfig)` - Important: Initializes agent
- `validate_config() -> bool` - Important: Config validation
- `format_prompt(template: str, **kwargs) -> str` - Useful: Prompt formatting
- `test_connection() -> tuple[bool, Optional[str]]` - Important: Connection testing

#### 3. src/core/orchestrator.py
File: /home/matthew/dev/ma_rag_rpg/src/core/orchestrator.py
Class: GameOrchestrator

Key methods:
- `execute_turn(session, player_command, retrieval_results, initial_context) -> Dict[str, Any]` - **CRITICAL**: Orchestrates agent execution
- `_update_session_state(session, outputs, context) -> None` - Important: State management

#### 4. src/core/session_manager.py
File: /home/matthew/dev/ma_rag_rpg/src/core/session_manager.py
Class: SessionManager

Key methods:
- `create_session(initial_context: Optional[str] = None) -> GameSession` - Important: Session creation
- `get_session(session_id: str) -> Optional[GameSession]` - Important: Session retrieval
- `delete_session(session_id: str) -> bool` - Important: Session cleanup
- `cleanup_expired_sessions() -> int` - Important: Session maintenance
- `list_sessions() -> list` - Useful: Session listing

---

## PHASE 2: REMAINING AGENTS

#### 5. src/agents/scene_planner.py
File: /home/matthew/dev/ma_rag_rpg/src/agents/scene_planner.py
Class: ScenePlannerAgent

Key methods:
- `process(context: AgentContext) -> AgentOutput` - **CRITICAL**: Main agent logic
- `_build_query(context: AgentContext) -> str` - Important: Query construction
- `_build_prompt(context, results) -> str` - Important: Prompt building
- `_parse_response(response, results, context) -> AgentOutput` - Important: Response parsing
- `_should_scene_transition(command: str) -> bool` - Useful: Scene transition logic

#### 6. src/agents/npc_manager.py
File: /home/matthew/dev/ma_rag_rpg/src/agents/npc_manager.py
Class: NPCManagerAgent

Key methods:
- `process(context: AgentContext) -> AgentOutput` - **CRITICAL**: Main agent logic
- `_get_responding_npc(context: AgentContext) -> Optional[str]` - Important: NPC selection
- `_get_or_extract_persona(npc_name, context) -> Dict[str, Any]` - **CRITICAL**: Persona management
- `_retrieve_persona(npc_name, context) -> List[RetrievalResult]` - Important: Persona retrieval
- `_retrieve_dialogue_context(npc_name, context) -> List[RetrievalResult]` - Important: Context retrieval
- `_build_prompt(npc_name, persona, context, dialogue_chunks) -> str` - Important: Prompt building
- `_parse_response(response, dialogue_chunks, npc_name, persona, context) -> AgentOutput` - Important: Response parsing

#### 7. src/agents/rules_referee.py
File: /home/matthew/dev/ma_rag_rpg/src/agents/rules_referee.py
Class: RulesRefereeAgent

Key methods:
- `process(context: AgentContext) -> AgentOutput` - **CRITICAL**: Main agent logic
- `_build_query(context: AgentContext) -> str` - Important: Query construction
- `_extract_action_keywords(command: str) -> List[str]` - Useful: Keyword extraction
- `_extract_entities(text: str) -> List[str]` - Useful: Entity extraction
- `_build_prompt(context, results) -> str` - Important: Prompt building
- `_parse_response(response, results) -> AgentOutput` - Important: Response parsing

---

## PHASE 3: RAG RETRIEVAL SYSTEM

#### 8. src/rag/hybrid_retriever.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/hybrid_retriever.py
Class: HybridRetriever

Key methods:
- `retrieve(query, top_k, filters) -> List[RetrievalResult]` - **CRITICAL**: Main retrieval method
- `retrieve_with_scores(query, top_k) -> List[RetrievalResult]` - Important: Alternative retrieval
- `_fuse_rrf(bm25_results, vector_results, top_k) -> List[RetrievalResult]` - **CRITICAL**: RRF fusion logic
- `_fuse_weighted(bm25_results, vector_results, top_k) -> List[RetrievalResult]` - **CRITICAL**: Weighted fusion logic

#### 9. src/rag/vector_retriever.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/vector_retriever.py
Class: VectorRetriever

Key methods:
- `retrieve(query, top_k, filters) -> List[RetrievalResult]` - **CRITICAL**: Vector search
- `retrieve_with_scores(query, top_k) -> List[RetrievalResult]` - Important: Alternative method

#### 10. src/rag/bm25_retriever.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/bm25_retriever.py
Class: BM25Retriever

Key methods:
- `_load_index() -> None` - Important: Index loading
- `_load_metadata() -> None` - Important: Metadata loading
- `_load_chunks() -> None` - Important: Chunk loading
- `load_index(index_path, metadata_path) -> None` - Important: Public load method
- `is_loaded() -> bool` - Useful: Status check
- `retrieve(query, top_k, filters) -> List[RetrievalResult]` - **CRITICAL**: BM25 retrieval
- `retrieve_with_scores(query, top_k) -> List[RetrievalResult]` - Important: Alternative method

#### 11. src/rag/base_retriever.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/base_retriever.py
Class: BaseRetriever (abstract)

Note: This is an abstract base class. No instrumentation needed on abstract methods.

#### 12. src/rag/query_rewriter.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/query_rewriter.py
Class: QueryRewriter

Key methods:
- `rewrite(query: str) -> str` - **CRITICAL**: Main rewriting logic
- `expand(query: str) -> str` - Important: Query expansion
- `llm_rewrite(query: str) -> str` - Important: LLM-based rewriting

#### 13. src/rag/vector_db/base.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/vector_db/base.py
Class: BaseVectorDB (abstract)

Note: Abstract base class. No instrumentation on abstract methods.

---

## PHASE 4: INGESTION PIPELINE

#### 14. src/ingestion/pipeline.py
File: /home/matthew/dev/ma_rag_rpg/src/ingestion/pipeline.py
Class: IngestionPipeline

Key methods:
- `ingest(corpus_path, collection_name, overwrite, chunk_size, chunk_overlap) -> IngestionResult` - **CRITICAL**: Main pipeline

#### 15. src/ingestion/chunker.py
File: /home/matthew/dev/ma_rag_rpg/src/ingestion/chunker.py
Class: Chunker

Key methods:
- `chunk(text, strategy, chunk_size, chunk_overlap) -> List[Chunk]` - **CRITICAL**: Main chunking method
- `_chunk_by_sentence(text, chunk_size, overlap) -> List[Chunk]` - Important: Sentence strategy
- `_chunk_by_paragraph(text, chunk_size, overlap) -> List[Chunk]` - Important: Paragraph strategy
- `_chunk_sliding_window(text, chunk_size, overlap) -> List[Chunk]` - Important: Window strategy

#### 16. src/ingestion/embedder.py
File: /home/matthew/dev/ma_rag_rpg/src/ingestion/embedder.py
Class: Embedder

Key methods:
- `_initialize_model() -> None` - Important: Model initialization
- `embed(texts: List[str]) -> List[List[float]]` - **CRITICAL**: Single embedding
- `embed_batch(texts: List[str], batch_size) -> List[List[float]]` - **CRITICAL**: Batch embedding

#### 17. src/ingestion/bm25_indexer.py
File: /home/matthew/dev/ma_rag_rpg/src/ingestion/bm25_indexer.py
Class: BM25Indexer

Key methods:
- `build_index(chunks: List[str]) -> BM25Okapi` - **CRITICAL**: Index building
- `save_index(index, path) -> None` - Important: Index persistence
- `load_index(path) -> BM25Okapi` - Important: Index loading

#### 18. src/ingestion/metadata_store.py
File: /home/matthew/dev/ma_rag_rpg/src/ingestion/metadata_store.py
Class: MetadataStore

Key methods:
- `save_metadata(metadata_list, path) -> None` - Important: Metadata persistence
- `load_metadata(path) -> Dict[str, ChunkMetadata]` - Important: Metadata loading

---

## ADDITIONAL CRITICAL FILES

#### 19. src/rag/vector_db/chroma_provider.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/vector_db/chroma_provider.py
Class: ChromaVectorDB

Key methods:
- `initialize(config) -> None` - Important: Initialization
- `create_collection(collection_name, embedding_dimension, metadata) -> None` - Important
- `add_documents(collection_name, documents) -> None` - Important
- `search(collection_name, query_embedding, top_k, filters) -> List[VectorSearchResult]` - **CRITICAL**: Search

#### 20. src/rag/vector_db/pinecone_provider.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/vector_db/pinecone_provider.py
Class: PineconeVectorDB

Key methods:
- `initialize(config) -> None` - Important: Initialization
- `create_collection(collection_name, embedding_dimension, metadata) -> None` - Important
- `add_documents(collection_name, documents) -> None` - Important
- `search(collection_name, query_embedding, top_k, filters) -> List[VectorSearchResult]` - **CRITICAL**: Search

#### 21. src/rag/vector_db/factory.py
File: /home/matthew/dev/ma_rag_rpg/src/rag/vector_db/factory.py
Class: VectorDBFactory

Key methods:
- `create(provider, config) -> BaseVectorDB` - Important: Factory method

---

## INSTRUMENTATION RECOMMENDATIONS

### Priority 1: CRITICAL (Must have for debugging)
These methods directly impact core functionality and require comprehensive logging:
- GameLoop.execute_turn
- GameLoop._perform_retrieval
- GameLoop._execute_agents
- RetrievalManager.retrieve
- All Agent.process() methods (Narrator, ScenePlanner, NPCManager, RulesReferee)
- HybridRetriever.retrieve, _fuse_rrf, _fuse_weighted
- VectorRetriever.retrieve
- BM25Retriever.retrieve
- Embedder.embed, embed_batch
- IngestionPipeline.ingest
- Chunker.chunk
- LLMClient.generate

### Priority 2: IMPORTANT (Highly useful for debugging)
These methods are called frequently or manage critical state:
- GameSession.add_turn, _apply_sliding_window
- BaseAgent.__init__, validate_config
- GameOrchestrator.execute_turn
- SessionManager.create_session, get_session
- All Agent helper methods (_build_query, _build_prompt, _parse_response)
- BM25Indexer.build_index, load_index
- Vector DB provider methods (search, add_documents)
- QueryRewriter.rewrite
- MetadataStore.save_metadata, load_metadata

### Priority 3: USEFUL (Context-dependent)
These provide supplementary information:
- Session state helpers
- Entity/keyword extraction methods
- Fallback/error handling paths
- Status checking methods

---

## DECORATOR PATTERNS

### Pattern 1: Comprehensive Method Logging
Use `@debug_log_method` for methods that:
- Take parameters you need to see
- Return important values
- Are entry points to major operations

Example:
```python
from ..utils.debug_logging import debug_log_method

@debug_log_method
def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
    pass
```

### Pattern 2: Call-Chain Logging
Use `@debug_log_calls` for methods that:
- Call many other methods
- Track execution flow
- Don't need parameter details

Example:
```python
@debug_log_calls
def _fuse_rrf(self, bm25_results, vector_results, top_k):
    pass
```

---

## INSTRUMENTATION ORDER RECOMMENDATION

1. **Phase 1A (Week 1)**: Complete Core Module
   - session.py (4 methods)
   - base_agent.py (7 methods)
   - orchestrator.py (2 methods)
   - session_manager.py (5 methods)

2. **Phase 2 (Week 2)**: Complete Agents
   - scene_planner.py (5 methods)
   - npc_manager.py (7 methods)
   - rules_referee.py (6 methods)

3. **Phase 3 (Week 3)**: RAG System
   - hybrid_retriever.py (4 methods)
   - vector_retriever.py (2 methods)
   - bm25_retriever.py (7 methods)
   - query_rewriter.py (3 methods)

4. **Phase 4 (Week 4)**: Ingestion Pipeline
   - pipeline.py (1 method - critical)
   - chunker.py (4 methods)
   - embedder.py (3 methods)
   - bm25_indexer.py (3 methods)
   - metadata_store.py (2 methods)

5. **Phase 5 (Week 5)**: Vector DB Providers
   - chroma_provider.py (4 methods)
   - pinecone_provider.py (4 methods)
   - factory.py (1 method)

---

## TOTAL INSTRUMENTATION COUNT

- **Core Module**: 18 methods
- **Agents**: 18 methods
- **RAG Retrievers**: 18 methods
- **Ingestion Pipeline**: 13 methods
- **Vector DB Providers**: 9 methods

**TOTAL: 76 methods to decorate** (across 21 critical files)

---

## NOTES

- All metrics assume using `@debug_log_method` for primary methods
- Use `@debug_log_calls` sparingly for flow-heavy internal methods
- Priority is on entry points first (public API), then critical internals
- Test each phase before moving to next
- Consider adding integration tests to verify logging doesn't impact functionality

