"""
Akari (Light Up) Puzzle Solver — Colored Lights Edition.

Grid cell notation
------------------
'.'  empty cell — must be illuminated by at least one light
'#'  opaque block — blocks all light; no light may be placed here
'0'  flammable block — blocks all light; no light may be placed in any of
     the four orthogonally adjacent cells
'1'–'4'  numbered block — blocks all light; no light may be placed here;
     exactly N of its orthogonally adjacent non-block cells must contain
     a light.

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
6. Each numbered block ('1'–'4') must have exactly that many lights placed
   in its orthogonally adjacent (non-block) cells.
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

# Numbered blocks '1'–'4': opaque blocks that require exactly N adjacent lights.
NUMBERED_BLOCKS: FrozenSet[str] = frozenset({"1", "2", "3", "4"})

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
        """Return True for any block type (opaque, flammable, or numbered)."""
        return self.grid[r][c] in (BLOCK, FLAMMABLE) or self.grid[r][c] in NUMBERED_BLOCKS

    def is_flammable(self, r: int, c: int) -> bool:
        return self.grid[r][c] == FLAMMABLE

    def is_numbered_block(self, r: int, c: int) -> bool:
        """Return True iff the cell is a numbered block ('1'–'4')."""
        return self.grid[r][c] in NUMBERED_BLOCKS

    def numbered_block_value(self, r: int, c: int) -> int:
        """Return the required adjacent-light count for a numbered block."""
        return int(self.grid[r][c])

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
        * Every numbered block has exactly the required number of adjacent lights.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                if self.is_block(r, c):
                    # Check numbered-block adjacency constraint.
                    if self.is_numbered_block(r, c):
                        required = self.numbered_block_value(r, c)
                        adj = sum(
                            1
                            for dr, dc in DIRECTIONS
                            if self.in_bounds(r + dr, c + dc)
                            and (r + dr, c + dc) in lights
                        )
                        if adj != required:
                            return False
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

    def _numbered_blocks_feasible(
        self,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
    ) -> bool:
        """
        Pruning check for numbered blocks.

        For each numbered block, count how many adjacent cells already have a
        light (``adj_lights``) and how many adjacent cells are still undecided
        (``adj_free``).  Prune if:

        * ``adj_lights`` already exceeds the required count, or
        * ``adj_lights + adj_free`` is less than the required count
          (impossible to satisfy even with maximum future placements).
        """
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.is_numbered_block(r, c):
                    continue
                required = self.numbered_block_value(r, c)
                adj_lights = 0
                adj_free = 0
                for dr, dc in DIRECTIONS:
                    nr, nc = r + dr, c + dc
                    if not self.in_bounds(nr, nc):
                        continue
                    if self.is_block(nr, nc):
                        continue
                    if (nr, nc) in lights:
                        adj_lights += 1
                    elif (nr, nc) not in decided:
                        adj_free += 1
                if adj_lights > required:
                    return False
                if adj_lights + adj_free < required:
                    return False
        return True

    # ------------------------------------------------------------------
    # Additional pruning helpers
    # ------------------------------------------------------------------

    def _can_be_illuminated(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
    ) -> bool:
        """
        Return True iff ``(r, c)`` is either already illuminated or has at
        least one undecided (not yet committed) cell in one of its four
        sight-line segments — meaning a future light could still reach it.
        """
        if self.get_illumination_colors(r, c, lights):
            return True
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                if (nr, nc) not in decided:
                    return True
                nr += dr
                nc += dc
        return False

    def _illumination_feasible_after_no_light(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
    ) -> bool:
        """
        After committing ``(r, c)`` to *no light*, verify that:

        1. ``(r, c)`` itself can still be illuminated (own light is off the
           table, so it needs a light elsewhere in its sight).
        2. Every decided-no-light cell that can see ``(r, c)`` can still be
           illuminated (``(r, c)`` is no longer an available light source for
           them, narrowing their options).
        """
        if not self._can_be_illuminated(r, c, lights, decided):
            return False
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                if (nr, nc) in decided and (nr, nc) not in lights:
                    if not self._can_be_illuminated(nr, nc, lights, decided):
                        return False
                nr += dr
                nc += dc
        return True

    def _required_colors_satisfiable(
        self,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
    ) -> bool:
        """
        For every required-colour cell whose target is not yet fully achieved,
        verify that at least one undecided cell exists in its sight lines so
        that the missing component colour(s) could still be provided.

        Also checks that current illumination does not already contain a colour
        outside the target set (which can never be undone).
        """
        for (r, c), req in self.required_colors.items():
            req_set = REQUIRED_COLOR_COMPONENTS.get(req, frozenset())
            current = self.get_illumination_colors(r, c, lights)

            # Wrong colour already present — unrecoverable.
            if not current.issubset(req_set):
                return False

            needed = req_set - current
            if not needed:
                continue  # Already fully satisfied.

            # Need more colours: there must be at least one undecided cell in
            # the sight lines (including the cell itself) that could supply them.
            has_undecided = (r, c) not in decided
            if not has_undecided:
                for dr, dc in DIRECTIONS:
                    nr, nc = r + dr, c + dc
                    while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                        if (nr, nc) not in decided:
                            has_undecided = True
                            break
                        nr += dr
                        nc += dc
                    if has_undecided:
                        break
            if not has_undecided:
                return False
        return True

    # ------------------------------------------------------------------
    # Constraint propagation helpers
    # ------------------------------------------------------------------

    def _compute_forbidden(self) -> Set[Tuple[int, int]]:
        """Return the set of empty cells that must never hold a light
        (i.e. they are orthogonally adjacent to a flammable block)."""
        forbidden: Set[Tuple[int, int]] = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.is_block(r, c):
                    continue
                for dr, dc in DIRECTIONS:
                    nr, nc = r + dr, c + dc
                    if self.in_bounds(nr, nc) and self.is_flammable(nr, nc):
                        forbidden.add((r, c))
                        break
        return forbidden

    def _mark_fire_hazard(
        self,
        r: int,
        c: int,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
    ) -> None:
        """After placing a light at ``(r, c)``, mark every other cell in its
        four sight-line segments as decided-no-light (fire hazard)."""
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                decided.add((nr, nc))  # no-light (not added to lights)
                nr += dr
                nc += dc

    def _propagate(
        self,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
        forbidden: Set[Tuple[int, int]],
    ) -> bool:
        """
        Apply constraint propagation until a fixpoint is reached.

        Propagation rules applied repeatedly:

        1. **Required-colour unit rule** — for each required-colour cell that
           still needs a colour component *k*, collect every undecided,
           non-forbidden cell visible from it (including itself) whose
           placement of colour *k* is not immediately blocked by a fire hazard.
           If there is exactly *one* such candidate, force colour *k* there.
           If there are *zero* candidates, return ``False`` (contradiction).

        2. **Illumination unit rule** — for each undecided non-block cell that
           is not yet illuminated, collect every undecided cell (including
           itself) that could illuminate it (i.e. is in one of its four sight
           segments and is not forbidden).  If there is exactly *one* such
           candidate, force *some* light there.  If colour is already pinned
           by a required-colour constraint at that candidate, use that colour;
           otherwise we cannot fix the colour yet (skip forcing—colour will be
           resolved by other rules or backtracking).

        3. **Feasibility checks** — after every forced placement propagate the
           fire-hazard constraint and verify that no required-colour cell has
           already received a wrong colour.

        Modifies *lights* and *decided* in place.  Returns ``True`` if
        consistent so far, ``False`` if a contradiction has been found.
        """
        changed = True
        while changed:
            changed = False

            # ---- Rule 1: required-colour unit propagation ----
            for (r, c), req in self.required_colors.items():
                req_set = REQUIRED_COLOR_COMPONENTS.get(req, frozenset())
                current = self.get_illumination_colors(r, c, lights)

                if not current.issubset(req_set):
                    return False  # wrong colour already present

                needed = req_set - current
                for color in list(needed):
                    # Find undecided non-forbidden candidates for this colour.
                    candidates: List[Tuple[int, int]] = []

                    # Cell (r,c) itself as a candidate.
                    if (
                        (r, c) not in decided
                        and (r, c) not in forbidden
                        and not self.lights_in_sight(r, c, lights)
                    ):
                        candidates.append((r, c))

                    for dr, dc in DIRECTIONS:
                        nr, nc = r + dr, c + dc
                        while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                            if (
                                (nr, nc) not in decided
                                and (nr, nc) not in forbidden
                                and not self.lights_in_sight(nr, nc, lights)
                            ):
                                candidates.append((nr, nc))
                            nr += dr
                            nc += dc

                    if not candidates:
                        return False  # no way to supply this colour

                    if len(candidates) == 1:
                        pos = candidates[0]
                        pr, pc = pos
                        # Conflict: pos already has a different colour?
                        if pos in lights:
                            if lights[pos] != color:
                                return False
                            # Already set correctly — nothing to do.
                        else:
                            # Force placement.
                            lights[pos] = color
                            decided.add(pos)
                            self._mark_fire_hazard(pr, pc, lights, decided)
                            changed = True

                            # Verify no required-colour cell is contaminated.
                            if not self._required_colors_feasible(lights):
                                return False

            # ---- Rule 2: illumination unit propagation ----
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.is_block(r, c):
                        continue
                    if (r, c) in decided:
                        # Already decided; just verify it's illuminated if no-light.
                        if (r, c) not in lights:
                            if not self.get_illumination_colors(r, c, lights):
                                # Decided no-light but dark — contradiction only if
                                # no undecided cell can still reach it.
                                if not self._can_be_illuminated(r, c, lights, decided):
                                    return False
                        continue

                    # Undecided cell — find all possible illumination sources.
                    sources: List[Tuple[int, int]] = []
                    if (r, c) not in forbidden:
                        sources.append((r, c))
                    for dr, dc in DIRECTIONS:
                        nr, nc = r + dr, c + dc
                        while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                            if (nr, nc) not in decided and (nr, nc) not in forbidden:
                                sources.append((nr, nc))
                            nr += dr
                            nc += dc

                    # Already illuminated by an existing light — fine.
                    if self.get_illumination_colors(r, c, lights):
                        continue

                    if not sources:
                        return False  # Can never be illuminated.

                    if len(sources) == 1:
                        pos = sources[0]
                        pr, pc = pos
                        if pos in lights:
                            continue  # already a light here, illumination satisfied

                        # Determine colour: if (pos) is a required-colour cell
                        # and that colour is a single primary, use it; otherwise
                        # we need backtracking to choose a colour — skip for now.
                        forced_color: Optional[str] = None
                        if pos in self.required_colors:
                            req = self.required_colors[pos]
                            comps = REQUIRED_COLOR_COMPONENTS.get(req, frozenset())
                            if len(comps) == 1:
                                forced_color = next(iter(comps))

                        if forced_color is not None and pos not in forbidden:
                            lights[pos] = forced_color
                            decided.add(pos)
                            self._mark_fire_hazard(pr, pc, lights, decided)
                            changed = True
                            if not self._required_colors_feasible(lights):
                                return False

            # ---- Sanity: required-colour feasibility ----
            if not self._required_colors_feasible(lights):
                return False
            if not self._numbered_blocks_feasible(lights, decided):
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
        forbidden = self._compute_forbidden()

        # Seed state.
        lights: Dict[Tuple[int, int], str] = {}
        decided: Set[Tuple[int, int]] = set()

        # Apply propagation before any backtracking.
        if not self._propagate(lights, decided, forbidden):
            return []

        solutions: List[Dict[Tuple[int, int], str]] = []
        self._backtrack_propagate(lights, decided, forbidden, solutions)
        return solutions

    def _choose_cell(
        self,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
        forbidden: Set[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        """
        Pick the next undecided cell to branch on using a
        minimum-remaining-values (MRV) heuristic.

        Priority (ascending sort key → pick smallest):

        1. Required-colour cells that are not yet fully satisfied come first
           (they carry the most information).
        2. Among equal priority, prefer cells with fewer potential light
           sources in their sight lines (most-constrained-variable).
        """
        best: Optional[Tuple[int, int]] = None
        best_key: tuple = (10, 10**9)

        for r in range(self.rows):
            for c in range(self.cols):
                if self.is_block(r, c) or (r, c) in decided:
                    continue

                # Priority 0 = required-colour not yet satisfied, 1 = other.
                is_req = (r, c) in self.required_colors
                if is_req:
                    req_set = REQUIRED_COLOR_COMPONENTS.get(
                        self.required_colors[(r, c)], frozenset()
                    )
                    current = self.get_illumination_colors(r, c, lights)
                    priority = 0 if req_set - current else 1
                else:
                    priority = 1

                # Count undecided non-forbidden potential illumination sources.
                sources = 0
                if (r, c) not in forbidden:
                    sources += 1
                for dr, dc in DIRECTIONS:
                    nr, nc = r + dr, c + dc
                    while self.in_bounds(nr, nc) and not self.is_block(nr, nc):
                        if (nr, nc) not in decided and (nr, nc) not in forbidden:
                            sources += 1
                        nr += dr
                        nc += dc

                key = (priority, sources)
                if key < best_key:
                    best_key = key
                    best = (r, c)

        return best

    def _backtrack_propagate(
        self,
        lights: Dict[Tuple[int, int], str],
        decided: Set[Tuple[int, int]],
        forbidden: Set[Tuple[int, int]],
        solutions: List[Dict[Tuple[int, int], str]],
    ) -> None:
        """Backtracking search with propagation at every node."""
        cell = self._choose_cell(lights, decided, forbidden)

        if cell is None:
            # All cells decided — verify and record.
            if self._is_valid_solution(lights):
                solutions.append(dict(lights))
            return

        r, c = cell

        # ---- Option A: no light at (r, c) ----
        decided_a = set(decided)
        decided_a.add((r, c))
        lights_a = dict(lights)
        if (
            self._illumination_feasible_after_no_light(r, c, lights_a, decided_a)
            and self._propagate(lights_a, decided_a, forbidden)
        ):
            self._backtrack_propagate(lights_a, decided_a, forbidden, solutions)

        # ---- Options B–D: place a light at (r, c) ----
        if self.can_place_light(r, c, lights):
            for color in COLORS:
                lights_b = dict(lights)
                lights_b[(r, c)] = color
                decided_b = set(decided)
                decided_b.add((r, c))
                self._mark_fire_hazard(r, c, lights_b, decided_b)

                if (
                    self._required_colors_feasible(lights_b)
                    and self._propagate(lights_b, decided_b, forbidden)
                ):
                    self._backtrack_propagate(lights_b, decided_b, forbidden, solutions)

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
                if self.is_numbered_block(r, c):
                    row_str += f" {self.grid[r][c]} |"
                elif self.is_flammable(r, c):
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
        print("Legend: light=[R/G/B]  illuminated=(color)  block=###  flammable=F  numbered=[1-4]")
        if self.required_colors:
            fmt = {f"({r},{c})": v for (r, c), v in self.required_colors.items()}
            print(f"Required colours: {fmt}")
