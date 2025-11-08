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

logger = get_logger(__name__)


class TurnPhase(str, Enum):
    """Phases of a game turn for progress tracking."""
    STARTED = "started"
    RETRIEVAL = "retrieval"
    NARRATOR = "narrator"
    SCENE_PLANNER = "scene_planner"
    NPC_MANAGER = "npc_manager"
    RULES_REFEREE = "rules_referee"
    AGGREGATING = "aggregating"
    UPDATING_STATE = "updating_state"
    COMPLETED = "completed"
    ERROR = "error"


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
    narrator_output: Optional[Dict[str, Any]] = None
    scene_planner_output: Optional[Dict[str, Any]] = None
    npc_output: Optional[Dict[str, Any]] = None
    rules_validation: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert turn result to dictionary."""
        return {
            "turn_number": self.turn_number,
            "session_id": self.session_id,
            "player_command": self.player_command,
            "narrator_output": self.narrator_output,
            "scene_planner_output": self.scene_planner_output,
            "npc_output": self.npc_output,
            "rules_validation": self.rules_validation,
            "metadata": self.metadata,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error": self.error,
        }


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

    def execute_turn(
        self,
        session: GameSession,
        player_command: str,
        initial_context: Optional[str] = None,
    ) -> TurnResult:
        """
        Execute a complete game turn with all agents.

        Args:
            session: Current game session
            player_command: Player's command/action
            initial_context: Optional initial context for first turn

        Returns:
            TurnResult with all agent outputs and metadata
        """
        start_time = time.time()
        turn_number = len(session.turns) + 1

        # Initialize progress tracking
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
            player_command=player_command[:100],  # Truncate for logging
        )

        try:
            # Phase 1: Retrieval
            progress.phase = TurnPhase.RETRIEVAL
            progress.message = "Retrieving relevant context from corpus"
            self._update_progress(progress)

            retrieval_results = self._perform_retrieval(
                session, player_command, progress
            )

            # Phase 2: Execute agents through orchestrator
            agent_outputs = self._execute_agents(
                session, player_command, retrieval_results, initial_context, progress
            )

            # Phase 3: Aggregate outputs
            progress.phase = TurnPhase.AGGREGATING
            progress.message = "Aggregating agent outputs"
            self._update_progress(progress)

            turn_result = self._aggregate_outputs(
                session_id=session.session_id,
                turn_number=turn_number,
                player_command=player_command,
                agent_outputs=agent_outputs,
                retrieval_results=retrieval_results,
            )

            # Phase 4: Update session state
            progress.phase = TurnPhase.UPDATING_STATE
            progress.message = "Updating session state"
            self._update_progress(progress)

            # Create turn and add to session
            turn = Turn(
                turn_number=turn_number,
                player_command=player_command,
                agent_outputs=agent_outputs,
            )
            session.add_turn(turn)

            # Complete
            duration = time.time() - start_time
            turn_result.duration_seconds = duration

            progress.phase = TurnPhase.COMPLETED
            progress.message = f"Turn {turn_number} completed successfully"
            self._update_progress(progress)

            self.logger.info(
                "Game loop completed",
                session_id=session.session_id,
                turn_number=turn_number,
                duration_seconds=duration,
                agents_completed=progress.agents_completed,
            )

            return turn_result

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

    def _perform_retrieval(
        self,
        session: GameSession,
        player_command: str,
        progress: TurnProgress,
    ) -> List[RetrievalResult]:
        """
        Perform retrieval for the turn.

        Args:
            session: Current game session
            player_command: Player's command
            progress: Progress tracker

        Returns:
            List of retrieval results
        """
        # Build retrieval query from player command and context
        query_parts = [player_command]

        # Add current scene context
        if session.state.get("current_scene"):
            query_parts.append(f"Scene: {session.state['current_scene']}")

        # Add recent context from memory
        if session.state.get("memory"):
            recent_memory = session.state["memory"][-2:]  # Last 2 turns
            for mem in recent_memory:
                query_parts.append(mem.get("player_command", ""))

        query = " ".join(query_parts)

        self.logger.debug(
            "Performing retrieval",
            session_id=session.session_id,
            query_length=len(query),
        )

        # Retrieve chunks
        results = self.retrieval_manager.retrieve(
            query=query,
            top_k=10,
            agent_name="game_loop",
        )

        progress.retrieval_calls += 1

        self.logger.debug(
            "Retrieval completed",
            session_id=session.session_id,
            num_results=len(results),
        )

        return results

    def _execute_agents(
        self,
        session: GameSession,
        player_command: str,
        retrieval_results: List[RetrievalResult],
        initial_context: Optional[str],
        progress: TurnProgress,
    ) -> Dict[str, Any]:
        """
        Execute all agents through the orchestrator.

        Args:
            session: Current game session
            player_command: Player's command
            retrieval_results: Retrieved chunks
            initial_context: Optional initial context
            progress: Progress tracker

        Returns:
            Dictionary of agent outputs
        """
        # Track agent execution
        agent_order = ["narrator", "scene_planner", "npc_manager", "rules_referee"]

        # Build agent context
        context = AgentContext(
            player_command=player_command,
            session_state=session.state,
            retrieval_results=retrieval_results,
            previous_turns=session.state.get("memory", []),
        )

        if initial_context and len(session.turns) == 0:
            context.session_state["initial_context"] = initial_context

        outputs = {}

        # Execute each agent with progress tracking
        for agent_name in agent_order:
            if agent_name not in self.orchestrator.agents:
                continue

            agent = self.orchestrator.agents[agent_name]

            if not agent.config.enabled:
                self.logger.debug(
                    "Agent disabled, skipping",
                    agent_name=agent_name,
                    session_id=session.session_id,
                )
                continue

            # Update progress
            phase_map = {
                "narrator": TurnPhase.NARRATOR,
                "scene_planner": TurnPhase.SCENE_PLANNER,
                "npc_manager": TurnPhase.NPC_MANAGER,
                "rules_referee": TurnPhase.RULES_REFEREE,
            }
            progress.phase = phase_map.get(agent_name, TurnPhase.STARTED)
            progress.current_agent = agent_name
            progress.message = f"Executing {agent_name}"
            self._update_progress(progress)

            try:
                self.logger.debug(
                    "Executing agent",
                    agent_name=agent_name,
                    session_id=session.session_id,
                )

                agent_start = time.time()
                agent_output = agent.process(context)
                agent_duration = time.time() - agent_start

                # Update context with this agent's output for next agents
                context.session_state[f"{agent_name}_output"] = agent_output.content

                outputs[agent_name] = {
                    "content": agent_output.content,
                    "citations": agent_output.citations,
                    "reasoning": agent_output.reasoning,
                    "metadata": agent_output.metadata,
                    "execution_time": agent_duration,
                }

                progress.agents_completed.append(agent_name)

                self.logger.debug(
                    "Agent completed",
                    agent_name=agent_name,
                    session_id=session.session_id,
                    duration_seconds=agent_duration,
                )

            except Exception as e:
                error_msg = str(e)
                progress.agents_failed.append(agent_name)

                self.logger.error(
                    "Agent failed",
                    agent_name=agent_name,
                    session_id=session.session_id,
                    error=error_msg,
                    exc_info=True,
                )

                outputs[agent_name] = {
                    "content": f"Error: {error_msg}",
                    "citations": [],
                    "error": True,
                    "error_message": error_msg,
                }

        # Update session state based on agent outputs
        self._update_session_state_from_outputs(session, outputs)

        return outputs

    def _update_session_state_from_outputs(
        self,
        session: GameSession,
        outputs: Dict[str, Any],
    ) -> None:
        """Update session state based on agent outputs."""
        # Update current scene from scene_planner
        if "scene_planner" in outputs:
            scene_plan = outputs["scene_planner"].get("metadata", {}).get("scene_plan")
            if scene_plan:
                if scene_plan.get("next_scene"):
                    session.state["current_scene"] = scene_plan["next_scene"]

                responding_npc = scene_plan.get("responding_npc")
                if responding_npc and responding_npc not in session.state["active_npcs"]:
                    session.state["active_npcs"].append(responding_npc)

        # Update from narrator if scene_planner didn't set it
        elif "narrator" in outputs:
            narrator_metadata = outputs["narrator"].get("metadata", {})
            if "scene" in narrator_metadata:
                session.state["current_scene"] = narrator_metadata["scene"]

        # Store rules validation result
        if "rules_referee" in outputs:
            validation = outputs["rules_referee"].get("metadata", {}).get("validation_result")
            session.state["last_validation"] = validation

    def _aggregate_outputs(
        self,
        session_id: str,
        turn_number: int,
        player_command: str,
        agent_outputs: Dict[str, Any],
        retrieval_results: List[RetrievalResult],
    ) -> TurnResult:
        """
        Aggregate agent outputs into a turn result.

        Args:
            session_id: Session identifier
            turn_number: Turn number
            player_command: Player's command
            agent_outputs: Dictionary of agent outputs
            retrieval_results: Retrieved chunks

        Returns:
            TurnResult with aggregated outputs
        """
        metadata = {
            "retrieval": {
                "num_chunks": len(retrieval_results),
                "chunks": [
                    {
                        "chunk_id": r.chunk_id,
                        "score": r.score,
                        "text": r.chunk_text[:200],  # Truncate for metadata
                    }
                    for r in retrieval_results[:5]  # Top 5
                ],
            },
            "agents_executed": list(agent_outputs.keys()),
            "timestamp": datetime.now().isoformat(),
        }

        return TurnResult(
            turn_number=turn_number,
            session_id=session_id,
            player_command=player_command,
            narrator_output=agent_outputs.get("narrator"),
            scene_planner_output=agent_outputs.get("scene_planner"),
            npc_output=agent_outputs.get("npc_manager"),
            rules_validation=agent_outputs.get("rules_referee"),
            metadata=metadata,
            success=True,
        )

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
