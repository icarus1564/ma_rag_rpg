"""Game API endpoints for player interactions."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from ..schemas.game_schemas import (
    NewGameRequest,
    NewGameResponse,
    TurnRequest,
    TurnResponse,
    GameStateResponse,
    AgentOutput,
    TurnMetadata,
)
from src.core.session_manager import SessionManager
from src.core.game_loop import GameLoop, TurnProgress
from src.utils.logging import get_logger
from . import status

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["game"])

# Global state (will be initialized in app startup)
_session_manager: SessionManager = None
_game_loop: GameLoop = None
_turn_progress: Dict[str, TurnProgress] = {}


def set_game_dependencies(session_manager: SessionManager, game_loop: GameLoop):
    """Set dependencies for game endpoints."""
    global _session_manager, _game_loop
    _session_manager = session_manager
    _game_loop = game_loop


def progress_callback(progress: TurnProgress):
    """Callback to track turn progress."""
    _turn_progress[progress.session_id] = progress


@router.post("/new_game", response_model=NewGameResponse)
async def new_game(request: NewGameRequest):
    """
    Create a new game session.

    Args:
        request: New game request with optional initial context

    Returns:
        NewGameResponse with session ID and initial information
    """
    if _session_manager is None:
        raise HTTPException(status_code=500, detail="Game system not initialized")

    logger.info("Creating new game session", initial_context_provided=request.initial_context is not None)

    try:
        # Create new session
        session = _session_manager.create_session(initial_context=request.initial_context)

        logger.info("Game session created", session_id=session.session_id)

        return NewGameResponse(
            session_id=session.session_id,
            message="Welcome to the Multi-Agent RAG RPG! Your adventure begins...",
            initial_scene=request.initial_context,
            created_at=session.created_at.isoformat(),
        )

    except Exception as e:
        logger.error("Failed to create game session", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create game session: {str(e)}")


@router.post("/turn", response_model=TurnResponse)
async def process_turn(request: TurnRequest):
    """
    Process a player turn through the game loop.

    Args:
        request: Turn request with session ID and player command

    Returns:
        TurnResponse with all agent outputs
    """
    if _session_manager is None or _game_loop is None:
        raise HTTPException(status_code=500, detail="Game system not initialized")

    logger.info(
        "Processing turn",
        session_id=request.session_id,
        command_length=len(request.player_command)
    )

    # Get session
    session = _session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found or expired"
        )

    try:
        # Get initial context for first turn
        initial_context = None
        if len(session.turns) == 0:
            initial_context = session.state.get("initial_context")

        # Execute turn through game loop
        result = _game_loop.execute_turn(
            session=session,
            player_command=request.player_command,
            initial_context=initial_context,
        )

        # Convert to response schema
        response = TurnResponse(
            turn_number=result.turn_number,
            session_id=result.session_id,
            player_command=result.player_command,
            narrator_output=_convert_agent_output(result.narrator_output),
            scene_planner_output=_convert_agent_output(result.scene_planner_output),
            npc_output=_convert_agent_output(result.npc_output),
            rules_validation=_convert_agent_output(result.rules_validation),
            metadata=TurnMetadata(**result.metadata),
            duration_seconds=result.duration_seconds,
            success=result.success,
            error=result.error,
        )

        # Increment turn counter
        status.increment_turn_count()

        logger.info(
            "Turn processed successfully",
            session_id=request.session_id,
            turn_number=result.turn_number,
            duration_seconds=result.duration_seconds,
        )

        return response

    except Exception as e:
        logger.error(
            "Failed to process turn",
            session_id=request.session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process turn: {str(e)}"
        )


@router.get("/state/{session_id}", response_model=GameStateResponse)
async def get_game_state(session_id: str):
    """
    Get current game state for a session.

    Args:
        session_id: Session identifier

    Returns:
        GameStateResponse with current state
    """
    if _session_manager is None:
        raise HTTPException(status_code=500, detail="Game system not initialized")

    logger.debug("Getting game state", session_id=session_id)

    session = _session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found or expired"
        )

    try:
        session_dict = session.to_dict()

        return GameStateResponse(
            session_id=session.session_id,
            turn_count=len(session.turns),
            current_scene=session.state.get("current_scene"),
            active_npcs=session.state.get("active_npcs", []),
            memory_size=len(session.state.get("memory", [])),
            created_at=session.created_at.isoformat(),
            last_accessed=session.last_accessed.isoformat(),
            state=session.state,
        )

    except Exception as e:
        logger.error(
            "Failed to get game state",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get game state: {str(e)}"
        )


@router.get("/progress/{session_id}")
async def get_turn_progress(session_id: str):
    """
    Get current turn progress for a session.

    Args:
        session_id: Session identifier

    Returns:
        Current turn progress information
    """
    if _game_loop is None:
        raise HTTPException(status_code=500, detail="Game system not initialized")

    progress = _game_loop.get_progress(session_id)

    if progress is None:
        # Check if session exists
        if _session_manager.get_session(session_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        # Session exists but no progress yet
        return {
            "session_id": session_id,
            "message": "No turn in progress",
            "phase": "idle"
        }

    return progress.to_dict()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a game session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    if _session_manager is None:
        raise HTTPException(status_code=500, detail="Game system not initialized")

    logger.info("Deleting session", session_id=session_id)

    deleted = _session_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    # Clean up progress tracking
    if session_id in _turn_progress:
        del _turn_progress[session_id]

    return {
        "message": f"Session {session_id} deleted successfully",
        "session_id": session_id
    }


def _convert_agent_output(output: Dict[str, Any] | None) -> AgentOutput | None:
    """Convert agent output dict to schema."""
    if output is None:
        return None

    return AgentOutput(
        content=output.get("content", ""),
        citations=output.get("citations", []),
        reasoning=output.get("reasoning"),
        metadata=output.get("metadata", {}),
        execution_time=output.get("execution_time"),
        error=output.get("error", False),
        error_message=output.get("error_message"),
    )
