"""Utilities for starting, querying, and stopping Stockfish."""

from __future__ import annotations

from typing import Optional

import chess
import chess.engine


def start_engine(stockfish_path: str) -> chess.engine.SimpleEngine:
    """Start a UCI engine process from the given binary path."""
    if not stockfish_path:
        raise ValueError("Sokvagen till Stockfish ar tom.")

    return chess.engine.SimpleEngine.popen_uci(stockfish_path)


def get_best_move(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    think_time: float = 0.2,
) -> Optional[chess.Move]:
    """Return the best move in the current position."""
    if think_time <= 0:
        raise ValueError("think_time maste vara storre an 0.")

    result = engine.play(board, chess.engine.Limit(time=think_time))
    return result.move


def configure_engine_strength(
    engine: chess.engine.SimpleEngine,
    *,
    skill_level: int,
) -> None:
    """Configure Stockfish playing strength (0-20)."""
    if not 0 <= skill_level <= 20:
        raise ValueError("skill_level maste vara mellan 0 och 20.")

    engine.configure({"Skill Level": skill_level})


def close_engine(engine: Optional[chess.engine.SimpleEngine]) -> None:
    """Close the engine process safely."""
    if engine is None:
        return

    try:
        engine.quit()
    except Exception:
        # Ignore shutdown errors to keep exit path predictable.
        pass
