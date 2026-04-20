"""Tkinter GUI for playing chess with optional Stockfish opponent."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import ctypes
import time
import uuid
from typing import Dict, Tuple

import chess
import chess.engine

from engine_utils import close_engine, configure_engine_strength, get_best_move, start_engine

try:
    from playsound import playsound
except Exception:  # pragma: no cover - optional dependency fallback
    playsound = None

SQUARE_SIZE = 72
BOARD_SIZE = SQUARE_SIZE * 8

LIGHT_SQUARE = "#F0D9B5"
DARK_SQUARE = "#B58863"
SELECTED_SQUARE = "#F6F669"
LAST_MOVE_FROM_LIGHT = "#D8D38A"
LAST_MOVE_FROM_DARK = "#C3AF61"
LAST_MOVE_TO_LIGHT = "#CFE68D"
LAST_MOVE_TO_DARK = "#A9C95F"

MODE_VS_ENGINE = "Spela mot Stockfish"
MODE_ANALYSIS = "Analyslage (du spelar bada sidor)"

DIFFICULTY_PRESETS: Dict[str, Tuple[int, float]] = {
    "Latt": (0, 0.05),
    "Medel": (6, 0.12),
    "Svar": (12, 0.25),
    "Mycket svar": (20, 0.5),
}

COLOR_OPTIONS: Dict[str, chess.Color] = {
    "Vit": chess.WHITE,
    "Svart": chess.BLACK,
}

TRACKED_PIECE_TYPES = (
    chess.PAWN,
    chess.KNIGHT,
    chess.BISHOP,
    chess.ROOK,
    chess.QUEEN,
)

STARTING_PIECE_COUNTS = {
    chess.PAWN: 8,
    chess.KNIGHT: 2,
    chess.BISHOP: 2,
    chess.ROOK: 2,
    chess.QUEEN: 1,
}

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}

PIECE_SHORT_NAMES = {
    chess.PAWN: "P",
    chess.KNIGHT: "N",
    chess.BISHOP: "B",
    chess.ROOK: "R",
    chess.QUEEN: "Q",
}


def format_game_result(board: chess.Board) -> str:
    """Return a human-readable game result string."""
    outcome = board.outcome()
    if outcome is None:
        return "okant resultat"
    if outcome.winner is None:
        return f"remi ({outcome.termination.name})"

    winner = "vit" if outcome.winner == chess.WHITE else "svart"
    return f"{winner} vinner ({outcome.termination.name})"


class SoundManager:
    """Handle optional GUI sound effects."""

    def __init__(self, base_dir: Path) -> None:
        sounds_dir = base_dir / "sounds"
        self.move_sound = sounds_dir / "move-self.mp3"
        self.capture_sound = sounds_dir / "capture.mp3"
        self.notify_sound = sounds_dir / "notify.mp3"
        self._use_win_mci = playsound is None and os.name == "nt"
        self._winmm = ctypes.windll.winmm if self._use_win_mci else None

    def _play_file(self, path: Path) -> None:
        if not path.exists():
            return

        if playsound is not None:
            threading.Thread(
                target=self._play_file_sync,
                args=(str(path),),
                daemon=True,
            ).start()
            return

        if self._use_win_mci:
            threading.Thread(
                target=self._play_file_windows_mci,
                args=(str(path),),
                daemon=True,
            ).start()
            return

    @staticmethod
    def _play_file_sync(path: str) -> None:
        try:
            playsound(path)
        except Exception:
            # Ignore sound failures so gameplay never breaks.
            pass

    def _play_file_windows_mci(self, path: str) -> None:
        """Play mp3 on Windows without external dependencies."""
        if self._winmm is None:
            return

        alias = f"sfx_{uuid.uuid4().hex}"
        safe_path = path.replace('"', "")
        try:
            open_result = self._winmm.mciSendStringW(
                f'open "{safe_path}" type mpegvideo alias {alias}',
                None,
                0,
                None,
            )
            if open_result != 0:
                return

            self._winmm.mciSendStringW(f"play {alias}", None, 0, None)

            length_buffer = ctypes.create_unicode_buffer(64)
            length_result = self._winmm.mciSendStringW(
                f"status {alias} length",
                length_buffer,
                len(length_buffer),
                None,
            )
            if length_result == 0 and length_buffer.value.isdigit():
                time.sleep((int(length_buffer.value) / 1000.0) + 0.15)
            else:
                time.sleep(1.0)
        except Exception:
            pass
        finally:
            try:
                self._winmm.mciSendStringW(f"close {alias}", None, 0, None)
            except Exception:
                pass

    def play_move(self) -> None:
        self._play_file(self.move_sound)

    def play_capture(self) -> None:
        self._play_file(self.capture_sound)

    def play_notify(self) -> None:
        self._play_file(self.notify_sound)


class ChessGUI(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Schack med Stockfish")
        self.resizable(False, False)

        self.board = chess.Board()
        self.selected_square: chess.Square | None = None
        self.last_move: chess.Move | None = None

        self.mode_var = tk.StringVar(value=MODE_VS_ENGINE)
        self.color_var = tk.StringVar(value="Vit")
        self.difficulty_var = tk.StringVar(value="Medel")
        self.status_var = tk.StringVar(value="Redo.")
        self.white_lost_var = tk.StringVar(value="")
        self.black_lost_var = tk.StringVar(value="")

        self.player_color = chess.WHITE
        self.engine_think_time = 0.12
        self.sounds = SoundManager(Path(__file__).resolve().parent)

        self.engine = self._create_engine()
        if self.engine is None:
            self.destroy()
            return

        self._build_ui()
        self._start_new_game()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_engine(self) -> chess.engine.SimpleEngine | None:
        stockfish_path = os.getenv("STOCKFISH_PATH")
        if not stockfish_path:
            messagebox.showinfo(
                "Sokvag saknas",
                "STOCKFISH_PATH ar inte satt.\nValj en Stockfish-binär manuellt.",
            )
            stockfish_path = filedialog.askopenfilename(
                title="Valj Stockfish-binär",
                filetypes=[("Executable", "*.exe"), ("Alla filer", "*.*")],
            )
            if not stockfish_path:
                messagebox.showerror("Ingen binär vald", "Kan inte starta utan Stockfish.")
                return None

        try:
            return start_engine(stockfish_path)
        except (FileNotFoundError, OSError, chess.engine.EngineError) as error:
            messagebox.showerror(
                "Startfel",
                f"Kunde inte starta Stockfish fran '{stockfish_path}'.\nFel: {error}",
            )
            return None

    def _build_ui(self) -> None:
        controls = tk.Frame(self, padx=10, pady=10)
        controls.pack(fill="x")

        tk.Label(controls, text="Lage:").grid(row=0, column=0, sticky="w")
        tk.OptionMenu(controls, self.mode_var, MODE_VS_ENGINE, MODE_ANALYSIS).grid(
            row=0, column=1, sticky="w", padx=(4, 10)
        )

        tk.Label(controls, text="Din farg:").grid(row=0, column=2, sticky="w")
        tk.OptionMenu(controls, self.color_var, *COLOR_OPTIONS.keys()).grid(
            row=0, column=3, sticky="w", padx=(4, 10)
        )

        tk.Label(controls, text="Svartsgrad:").grid(row=0, column=4, sticky="w")
        tk.OptionMenu(controls, self.difficulty_var, *DIFFICULTY_PRESETS.keys()).grid(
            row=0, column=5, sticky="w", padx=(4, 10)
        )

        tk.Button(controls, text="Nytt parti", command=self._start_new_game).grid(
            row=0, column=6, padx=(4, 0)
        )
        tk.Button(controls, text="Tips", command=self._show_tip).grid(
            row=0, column=7, padx=(4, 0)
        )

        self.canvas = tk.Canvas(self, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.canvas.pack(padx=10)
        self.canvas.bind("<Button-1>", self._on_board_click)

        scoreboard = tk.Frame(self, padx=10, pady=2)
        scoreboard.pack(fill="x")
        tk.Label(scoreboard, textvariable=self.white_lost_var, anchor="w").pack(fill="x")
        tk.Label(scoreboard, textvariable=self.black_lost_var, anchor="w").pack(fill="x")

        tk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=8)

    def _start_new_game(self) -> None:
        self.board = chess.Board()
        self.selected_square = None
        self.last_move = None

        difficulty_name = self.difficulty_var.get()
        skill_level, self.engine_think_time = DIFFICULTY_PRESETS[difficulty_name]
        self.player_color = COLOR_OPTIONS[self.color_var.get()]

        if self.engine is not None:
            configure_engine_strength(self.engine, skill_level=skill_level)

        if self.mode_var.get() == MODE_ANALYSIS:
            self.status_var.set(
                "Analyslage: klicka en pjäs och klicka malrutan. Du spelar bada sidor."
            )
        else:
            chosen = "vit" if self.player_color == chess.WHITE else "svart"
            self.status_var.set(
                f"Mot Stockfish: du spelar {chosen}. Klicka en pjäs och sedan malruta."
            )

        self._draw_board()
        self._update_scoreboard()
        self._maybe_engine_turn()

    def _draw_board(self) -> None:
        self.canvas.delete("all")

        for row in range(8):
            for col in range(8):
                x1 = col * SQUARE_SIZE
                y1 = row * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                square = chess.square(col, 7 - row)

                is_light = (row + col) % 2 == 0
                fill = LIGHT_SQUARE if is_light else DARK_SQUARE

                if self.last_move is not None:
                    if square == self.last_move.from_square:
                        fill = LAST_MOVE_FROM_LIGHT if is_light else LAST_MOVE_FROM_DARK
                    elif square == self.last_move.to_square:
                        fill = LAST_MOVE_TO_LIGHT if is_light else LAST_MOVE_TO_DARK

                if self.selected_square == square:
                    fill = SELECTED_SQUARE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill)

                piece = self.board.piece_at(square)
                if piece is not None:
                    self.canvas.create_text(
                        x1 + SQUARE_SIZE / 2,
                        y1 + SQUARE_SIZE / 2,
                        text=piece.unicode_symbol(),
                        font=("Segoe UI Symbol", 36),
                    )

    def _on_board_click(self, event: tk.Event[tk.Misc]) -> None:
        if self.board.is_game_over():
            return

        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        if not (0 <= col <= 7 and 0 <= row <= 7):
            return

        clicked_square = chess.square(col, 7 - row)
        mode = self.mode_var.get()
        player_to_move = self.board.turn

        if mode == MODE_VS_ENGINE and player_to_move != self.player_color:
            self.status_var.set("Vanta: Stockfish tanker...")
            return

        if self.selected_square is None:
            piece = self.board.piece_at(clicked_square)
            if piece is None:
                return
            if piece.color != self.board.turn:
                return
            self.selected_square = clicked_square
            self._draw_board()
            return

        from_square = self.selected_square
        to_square = clicked_square
        self.selected_square = None

        if from_square == to_square:
            self._draw_board()
            return

        move = chess.Move(from_square, to_square)
        if move not in self.board.legal_moves:
            moving_piece = self.board.piece_at(from_square)
            if (
                moving_piece is not None
                and moving_piece.piece_type == chess.PAWN
                and chess.square_rank(to_square) in {0, 7}
            ):
                move = chess.Move(from_square, to_square, promotion=chess.QUEEN)

        if move not in self.board.legal_moves:
            self.status_var.set("Olagligt drag. Forsok igen.")
            self._draw_board()
            return

        was_capture = is_capture(move, self.board)
        self.board.push(move)
        self.last_move = move
        if was_capture:
            self.sounds.play_capture()
        else:
            self.sounds.play_move()
        self._draw_board()
        self._update_scoreboard()
        self._after_human_move(move)

    def _after_human_move(self, move: chess.Move) -> None:
        if self.board.is_game_over():
            self._show_game_over()
            return

        mode = self.mode_var.get()
        if mode == MODE_ANALYSIS:
            self._show_analysis_hint(move)
            if self.board.is_check():
                self.sounds.play_notify()
            return

        self.status_var.set(f"Du spelade {move.uci()}. Stockfish tanker...")
        if self.board.is_check():
            self.sounds.play_notify()
        self.after(120, self._play_engine_move)

    def _show_analysis_hint(self, move: chess.Move) -> None:
        if self.engine is None:
            self.status_var.set(f"Du spelade {move.uci()}.")
            return

        try:
            best_move = get_best_move(self.engine, self.board, think_time=self.engine_think_time)
        except chess.engine.EngineError as error:
            self.status_var.set(f"Du spelade {move.uci()}. Kunde inte hamta forslag: {error}")
            return

        if best_move is None:
            self.status_var.set(f"Du spelade {move.uci()}. Inget forslag tillgangligt.")
            return

        self.status_var.set(f"Du spelade {move.uci()}. Stockfish foreslar: {best_move.uci()}.")

    def _show_tip(self) -> None:
        """Show a Stockfish recommendation for side to move."""
        if self.board.is_game_over():
            self.status_var.set("Partiet ar redan slut.")
            return
        if self.engine is None:
            self.status_var.set("Tips ar inte tillgangligt utan Stockfish.")
            return

        try:
            best_move = get_best_move(self.engine, self.board, think_time=self.engine_think_time)
        except chess.engine.EngineError as error:
            self.status_var.set(f"Kunde inte hamta tips: {error}")
            return

        if best_move is None:
            self.status_var.set("Inget tips tillgangligt i denna position.")
            return

        side = "vit" if self.board.turn == chess.WHITE else "svart"
        self.status_var.set(f"Tips for {side}: spela {best_move.uci()}.")

    def _maybe_engine_turn(self) -> None:
        if (
            self.mode_var.get() == MODE_VS_ENGINE
            and not self.board.is_game_over()
            and self.board.turn != self.player_color
        ):
            self.status_var.set("Stockfish tanker...")
            self.after(120, self._play_engine_move)

    def _play_engine_move(self) -> None:
        if self.engine is None or self.board.is_game_over():
            return
        if self.mode_var.get() != MODE_VS_ENGINE:
            return
        if self.board.turn == self.player_color:
            return

        try:
            best_move = get_best_move(self.engine, self.board, think_time=self.engine_think_time)
        except chess.engine.EngineError as error:
            self.status_var.set(f"Stockfish-fel: {error}")
            return

        if best_move is None:
            self.status_var.set("Stockfish hittade inget drag.")
            return

        was_capture = is_capture(best_move, self.board)
        self.board.push(best_move)
        self.last_move = best_move
        if was_capture:
            self.sounds.play_capture()
        else:
            self.sounds.play_move()
        self._draw_board()
        self._update_scoreboard()

        if self.board.is_game_over():
            self._show_game_over()
            return

        if self.board.is_check():
            self.sounds.play_notify()
            self.status_var.set(f"Stockfish spelade {best_move.uci()}. Schack! Din tur.")
            return

        self.status_var.set(f"Stockfish spelade {best_move.uci()}. Din tur.")

    def _show_game_over(self) -> None:
        result = format_game_result(self.board)
        self.sounds.play_notify()
        self.status_var.set(f"Partiet ar slut: {result}")
        messagebox.showinfo("Parti slut", f"{result}")

    def _on_close(self) -> None:
        close_engine(self.engine)
        self.destroy()

    def _update_scoreboard(self) -> None:
        """Refresh lost-piece summaries and point totals for both sides."""
        white_lost_counts, white_lost_points = self._calculate_lost_material(chess.WHITE)
        black_lost_counts, black_lost_points = self._calculate_lost_material(chess.BLACK)

        self.white_lost_var.set(
            f"Vit forlorat: {self._format_lost_material(white_lost_counts)} | Poang: {white_lost_points}"
        )
        self.black_lost_var.set(
            f"Svart forlorat: {self._format_lost_material(black_lost_counts)} | Poang: {black_lost_points}"
        )

    def _calculate_lost_material(self, color: chess.Color) -> Tuple[Dict[int, int], int]:
        """Return lost piece counts and total points for the given side."""
        lost_counts: Dict[int, int] = {}
        lost_points = 0
        for piece_type in TRACKED_PIECE_TYPES:
            current_count = len(self.board.pieces(piece_type, color))
            lost_count = STARTING_PIECE_COUNTS[piece_type] - current_count
            lost_counts[piece_type] = max(0, lost_count)
            lost_points += lost_counts[piece_type] * PIECE_VALUES[piece_type]

        return lost_counts, lost_points

    def _format_lost_material(self, lost_counts: Dict[int, int]) -> str:
        """Format lost counts for scoreboard display."""
        parts = []
        for piece_type in TRACKED_PIECE_TYPES:
            parts.append(f"{PIECE_SHORT_NAMES[piece_type]}:{lost_counts[piece_type]}")
        return " ".join(parts)


def main() -> int:
    app = ChessGUI()
    if not app.winfo_exists():
        return 1
    app.mainloop()
    return 0


def is_capture(move: chess.Move, board: chess.Board) -> bool:
    """Return True if the move captures a piece in the current position."""
    return board.is_capture(move)


if __name__ == "__main__":
    raise SystemExit(main())
