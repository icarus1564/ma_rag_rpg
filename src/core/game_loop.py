"""Game loop orchestrating agent execution with comprehensive logging and progress tracking."""

import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, RetrievalResult
from .session import GameSession, Turn
from .orchestrator import GameOrchestrator
from .retrieval_manager import RetrievalManager
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)

# Import status recording function
try:
    from ..api.endpoints import status as status_module
except ImportError:
    status_module = None


class TurnPhase(str, Enum):
    """Phases of a game turn for progress tracking."""
    STARTED = "started"
    USER_RETRIEVAL = "user_retrieval"
    USER_VALIDATION = "user_validation"
    SCENE_PLANNING = "scene_planning"
    PERSONA_EXTRACTION = "persona_extraction"
    NARRATOR_DISQUALIFY = "narrator_disqualify"
    NARRATOR_SCENE = "narrator_scene"
    NPC_RESPONSE = "npc_response"
    AGENT_RETRIEVAL = "agent_retrieval"
    AGENT_VALIDATION = "agent_validation"
    NARRATOR_CORRECTION = "narrator_correction"
    AGGREGATING = "aggregating"
    UPDATING_STATE = "updating_state"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result from RulesReferee validation."""
    approved: bool
    reason: str
    confidence: float  # 0.0 to 1.0
    relevant_chunks: List[str]  # Chunk IDs used for validation
    suggestions: Optional[List[str]] = None  # Alternative approaches if rejected
    citations: List[int] = field(default_factory=list)  # Citation indices


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


@dataclass
class TurnProgress:
    """Progress information for a game turn."""
    turn_number: int
    session_id: str
    phase: TurnPhase
    current_agent: Optional[str] = None
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    retrieval_calls: int = 0
    agents_completed: List[str] = field(default_factory=list)
    agents_failed: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary."""
        return {
            "turn_number": self.turn_number,
            "session_id": self.session_id,
            "phase": self.phase.value,
            "current_agent": self.current_agent,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "retrieval_calls": self.retrieval_calls,
            "agents_completed": self.agents_completed,
            "agents_failed": self.agents_failed,
            "error": self.error,
        }


@dataclass
class TurnResult:
    """Result of a game turn."""
    turn_number: int
    session_id: str
    player_command: str

    # Validation results
    user_validation: Optional[ValidationResult] = None
    agent_validation: Optional[ValidationResult] = None

    # Scene planning
    scene_plan: Optional[ScenePlanOutput] = None

    # Agent outputs (only ONE will be populated per turn)
    narrator_output: Optional[Dict[str, Any]] = None
    npc_output: Optional[Dict[str, Any]] = None

    # Legacy fields for backward compatibility
    scene_planner_output: Optional[Dict[str, Any]] = None
    rules_validation: Optional[Dict[str, Any]] = None

    # Turn outcome
    success: bool = True
    player_wins: bool = False  # True if agent response was disqualified
    player_loses: bool = False  # True if user prompt was disqualified
    turn_ended_early: bool = False  # True if turn ended at validation

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert turn result to dictionary."""
        result = {
            "turn_number": self.turn_number,
            "session_id": self.session_id,
            "player_command": self.player_command,
            "narrator_output": self.narrator_output,
            "npc_output": self.npc_output,
            "scene_planner_output": self.scene_planner_output,
            "rules_validation": self.rules_validation,
            "success": self.success,
            "player_wins": self.player_wins,
            "player_loses": self.player_loses,
            "turn_ended_early": self.turn_ended_early,
            "metadata": self.metadata,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }

        # Add validation results if present
        if self.user_validation:
            result["user_validation"] = {
                "approved": self.user_validation.approved,
                "reason": self.user_validation.reason,
                "confidence": self.user_validation.confidence,
                "relevant_chunks": self.user_validation.relevant_chunks,
                "suggestions": self.user_validation.suggestions,
                "citations": self.user_validation.citations,
            }

        if self.agent_validation:
            result["agent_validation"] = {
                "approved": self.agent_validation.approved,
                "reason": self.agent_validation.reason,
                "confidence": self.agent_validation.confidence,
                "relevant_chunks": self.agent_validation.relevant_chunks,
                "suggestions": self.agent_validation.suggestions,
                "citations": self.agent_validation.citations,
            }

        # Add scene plan if present
        if self.scene_plan:
            result["scene_plan"] = {
                "next_action": self.scene_plan.next_action,
                "target": self.scene_plan.target,
                "reasoning": self.scene_plan.reasoning,
                "retrieval_quality": self.scene_plan.retrieval_quality,
                "validation_status": self.scene_plan.validation_status,
                "alternative_suggestions": self.scene_plan.alternative_suggestions,
                "metadata": self.scene_plan.metadata,
            }

        return result


class GameLoop:
    """Orchestrates the game loop with comprehensive logging and progress tracking."""

    def __init__(
        self,
        orchestrator: GameOrchestrator,
        retrieval_manager: RetrievalManager,
        progress_callback: Optional[Callable[[TurnProgress], None]] = None,
    ):
        """
        Initialize game loop.

        Args:
            orchestrator: Game orchestrator for agent execution
            retrieval_manager: Retrieval manager for RAG operations
            progress_callback: Optional callback for progress updates
        """
        self.orchestrator = orchestrator
        self.retrieval_manager = retrieval_manager
        self.progress_callback = progress_callback
        self.logger = get_logger(__name__)

        # Track progress per session
        self._progress: Dict[str, TurnProgress] = {}

    @debug_log_method
    def execute_turn(
        self,
        session: GameSession,
        player_command: str,
        initial_context: Optional[str] = None,
    ) -> TurnResult:
        """
        Execute a complete game turn with correct orchestration flow.

        Args:
            session: Current game session
            player_command: Player's command/action
            initial_context: Optional initial context for first turn

        Returns:
            TurnResult with all agent outputs and metadata
        """
        start_time = time.time()
        turn_number = len(session.turns) + 1

        # Phase 1: Initialize progress tracking
        progress = TurnProgress(
            turn_number=turn_number,
            session_id=session.session_id,
            phase=TurnPhase.STARTED,
            message=f"Starting turn {turn_number}",
        )
        self._update_progress(progress)

        self.logger.info(
            "Game loop started",
            session_id=session.session_id,
            turn_number=turn_number,
            player_command=player_command[:100],
        )

        try:
            # Store initial context if provided (for first turn)
            if initial_context and len(session.turns) == 0:
                session.state["initial_context"] = initial_context

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
                result = self._handle_disqualification(
                    session, turn_number, player_command, scene_plan, user_validation, progress
                )
                result.duration_seconds = time.time() - start_time
                self._add_turn_to_session(session, turn_number, player_command, result)
                return result

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
                result = self._handle_agent_disqualification(
                    session, turn_number, player_command, agent_output,
                    agent_validation, user_validation, scene_plan, progress
                )
                result.duration_seconds = time.time() - start_time
                self._add_turn_to_session(session, turn_number, player_command, result)
                return result

            # Phase 9: Update state and return success
            result = self._finalize_turn(
                session, turn_number, player_command, agent_output, agent_name,
                user_validation, agent_validation, scene_plan, progress
            )

            result.duration_seconds = time.time() - start_time
            self._add_turn_to_session(session, turn_number, player_command, result)

            progress.phase = TurnPhase.COMPLETED
            progress.message = f"Turn {turn_number} completed successfully"
            self._update_progress(progress)

            self.logger.info(
                "Game loop completed",
                session_id=session.session_id,
                turn_number=turn_number,
                duration_seconds=result.duration_seconds,
                agents_completed=progress.agents_completed,
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            progress.phase = TurnPhase.ERROR
            progress.error = error_msg
            progress.message = f"Error during turn {turn_number}: {error_msg}"
            self._update_progress(progress)

            self.logger.error(
                "Game loop failed",
                session_id=session.session_id,
                turn_number=turn_number,
                error=error_msg,
                duration_seconds=duration,
                exc_info=True,
            )

            return TurnResult(
                turn_number=turn_number,
                session_id=session.session_id,
                player_command=player_command,
                duration_seconds=duration,
                success=False,
                error=error_msg,
            )

    @debug_log_method
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
        self.logger.debug(
            "User prompt retrieval completed",
            session_id=session.session_id,
            num_results=len(results),
        )

        return results

    @debug_log_method
    def _build_retrieval_query(
        self,
        session: GameSession,
        player_command: str,
    ) -> str:
        """Build retrieval query from player command and context."""
        query_parts = [player_command]

        # Add current scene context
        if session.state.get("current_scene"):
            query_parts.append(f"Scene: {session.state['current_scene']}")

        # Add recent context from memory
        if session.state.get("memory"):
            recent_memory = session.state["memory"][-2:]  # Last 2 turns
            for mem in recent_memory:
                query_parts.append(mem.get("player_command", ""))

        return " ".join(query_parts)

    @debug_log_method
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
        from .base_agent import AgentContext

        context = AgentContext(
            player_command=player_command,
            session_state={"validation_mode": "user_prompt"},
            retrieval_results=retrieval_results,
            previous_turns=[],
        )

        # Execute RulesReferee
        try:
            agent_start = time.time()
            agent_output = referee.process(context)
            agent_duration = time.time() - agent_start
            progress.agents_completed.append("rules_referee")

            # Record successful agent call
            if status_module:
                status_module.record_agent_call("rules_referee", True, agent_duration)

            # Extract ValidationResult from agent output
            return self._extract_validation_result(agent_output)

        except Exception as e:
            agent_duration = time.time() - agent_start if 'agent_start' in locals() else 0.0
            self.logger.error("User prompt validation failed", error=str(e))
            progress.agents_failed.append("rules_referee")

            # Record failed agent call
            if status_module:
                status_module.record_agent_call("rules_referee", False, agent_duration, str(e))

            # Default to approved on error (fail-open)
            return ValidationResult(
                approved=True,
                reason=f"Validation error: {str(e)}",
                confidence=0.0,
                relevant_chunks=[],
            )

    @debug_log_method
    def _extract_validation_result(self, agent_output) -> ValidationResult:
        """Extract ValidationResult from RulesReferee output."""
        validation_data = agent_output.metadata.get("validation_result", {})

        # Handle dict or ValidationResult object
        if isinstance(validation_data, ValidationResult):
            return validation_data

        # Extract from dict
        return ValidationResult(
            approved=validation_data.get("approved", True),
            reason=validation_data.get("reason", agent_output.content or ""),
            confidence=validation_data.get("confidence", 0.5),
            relevant_chunks=validation_data.get("relevant_chunks", []),
            suggestions=validation_data.get("suggestions"),
            citations=validation_data.get("citations", []),
        )

    @debug_log_method
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
        from .base_agent import AgentContext

        context = AgentContext(
            player_command=player_command,
            session_state={
                **session.state,
                "validation_result": {
                    "approved": validation_result.approved,
                    "reason": validation_result.reason,
                    "confidence": validation_result.confidence,
                },
            },
            retrieval_results=retrieval_results,
            previous_turns=session.state.get("memory", []),
        )

        # Execute ScenePlanner
        try:
            agent_start = time.time()
            agent_output = planner.process(context)
            agent_duration = time.time() - agent_start
            progress.agents_completed.append("scene_planner")

            # Record successful agent call
            if status_module:
                status_module.record_agent_call("scene_planner", True, agent_duration)

            # Extract ScenePlanOutput from agent output
            return self._extract_scene_plan(agent_output, validation_result)

        except Exception as e:
            agent_duration = time.time() - agent_start if 'agent_start' in locals() else 0.0
            self.logger.error("Scene planning failed", error=str(e))
            progress.agents_failed.append("scene_planner")

            # Record failed agent call
            if status_module:
                status_module.record_agent_call("scene_planner", False, agent_duration, str(e))

            # Fallback to narrator
            return ScenePlanOutput(
                next_action="narrator_scene",
                target=None,
                reasoning=f"Scene planning error: {str(e)}",
                retrieval_quality=0.0,
                validation_status="error",
            )

    @debug_log_method
    def _extract_scene_plan(
        self,
        agent_output,
        validation_result: ValidationResult,
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
            reasoning=plan_data.get("reasoning", agent_output.content or ""),
            retrieval_quality=plan_data.get("retrieval_quality", 0.5),
            validation_status=plan_data.get("validation_status", "unknown"),
            alternative_suggestions=plan_data.get("alternative_suggestions"),
            metadata=plan_data.get("metadata", {}),
        )

    @debug_log_method
    def _execute_selected_agent(
        self,
        session: GameSession,
        player_command: str,
        retrieval_results: List[RetrievalResult],
        scene_plan: ScenePlanOutput,
        progress: TurnProgress,
    ) -> tuple[Dict[str, Any], str]:
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

    @debug_log_method
    def _execute_npc_manager(
        self,
        session: GameSession,
        player_command: str,
        retrieval_results: List[RetrievalResult],
        scene_plan: ScenePlanOutput,
        progress: TurnProgress,
    ) -> tuple[Dict[str, Any], str]:
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
        from .base_agent import AgentContext

        context = AgentContext(
            player_command=player_command,
            session_state={
                **session.state,
                "npc_name": npc_name,
                "npc_persona": persona,
            },
            retrieval_results=retrieval_results,
            previous_turns=session.state.get("memory", []),
        )

        # Execute
        agent_start = time.time()
        agent_output = npc_manager.process(context)
        agent_duration = time.time() - agent_start
        progress.agents_completed.append("npc_manager")

        # Record successful agent call
        if status_module:
            status_module.record_agent_call("npc_manager", True, agent_duration)

        return (
            {
                "content": agent_output.content,
                "citations": agent_output.citations,
                "reasoning": agent_output.reasoning,
                "metadata": {**agent_output.metadata, "npc_name": npc_name},
            },
            npc_name,  # Return NPC name as agent identifier
        )

    @debug_log_method
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
        from .base_agent import AgentContext

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
        agent_start = time.time()
        agent_output = extractor.process(context)
        agent_duration = time.time() - agent_start
        progress.agents_completed.append("npc_persona_extractor")

        # Record successful agent call
        if status_module:
            status_module.record_agent_call("npc_persona_extractor", True, agent_duration)

        # Extract persona from metadata
        persona = agent_output.metadata.get("persona", {})
        persona["extracted_at"] = datetime.now().isoformat()
        persona["chunks_used"] = [r.chunk_id for r in npc_chunks]

        return persona

    @debug_log_method
    def _execute_narrator(
        self,
        session: GameSession,
        player_command: str,
        retrieval_results: List[RetrievalResult],
        scene_plan: ScenePlanOutput,
        progress: TurnProgress,
    ) -> tuple[Dict[str, Any], str]:
        """Execute Narrator for scene description."""
        progress.phase = TurnPhase.NARRATOR_SCENE
        progress.current_agent = "narrator"
        progress.message = "Generating scene narration"
        self._update_progress(progress)

        narrator = self.orchestrator.agents.get("narrator")
        if not narrator or not narrator.config.enabled:
            raise ValueError("Narrator not available")

        # Create context
        from .base_agent import AgentContext

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
        agent_start = time.time()
        agent_output = narrator.process(context)
        agent_duration = time.time() - agent_start
        progress.agents_completed.append("narrator")

        # Record successful agent call
        if status_module:
            status_module.record_agent_call("narrator", True, agent_duration)

        return (
            {
                "content": agent_output.content,
                "citations": agent_output.citations,
                "reasoning": agent_output.reasoning,
                "metadata": agent_output.metadata,
            },
            "Narrator",
        )

    @debug_log_method
    def _retrieve_for_agent_response(
        self,
        session: GameSession,
        agent_output: Dict[str, Any],
        progress: TurnProgress,
    ) -> List[RetrievalResult]:
        """Retrieve corpus context for agent response validation."""
        progress.phase = TurnPhase.AGENT_RETRIEVAL
        progress.message = "Retrieving context for agent response validation"
        self._update_progress(progress)

        # Use agent response as query
        query = agent_output["content"]

        # Retrieve chunks
        results = self.retrieval_manager.retrieve(
            query=query,
            top_k=10,
            agent_name="agent_response_validation",
        )

        progress.retrieval_calls += 1
        self.logger.debug(
            "Agent response retrieval completed",
            session_id=session.session_id,
            num_results=len(results),
        )

        return results

    @debug_log_method
    def _validate_agent_response(
        self,
        agent_output: Dict[str, Any],
        retrieval_results: List[RetrievalResult],
        progress: TurnProgress,
    ) -> ValidationResult:
        """Validate agent response against corpus using RulesReferee."""
        progress.phase = TurnPhase.AGENT_VALIDATION
        progress.current_agent = "rules_referee"
        progress.message = "Validating agent response against corpus"
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
        from .base_agent import AgentContext

        context = AgentContext(
            player_command=agent_output["content"],
            session_state={"validation_mode": "agent_response"},
            retrieval_results=retrieval_results,
            previous_turns=[],
        )

        # Execute RulesReferee
        try:
            agent_start = time.time()
            referee_output = referee.process(context)
            agent_duration = time.time() - agent_start

            # Record successful agent call
            if status_module:
                status_module.record_agent_call("rules_referee", True, agent_duration)

            # Extract ValidationResult
            return self._extract_validation_result(referee_output)

        except Exception as e:
            agent_duration = time.time() - agent_start if 'agent_start' in locals() else 0.0
            self.logger.error("Agent response validation failed", error=str(e))

            # Record failed agent call
            if status_module:
                status_module.record_agent_call("rules_referee", False, agent_duration, str(e))

            # Default to approved on error (fail-open)
            return ValidationResult(
                approved=True,
                reason=f"Validation error: {str(e)}",
                confidence=0.0,
                relevant_chunks=[],
            )

    @debug_log_method
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
            from .base_agent import AgentContext

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
            agent_start = time.time()
            agent_output = narrator.process(context)
            agent_duration = time.time() - agent_start

            # Record successful agent call
            if status_module:
                status_module.record_agent_call("narrator", True, agent_duration)

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
                "retrieval": {},
                "agents_executed": progress.agents_completed,
                "timestamp": datetime.now().isoformat(),
            },
        )

    @debug_log_method
    def _handle_agent_disqualification(
        self,
        session: GameSession,
        turn_number: int,
        player_command: str,
        agent_output: Dict[str, Any],
        validation_result: ValidationResult,
        user_validation: ValidationResult,
        scene_plan: ScenePlanOutput,
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
            from .base_agent import AgentContext

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
            agent_start = time.time()
            narrator_output = narrator.process(context)
            agent_duration = time.time() - agent_start

            # Record successful agent call
            if status_module:
                status_module.record_agent_call("narrator", True, agent_duration)

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
            user_validation=user_validation,
            agent_validation=validation_result,
            scene_plan=scene_plan,
            narrator_output=correction_msg,
            success=True,
            player_wins=True,
            metadata={
                "original_agent_response": agent_output["content"],
                "disqualification_reason": validation_result.reason,
                "retrieval": {},
                "agents_executed": progress.agents_completed,
                "timestamp": datetime.now().isoformat(),
            },
        )

    @debug_log_method
    def _finalize_turn(
        self,
        session: GameSession,
        turn_number: int,
        player_command: str,
        agent_output: Dict[str, Any],
        agent_name: str,
        user_validation: ValidationResult,
        agent_validation: ValidationResult,
        scene_plan: ScenePlanOutput,
        progress: TurnProgress,
    ) -> TurnResult:
        """Finalize successful turn and return result."""
        progress.phase = TurnPhase.UPDATING_STATE
        progress.message = "Updating session state"
        self._update_progress(progress)

        # Update session state based on scene plan
        if scene_plan.target and scene_plan.target not in session.state["active_npcs"]:
            session.state["active_npcs"].append(scene_plan.target)

        # Store last validation
        session.state["last_validation"] = {
            "user_approved": user_validation.approved,
            "agent_approved": agent_validation.approved,
        }

        # Prepare result based on agent type
        if agent_name == "Narrator":
            narrator_output = agent_output
            npc_output = None
        else:
            narrator_output = None
            npc_output = agent_output

        return TurnResult(
            turn_number=turn_number,
            session_id=session.session_id,
            player_command=player_command,
            user_validation=user_validation,
            agent_validation=agent_validation,
            scene_plan=scene_plan,
            narrator_output=narrator_output,
            npc_output=npc_output,
            success=True,
            metadata={
                "retrieval_calls": progress.retrieval_calls,
                "agents_executed": progress.agents_completed,
                "persona_extracted": agent_name != "Narrator" and scene_plan.target not in session.persona_cache,
                "timestamp": datetime.now().isoformat(),
            },
        )

    @debug_log_method
    def _add_turn_to_session(
        self,
        session: GameSession,
        turn_number: int,
        player_command: str,
        result: TurnResult,
    ) -> None:
        """Add turn to session history."""
        # Build agent_outputs dict for backward compatibility
        agent_outputs = {}
        if result.narrator_output:
            agent_outputs["narrator"] = result.narrator_output
        if result.npc_output:
            agent_outputs["npc_manager"] = result.npc_output

        turn = Turn(
            turn_number=turn_number,
            player_command=player_command,
            agent_outputs=agent_outputs,
        )
        session.add_turn(turn)

    def _update_progress(self, progress: TurnProgress) -> None:
        """Update progress and notify callback."""
        # Store progress
        self._progress[progress.session_id] = progress

        # Log progress
        self.logger.debug(
            "Turn progress",
            session_id=progress.session_id,
            turn_number=progress.turn_number,
            phase=progress.phase.value,
            message=progress.message,
        )

        # Notify callback if provided
        if self.progress_callback:
            try:
                self.progress_callback(progress)
            except Exception as e:
                self.logger.error(
                    "Progress callback failed",
                    error=str(e),
                    exc_info=True,
                )

    def get_progress(self, session_id: str) -> Optional[TurnProgress]:
        """
        Get current progress for a session.

        Args:
            session_id: Session identifier

        Returns:
            TurnProgress if available, None otherwise
        """
        return self._progress.get(session_id)
