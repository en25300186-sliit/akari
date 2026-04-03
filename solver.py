"""
Akari (Light Up) Puzzle Solver — Colored Lights Edition.

Grid cell notation
------------------
'.'  empty cell — must be illuminated by at least one light
'#'  opaque block — blocks all light; no light may be placed here
'0'  flammable block — blocks all light; no light may be placed in any of
     the four orthogonally adjacent cells

Light colors
------------
'R'  Red
'G'  Green
'B'  Blue

Mixed illumination colors (when two light beams of different colors overlap)
----------------------------------------------------------------------------
'Y'  Yellow  = R + G
'C'  Cyan    = G + B
'M'  Magenta = B + R
'W'  White   = R + G + B  (all three colors combined)

Rules
-----
1. Lights shine outward in all four orthogonal directions until they hit a
   block or the edge of the grid.
2. No two lights may be in each other's line-of-sight (same unobstructed
   row or column segment) — that would be a fire hazard.
3. No light may be placed orthogonally adjacent to a flammable block ('0').
4. Every non-block cell must be illuminated by at least one light.
5. Cells listed in ``required_colors`` must be illuminated with exactly the
   specified mixed color.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLORS: Tuple[str, ...] = ("R", "G", "B")

BLOCK = "#"
FLAMMABLE = "0"
EMPTY = "."

# Required-color → component colors that must (and may only) illuminate a cell
REQUIRED_COLOR_COMPONENTS: Dict[str, FrozenSet[str]] = {
    "R": frozenset(["R"]),
    "G": frozenset(["G"]),
    "B": frozenset(["B"]),
    "Y": frozenset(["R", "G"]),
    "C": frozenset(["G", "B"]),
    "M": frozenset(["B", "R"]),
    "W": frozenset(["R", "G", "B"]),
}

# Frozenset of component colors → mixed color name
COLOR_MIX: Dict[FrozenSet[str], Optional[str]] = {
    frozenset(): None,
    frozenset(["R"]): "R",
    frozenset(["G"]): "G",
    frozenset(["B"]): "B",
    frozenset(["R", "G"]): "Y",
    frozenset(["G", "B"]): "C",
    frozenset(["B", "R"]): "M",
    frozenset(["R", "G", "B"]): "W",
}

DIRECTIONS: Tuple[Tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


class AkariSolver:
    """Backtracking solver for the coloured-light Akari puzzle."""

    def __init__(
        self,
        grid: List[List[str]],
        required_colors: Optional[Dict[Tuple[int, int], str]] = None,
    ) -> None:
        """
        Parameters
        ----------
        grid:
            2-D list of strings.  Each element is one of:
            ``'.'``  empty cell, ``'#'``  opaque block, ``'0'``  flammable block.
        required_colors:
            Mapping from ``(row, col)`` to the colour string that cell must
            display.  Valid values: ``'R'``, ``'G'``, ``'B'``,
            ``'Y'`` (yellow), ``'C'`` (cyan), ``'M'`` (magenta), ``'W'`` (white).
        """
        self.grid: List[List[str]] = [list(row) for row in grid]
        self.rows: int = len(grid)
        self.cols: int = len(grid[0]) if grid else 0
        self.required_colors: Dict[Tuple[int, int], str] = required_colors or {}

    # ------------------------------------------------------------------
    # Grid helpers
    # ------------------------------------------------------------------

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_block(self, r: int, c: int) -> bool:
        """Return True for any block type (opaque or flammable)."""
        return self.grid[r][c] in (BLOCK, FLAMMABLE)

    def is_flammable(self, r: int, c: int) -> bool:
        return self.grid[r][c] == FLAMMABLE

    # ------------------------------------------------------------------
    # Illumination helpers
    # ------------------------------------------------------------------

    def lights_in_sight(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
    ) -> List[Tuple[int, int]]:
        """
        Return every light position visible from ``(r, c)`` in the four
        orthogonal directions, *excluding* ``(r, c)`` itself.
        """
        visible: List[Tuple[int, int]] = []
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                if (nr, nc) in lights:
                    visible.append((nr, nc))
                nr += dr
                nc += dc
        return visible

    def get_illumination_colors(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
    ) -> FrozenSet[str]:
        """
        Return the frozenset of light colours that illuminate cell ``(r, c)``.
        A cell that holds a light is illuminated by that light's own colour.
        """
        colors: Set[str] = set()
        if (r, c) in lights:
            colors.add(lights[(r, c)])
        for pos in self.lights_in_sight(r, c, lights):
            colors.add(lights[pos])
        return frozenset(colors)

    @staticmethod
    def mix_color(colors: FrozenSet[str]) -> Optional[str]:
        """Translate a frozenset of component colours to the mixed colour name."""
        return COLOR_MIX.get(colors)

    # ------------------------------------------------------------------
    # Constraint helpers
    # ------------------------------------------------------------------

    def can_place_light(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
    ) -> bool:
        """
        Return True iff a light *may* be placed at ``(r, c)`` given the
        lights already placed.  Checks:

        * Cell is not a block.
        * Cell does not already hold a light.
        * No existing light is visible from this cell (fire hazard).
        * Cell is not orthogonally adjacent to a flammable block.
        """
        if self.is_block(r, c):
            return False
        if (r, c) in lights:
            return False
        if self.lights_in_sight(r, c, lights):
            return False
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc) and self.is_flammable(nr, nc):
                return False
        return True

    def _required_colors_feasible(
        self,
        lights: Dict[Tuple[int, int], str],
    ) -> bool:
        """
        Pruning check: for every required-colour cell that is *already*
        partially illuminated, ensure no extra colour has been added that
        makes it impossible to reach the target.

        If the current illumination contains a colour that is NOT part of the
        target colour's components, it can never be removed, so we prune.
        """
        for (r, c), req in self.required_colors.items():
            colors = self.get_illumination_colors(r, c, lights)
            if not colors:
                continue
            req_set = REQUIRED_COLOR_COMPONENTS.get(req, frozenset())
            if not colors.issubset(req_set):
                return False
        return True

    def _is_valid_solution(
        self,
        lights: Dict[Tuple[int, int], str],
    ) -> bool:
        """
        Return True iff ``lights`` represents a complete, valid solution:

        * Every non-block cell is illuminated.
        * Every cell in ``required_colors`` displays the required colour.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                if self.is_block(r, c):
                    continue
                colors = self.get_illumination_colors(r, c, lights)
                if not colors:
                    return False
                if (r, c) in self.required_colors:
                    req = self.required_colors[(r, c)]
                    actual = self.mix_color(colors)
                    if actual != req:
                        return False
        return True

    # ------------------------------------------------------------------
    # Back-tracking search
    # ------------------------------------------------------------------

    def solve(self) -> List[Dict[Tuple[int, int], str]]:
        """
        Find **all** valid solutions.

        Returns
        -------
        list of dicts
            Each dict maps ``(row, col)`` → colour string for every light
            placed in that solution.
        """
        empty_cells: List[Tuple[int, int]] = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if not self.is_block(r, c)
        ]
        solutions: List[Dict[Tuple[int, int], str]] = []
        self._backtrack(0, empty_cells, {}, solutions)
        return solutions

    def _backtrack(
        self,
        idx: int,
        empty_cells: List[Tuple[int, int]],
        lights: Dict[Tuple[int, int], str],
        solutions: List[Dict[Tuple[int, int], str]],
    ) -> None:
        if idx == len(empty_cells):
            if self._is_valid_solution(lights):
                solutions.append(dict(lights))
            return

        r, c = empty_cells[idx]

        # Option A: leave this cell without its own light
        self._backtrack(idx + 1, empty_cells, lights, solutions)

        # Options B–D: try placing each colour of light here
        if self.can_place_light(r, c, lights):
            for color in COLORS:
                lights[(r, c)] = color
                # Prune early if a required-colour cell is already violated
                if self._required_colors_feasible(lights):
                    self._backtrack(idx + 1, empty_cells, lights, solutions)
                del lights[(r, c)]

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_solution(
        self,
        lights: Dict[Tuple[int, int], str],
        solution_num: Optional[int] = None,
    ) -> None:
        """Pretty-print a single solution."""
        width = self.cols * 4 + 1
        header = f"Solution {solution_num}" if solution_num is not None else "Solution"
        print(f"\n{'=' * width}")
        print(f"  {header}")
        print(f"{'=' * width}")

        for r in range(self.rows):
            row_str = "|"
            for c in range(self.cols):
                if self.is_flammable(r, c):
                    row_str += " F |"
                elif self.is_block(r, c):
                    row_str += "###|"
                elif (r, c) in lights:
                    row_str += f" {lights[(r, c)]} |"
                else:
                    colors = self.get_illumination_colors(r, c, lights)
                    label = self.mix_color(colors) or "?"
                    row_str += f"({label})|"
            print(row_str)

        print(f"{'=' * width}")
        print("Legend: light=[R/G/B]  illuminated=(color)  block=###  flammable=F")
        if self.required_colors:
            fmt = {f"({r},{c})": v for (r, c), v in self.required_colors.items()}
            print(f"Required colours: {fmt}")
