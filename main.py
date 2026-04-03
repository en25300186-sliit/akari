"""
Interactive command-line interface for the Akari coloured-lights solver.

Run with:
    python main.py

The user specifies the grid size, places blocks/flammable blocks, optionally
marks cells with required illumination colours, and then the solver finds every
valid arrangement of Red, Green, and Blue lights that satisfies all the rules.

Example puzzles are also embedded at the bottom of this file; call
``run_example(n)`` to solve them directly.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from solver import BLOCK, COLORS, EMPTY, FLAMMABLE, AkariSolver

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_COLOR_LABELS = {
    "R": "Red",
    "G": "Green",
    "B": "Blue",
    "Y": "Yellow (R+G)",
    "C": "Cyan (G+B)",
    "M": "Magenta (B+R)",
    "W": "White (R+G+B)",
}

VALID_REQUIRED_COLORS = ("R", "G", "B", "Y", "C", "M", "W")


def print_puzzle(
    grid: List[List[str]],
    required_colors: Optional[Dict[Tuple[int, int], str]] = None,
) -> None:
    """Print the puzzle grid before solving."""
    required_colors = required_colors or {}
    rows, cols = len(grid), len(grid[0]) if grid else 0
    sep = "+" + "---+" * cols
    print(f"\nPuzzle ({rows}×{cols}):")
    print(sep)
    for r, row in enumerate(grid):
        line = "|"
        for c, cell in enumerate(row):
            if cell == BLOCK:
                line += "###|"
            elif cell == FLAMMABLE:
                line += " 0 |"
            elif (r, c) in required_colors:
                line += f"[{required_colors[(r, c)]}]|"
            else:
                line += "   |"
        print(line)
    print(sep)
    if required_colors:
        print("Required colours:", {f"({r},{c})": v for (r, c), v in required_colors.items()})


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _prompt_int(prompt: str, lo: int = 1, hi: int = 100) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            val = int(raw)
            if lo <= val <= hi:
                return val
        print(f"  ✗ Please enter an integer between {lo} and {hi}.")


def _parse_position(text: str, rows: int, cols: int) -> Optional[Tuple[int, int]]:
    """Parse '1-based row col' from text, returning 0-based (r, c) or None."""
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        r, c = int(parts[0]) - 1, int(parts[1]) - 1
    except ValueError:
        return None
    if 0 <= r < rows and 0 <= c < cols:
        return r, c
    return None


# ---------------------------------------------------------------------------
# Interactive setup
# ---------------------------------------------------------------------------


def interactive_setup() -> Tuple[List[List[str]], Dict[Tuple[int, int], str]]:
    """Walk the user through setting up a puzzle and return (grid, required_colors)."""
    print("\n" + "─" * 60)
    print("  AKARI — Coloured Lights Puzzle Solver")
    print("─" * 60)
    print("\nRules summary:")
    print("  Lights: R (Red)  G (Green)  B (Blue)")
    print("  Mixed:  Y=R+G (Yellow)  C=G+B (Cyan)  M=B+R (Magenta)")
    print("  • Lights shine in 4 orthogonal directions until a block or edge.")
    print("  • Two lights must never be in each other's line of sight.")
    print("  • Flammable blocks (0) cannot have lights placed next to them.")
    print("  • Every non-block cell must be illuminated.")
    print()

    rows = _prompt_int("Grid rows    (1–20): ", 1, 20)
    cols = _prompt_int("Grid columns (1–20): ", 1, 20)

    grid: List[List[str]] = [[EMPTY] * cols for _ in range(rows)]
    required_colors: Dict[Tuple[int, int], str] = {}

    # -- blocks ----------------------------------------------------------
    print("\n── Add blocks ─────────────────────────────────────────────")
    print("  '#'  opaque block    '0'  flammable block")
    print("  Format: row col type   (1-based, e.g. '2 3 #')")
    print("  Type 'done' when finished.")
    while True:
        raw = input("  block> ").strip()
        if raw.lower() == "done":
            break
        parts = raw.split()
        if len(parts) != 3:
            print("  ✗ Use format: row col type")
            continue
        pos = _parse_position(raw, rows, cols)
        if pos is None:
            print(f"  ✗ Position out of bounds (rows 1–{rows}, cols 1–{cols}).")
            continue
        btype = parts[2]
        if btype not in ("#", "0"):
            print("  ✗ Block type must be '#' or '0'.")
            continue
        grid[pos[0]][pos[1]] = btype
        print_puzzle(grid, required_colors)

    # -- required colours ------------------------------------------------
    print("\n── Set required illumination colours ───────────────────────")
    print("  Colours: R  G  B  Y (yellow)  C (cyan)  M (magenta)")
    print("  Format: row col colour   (e.g. '2 3 Y')")
    print("  Type 'done' when finished.")
    while True:
        raw = input("  colour> ").strip()
        if raw.lower() == "done":
            break
        parts = raw.split()
        if len(parts) != 3:
            print("  ✗ Use format: row col colour")
            continue
        pos = _parse_position(raw, rows, cols)
        if pos is None:
            print(f"  ✗ Position out of bounds (rows 1–{rows}, cols 1–{cols}).")
            continue
        r, c = pos
        if grid[r][c] != EMPTY:
            print("  ✗ Cannot set a required colour on a block cell.")
            continue
        colour = parts[2].upper()
        if colour not in VALID_REQUIRED_COLORS:
            print(f"  ✗ Unknown colour '{colour}'. Choose from: {VALID_REQUIRED_COLORS}")
            continue
        required_colors[(r, c)] = colour
        print_puzzle(grid, required_colors)

    return grid, required_colors


# ---------------------------------------------------------------------------
# Solve & display
# ---------------------------------------------------------------------------


def solve_and_display(
    grid: List[List[str]],
    required_colors: Optional[Dict[Tuple[int, int], str]] = None,
    max_display: int = 10,
) -> List[Dict[Tuple[int, int], str]]:
    """
    Solve the puzzle and print results.

    Parameters
    ----------
    grid:
        2-D list of cell strings (``'.'``, ``'#'``, ``'0'``).
    required_colors:
        Optional mapping from ``(row, col)`` to required colour.
    max_display:
        Maximum number of solutions to print (all are returned regardless).

    Returns
    -------
    list of solution dicts
    """
    required_colors = required_colors or {}
    print_puzzle(grid, required_colors)
    print("\nSolving …", end="", flush=True)

    solver = AkariSolver(grid, required_colors)
    solutions = solver.solve()

    print(f"\rFound {len(solutions)} solution(s).         ")

    if not solutions:
        print("No valid arrangement of lights exists for this puzzle.")
        return solutions

    display_count = min(len(solutions), max_display)
    for i, sol in enumerate(solutions[:display_count], 1):
        solver.display_solution(sol, solution_num=i)

    if len(solutions) > max_display:
        print(f"\n… and {len(solutions) - max_display} more solution(s) not shown.")

    return solutions


# ---------------------------------------------------------------------------
# Built-in example puzzles
# ---------------------------------------------------------------------------


def _example_1() -> None:
    """3×3 grid with a centre block.  Single-colour solutions."""
    print("\n=== Example 1: 3×3 with centre block ===")
    grid = [
        [".", ".", "."],
        [".", "#", "."],
        [".", ".", "."],
    ]
    solve_and_display(grid, max_display=5)


def _example_2() -> None:
    """4×4 grid with two flammable blocks and required colours."""
    print("\n=== Example 2: 4×4 with flammable blocks & required colours ===")
    grid = [
        [".", ".", ".", "."],
        [".", "0", ".", "."],
        [".", ".", "0", "."],
        [".", ".", ".", "."],
    ]
    required = {(0, 0): "R", (3, 3): "G"}
    solve_and_display(grid, required, max_display=5)


def _example_3() -> None:
    """
    5×5 grid showing mixed colours.
    The centre cell (2,2) must be illuminated Yellow (R+G), which requires
    a Red beam from the row and a Green beam from the column (or vice-versa).
    """
    print("\n=== Example 3: 5×5 — centre cell must be Yellow ===")
    grid = [
        [".", "#", ".", "#", "."],
        ["#", ".", ".", ".", "#"],
        [".", ".", ".", ".", "."],
        ["#", ".", ".", ".", "#"],
        [".", "#", ".", "#", "."],
    ]
    required = {(2, 2): "Y"}
    solve_and_display(grid, required, max_display=5)


EXAMPLES = {
    "1": _example_1,
    "2": _example_2,
    "3": _example_3,
}


def run_example(name: str) -> None:
    """Run one of the built-in example puzzles by name ('1', '2', or '3')."""
    fn = EXAMPLES.get(str(name))
    if fn is None:
        print(f"Unknown example '{name}'. Available: {list(EXAMPLES)}")
        return
    fn()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("\nAKARI SOLVER")
    print("============")
    print("1. Solve a puzzle interactively")
    print("2. Run built-in examples")

    choice = input("\nChoice (1/2): ").strip()

    if choice == "2":
        print("\nAvailable examples: 1, 2, 3")
        ex = input("Which example? ").strip()
        run_example(ex)
    else:
        grid, required_colors = interactive_setup()
        print("\nFinal puzzle:")
        solve_and_display(grid, required_colors)


if __name__ == "__main__":
    main()
