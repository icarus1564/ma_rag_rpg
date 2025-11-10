# GameLoop Redesign: Correct Agent Orchestration Flow

## Document Status
**Status:** Design Phase - Awaiting Approval
**Date:** 2025-11-10
**Purpose:** Fix agent orchestration to match the required control flow defined in `docs/GameLoopLogic.md`

---

## Executive Summary

The current `GameLoop` and `GameOrchestrator` implementations execute all agents in a fixed sequential order without proper decision points. This violates the required control flow where:

1. **RulesReferee** validates the user prompt FIRST
2. **ScenePlanner** makes routing decisions based on validation results
3. Only ONE agent (Narrator OR NPCManager) executes based on ScenePlanner's decision
4. Agent responses are validated AFTER generation

This design document specifies the corrected architecture to implement the proper orchestration flow.

---

## Problem Analysis

### Current Implementation Issues

**1. Incorrect Agent Execution Order (game_loop.py:328)**
```python
agent_order = ["narrator", "scene_planner", "npc_manager", "rules_referee"]
```
**Problem:** RulesReferee runs LAST instead of FIRST. All agents execute regardless of validation.

**2. No Decision Points (game_loop.py:344-428)**
```python
for agent_name in agent_order:
    # Executes ALL agents in sequence without branching
    agent_output = agent.process(context)
```
**Problem:** No conditional logic to route based on RulesReferee or ScenePlanner outputs.

**3. Missing Dual Validation**
- User prompt validation happens too late (or not at all)
- Agent response validation not implemented
- No win/loss determination logic

**4. Persona Dictionary Not Managed**
- No session-level persona cache
- NPCPersonaExtractor not called on-demand
- No persona persistence

**5. Wrong Agent Communication Pattern**
- Agents don't receive outputs from previous agents in a structured way
- ScenePlanner doesn't get RulesReferee judgment
- NPCManager doesn't get extracted persona

---

## Required Control Flow

### Turn Execution Phases

```
Phase 1: TURN START
├─ Initialize turn number
├─ Log turn start
└─ Create progress tracker

Phase 2: USER PROMPT RETRIEVAL
├─ Retrieve relevant corpus chunks for user prompt
├─ Update progress: "Retrieving context for user prompt"
└─ Return: retrieval_results_user

Phase 3: USER PROMPT VALIDATION
├─ Call RulesReferee(user_prompt, retrieval_results_user)
├─ Update progress: "Validating user prompt against corpus"
├─ RulesReferee returns: ValidationResult
│  ├─ approved: bool
│  ├─ reason: str
│  ├─ confidence: float
│  └─ suggestions: Optional[List[str]]
└─ Log validation result

Phase 4: SCENE PLANNING & ROUTING DECISION
├─ Call ScenePlanner(user_prompt, retrieval_results_user, validation_result)
├─ Update progress: "Planning scene and determining next agent"
├─ ScenePlanner returns: ScenePlanOutput
│  ├─ next_action: "engage_npc" | "narrator_scene" | "disqualify"
│  ├─ target: Optional[str]  # NPC name if engage_npc
│  ├─ reasoning: str
│  ├─ retrieval_quality: float
│  └─ alternative_suggestions: Optional[List[str]]
└─ Log scene plan decision

Phase 5: AGENT EXECUTION (CONDITIONAL BRANCHING)
├─ IF next_action == "disqualify":
│  ├─ Call Narrator(disqualification_mode=True, reasoning, suggestions)
│  ├─ Update progress: "Generating disqualification message"
│  ├─ Post narrator response to UI
│  ├─ TURN ENDS → PLAYER LOSES
│  └─ Return TurnResult(success=False, reason="disqualified")
│
├─ ELSE IF next_action == "engage_npc":
│  ├─ npc_name = scene_plan.target
│  ├─ IF npc_name NOT IN session.persona_cache:
│  │  ├─ Call NPCPersonaExtractor(npc_name, corpus_chunks)
│  │  ├─ Update progress: "Extracting persona for {npc_name}"
│  │  ├─ Store persona in session.persona_cache[npc_name]
│  │  └─ Log persona extraction
│  ├─ ELSE:
│  │  └─ Load persona from session.persona_cache[npc_name]
│  ├─ Call NPCManager(user_prompt, persona, retrieval_results_user)
│  ├─ Update progress: "Generating response as {npc_name}"
│  └─ agent_response = npc_output
│
└─ ELSE IF next_action == "narrator_scene":
   ├─ Call Narrator(narration_mode=True, scene_context)
   ├─ Update progress: "Generating scene narration"
   └─ agent_response = narrator_output

Phase 6: AGENT RESPONSE RETRIEVAL (SKIP IF DISQUALIFIED)
├─ IF NOT disqualified:
│  ├─ Retrieve relevant corpus chunks for agent_response
│  ├─ Update progress: "Retrieving context for agent response validation"
│  └─ Return: retrieval_results_agent

Phase 7: AGENT RESPONSE VALIDATION (SKIP IF DISQUALIFIED)
├─ IF NOT disqualified:
│  ├─ Call RulesReferee(agent_response, retrieval_results_agent)
│  ├─ Update progress: "Validating agent response against corpus"
│  ├─ RulesReferee returns: ValidationResult
│  │  ├─ approved: bool
│  │  ├─ reason: str
│  │  └─ confidence: float
│  └─ Log validation result

Phase 8: FINAL RESPONSE HANDLING
├─ IF agent_response_approved:
│  ├─ Post agent_response to UI (with agent identification)
│  ├─ TURN ENDS → GAME CONTINUES
│  └─ Return TurnResult(success=True, agent_output)
│
└─ ELSE (agent_response_disqualified):
   ├─ Call Narrator(correction_mode=True, agent_response, disqualification_reason)
   ├─ Update progress: "Agent response disqualified - generating correction"
   ├─ Post correction to UI
   ├─ TURN ENDS → PLAYER WINS
   └─ Return TurnResult(success=True, player_wins=True, correction)

Phase 9: UPDATE SESSION STATE
├─ Update session.state.current_scene
├─ Update session.state.active_npcs
├─ Update session.state.last_validation
├─ Add turn to session.turns
└─ Log turn completion

Phase 10: TURN COMPLETE
├─ Calculate total duration
├─ Update progress: "Turn {n} completed"
└─ Return TurnResult
```

---

## Data Structures

### 1. ValidationResult (New Structure)

```python
@dataclass
class ValidationResult:
    """Result from RulesReferee validation."""
    approved: bool
    reason: str
    confidence: float  # 0.0 to 1.0
    relevant_chunks: List[str]  # Chunk IDs used for validation
    suggestions: Optional[List[str]] = None  # Alternative approaches if rejected
    citations: List[int] = field(default_factory=list)  # Citation indices
```

**Usage:**
- Returned by RulesReferee for both user prompt and agent response validation
- Passed to ScenePlanner for decision making
- Stored in turn result metadata

### 2. ScenePlanOutput (New Structure)

```python
@dataclass
class ScenePlanOutput:
    """Output from ScenePlanner routing decision."""
    next_action: str  # "engage_npc", "narrator_scene", "disqualify"
    target: Optional[str]  # NPC name if engage_npc, None otherwise
    reasoning: str  # Why this decision was made
    retrieval_quality: float  # Quality assessment of retrieval results
    validation_status: str  # "approved", "rejected", "uncertain"
    alternative_suggestions: Optional[List[str]] = None  # If disqualified
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**next_action Values:**
- `"disqualify"`: User prompt doesn't match corpus → call Narrator with disqualification
- `"narrator_scene"`: Valid prompt, no NPC interaction → call Narrator for scene description
- `"engage_npc"`: Valid prompt, NPC should respond → call NPCManager with persona

### 3. TurnPhase (Updated Enum)

```python
class TurnPhase(str, Enum):
    """Phases of a game turn for progress tracking."""
    STARTED = "started"
    USER_RETRIEVAL = "user_retrieval"
    USER_VALIDATION = "user_validation"
    SCENE_PLANNING = "scene_planning"
    PERSONA_EXTRACTION = "persona_extraction"  # NEW
    NARRATOR_DISQUALIFY = "narrator_disqualify"  # NEW
    NARRATOR_SCENE = "narrator_scene"  # NEW
    NPC_RESPONSE = "npc_response"  # NEW
    AGENT_RETRIEVAL = "agent_retrieval"  # NEW
    AGENT_VALIDATION = "agent_validation"  # NEW
    NARRATOR_CORRECTION = "narrator_correction"  # NEW
    AGGREGATING = "aggregating"
    UPDATING_STATE = "updating_state"
    COMPLETED = "completed"
    ERROR = "error"
```

### 4. TurnResult (Updated Structure)

```python
@dataclass
class TurnResult:
    """Result of a game turn."""
    turn_number: int
    session_id: str
    player_command: str

    # Validation results
    user_validation: Optional[ValidationResult] = None  # NEW
    agent_validation: Optional[ValidationResult] = None  # NEW

    # Scene planning
    scene_plan: Optional[ScenePlanOutput] = None  # NEW

    # Agent outputs (only ONE will be populated)
    narrator_output: Optional[Dict[str, Any]] = None
    npc_output: Optional[Dict[str, Any]] = None

    # Turn outcome
    success: bool = True
    player_wins: bool = False  # NEW: True if agent response was disqualified
    player_loses: bool = False  # NEW: True if user prompt was disqualified
    turn_ended_early: bool = False  # NEW: True if turn ended at validation

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: Optional[str] = None
```

### 5. SessionState (Extended)

```python
class GameSession:
    # Existing fields...

    # NEW: Persona cache for NPCs
    persona_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Key: NPC name, Value: ExtractedPersona

    # NEW: Track turn outcomes
    wins: int = 0  # Player wins (agent disqualified)
    losses: int = 0  # Player losses (user disqualified)
```

**persona_cache Structure:**
```python
{
    "Gandalf": {
        "speaking_style": "wise and cryptic",
        "personality_traits": ["intelligent", "mysterious", "patient"],
        "background": "Ancient wizard...",
        "extracted_at": "2025-11-10T10:23:45Z",
        "chunks_used": ["chunk_42", "chunk_87", ...],
    }
}
```

---

## Component Modifications

### 1. GameLoop Class (src/core/game_loop.py)

**Major Changes:**

#### A. New `execute_turn()` Structure

```python
@debug_log_method
def execute_turn(
    self,
    session: GameSession,
    player_command: str,
    initial_context: Optional[str] = None,
) -> TurnResult:
    """Execute turn with correct orchestration flow."""

    # Phase 1: Initialize
    # Phase 2: User prompt retrieval
    user_retrieval = self._retrieve_for_user_prompt(session, player_command, progress)

    # Phase 3: User prompt validation
    user_validation = self._validate_user_prompt(
        player_command, user_retrieval, progress
    )

    # Phase 4: Scene planning & routing
    scene_plan = self._plan_scene(
        session, player_command, user_retrieval, user_validation, progress
    )

    # Phase 5: Conditional agent execution
    if scene_plan.next_action == "disqualify":
        return self._handle_disqualification(
            session, turn_number, player_command, scene_plan, user_validation, progress
        )

    # Phase 5 continued: Execute appropriate agent
    agent_output, agent_name = self._execute_selected_agent(
        session, player_command, user_retrieval, scene_plan, progress
    )

    # Phase 6: Agent response retrieval
    agent_retrieval = self._retrieve_for_agent_response(
        session, agent_output, progress
    )

    # Phase 7: Agent response validation
    agent_validation = self._validate_agent_response(
        agent_output, agent_retrieval, progress
    )

    # Phase 8: Final response handling
    if not agent_validation.approved:
        return self._handle_agent_disqualification(
            session, turn_number, player_command, agent_output,
            agent_validation, progress
        )

    # Phase 9: Update state and return success
    return self._finalize_turn(
        session, turn_number, player_command, agent_output, agent_name,
        user_validation, agent_validation, scene_plan, progress
    )
```

#### B. New Helper Methods

**1. `_retrieve_for_user_prompt()`**
```python
def _retrieve_for_user_prompt(
    self,
    session: GameSession,
    player_command: str,
    progress: TurnProgress,
) -> List[RetrievalResult]:
    """Retrieve corpus context for user prompt validation."""
    progress.phase = TurnPhase.USER_RETRIEVAL
    progress.message = "Retrieving context for user prompt"
    self._update_progress(progress)

    # Build query from player command + recent context
    query = self._build_retrieval_query(session, player_command)

    # Retrieve chunks
    results = self.retrieval_manager.retrieve(
        query=query,
        top_k=10,
        agent_name="user_prompt_validation",
    )

    progress.retrieval_calls += 1
    return results
```

**2. `_validate_user_prompt()`**
```python
def _validate_user_prompt(
    self,
    player_command: str,
    retrieval_results: List[RetrievalResult],
    progress: TurnProgress,
) -> ValidationResult:
    """Validate user prompt against corpus using RulesReferee."""
    progress.phase = TurnPhase.USER_VALIDATION
    progress.current_agent = "rules_referee"
    progress.message = "Validating user prompt against corpus"
    self._update_progress(progress)

    # Get RulesReferee agent
    referee = self.orchestrator.agents.get("rules_referee")
    if not referee or not referee.config.enabled:
        # Default to approved if referee not available
        return ValidationResult(
            approved=True,
            reason="RulesReferee not available",
            confidence=0.5,
            relevant_chunks=[],
        )

    # Create context for validation
    context = AgentContext(
        player_command=player_command,
        session_state={"validation_mode": "user_prompt"},
        retrieval_results=retrieval_results,
        previous_turns=[],
    )

    # Execute RulesReferee
    try:
        agent_output = referee.process(context)
        progress.agents_completed.append("rules_referee")

        # Extract ValidationResult from agent output
        return self._extract_validation_result(agent_output)

    except Exception as e:
        self.logger.error("User prompt validation failed", error=str(e))
        progress.agents_failed.append("rules_referee")
        # Default to approved on error (fail-open)
        return ValidationResult(
            approved=True,
            reason=f"Validation error: {str(e)}",
            confidence=0.0,
            relevant_chunks=[],
        )
```

**3. `_plan_scene()`**
```python
def _plan_scene(
    self,
    session: GameSession,
    player_command: str,
    retrieval_results: List[RetrievalResult],
    validation_result: ValidationResult,
    progress: TurnProgress,
) -> ScenePlanOutput:
    """Plan scene and determine next agent using ScenePlanner."""
    progress.phase = TurnPhase.SCENE_PLANNING
    progress.current_agent = "scene_planner"
    progress.message = "Planning scene and determining next agent"
    self._update_progress(progress)

    # Get ScenePlanner agent
    planner = self.orchestrator.agents.get("scene_planner")
    if not planner or not planner.config.enabled:
        # Default to narrator if planner not available
        return ScenePlanOutput(
            next_action="narrator_scene",
            target=None,
            reasoning="ScenePlanner not available",
            retrieval_quality=0.5,
            validation_status="unknown",
        )

    # Create context with validation result
    context = AgentContext(
        player_command=player_command,
        session_state={
            **session.state,
            "validation_result": validation_result,  # CRITICAL: Pass validation
        },
        retrieval_results=retrieval_results,
        previous_turns=session.state.get("memory", []),
    )

    # Execute ScenePlanner
    try:
        agent_output = planner.process(context)
        progress.agents_completed.append("scene_planner")

        # Extract ScenePlanOutput from agent output
        return self._extract_scene_plan(agent_output, validation_result)

    except Exception as e:
        self.logger.error("Scene planning failed", error=str(e))
        progress.agents_failed.append("scene_planner")
        # Fallback to narrator
        return ScenePlanOutput(
            next_action="narrator_scene",
            target=None,
            reasoning=f"Scene planning error: {str(e)}",
            retrieval_quality=0.0,
            validation_status="error",
        )
```

**4. `_execute_selected_agent()`**
```python
def _execute_selected_agent(
    self,
    session: GameSession,
    player_command: str,
    retrieval_results: List[RetrievalResult],
    scene_plan: ScenePlanOutput,
    progress: TurnProgress,
) -> Tuple[Dict[str, Any], str]:
    """Execute the agent selected by ScenePlanner."""

    if scene_plan.next_action == "engage_npc":
        return self._execute_npc_manager(
            session, player_command, retrieval_results, scene_plan, progress
        )

    elif scene_plan.next_action == "narrator_scene":
        return self._execute_narrator(
            session, player_command, retrieval_results, scene_plan, progress
        )

    else:
        # Should not reach here (disqualify handled earlier)
        raise ValueError(f"Unexpected next_action: {scene_plan.next_action}")
```

**5. `_execute_npc_manager()`**
```python
def _execute_npc_manager(
    self,
    session: GameSession,
    player_command: str,
    retrieval_results: List[RetrievalResult],
    scene_plan: ScenePlanOutput,
    progress: TurnProgress,
) -> Tuple[Dict[str, Any], str]:
    """Execute NPCManager with persona extraction if needed."""

    npc_name = scene_plan.target
    if not npc_name:
        raise ValueError("engage_npc action requires target NPC name")

    # Check persona cache
    if npc_name not in session.persona_cache:
        # Extract persona
        progress.phase = TurnPhase.PERSONA_EXTRACTION
        progress.current_agent = "npc_persona_extractor"
        progress.message = f"Extracting persona for {npc_name}"
        self._update_progress(progress)

        persona = self._extract_persona(session, npc_name, progress)
        session.persona_cache[npc_name] = persona
    else:
        persona = session.persona_cache[npc_name]
        self.logger.debug(f"Using cached persona for {npc_name}")

    # Execute NPCManager
    progress.phase = TurnPhase.NPC_RESPONSE
    progress.current_agent = "npc_manager"
    progress.message = f"Generating response as {npc_name}"
    self._update_progress(progress)

    npc_manager = self.orchestrator.agents.get("npc_manager")
    if not npc_manager or not npc_manager.config.enabled:
        raise ValueError("NPCManager not available")

    # Create context with persona
    context = AgentContext(
        player_command=player_command,
        session_state={
            **session.state,
            "npc_name": npc_name,
            "npc_persona": persona,  # CRITICAL: Pass persona
        },
        retrieval_results=retrieval_results,
        previous_turns=session.state.get("memory", []),
    )

    # Execute
    agent_output = npc_manager.process(context)
    progress.agents_completed.append("npc_manager")

    return (
        {
            "content": agent_output.content,
            "citations": agent_output.citations,
            "reasoning": agent_output.reasoning,
            "metadata": {**agent_output.metadata, "npc_name": npc_name},
        },
        npc_name  # Return NPC name as agent identifier
    )
```

**6. `_execute_narrator()`**
```python
def _execute_narrator(
    self,
    session: GameSession,
    player_command: str,
    retrieval_results: List[RetrievalResult],
    scene_plan: ScenePlanOutput,
    progress: TurnProgress,
) -> Tuple[Dict[str, Any], str]:
    """Execute Narrator for scene description."""

    progress.phase = TurnPhase.NARRATOR_SCENE
    progress.current_agent = "narrator"
    progress.message = "Generating scene narration"
    self._update_progress(progress)

    narrator = self.orchestrator.agents.get("narrator")
    if not narrator or not narrator.config.enabled:
        raise ValueError("Narrator not available")

    # Create context
    context = AgentContext(
        player_command=player_command,
        session_state={
            **session.state,
            "mode": "narration",
        },
        retrieval_results=retrieval_results,
        previous_turns=session.state.get("memory", []),
    )

    # Execute
    agent_output = narrator.process(context)
    progress.agents_completed.append("narrator")

    return (
        {
            "content": agent_output.content,
            "citations": agent_output.citations,
            "reasoning": agent_output.reasoning,
            "metadata": agent_output.metadata,
        },
        "Narrator"
    )
```

**7. `_handle_disqualification()`**
```python
def _handle_disqualification(
    self,
    session: GameSession,
    turn_number: int,
    player_command: str,
    scene_plan: ScenePlanOutput,
    validation_result: ValidationResult,
    progress: TurnProgress,
) -> TurnResult:
    """Handle user prompt disqualification - player loses."""

    progress.phase = TurnPhase.NARRATOR_DISQUALIFY
    progress.current_agent = "narrator"
    progress.message = "Generating disqualification message"
    self._update_progress(progress)

    narrator = self.orchestrator.agents.get("narrator")
    if not narrator or not narrator.config.enabled:
        # Fallback message if narrator unavailable
        disqualification_msg = {
            "content": (
                f"That action doesn't fit this world. {validation_result.reason}\n\n"
                f"Try: {', '.join(scene_plan.alternative_suggestions or [])}"
            ),
            "citations": [],
            "reasoning": "Narrator unavailable for disqualification",
            "metadata": {},
        }
    else:
        # Create context for disqualification
        context = AgentContext(
            player_command=player_command,
            session_state={
                **session.state,
                "mode": "disqualification",
                "disqualification_reason": validation_result.reason,
                "alternative_suggestions": scene_plan.alternative_suggestions,
            },
            retrieval_results=[],
            previous_turns=session.state.get("memory", []),
        )

        # Execute narrator
        agent_output = narrator.process(context)
        disqualification_msg = {
            "content": agent_output.content,
            "citations": agent_output.citations,
            "reasoning": agent_output.reasoning,
            "metadata": agent_output.metadata,
        }

    progress.agents_completed.append("narrator")

    # Update session
    session.losses += 1

    # Complete turn
    progress.phase = TurnPhase.COMPLETED
    progress.message = f"Turn {turn_number} ended - user prompt disqualified"
    self._update_progress(progress)

    return TurnResult(
        turn_number=turn_number,
        session_id=session.session_id,
        player_command=player_command,
        user_validation=validation_result,
        scene_plan=scene_plan,
        narrator_output=disqualification_msg,
        success=True,
        player_loses=True,
        turn_ended_early=True,
        metadata={
            "disqualification_reason": validation_result.reason,
            "alternative_suggestions": scene_plan.alternative_suggestions,
        },
    )
```

**8. `_handle_agent_disqualification()`**
```python
def _handle_agent_disqualification(
    self,
    session: GameSession,
    turn_number: int,
    player_command: str,
    agent_output: Dict[str, Any],
    validation_result: ValidationResult,
    progress: TurnProgress,
) -> TurnResult:
    """Handle agent response disqualification - player wins."""

    progress.phase = TurnPhase.NARRATOR_CORRECTION
    progress.current_agent = "narrator"
    progress.message = "Agent response disqualified - generating correction"
    self._update_progress(progress)

    narrator = self.orchestrator.agents.get("narrator")
    if not narrator or not narrator.config.enabled:
        # Fallback message
        correction_msg = {
            "content": (
                f"[Agent response rejected: {validation_result.reason}]\n\n"
                f"Original response: {agent_output['content'][:200]}..."
            ),
            "citations": [],
            "reasoning": "Narrator unavailable for correction",
            "metadata": {},
        }
    else:
        # Create context for correction
        context = AgentContext(
            player_command=player_command,
            session_state={
                **session.state,
                "mode": "correction",
                "agent_response": agent_output["content"],
                "disqualification_reason": validation_result.reason,
            },
            retrieval_results=[],
            previous_turns=session.state.get("memory", []),
        )

        # Execute narrator
        narrator_output = narrator.process(context)
        correction_msg = {
            "content": narrator_output.content,
            "citations": narrator_output.citations,
            "reasoning": narrator_output.reasoning,
            "metadata": narrator_output.metadata,
        }

    progress.agents_completed.append("narrator")

    # Update session
    session.wins += 1

    # Complete turn
    progress.phase = TurnPhase.COMPLETED
    progress.message = f"Turn {turn_number} ended - agent response disqualified (player wins)"
    self._update_progress(progress)

    return TurnResult(
        turn_number=turn_number,
        session_id=session.session_id,
        player_command=player_command,
        agent_validation=validation_result,
        narrator_output=correction_msg,
        success=True,
        player_wins=True,
        metadata={
            "original_agent_response": agent_output["content"],
            "disqualification_reason": validation_result.reason,
        },
    )
```

---

### 2. GameOrchestrator (src/core/orchestrator.py)

**Status:** Minimal changes required - orchestration logic moves to GameLoop

**Changes:**
1. Remove `execute_turn()` method (logic moves to GameLoop)
2. Keep `agents` dict as-is (accessed by GameLoop)
3. Remove `_update_session_state()` (moves to GameLoop)

**Reasoning:**
- GameOrchestrator becomes a simple container for agents
- GameLoop handles orchestration logic with proper control flow
- Cleaner separation of concerns

---

### 3. Agent Interface Updates

#### A. RulesReferee Agent

**Current Issue:** Returns generic AgentOutput instead of structured ValidationResult

**Required Change:**
```python
# In metadata field of AgentOutput:
agent_output.metadata["validation_result"] = ValidationResult(
    approved=bool,
    reason=str,
    confidence=float,
    relevant_chunks=List[str],
    suggestions=Optional[List[str]],
    citations=List[int],
)
```

**GameLoop Extraction:**
```python
def _extract_validation_result(self, agent_output: AgentOutput) -> ValidationResult:
    """Extract ValidationResult from RulesReferee output."""
    validation_data = agent_output.metadata.get("validation_result", {})

    # Handle dict or ValidationResult object
    if isinstance(validation_data, ValidationResult):
        return validation_data

    return ValidationResult(
        approved=validation_data.get("approved", True),
        reason=validation_data.get("reason", ""),
        confidence=validation_data.get("confidence", 0.5),
        relevant_chunks=validation_data.get("relevant_chunks", []),
        suggestions=validation_data.get("suggestions"),
        citations=validation_data.get("citations", []),
    )
```

#### B. ScenePlanner Agent

**Current Issue:** Returns generic output without routing decision

**Required Change:**
```python
# In metadata field of AgentOutput:
agent_output.metadata["scene_plan"] = ScenePlanOutput(
    next_action=str,  # "engage_npc", "narrator_scene", "disqualify"
    target=Optional[str],
    reasoning=str,
    retrieval_quality=float,
    validation_status=str,
    alternative_suggestions=Optional[List[str]],
)
```

**GameLoop Extraction:**
```python
def _extract_scene_plan(
    self,
    agent_output: AgentOutput,
    validation_result: ValidationResult
) -> ScenePlanOutput:
    """Extract ScenePlanOutput from ScenePlanner output."""
    plan_data = agent_output.metadata.get("scene_plan", {})

    # Handle dict or ScenePlanOutput object
    if isinstance(plan_data, ScenePlanOutput):
        return plan_data

    # Determine next_action based on validation if not set
    next_action = plan_data.get("next_action", "narrator_scene")
    if not validation_result.approved and next_action != "disqualify":
        next_action = "disqualify"

    return ScenePlanOutput(
        next_action=next_action,
        target=plan_data.get("target"),
        reasoning=plan_data.get("reasoning", ""),
        retrieval_quality=plan_data.get("retrieval_quality", 0.5),
        validation_status=plan_data.get("validation_status", "unknown"),
        alternative_suggestions=plan_data.get("alternative_suggestions"),
        metadata=plan_data.get("metadata", {}),
    )
```

#### C. NPCPersonaExtractor Agent

**Current Issue:** Not called on-demand; no persona caching

**Required Interface:**
```python
def extract_persona(
    self,
    npc_name: str,
    corpus_chunks: List[RetrievalResult],
) -> Dict[str, Any]:
    """
    Extract NPC persona from corpus.

    Returns:
        {
            "speaking_style": str,
            "personality_traits": List[str],
            "background": str,
            "extracted_at": str (ISO timestamp),
            "chunks_used": List[str] (chunk IDs),
        }
    """
```

**GameLoop Usage:**
```python
def _extract_persona(
    self,
    session: GameSession,
    npc_name: str,
    progress: TurnProgress,
) -> Dict[str, Any]:
    """Extract persona for NPC using NPCPersonaExtractor."""

    extractor = self.orchestrator.agents.get("npc_persona_extractor")
    if not extractor or not extractor.config.enabled:
        # Return generic persona if extractor unavailable
        return {
            "speaking_style": "conversational",
            "personality_traits": ["friendly"],
            "background": f"Character named {npc_name}",
            "extracted_at": datetime.now().isoformat(),
            "chunks_used": [],
        }

    # Retrieve chunks about this NPC
    query = f"character {npc_name} personality dialogue speaking"
    npc_chunks = self.retrieval_manager.retrieve(
        query=query,
        top_k=10,
        agent_name="npc_persona_extraction",
    )

    # Create context
    context = AgentContext(
        player_command=f"Extract persona for {npc_name}",
        session_state={
            **session.state,
            "npc_name": npc_name,
        },
        retrieval_results=npc_chunks,
        previous_turns=[],
    )

    # Execute extractor
    agent_output = extractor.process(context)
    progress.agents_completed.append("npc_persona_extractor")

    # Extract persona from metadata
    persona = agent_output.metadata.get("persona", {})
    persona["extracted_at"] = datetime.now().isoformat()
    persona["chunks_used"] = [r.chunk_id for r in npc_chunks]

    return persona
```

#### D. Narrator Agent

**Required Modes:** The Narrator must handle three distinct modes:

1. **Narration Mode** (scene description)
```python
context.session_state["mode"] = "narration"
```

2. **Disqualification Mode** (user prompt rejected)
```python
context.session_state["mode"] = "disqualification"
context.session_state["disqualification_reason"] = str
context.session_state["alternative_suggestions"] = List[str]
```

3. **Correction Mode** (agent response rejected)
```python
context.session_state["mode"] = "correction"
context.session_state["agent_response"] = str
context.session_state["disqualification_reason"] = str
```

**Narrator Implementation Pattern:**
```python
def process(self, context: AgentContext) -> AgentOutput:
    mode = context.session_state.get("mode", "narration")

    if mode == "disqualification":
        return self._generate_disqualification(context)
    elif mode == "correction":
        return self._generate_correction(context)
    else:  # "narration"
        return self._generate_scene(context)
```

---

## Session State Management

### Persona Cache

**Location:** `session.persona_cache`

**Structure:**
```python
{
    "Gandalf": {
        "speaking_style": "wise and cryptic",
        "personality_traits": ["intelligent", "mysterious", "patient"],
        "background": "Ancient wizard of great power...",
        "extracted_at": "2025-11-10T10:23:45Z",
        "chunks_used": ["chunk_42", "chunk_87", "chunk_103"],
    },
    "Frodo": {
        "speaking_style": "earnest and determined",
        "personality_traits": ["brave", "loyal", "curious"],
        "background": "Young hobbit bearing the One Ring...",
        "extracted_at": "2025-11-10T10:25:12Z",
        "chunks_used": ["chunk_15", "chunk_29"],
    },
}
```

**Lifecycle:**
- Populated on first NPC encounter per session
- Persists for duration of session
- Cleared on session end or corpus change
- Future: Persist to database keyed by corpus hash

**Invalidation:**
- When corpus changes (corpus_path or embedding model changes)
- Explicit clear via API endpoint (future)
- Session timeout

---

## Progress Tracking & UI Updates

### Phase Names for UI Display

```python
PHASE_DISPLAY_NAMES = {
    TurnPhase.STARTED: "Initializing turn",
    TurnPhase.USER_RETRIEVAL: "Retrieving context for your prompt",
    TurnPhase.USER_VALIDATION: "Validating your prompt against the world",
    TurnPhase.SCENE_PLANNING: "Planning the scene",
    TurnPhase.PERSONA_EXTRACTION: "Learning about {npc_name}",
    TurnPhase.NARRATOR_DISQUALIFY: "That doesn't fit this world...",
    TurnPhase.NARRATOR_SCENE: "Describing the scene",
    TurnPhase.NPC_RESPONSE: "Generating {npc_name}'s response",
    TurnPhase.AGENT_RETRIEVAL: "Verifying response accuracy",
    TurnPhase.AGENT_VALIDATION: "Checking response against the world",
    TurnPhase.NARRATOR_CORRECTION: "The world speaks truth",
    TurnPhase.AGGREGATING: "Finalizing response",
    TurnPhase.UPDATING_STATE: "Updating game state",
    TurnPhase.COMPLETED: "Turn complete",
    TurnPhase.ERROR: "An error occurred",
}
```

### UI Display Format

**During Turn Processing:**
```
Processing Turn 3

Phase 1: ✓ Retrieving context for your prompt
Phase 2: ✓ Validating your prompt against the world
Phase 3: ⟳ Planning the scene...
```

**After Disqualification:**
```
Turn 3 Complete - Prompt Rejected

Your prompt didn't match the world of the corpus.
Reason: No information about quantum physics in Middle-earth.

Try instead:
- Ask about magic or wizardry
- Inquire about the hobbits or the Shire
- Explore the history of Gondor
```

**After Agent Win (Player Wins):**
```
Turn 3 Complete - You Win!

The agent's response contradicted the corpus and was rejected.

Corrected response:
[Narrator provides accurate version based on corpus]
```

**After Successful Turn:**
```
Turn 3 Complete

Gandalf:
"There are older and fouler things than Orcs in the deep places of the world."

[Citations: Passages 42, 87]
```

---

## API Response Structure

### Turn Result Response

```json
{
  "turn_number": 3,
  "session_id": "abc-123",
  "player_command": "Ask Gandalf about the Balrog",

  "user_validation": {
    "approved": true,
    "reason": "Query matches corpus content",
    "confidence": 0.92,
    "relevant_chunks": ["chunk_42", "chunk_87"],
    "citations": [1, 2]
  },

  "scene_plan": {
    "next_action": "engage_npc",
    "target": "Gandalf",
    "reasoning": "Player directly addressed Gandalf",
    "retrieval_quality": 0.88,
    "validation_status": "approved"
  },

  "npc_output": {
    "content": "There are older and fouler things than Orcs...",
    "citations": [1, 2, 5],
    "reasoning": "Response grounded in Gandalf's knowledge of Moria",
    "metadata": {
      "npc_name": "Gandalf",
      "persona_cached": true
    }
  },

  "agent_validation": {
    "approved": true,
    "reason": "Response matches corpus descriptions",
    "confidence": 0.95,
    "relevant_chunks": ["chunk_42", "chunk_87", "chunk_103"]
  },

  "success": true,
  "player_wins": false,
  "player_loses": false,
  "turn_ended_early": false,

  "metadata": {
    "retrieval_calls": 2,
    "agents_executed": ["rules_referee", "scene_planner", "npc_manager"],
    "persona_extracted": false,
    "timestamp": "2025-11-10T10:25:45Z"
  },

  "duration_seconds": 3.42
}
```

---

## Testing Strategy

### Unit Tests

**1. GameLoop Phase Tests**
- Test each phase executes in correct order
- Test progress updates at each phase
- Test phase skipping (disqualification short-circuit)

**2. Validation Tests**
- Test user prompt validation (approved/rejected)
- Test agent response validation (approved/rejected)
- Test validation result extraction

**3. Scene Planning Tests**
- Test routing to narrator (scene mode)
- Test routing to NPCManager (engage_npc mode)
- Test routing to narrator (disqualify mode)

**4. Persona Cache Tests**
- Test persona extraction on first encounter
- Test persona cache hit on subsequent encounters
- Test cache invalidation

### Integration Tests

**1. Happy Path - Successful NPC Interaction**
```python
def test_successful_npc_interaction():
    # User: "Talk to Gandalf about magic"
    # Expected: Approved → engage_npc → persona extraction → NPC response → validated → success
```

**2. User Disqualification**
```python
def test_user_prompt_disqualified():
    # User: "Ask about quantum physics"
    # Expected: Rejected → disqualify → narrator disqualification → player_loses=True
```

**3. Agent Disqualification**
```python
def test_agent_response_disqualified():
    # User: Valid prompt
    # Agent: Response that contradicts corpus
    # Expected: Approved → agent executes → response rejected → correction → player_wins=True
```

**4. Scene Description**
```python
def test_scene_description():
    # User: "Look around the Shire"
    # Expected: Approved → narrator_scene → narrator executes → validated → success
```

**5. Persona Caching**
```python
def test_persona_caching():
    # Turn 1: "Talk to Gandalf" → persona extracted
    # Turn 2: "Ask Gandalf again" → persona from cache
    assert turn1_metadata["persona_extracted"] == True
    assert turn2_metadata["persona_extracted"] == False
```

---

## Migration Path

### Phase 1: Create New Structures
1. Define ValidationResult dataclass
2. Define ScenePlanOutput dataclass
3. Update TurnPhase enum
4. Update TurnResult dataclass
5. Extend GameSession with persona_cache

### Phase 2: Update GameLoop
1. Refactor `execute_turn()` with new control flow
2. Implement helper methods:
   - `_retrieve_for_user_prompt()`
   - `_validate_user_prompt()`
   - `_plan_scene()`
   - `_execute_selected_agent()`
   - `_execute_npc_manager()`
   - `_execute_narrator()`
   - `_handle_disqualification()`
   - `_handle_agent_disqualification()`
3. Add extraction helpers:
   - `_extract_validation_result()`
   - `_extract_scene_plan()`
   - `_extract_persona()`

### Phase 3: Update GameOrchestrator
1. Remove `execute_turn()` method
2. Remove `_update_session_state()` method
3. Verify agents dict remains accessible

### Phase 4: Update Tests
1. Update existing game_loop tests for new flow
2. Add new tests for validation, scene planning, persona caching
3. Update integration tests for new turn outcomes

### Phase 5: Agent Updates (Future)
1. Update RulesReferee to return ValidationResult in metadata
2. Update ScenePlanner to return ScenePlanOutput in metadata
3. Update Narrator to support three modes
4. Update NPCManager to use persona from context
5. Update NPCPersonaExtractor interface

---

## Success Criteria

### MVP Complete When:

1. **Correct Execution Order:**
   - [ ] User prompt validated BEFORE scene planning
   - [ ] Scene planning happens BEFORE agent execution
   - [ ] Only ONE agent (Narrator OR NPCManager) executes per turn
   - [ ] Agent response validated AFTER generation

2. **Proper Routing:**
   - [ ] Disqualified prompts → narrator disqualification → turn ends
   - [ ] Valid prompts with NPC → persona extraction → NPCManager
   - [ ] Valid prompts without NPC → narrator scene description
   - [ ] Disqualified agent responses → narrator correction → player wins

3. **Persona Management:**
   - [ ] Personas extracted on first NPC encounter
   - [ ] Personas cached in session
   - [ ] Cache hit rate tracked in metadata

4. **Turn Outcomes:**
   - [ ] player_wins=True when agent disqualified
   - [ ] player_loses=True when user disqualified
   - [ ] Proper win/loss counts in session state

5. **Progress Tracking:**
   - [ ] All phases logged correctly
   - [ ] UI displays current phase during turn
   - [ ] Phase-specific messages shown

6. **Testing:**
   - [ ] All unit tests passing
   - [ ] All integration tests passing
   - [ ] Happy path works end-to-end
   - [ ] Edge cases handled gracefully

---

## Notes for Implementation

**Do NOT modify agents in this iteration:**
- Focus on GameLoop and orchestration logic only
- Agents will be updated in future iteration to return proper structures
- For now, use extraction helpers to parse current agent outputs

**Backward Compatibility:**
- Maintain existing API endpoints
- Extend TurnResult without breaking existing fields
- Add new fields as optional

**Error Handling:**
- Fail-open for validation (approve on error)
- Fallback to narrator if routing fails
- Log all errors but continue turn when possible

**Performance:**
- Persona cache reduces repeated extractions
- Validation adds ~1-2s per turn (acceptable)
- Progress tracking has minimal overhead

---

## End of Design Document

**Approval Required Before Implementation**

This design document specifies the complete restructuring of the GameLoop orchestration to match the required control flow. Upon approval, implementation will proceed in the phases outlined in the Migration Path section.
