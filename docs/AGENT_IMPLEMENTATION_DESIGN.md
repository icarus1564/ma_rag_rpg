# Agent Implementation Design Document

**Project:** Multi-Agent RAG RPG Framework
**Phase:** Phase 3 - Agent Implementations
**Status:** Design Complete - Ready for Implementation
**Date:** 2025-11-07
**Author:** Claude Code & Matthew Canaday

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Infrastructure Review](#infrastructure-review)
4. [Agent Architecture](#agent-architecture)
5. [Narrator Agent](#narrator-agent)
6. [ScenePlanner Agent](#sceneplanner-agent)
7. [NPCManager Agent](#npcmanager-agent)
8. [RulesReferee Agent](#rulesreferee-agent)
9. [Shared Components](#shared-components)
10. [Integration with Existing System](#integration-with-existing-system)
11. [Testing Strategy](#testing-strategy)
12. [Implementation Order](#implementation-order)

---

## Overview

This document provides a comprehensive design for implementing the four core agents in the Multi-Agent RAG RPG system:

1. **Narrator**: Generates scene descriptions grounded in corpus
2. **ScenePlanner**: Determines next scene and which NPC should respond
3. **NPCManager**: Generates NPC dialogue with just-in-time persona extraction
4. **RulesReferee**: Validates player actions against corpus facts

All infrastructure for these agents is already in place (Phase 1 and Phase 2 complete). This design ensures agents have access to all necessary functions and processes.

---

## Design Principles

### 1. Corpus-Grounded Operation
- All agent outputs must be grounded in retrieved corpus chunks
- Citations are mandatory for all factual claims
- Agents should explicitly cite chunk IDs in their reasoning

### 2. Stateless Agent Design
- Agents receive context via `AgentContext` and return `AgentOutput`
- No mutable state within agent instances (except caches)
- Session state managed externally by `GameSession`

### 3. Retrieval-First Approach
- Each agent should retrieve relevant context before generation
- Use `RetrievalManager` for all retrieval operations
- Leverage query rewriting for better retrieval quality

### 4. Structured Output
- All agents return `AgentOutput` with content, citations, reasoning, and metadata
- Metadata should include agent-specific data (e.g., scene plans, validation results)
- Citations should reference chunk IDs for traceability

### 5. Error Handling
- Agents should handle LLM failures gracefully
- Return error outputs rather than raising exceptions
- Log errors with context for debugging

### 6. Configurability
- All prompts and behaviors configurable via `config/agents.yaml`
- Support for different LLM providers and models per agent
- Temperature and max_tokens configurable per agent

---

## Infrastructure Review

### Available Components

**From Phase 1 (Core Framework):**
- ✅ `BaseAgent` - Abstract class with LLM integration
- ✅ `LLMClient` - Multi-provider LLM abstraction (OpenAI, Gemini, Ollama)
- ✅ `AgentContext` - Input context dataclass
- ✅ `AgentOutput` - Output dataclass with citations
- ✅ `RetrievalResult` - RAG result dataclass
- ✅ `GameSession` - Session state with sliding window memory
- ✅ `GameOrchestrator` - Agent coordination and execution
- ✅ `SessionManager` - Thread-safe session storage
- ✅ Configuration system via YAML

**From Phase 2 (RAG Infrastructure):**
- ✅ `RetrievalManager` - Retrieval coordination with caching
- ✅ `HybridRetriever` - BM25 + vector search with fusion
- ✅ `QueryRewriter` - Query enhancement
- ✅ `VectorDB` abstraction - ChromaDB and Pinecone support
- ✅ Full ingestion pipeline

**What Agents Have Access To:**

```python
# From AgentContext
context.player_command       # Player's input
context.session_state        # Current session state dict
context.retrieval_results    # Pre-retrieved chunks (if any)
context.previous_turns       # Recent conversation history

# From BaseAgent
self.config                  # AgentConfig with LLM settings
self.llm_client              # LLM abstraction
self.logger                  # Structured logger
self.format_prompt()         # Prompt template formatting
self.extract_citations()     # Citation extraction utility
```

### Missing Components (To Be Implemented)

1. **Prompt Templates**: Agent-specific prompt templates (can be stored in code or config)
2. **NPC Persona Extractor**: Utility class for just-in-time persona extraction
3. **Structured Output Parsers**: For parsing scene plans and validation results
4. **Agent-Specific Utilities**: Helper functions for each agent type

---

## Agent Architecture

### Common Agent Structure

All agents follow this pattern:

```python
from src.core.base_agent import BaseAgent, AgentContext, AgentOutput
from src.core.config import AgentConfig
from src.core.retrieval_manager import RetrievalManager

class ExampleAgent(BaseAgent):
    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        super().__init__(config)
        self.retrieval_manager = retrieval_manager

    def process(self, context: AgentContext) -> AgentOutput:
        """Process context and return agent output."""
        # 1. Build retrieval query
        query = self._build_query(context)

        # 2. Retrieve relevant context
        retrieval_results = self.retrieval_manager.retrieve(
            query=query,
            top_k=self.config.retrieval_top_k,
            agent_name=self.config.name
        )

        # 3. Build prompt
        prompt = self._build_prompt(context, retrieval_results)

        # 4. Generate output
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt()
            )
        except Exception as e:
            self.logger.error("Generation failed", error=str(e))
            return AgentOutput(
                content=f"Error: {str(e)}",
                citations=[],
                reasoning="LLM generation failed",
                metadata={"error": True}
            )

        # 5. Parse response and extract citations
        output = self._parse_response(response, retrieval_results)

        return output

    def _build_query(self, context: AgentContext) -> str:
        """Build retrieval query from context."""
        raise NotImplementedError

    def _build_prompt(self, context: AgentContext, results: List[RetrievalResult]) -> str:
        """Build LLM prompt from context and retrieval results."""
        raise NotImplementedError

    def _get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        raise NotImplementedError

    def _parse_response(self, response: str, results: List[RetrievalResult]) -> AgentOutput:
        """Parse LLM response into AgentOutput."""
        raise NotImplementedError
```

### Dependency Injection

Agents require `RetrievalManager` for RAG operations. This should be injected during instantiation:

```python
# In game initialization or API setup
retrieval_manager = RetrievalManager(
    retriever=hybrid_retriever,
    query_rewriter=query_rewriter
)

narrator = NarratorAgent(
    config=app_config.agents["Narrator"],
    retrieval_manager=retrieval_manager
)
```

---

## Narrator Agent

### Purpose
Generate immersive scene descriptions grounded in the corpus. The Narrator sets the stage for player interactions by describing locations, atmosphere, and present elements.

### File: `src/agents/narrator.py`

### Responsibilities
1. Retrieve relevant scene/location descriptions from corpus
2. Generate atmospheric and descriptive text
3. Introduce NPCs present in the scene
4. Describe available interactions and objects
5. Maintain narrative consistency with previous turns

### Retrieval Strategy

**Query Construction:**

Steps:
1. Extract location/scene keywords from player command or session state
2. Combine for rich query
3. Add context from previous turns -- NOTE: We will want to dive into this as context bloat is a common cause of issues for longer sessions

**Retrieval Parameters:**
- `top_k`: 5-7 chunks (configurable)
- Query rewriting: Enabled (expand location/scene keywords)
- Focus: Location descriptions, scene settings, atmospheric details

### Prompt Structure

**System Prompt:**
```
You are the Narrator for an interactive story. Your role is to describe scenes,
locations, and atmosphere based ONLY on information from the provided text passages.

Rules:
1. Base all descriptions on the retrieved passages
2. Cite passage numbers [1], [2], etc. for all factual claims
3. Create immersive, vivid descriptions while staying true to the source material
4. Do not invent facts not present in the passages
5. Describe what the player can see, hear, smell, and feel
6. Introduce NPCs present in the scene if mentioned in passages
7. Keep descriptions concise but evocative (2-4 paragraphs)

Format your response as:
DESCRIPTION: [Your scene description with inline citations like [1], [2]]
REASONING: [Brief explanation of which passages informed your description]
```

**User Prompt Template:**
```
Retrieved Passages:
{retrieved_chunks}

Player Command: {player_command}

Current Scene: {current_scene}

Previous Context: {memory_context}

Generate a scene description for the player based on the retrieved passages.
```

### Output Structure

```python
AgentOutput(
    content="<scene description with citations>",
    citations=["chunk_0", "chunk_3", "chunk_7"],
    reasoning="Used passages about [location X] and [atmosphere Y]...",
    metadata={
        "scene": "<extracted scene name>",
        "npcs_mentioned": ["NPC1", "NPC2"],
        "locations_mentioned": ["Location1"],
        "keywords": ["keyword1", "keyword2"]
    }
)
```

### Implementation Details

**Key Methods:**
- `_build_query()`: Extract scene/location keywords from context
- `_build_prompt()`: Format system and user prompts with retrieved chunks
- `_parse_response()`: Parse LLM output, extract citations and metadata
- `_extract_npcs()`: Identify NPCs mentioned in the description
- `_extract_locations()`: Identify locations mentioned

**Special Handling:**
- First turn: Should provide initial scene setting based on `initial_context`
- Scene transitions: Detect when player moves to new location
- NPC introduction: Prepare context for NPCManager

**Error Cases:**
- No relevant chunks retrieved: Use generic "you see nothing specific" response
- LLM failure: Return error message with graceful fallback

---

## ScenePlanner Agent

### Purpose
Determine the narrative flow by deciding what happens next and which NPC (if any) should respond to the player's action. Acts as the "game master" coordinating the story.

### File: `src/agents/scene_planner.py`

### Responsibilities
1. Analyze player command and current game state
2. Determine if action triggers NPC response
3. Select appropriate NPC to respond (if applicable)
4. Determine if scene transition is needed
5. Provide reasoning for decisions

### Retrieval Strategy

**Query Construction:**
```python
def _build_query(self, context: AgentContext) -> str:
    """Build query for scene planning."""
    player_command = context.player_command
    current_scene = context.session_state.get("current_scene", "")

    # Focus on character interactions and dialogue triggers
    query = f"character NPC dialogue {player_command} {current_scene}"

    # Add context about active NPCs
    active_npcs = context.session_state.get("active_npcs", [])
    if active_npcs:
        query += " " + " ".join(active_npcs)

    return query
```

**Retrieval Parameters:**
- `top_k`: 5-8 chunks
- Query rewriting: Enabled (expand character names, action keywords)
- Focus: Character mentions, dialogue patterns, interaction descriptions

### Prompt Structure

**System Prompt:**
```
You are the ScenePlanner for an interactive story. Your role is to analyze the
player's action and determine the story flow based on the retrieved passages.

Rules:
1. Determine if an NPC should respond based on the passages
2. If an NPC should respond, select the most appropriate one from the passages
3. Determine if a scene transition is needed
4. Base all decisions on the retrieved passages
5. Cite passage numbers [1], [2], etc. for your reasoning

Output Format (JSON):
{
  "npc_responds": true/false,
  "responding_npc": "NPC Name" or null,
  "next_scene": "Scene Name" or null,
  "reasoning": "Explanation with citations",
  "fallback_to_narrator": true/false
}
```

**User Prompt Template:**
```
Retrieved Passages:
{retrieved_chunks}

Player Command: {player_command}

Current Scene: {current_scene}

Active NPCs: {active_npcs}

Previous Turn Summary: {previous_turn_summary}

Analyze the player's action and determine the scene flow.
```

### Output Structure

```python
AgentOutput(
    content="<reasoning text>",
    citations=["chunk_1", "chunk_5"],
    reasoning="Player's action triggers response from [NPC]...",
    metadata={
        "scene_plan": {
            "npc_responds": True,
            "responding_npc": "Gandalf",
            "next_scene": "Prancing Pony Inn",
            "fallback_to_narrator": False
        }
    }
)
```

### Implementation Details

**Key Methods:**
- `_build_query()`: Focus on character interactions and dialogue
- `_parse_response()`: Parse JSON output into ScenePlan
- `_extract_npc_from_passages()`: Identify NPCs mentioned in retrieved chunks
- `_should_scene_transition()`: Determine if player has moved to new location

**Decision Logic:**
1. Check if player command is directed at specific NPC
2. Check if any NPC is mentioned in retrieved passages related to action
3. If NPC found and relevant, trigger NPC response
4. If no NPC response needed, fallback to Narrator
5. Check for scene transition keywords (go, move, enter, etc.)

**Special Cases:**
- Multiple NPCs present: Choose most relevant based on retrieval scores
- No NPCs available: Set `fallback_to_narrator=True`
- Ambiguous actions: Default to Narrator description

---

## NPCManager Agent

### Purpose
Generate authentic NPC dialogue grounded in character information from the corpus. Uses just-in-time persona extraction to build character voice dynamically.

### File: `src/agents/npc_manager.py`

### Responsibilities
1. Retrieve character-specific information for the speaking NPC
2. Extract persona (speaking style, personality, knowledge) just-in-time
3. Generate in-character dialogue
4. Ensure consistency with character as portrayed in corpus
5. Cite sources for character knowledge

### Retrieval Strategy

**Two-Stage Retrieval:**

**Stage 1: Persona Extraction**
```python
def _retrieve_persona(self, npc_name: str, context: AgentContext) -> Dict[str, Any]:
    """Retrieve and extract NPC persona just-in-time."""
    # Query for character information
    query = f"{npc_name} character personality speaking style dialogue"

    persona_results = self.retrieval_manager.retrieve(
        query=query,
        top_k=10,  # More chunks for comprehensive persona
        agent_name=f"{self.config.name}_persona"
    )

    # Extract persona using LLM
    persona = self._extract_persona_from_chunks(npc_name, persona_results)

    # Cache for session
    self._cache_persona(npc_name, persona, context.session_state)

    return persona
```

**Stage 2: Dialogue Context Retrieval**
```python
def _build_query(self, context: AgentContext) -> str:
    """Build query for dialogue context."""
    npc_name = context.session_state.get("responding_npc", "")
    player_command = context.player_command

    # Focus on dialogue and conversation
    query = f"{npc_name} dialogue conversation {player_command}"

    return query
```

**Retrieval Parameters:**
- Persona extraction: `top_k=10`
- Dialogue context: `top_k=5-7`
- Query rewriting: Enabled
- Focus: Character descriptions, dialogue samples, personality traits

### Persona Extraction

**File: `src/agents/npc_persona_extractor.py`**

```python
class NPCPersonaExtractor:
    """Extracts NPC persona from corpus chunks."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract_persona(
        self,
        npc_name: str,
        chunks: List[RetrievalResult]
    ) -> Dict[str, Any]:
        """Extract persona from retrieved chunks.

        Returns:
            {
                "speaking_style": "...",
                "personality_traits": ["trait1", "trait2"],
                "background": "...",
                "knowledge_areas": ["area1", "area2"],
                "dialogue_examples": ["example1", "example2"],
                "citations": ["chunk_1", "chunk_3"]
            }
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(npc_name, chunks)

        # Use LLM to extract structured persona
        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=self._get_extraction_system_prompt()
        )

        # Parse JSON response
        persona = self._parse_persona_response(response, chunks)

        return persona
```

**Persona Extraction Prompt:**
```
Based on the following passages about {npc_name}, extract their character profile:

Retrieved Passages:
{chunks}

Extract and provide (in JSON format):
1. Speaking style (formal/informal, vocabulary, speech patterns)
2. Personality traits (3-5 key traits)
3. Background (brief summary)
4. Knowledge areas (what they know about)
5. Dialogue examples (2-3 representative quotes from passages)
6. Citations (chunk IDs used)

Format:
{
  "speaking_style": "...",
  "personality_traits": [...],
  "background": "...",
  "knowledge_areas": [...],
  "dialogue_examples": [...],
  "citations": [...]
}
```

### Prompt Structure

**System Prompt:**
```
You are roleplaying as {npc_name} in an interactive story. Your responses must
be completely in-character based on the character profile and passages provided.

Character Profile:
{persona}

Rules:
1. Stay strictly in character based on the profile
2. Use the speaking style described in the profile
3. Only discuss topics within the character's knowledge areas
4. Base dialogue on similar examples from the passages
5. Cite passage numbers [1], [2] in your internal reasoning
6. Respond naturally to the player's action/question
7. Keep responses concise (1-3 paragraphs)

Format:
DIALOGUE: [Your in-character response]
REASONING: [Brief explanation with citations]
```

**User Prompt Template:**
```
Retrieved Context Passages:
{dialogue_context_chunks}

Player's Action/Question: {player_command}

Current Scene: {current_scene}

Previous Conversation Context: {memory_context}

Respond as {npc_name}.
```

### Output Structure

```python
AgentOutput(
    content="<NPC dialogue>",
    citations=["chunk_2", "chunk_5", "chunk_9"],
    reasoning="Response based on character's [trait] and knowledge of [topic]...",
    metadata={
        "npc_name": "Gandalf",
        "persona_used": {
            "speaking_style": "...",
            "traits": [...]
        },
        "persona_cached": True,
        "dialogue_context_chunks": 5
    }
)
```

### Implementation Details

**Key Methods:**
- `_get_or_extract_persona()`: Get cached persona or extract just-in-time
- `_retrieve_persona()`: Retrieve chunks for persona extraction
- `_retrieve_dialogue_context()`: Retrieve chunks for dialogue generation
- `_build_prompt()`: Build prompt with persona and dialogue context
- `_parse_response()`: Parse dialogue and extract reasoning

**Caching Strategy:**
- Cache extracted personas in session state: `session_state["npc_personas"][npc_name]`
- Persona cache expires when session ends
- Cache key: `f"npc_persona_{npc_name}"`

**Special Cases:**
- First mention of NPC: Always extract persona
- Subsequent mentions: Use cached persona
- Unknown NPC: Return error or fallback to generic response

**Error Cases:**
- Persona extraction fails: Use generic personality
- No dialogue context: Base response only on persona
- LLM failure: Return error message

---

## RulesReferee Agent

### Purpose
Validate player actions against corpus facts to prevent hallucinations and maintain story consistency. Acts as a fact-checker ensuring all actions are grounded in the world established by the corpus.

### File: `src/agents/rules_referee.py`

### Responsibilities
1. Retrieve relevant facts about the player's intended action
2. Check for contradictions with corpus
3. Approve actions that are consistent or neutral
4. Reject actions that contradict established facts
5. Provide clear explanations with citations

### Retrieval Strategy

**Query Construction:**
```python
def _build_query(self, context: AgentContext) -> str:
    """Build query for fact validation."""
    player_command = context.player_command
    current_scene = context.session_state.get("current_scene", "")

    # Extract key action verbs and objects
    action_keywords = self._extract_action_keywords(player_command)

    # Build validation query
    query_parts = [player_command, current_scene] + action_keywords

    # Add context from narrator and NPC outputs
    if "narrator_output" in context.session_state:
        # Extract entities mentioned in scene
        pass

    return " ".join(query_parts)
```

**Retrieval Parameters:**
- `top_k`: 8-10 chunks (need comprehensive context)
- Query rewriting: Enabled (expand action keywords)
- Focus: Facts about objects, locations, characters, rules, physics

### Prompt Structure

**System Prompt:**
```
You are the RulesReferee for an interactive story. Your role is to validate player
actions against the established facts in the source material.

Rules:
1. Check if the action contradicts any facts in the retrieved passages
2. REJECT if there is a clear contradiction with cited evidence
3. APPROVE if action is consistent or neutral (not mentioned in passages)
4. When in doubt, APPROVE (allow creative interpretation)
5. Provide clear reasoning with passage citations

Validation Criteria:
- Physical impossibilities (based on passages)
- Character capability contradictions
- Location/setting inconsistencies
- Item/object availability
- Established rules violations

Output Format (JSON):
{
  "approved": true/false,
  "reason": "Explanation with citations [1], [2]",
  "severity": "blocking" / "warning" / "none",
  "suggested_alternative": "Alternative action" or null
}
```

**User Prompt Template:**
```
Retrieved Passages (Facts):
{retrieved_chunks}

Player's Intended Action: {player_command}

Current Scene: {current_scene}

Recent Context: {memory_context}

Narrator's Description: {narrator_output}

NPC Response (if any): {npc_output}

Validate the player's action against the retrieved facts.
```

### Output Structure

```python
AgentOutput(
    content="<validation explanation>",
    citations=["chunk_4", "chunk_7"],
    reasoning="Action contradicts established fact in passage [4]...",
    metadata={
        "validation_result": {
            "approved": False,
            "reason": "Dragons in this world cannot fly, as stated in [4]",
            "severity": "blocking",
            "suggested_alternative": "Try riding the dragon on the ground"
        }
    }
)
```

### Validation Result Types

```python
class ValidationSeverity(str, Enum):
    BLOCKING = "blocking"     # Clear contradiction, action cannot proceed
    WARNING = "warning"       # Questionable but allowable
    NONE = "none"            # No issues, action approved
```

### Implementation Details

**Key Methods:**
- `_build_query()`: Extract action components for targeted retrieval
- `_extract_action_keywords()`: Parse player command for key verbs/objects
- `_check_contradiction()`: Compare action against retrieved facts
- `_parse_response()`: Parse validation JSON
- `_build_rejection_message()`: Format helpful rejection message

**Validation Logic:**
1. Retrieve passages related to action components
2. Check for explicit contradictions
3. If contradiction found: REJECT with citation
4. If no mention in passages: APPROVE (allow creativity)
5. If ambiguous: APPROVE with warning

**Special Cases:**
- Creative actions: Default to approval unless clear contradiction
- Multiple interpretations: Choose most permissive
- Missing information: Approve (corpus may not cover everything)

**Error Cases:**
- No relevant chunks: Approve by default (benefit of doubt)
- LLM failure: Approve with warning in metadata
- Ambiguous validation: Log warning and approve

---

## Shared Components

### Prompt Template Manager

**File: `src/agents/prompt_templates.py`**

Centralized prompt template management:

```python
class PromptTemplateManager:
    """Manages prompt templates for all agents."""

    TEMPLATES = {
        "narrator_system": "...",
        "narrator_user": "...",
        "scene_planner_system": "...",
        # etc.
    }

    @classmethod
    def get_template(cls, template_name: str) -> str:
        """Get prompt template by name."""
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"Template not found: {template_name}")
        return cls.TEMPLATES[template_name]

    @classmethod
    def format_template(cls, template_name: str, **kwargs) -> str:
        """Format template with provided variables."""
        template = cls.get_template(template_name)
        return template.format(**kwargs)
```

### Response Parsers

**File: `src/agents/response_parsers.py`**

```python
class ResponseParser:
    """Parse structured LLM responses."""

    @staticmethod
    def parse_json_response(response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Extract JSON from markdown code blocks if present
        # Handle malformed JSON
        pass

    @staticmethod
    def extract_citations(response: str) -> List[str]:
        """Extract citation markers [1], [2] from text."""
        import re
        citations = re.findall(r'\[(\d+)\]', response)
        return citations

    @staticmethod
    def parse_sectioned_response(response: str) -> Dict[str, str]:
        """Parse response with sections like DESCRIPTION:, REASONING:"""
        sections = {}
        current_section = None
        current_content = []

        for line in response.split('\n'):
            if ':' in line and line.split(':')[0].isupper():
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line.split(':')[0].lower()
                current_content = [line.split(':', 1)[1].strip()]
            else:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections
```

### Citation Mapper

**File: `src/agents/citation_utils.py`**

```python
class CitationMapper:
    """Map citation markers to chunk IDs."""

    @staticmethod
    def map_citations(
        citation_markers: List[str],
        retrieval_results: List[RetrievalResult]
    ) -> List[str]:
        """Map citation numbers to chunk IDs.

        Args:
            citation_markers: List of citation numbers ["1", "2", "5"]
            retrieval_results: Retrieved chunks in order

        Returns:
            List of chunk IDs
        """
        chunk_ids = []
        for marker in citation_markers:
            try:
                idx = int(marker) - 1  # Citations are 1-indexed
                if 0 <= idx < len(retrieval_results):
                    chunk_ids.append(retrieval_results[idx].chunk_id)
            except (ValueError, IndexError):
                pass
        return chunk_ids

    @staticmethod
    def format_chunks_for_prompt(
        results: List[RetrievalResult],
        include_scores: bool = False
    ) -> str:
        """Format retrieval results for prompt.

        Returns formatted string like:
        [1] (Score: 0.85) Text of chunk 1...
        [2] (Score: 0.72) Text of chunk 2...
        """
        formatted = []
        for i, result in enumerate(results, 1):
            if include_scores:
                formatted.append(f"[{i}] (Score: {result.score:.2f}) {result.chunk_text}")
            else:
                formatted.append(f"[{i}] {result.chunk_text}")

        return "\n\n".join(formatted)
```

---

## Integration with Existing System

### Agent Instantiation

**During Application Startup:**

```python
# In src/api/app.py or src/core/game_setup.py

from src.core.config import AppConfig
from src.core.retrieval_manager import RetrievalManager
from src.rag.hybrid_retriever import HybridRetriever
from src.rag.bm25_retriever import BM25Retriever
from src.rag.vector_retriever import VectorRetriever
from src.rag.query_rewriter import QueryRewriter
from src.agents.narrator import NarratorAgent
from src.agents.scene_planner import ScenePlannerAgent
from src.agents.npc_manager import NPCManagerAgent
from src.agents.rules_referee import RulesRefereeAgent

def initialize_agents(config: AppConfig) -> Dict[str, BaseAgent]:
    """Initialize all agents with dependencies."""

    # 1. Load retrievers
    bm25_retriever = BM25Retriever(...)
    vector_retriever = VectorRetriever(...)
    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        ...
    )

    # 2. Create query rewriter
    query_rewriter = QueryRewriter(config.retrieval)

    # 3. Create retrieval manager
    retrieval_manager = RetrievalManager(
        retriever=hybrid_retriever,
        query_rewriter=query_rewriter
    )

    # 4. Initialize agents
    agents = {}

    if "narrator" in config.agents:
        agents["narrator"] = NarratorAgent(
            config=config.agents["narrator"],
            retrieval_manager=retrieval_manager
        )

    if "scene_planner" in config.agents:
        agents["scene_planner"] = ScenePlannerAgent(
            config=config.agents["scene_planner"],
            retrieval_manager=retrieval_manager
        )

    if "npc_manager" in config.agents:
        agents["npc_manager"] = NPCManagerAgent(
            config=config.agents["npc_manager"],
            retrieval_manager=retrieval_manager
        )

    if "rules_referee" in config.agents:
        agents["rules_referee"] = RulesRefereeAgent(
            config=config.agents["rules_referee"],
            retrieval_manager=retrieval_manager
        )

    return agents
```

### Game Loop Integration

**File: `src/core/game_loop.py`** (to be created)

```python
class GameLoop:
    """Orchestrates a single game turn with agents."""

    def __init__(
        self,
        orchestrator: GameOrchestrator,
        retrieval_manager: RetrievalManager
    ):
        self.orchestrator = orchestrator
        self.retrieval_manager = retrieval_manager

    def execute_turn(
        self,
        session: GameSession,
        player_command: str,
        initial_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a single game turn.

        Returns:
            {
                "turn_number": int,
                "outputs": {
                    "narrator": {...},
                    "scene_planner": {...},
                    "npc_manager": {...},
                    "rules_referee": {...}
                },
                "retrieved_chunks": [...],
                "session_state": {...}
            }
        """
        # 1. Pre-retrieve context for all agents
        retrieval_results = self.retrieval_manager.retrieve(
            query=player_command,
            top_k=10,
            agent_name="game_loop"
        )

        # 2. Execute orchestrator
        turn_result = self.orchestrator.execute_turn(
            session=session,
            player_command=player_command,
            retrieval_results=retrieval_results,
            initial_context=initial_context
        )

        # 3. Add retrieval results to response
        turn_result["retrieved_chunks"] = [
            {
                "chunk_id": r.chunk_id,
                "text": r.chunk_text,
                "score": r.score
            }
            for r in retrieval_results
        ]

        # 4. Add session state
        turn_result["session_state"] = session.to_dict()

        return turn_result
```

### API Endpoint Integration

**File: `src/api/endpoints/game.py`** (to be created)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.core.game_loop import GameLoop
from src.core.session_manager import SessionManager

router = APIRouter(prefix="/game", tags=["game"])

class NewGameRequest(BaseModel):
    initial_context: Optional[str] = None

class TurnRequest(BaseModel):
    session_id: str
    player_command: str

@router.post("/new_game")
async def new_game(request: NewGameRequest):
    """Create a new game session."""
    session_id = session_manager.create_session()

    # Execute first turn with initial context
    if request.initial_context:
        turn_result = game_loop.execute_turn(
            session=session_manager.get_session(session_id),
            player_command="look around",
            initial_context=request.initial_context
        )
        return {
            "session_id": session_id,
            "turn_result": turn_result
        }

    return {"session_id": session_id}

@router.post("/turn")
async def process_turn(request: TurnRequest):
    """Process a player command."""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    turn_result = game_loop.execute_turn(
        session=session,
        player_command=request.player_command
    )

    return turn_result

@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get current game state."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.to_dict()
```

---

## Testing Strategy

### Unit Tests

**For Each Agent:**

```python
# tests/test_agents/test_narrator.py

import pytest
from unittest.mock import Mock
from src.agents.narrator import NarratorAgent
from src.core.base_agent import AgentContext, RetrievalResult

def test_narrator_generates_description(mock_retrieval_manager, mock_llm_config):
    """Test narrator generates scene description."""
    narrator = NarratorAgent(
        config=mock_llm_config,
        retrieval_manager=mock_retrieval_manager
    )

    context = AgentContext(
        player_command="look around",
        session_state={"current_scene": "tavern"},
        retrieval_results=[
            RetrievalResult(
                chunk_text="The tavern is dimly lit...",
                score=0.9,
                chunk_id="chunk_1"
            )
        ],
        previous_turns=[]
    )

    output = narrator.process(context)

    assert output.content
    assert len(output.citations) > 0
    assert output.reasoning
    assert "scene" in output.metadata

def test_narrator_handles_no_retrieval_results():
    """Test narrator handles case with no retrieval results."""
    # Test fallback behavior
    pass

def test_narrator_extracts_npcs_from_description():
    """Test NPC extraction from scene description."""
    pass
```

**Test Coverage for Each Agent:**
- ✅ Basic processing with valid input
- ✅ Retrieval query construction
- ✅ Prompt building
- ✅ Response parsing
- ✅ Citation extraction
- ✅ Error handling (LLM failure, no retrieval results)
- ✅ Edge cases (empty input, malformed responses)

### Integration Tests

**File: `tests/test_integration/test_agent_coordination.py`**

```python
def test_full_turn_with_all_agents(
    narrator, scene_planner, npc_manager, rules_referee,
    orchestrator, session
):
    """Test full turn with all agents coordinating."""

    # Execute turn
    turn_result = orchestrator.execute_turn(
        session=session,
        player_command="talk to Gandalf",
        retrieval_results=mock_retrieval_results
    )

    # Verify all agents executed
    assert "narrator" in turn_result["outputs"]
    assert "scene_planner" in turn_result["outputs"]
    assert "npc_manager" in turn_result["outputs"]
    assert "rules_referee" in turn_result["outputs"]

    # Verify scene planner triggered NPC response
    scene_plan = turn_result["outputs"]["scene_planner"]["metadata"]["scene_plan"]
    assert scene_plan["npc_responds"] == True
    assert scene_plan["responding_npc"] == "Gandalf"

    # Verify NPC manager used correct persona
    npc_output = turn_result["outputs"]["npc_manager"]
    assert "Gandalf" in npc_output["metadata"]["npc_name"]

def test_narrator_to_scene_planner_handoff():
    """Test data flow from Narrator to ScenePlanner."""
    pass

def test_scene_planner_triggers_npc_response():
    """Test ScenePlanner correctly triggers NPCManager."""
    pass

def test_rules_referee_blocks_invalid_action():
    """Test RulesReferee blocks contradictory action."""
    pass
```

### Mock Fixtures

**File: `tests/conftest.py`** (additions)

```python
@pytest.fixture
def mock_retrieval_manager():
    """Mock RetrievalManager for testing."""
    manager = Mock()
    manager.retrieve.return_value = [
        RetrievalResult(
            chunk_text="Sample chunk text",
            score=0.9,
            chunk_id="chunk_0",
            metadata={}
        )
    ]
    return manager

@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for testing."""
    client = Mock()
    client.generate.return_value = "Sample LLM response"
    return client

@pytest.fixture
def sample_agent_config():
    """Sample AgentConfig for testing."""
    from src.core.config import AgentConfig, LLMConfig, LLMProvider

    return AgentConfig(
        name="TestAgent",
        llm=LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="test-model",
            temperature=0.7,
            max_tokens=1000
        ),
        retrieval_top_k=5,
        enabled=True
    )
```

---

## Implementation Order

### Phase 3A: Core Agents (Week 1-2)

1. **Shared Components** (1-2 days)
   - `src/agents/prompt_templates.py`
   - `src/agents/response_parsers.py`
   - `src/agents/citation_utils.py`
   - Unit tests for utilities

2. **Narrator Agent** (2-3 days)
   - `src/agents/narrator.py`
   - Unit tests
   - Integration test with orchestrator
   - Configuration in `config/agents.yaml`

3. **RulesReferee Agent** (2-3 days)
   - `src/agents/rules_referee.py`
   - Unit tests
   - Integration test with orchestrator
   - Validation logic testing

### Phase 3B: Planning and NPC Agents (Week 2-3)

4. **ScenePlanner Agent** (2-3 days)
   - `src/agents/scene_planner.py`
   - Unit tests
   - Integration test with Narrator and NPCManager
   - Decision logic testing

5. **NPC Persona Extractor** (2-3 days)
   - `src/agents/npc_persona_extractor.py`
   - Persona extraction logic
   - Caching strategy
   - Unit tests

6. **NPCManager Agent** (3-4 days)
   - `src/agents/npc_manager.py`
   - Integration with persona extractor
   - Unit tests
   - Integration tests with ScenePlanner
   - Persona caching tests

### Phase 3C: Integration and Testing (Week 3-4)

7. **Game Loop** (2-3 days)
   - `src/core/game_loop.py`
   - Integration with all agents
   - Turn execution logic
   - Unit and integration tests

8. **API Endpoints** (2-3 days)
   - `src/api/endpoints/game.py`
   - `/new_game` endpoint
   - `/turn` endpoint
   - `/state/{session_id}` endpoint
   - API integration tests

9. **End-to-End Testing** (2-3 days)
   - Full game flow tests
   - Multi-turn conversation tests
   - Error handling and edge cases
   - Performance testing

10. **Documentation and Examples** (1-2 days)
    - Usage examples
    - Configuration guide
    - Troubleshooting guide
    - Update README

### Estimated Timeline
- **Total: 3-4 weeks**
- **Phase 3A**: 1-2 weeks (Core agents)
- **Phase 3B**: 1-1.5 weeks (Planning and NPC)
- **Phase 3C**: 1-1.5 weeks (Integration)

---

## Success Criteria

### Functional Requirements
- ✅ All four agents implemented and passing unit tests
- ✅ Agents successfully coordinate through orchestrator
- ✅ Retrieval integration works correctly
- ✅ Citations are properly extracted and tracked
- ✅ NPC persona extraction works and caches correctly
- ✅ Scene planning logic correctly determines NPC responses
- ✅ Rules validation blocks contradictory actions
- ✅ Game loop executes complete turns
- ✅ API endpoints functional and tested

### Quality Requirements
- ✅ Test coverage > 80% for all agent code
- ✅ All agents handle LLM failures gracefully
- ✅ Configuration system works for all agents
- ✅ Logging provides visibility into agent decisions
- ✅ Performance acceptable (< 5 seconds per turn with local LLM)
- ✅ Documentation complete and accurate

### Integration Requirements
- ✅ Agents work with all supported LLM providers (OpenAI, Gemini, Ollama)
- ✅ Retrieval system integration is seamless
- ✅ Session management works correctly
- ✅ Multi-session concurrency works
- ✅ Error states are handled gracefully

---

## Appendix: Example Configurations

### Example `config/agents.yaml` with Prompt Templates

```yaml
agents:
  narrator:
    name: "The Narrator"
    llm:
      provider: ollama
      model: mistral
      temperature: 0.8
      max_tokens: 1500
    persona_template: |
      You are an experienced storyteller who brings scenes to life with vivid descriptions.
    retrieval_query_template: "scene location setting atmosphere {current_scene} {player_command}"
    retrieval_top_k: 7
    enabled: true

  scene_planner:
    name: "ScenePlanner"
    llm:
      provider: ollama
      model: llama2
      temperature: 0.5
      max_tokens: 500
    retrieval_query_template: "character NPC interaction {player_command} {current_scene}"
    retrieval_top_k: 8
    enabled: true

  npc_manager:
    name: "NPCManager"
    llm:
      provider: openai
      model: gpt-4
      temperature: 0.7
      max_tokens: 1000
    retrieval_query_template: "{npc_name} dialogue conversation {player_command}"
    retrieval_top_k: 6
    enabled: true

  rules_referee:
    name: "RulesReferee"
    llm:
      provider: ollama
      model: llama2
      temperature: 0.3
      max_tokens: 500
    retrieval_query_template: "facts rules {player_command} {current_scene}"
    retrieval_top_k: 10
    enabled: true
```

---

## Conclusion

This design document provides a complete blueprint for implementing all four agents in Phase 3. All necessary infrastructure is in place from Phases 1 and 2. The agents are designed to:

1. **Work seamlessly with existing infrastructure**
2. **Maintain corpus grounding through citations**
3. **Coordinate effectively via the orchestrator**
4. **Handle errors gracefully**
5. **Be fully configurable**
6. **Be thoroughly testable**

The implementation can proceed immediately following the suggested order, with each agent building on the previous work. The estimated timeline of 3-4 weeks is realistic for a complete, tested implementation.

**Next Steps:**
1. Review this design with stakeholders
2. Begin implementation with shared components
3. Implement agents in suggested order
4. Test continuously throughout implementation
5. Document as you go

**Questions or concerns should be addressed before implementation begins.**
