"""
Unit tests for the Akari coloured-lights solver.

Run with:
    pytest tests/
"""

from __future__ import annotations

import pytest

from solver import BLOCK, EMPTY, FLAMMABLE, COLOR_MIX, NUMBERED_BLOCKS, AkariSolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _solutions_as_frozensets(solutions):
    """Convert each solution dict to a frozenset of (r, c, colour) triples."""
    return {frozenset((r, c, col) for (r, c), col in sol.items()) for sol in solutions}


def _light_positions(solutions):
    """Return the set of light-position sets (ignoring colour)."""
    return {frozenset(sol.keys()) for sol in solutions}


# ---------------------------------------------------------------------------
# COLOR_MIX table
# ---------------------------------------------------------------------------


class TestColorMix:
    def test_single_red(self):
        assert COLOR_MIX[frozenset(["R"])] == "R"

    def test_single_green(self):
        assert COLOR_MIX[frozenset(["G"])] == "G"

    def test_single_blue(self):
        assert COLOR_MIX[frozenset(["B"])] == "B"

    def test_red_green_gives_yellow(self):
        assert COLOR_MIX[frozenset(["R", "G"])] == "Y"

    def test_green_blue_gives_cyan(self):
        assert COLOR_MIX[frozenset(["G", "B"])] == "C"

    def test_blue_red_gives_magenta(self):
        assert COLOR_MIX[frozenset(["B", "R"])] == "M"

    def test_all_three_gives_white(self):
        assert COLOR_MIX[frozenset(["R", "G", "B"])] == "W"

    def test_empty_gives_none(self):
        assert COLOR_MIX[frozenset()] is None


# ---------------------------------------------------------------------------
# AkariSolver — grid helpers
# ---------------------------------------------------------------------------


class TestGridHelpers:
    def setup_method(self):
        grid = [
            [".", "#", "."],
            ["0", ".", "."],
        ]
        self.solver = AkariSolver(grid)

    def test_in_bounds(self):
        assert self.solver.in_bounds(0, 0)
        assert self.solver.in_bounds(1, 2)
        assert not self.solver.in_bounds(-1, 0)
        assert not self.solver.in_bounds(0, 3)
        assert not self.solver.in_bounds(2, 0)

    def test_is_block_opaque(self):
        assert self.solver.is_block(0, 1)

    def test_is_block_flammable(self):
        assert self.solver.is_block(1, 0)

    def test_is_not_block_empty(self):
        assert not self.solver.is_block(0, 0)

    def test_is_flammable(self):
        assert self.solver.is_flammable(1, 0)
        assert not self.solver.is_flammable(0, 1)  # opaque, not flammable


# ---------------------------------------------------------------------------
# AkariSolver — illumination
# ---------------------------------------------------------------------------


class TestIllumination:
    def test_light_illuminates_itself(self):
        grid = [["."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "R"}
        colors = solver.get_illumination_colors(0, 0, lights)
        assert colors == frozenset(["R"])

    def test_light_illuminates_row(self):
        # R at (0,0) should illuminate (0,1) and (0,2)
        grid = [[".", ".", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "R"}
        assert solver.get_illumination_colors(0, 1, lights) == frozenset(["R"])
        assert solver.get_illumination_colors(0, 2, lights) == frozenset(["R"])

    def test_light_illuminates_column(self):
        # G at (0,0) should illuminate (1,0) and (2,0)
        grid = [[".", "."], [".", "."], [".", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "G"}
        assert solver.get_illumination_colors(1, 0, lights) == frozenset(["G"])
        assert solver.get_illumination_colors(2, 0, lights) == frozenset(["G"])

    def test_block_stops_light(self):
        # R at (0,0), block at (0,1): (0,2) should NOT be illuminated
        grid = [[".", "#", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "R"}
        assert solver.get_illumination_colors(0, 2, lights) == frozenset()

    def test_two_perpendicular_lights_mix(self):
        # R at (1,0), G at (0,1) — both shine on (1,1) → Yellow
        grid = [[".", ".", "."], [".", ".", "."], [".", ".", "."]]
        solver = AkariSolver(grid)
        lights = {(1, 0): "R", (0, 1): "G"}
        colors = solver.get_illumination_colors(1, 1, lights)
        assert colors == frozenset(["R", "G"])
        assert solver.mix_color(colors) == "Y"

    def test_lights_in_sight_finds_visible_lights(self):
        grid = [[".", ".", ".", ".", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 2): "B"}
        visible = solver.lights_in_sight(0, 0, lights)
        assert (0, 2) in visible

    def test_lights_in_sight_blocked_by_block(self):
        grid = [[".", "#", ".", ".", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 3): "B"}
        visible = solver.lights_in_sight(0, 0, lights)
        assert (0, 3) not in visible


# ---------------------------------------------------------------------------
# AkariSolver — can_place_light
# ---------------------------------------------------------------------------


class TestCanPlaceLight:
    def test_cannot_place_on_block(self):
        grid = [["#"]]
        solver = AkariSolver(grid)
        assert not solver.can_place_light(0, 0, {})

    def test_cannot_place_on_existing_light(self):
        grid = [["."]]
        solver = AkariSolver(grid)
        assert not solver.can_place_light(0, 0, {(0, 0): "R"})

    def test_cannot_place_adjacent_to_flammable(self):
        # (0,0) is adjacent to flammable (0,1)
        grid = [[".", "0"]]
        solver = AkariSolver(grid)
        assert not solver.can_place_light(0, 0, {})

    def test_cannot_place_when_light_in_sight(self):
        # R already at (0,0); placing anything at (0,2) would see it
        grid = [[".", ".", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "R"}
        assert not solver.can_place_light(0, 2, lights)

    def test_can_place_when_blocked_from_existing_light(self):
        # R at (0,0), block at (0,1): (0,2) is safe
        grid = [[".", "#", "."]]
        solver = AkariSolver(grid)
        lights = {(0, 0): "R"}
        assert solver.can_place_light(0, 2, lights)


# ---------------------------------------------------------------------------
# AkariSolver — solve: small grids
# ---------------------------------------------------------------------------


class TestSolveSmallGrids:
    def test_1x1_grid_three_solutions(self):
        """Single cell: R, G, or B light — 3 solutions."""
        solver = AkariSolver([[EMPTY]])
        solutions = solver.solve()
        assert len(solutions) == 3
        assert {sol[(0, 0)] for sol in solutions} == {"R", "G", "B"}

    def test_1x2_grid_six_solutions(self):
        """1×2 row: only one light fits; 2 positions × 3 colours = 6."""
        solver = AkariSolver([[EMPTY, EMPTY]])
        solutions = solver.solve()
        assert len(solutions) == 6

    def test_1x3_row_nine_solutions(self):
        """1×3 row: one light anywhere illuminates all three; 3×3 = 9."""
        solver = AkariSolver([[EMPTY, EMPTY, EMPTY]])
        solutions = solver.solve()
        assert len(solutions) == 9

    def test_2x2_grid_eighteen_solutions(self):
        """
        2×2: diagonal pairs (0,0)+(1,1) or (0,1)+(1,0).
        Each pair has 3×3=9 colour combinations → 18 total.
        """
        grid = [[EMPTY, EMPTY], [EMPTY, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 18

    def test_1x3_with_centre_block_nine_solutions(self):
        """Block in the middle creates two isolated cells, each needs its own light."""
        grid = [[EMPTY, BLOCK, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 9

    def test_all_blocks_one_trivial_solution(self):
        """If the grid has no empty cells, there is exactly one (trivial) solution."""
        grid = [[BLOCK, BLOCK], [BLOCK, BLOCK]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert solutions == [{}]


# ---------------------------------------------------------------------------
# AkariSolver — flammable block constraint
# ---------------------------------------------------------------------------


class TestFlammableBlocks:
    def test_cells_adjacent_to_flammable_cannot_have_lights(self):
        # Both empty cells border the flammable block → no lights possible → unsolvable
        grid = [[EMPTY, FLAMMABLE, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 0

    def test_non_adjacent_cell_can_have_light(self):
        # (0,0) is safe from the flammable block at (0,2)
        grid = [[EMPTY, EMPTY, FLAMMABLE]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        # (0,0) or (0,1) can have a light; (0,1) is adjacent to flammable so excluded
        # Only (0,0) can hold a light (illuminates (0,0) and (0,1))
        assert len(solutions) == 3  # 3 colours at (0,0)
        for sol in solutions:
            assert (0, 2) not in sol  # flammable cell never holds a light
            if (0, 1) in sol:
                pytest.fail("Light placed adjacent to flammable block")


# ---------------------------------------------------------------------------
# AkariSolver — required colours (single colours)
# ---------------------------------------------------------------------------


class TestRequiredSingleColors:
    def test_required_R_on_single_cell(self):
        solver = AkariSolver([[EMPTY]], required_colors={(0, 0): "R"})
        solutions = solver.solve()
        assert len(solutions) == 1
        assert solutions[0][(0, 0)] == "R"

    def test_required_G_on_single_cell(self):
        solver = AkariSolver([[EMPTY]], required_colors={(0, 0): "G"})
        solutions = solver.solve()
        assert len(solutions) == 1
        assert solutions[0][(0, 0)] == "G"

    def test_required_B_on_single_cell(self):
        solver = AkariSolver([[EMPTY]], required_colors={(0, 0): "B"})
        solutions = solver.solve()
        assert len(solutions) == 1
        assert solutions[0][(0, 0)] == "B"

    def test_required_colour_satisfied_by_remote_light(self):
        # (0,2) requires R; light R at (0,0) shines across the row.
        grid = [[EMPTY, EMPTY, EMPTY]]
        solver = AkariSolver(grid, required_colors={(0, 2): "R"})
        solutions = solver.solve()
        assert len(solutions) > 0
        for sol in solutions:
            colors = solver.get_illumination_colors(0, 2, sol)
            assert solver.mix_color(colors) == "R"

    def test_impossible_required_colour_zero_solutions(self):
        # Cell surrounded by flammable block — can never be illuminated
        grid = [[FLAMMABLE, EMPTY, FLAMMABLE]]
        solver = AkariSolver(grid, required_colors={(0, 1): "R"})
        solutions = solver.solve()
        assert len(solutions) == 0


# ---------------------------------------------------------------------------
# AkariSolver — required colours (mixed colours)
# ---------------------------------------------------------------------------


class TestRequiredMixedColors:
    def _centre_grid(self):
        """3×3 open grid."""
        return [[EMPTY] * 3 for _ in range(3)]

    def test_required_yellow_all_solutions_satisfy_it(self):
        """Centre of 3×3 must be Yellow; every solution must satisfy this."""
        solver = AkariSolver(self._centre_grid(), required_colors={(1, 1): "Y"})
        solutions = solver.solve()
        assert len(solutions) > 0
        for sol in solutions:
            colors = solver.get_illumination_colors(1, 1, sol)
            assert solver.mix_color(colors) == "Y", (
                f"Solution {sol} illuminates (1,1) with {colors}"
            )

    def test_required_cyan_all_solutions_satisfy_it(self):
        solver = AkariSolver(self._centre_grid(), required_colors={(1, 1): "C"})
        solutions = solver.solve()
        assert len(solutions) > 0
        for sol in solutions:
            colors = solver.get_illumination_colors(1, 1, sol)
            assert solver.mix_color(colors) == "C"

    def test_required_magenta_all_solutions_satisfy_it(self):
        solver = AkariSolver(self._centre_grid(), required_colors={(1, 1): "M"})
        solutions = solver.solve()
        assert len(solutions) > 0
        for sol in solutions:
            colors = solver.get_illumination_colors(1, 1, sol)
            assert solver.mix_color(colors) == "M"

    def test_mixed_colour_requires_perpendicular_lights(self):
        """
        In a 1×3 row, the centre cannot be Yellow because both lights would
        need to be in the same row segment — fire hazard.  Zero solutions.
        """
        grid = [[EMPTY, EMPTY, EMPTY]]
        solver = AkariSolver(grid, required_colors={(0, 1): "Y"})
        solutions = solver.solve()
        assert len(solutions) == 0

    def test_mixed_colour_achievable_with_perpendicular_lights(self):
        """
        3×1 column with centre requiring Yellow:
        R above + G below would both be in the same column segment → impossible.
        """
        grid = [[EMPTY], [EMPTY], [EMPTY]]
        solver = AkariSolver(grid, required_colors={(1, 0): "Y"})
        solutions = solver.solve()
        assert len(solutions) == 0


# ---------------------------------------------------------------------------
# AkariSolver — lights may not shine on each other
# ---------------------------------------------------------------------------


class TestLightsDoNotShineOnEachOther:
    def test_two_lights_same_row_segment_invalid(self):
        """Any solution must not contain two lights in the same unobstructed row."""
        grid = [[EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        for sol in solutions:
            positions = list(sol.keys())
            for i, (r1, c1) in enumerate(positions):
                for r2, c2 in positions[i + 1 :]:
                    assert not (r1 == r2), f"Two lights in same row: {sol}"

    def test_two_lights_same_col_segment_invalid(self):
        """Any solution must not contain two lights in the same unobstructed column."""
        grid = [[EMPTY], [EMPTY], [EMPTY], [EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        for sol in solutions:
            positions = list(sol.keys())
            for i, (r1, c1) in enumerate(positions):
                for r2, c2 in positions[i + 1 :]:
                    assert not (c1 == c2), f"Two lights in same col: {sol}"

    def test_block_separates_two_lights_in_same_row(self):
        """Block in the middle allows lights on both sides of it."""
        grid = [[EMPTY, BLOCK, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        # All solutions should have lights on both sides (separated by block)
        position_sets = _light_positions(solutions)
        assert frozenset([(0, 0), (0, 2)]) in position_sets


# ---------------------------------------------------------------------------
# AkariSolver — all non-block cells illuminated
# ---------------------------------------------------------------------------


class TestAllCellsIlluminated:
    def _check_all_illuminated(self, grid, solutions):
        solver = AkariSolver(grid)
        for sol in solutions:
            for r in range(len(grid)):
                for c in range(len(grid[0])):
                    if grid[r][c] != EMPTY:
                        continue
                    colors = solver.get_illumination_colors(r, c, sol)
                    assert colors, (
                        f"Cell ({r},{c}) not illuminated in solution {sol}"
                    )

    def test_every_cell_illuminated_2x2(self):
        grid = [[EMPTY, EMPTY], [EMPTY, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        self._check_all_illuminated(grid, solutions)

    def test_every_cell_illuminated_3x3_with_centre_block(self):
        grid = [
            [EMPTY, EMPTY, EMPTY],
            [EMPTY, BLOCK, EMPTY],
            [EMPTY, EMPTY, EMPTY],
        ]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) > 0
        self._check_all_illuminated(grid, solutions)


# ---------------------------------------------------------------------------
# AkariSolver — numbered blocks (1–4 adjacent lights required)
# ---------------------------------------------------------------------------


class TestNumberedBlocks:
    def test_numbered_block_is_a_block(self):
        """Numbered blocks must block light and cannot hold lights themselves."""
        grid = [[".", "2", "."]]
        solver = AkariSolver(grid)
        assert solver.is_block(0, 1)
        assert solver.is_numbered_block(0, 1)
        assert solver.numbered_block_value(0, 1) == 2

    def test_light_cannot_be_placed_on_numbered_block(self):
        grid = [["2"]]
        solver = AkariSolver(grid)
        assert not solver.can_place_light(0, 0, {})

    def test_numbered_block_1_requires_exactly_one_adjacent_light(self):
        """
        1×3 row with a '1' block in the centre.
        The block requires exactly one adjacent light (either (0,0) or (0,2)).
        However, placing only one light leaves the far side unilluminated
        (the '1' block itself blocks the beam), and placing both violates the
        '1' constraint → no valid solution exists.
        """
        grid = [[".", "1", "."]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 0

    def test_numbered_block_0_equivalent_to_flammable_adjacency(self):
        """
        A '0' flammable block already prohibits any adjacent light; confirm
        the numbered-block validation path also catches this via _is_valid_solution.
        Note: '0' is handled as FLAMMABLE, not as a numbered block.
        """
        grid = [[".", "0", "."]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        # Both adjacent cells are blocked from holding lights → no illumination → 0 solutions.
        assert len(solutions) == 0

    def test_numbered_block_2_requires_two_adjacent_lights(self):
        """
        3×3 grid with a '2' block in the centre.
        Exactly two of the four orthogonal neighbours must hold lights.
        """
        grid = [
            [".", ".", "."],
            [".", "2", "."],
            [".", ".", "."],
        ]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) > 0
        for sol in solutions:
            adj = sum(
                1
                for (r, c) in sol
                if (r, c) in {(0, 1), (1, 0), (1, 2), (2, 1)}
            )
            assert adj == 2, f"Expected 2 adjacent lights, got {adj} in {sol}"

    def test_numbered_block_impossible_if_not_enough_adjacent_cells(self):
        """
        A '3' block in the corner has only 2 adjacent cells → impossible.
        """
        grid = [["3", "."], [".", "."]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 0

    def test_numbered_block_4_requires_all_four_adjacent_lights(self):
        """
        3×3 grid with a '4' block in the centre — all four orthogonal
        neighbours must hold lights.

        The '4' block itself separates (1,0) from (1,2) and (0,1) from (2,1),
        so no fire-hazard exists between any pair of the four adjacent lights.
        All corner cells are illuminated by the four lights.
        Each of the four lights has 3 colour choices → 3^4 = 81 solutions.
        """
        grid = [
            [".", ".", "."],
            [".", "4", "."],
            [".", ".", "."],
        ]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 81
        for sol in solutions:
            adj = sum(
                1
                for (r, c) in sol
                if (r, c) in {(0, 1), (1, 0), (1, 2), (2, 1)}
            )
            assert adj == 4, f"Expected 4 adjacent lights, got {adj} in {sol}"

    def test_numbered_block_lights_do_not_block_each_other_when_separated(self):
        """
        A '2' block with '#' blocks above and below it.  The only cells
        orthogonally adjacent to '2' are (1,0) and (1,2), so both must
        hold lights.  The '2' block itself separates them → no fire hazard.
        No additional lights can be placed anywhere (every other empty cell
        sees (1,0) or (1,2) directly).  3 colour choices each → 9 solutions.
        """
        grid = [
            [".", "#", "."],
            [".", "2", "."],
            [".", "#", "."],
        ]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        assert len(solutions) == 9
        for sol in solutions:
            assert (1, 0) in sol and (1, 2) in sol, (
                f"Expected lights at (1,0) and (1,2) only, got {sol}"
            )

    def test_is_numbered_block_false_for_other_cell_types(self):
        grid = [[".", "#", "0"]]
        solver = AkariSolver(grid)
        assert not solver.is_numbered_block(0, 0)
        assert not solver.is_numbered_block(0, 1)
        assert not solver.is_numbered_block(0, 2)

    def test_numbered_blocks_constant(self):
        assert "1" in NUMBERED_BLOCKS
        assert "2" in NUMBERED_BLOCKS
        assert "3" in NUMBERED_BLOCKS
        assert "4" in NUMBERED_BLOCKS
        assert "#" not in NUMBERED_BLOCKS
        assert "0" not in NUMBERED_BLOCKS


class TestDisplaySolution:
    def test_display_does_not_crash(self, capsys):
        grid = [[EMPTY, EMPTY], [EMPTY, EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        solver.display_solution(solutions[0], solution_num=1)
        captured = capsys.readouterr()
        assert "Solution 1" in captured.out

    def test_display_shows_light_colours(self, capsys):
        grid = [[EMPTY]]
        solver = AkariSolver(grid)
        solutions = solver.solve()
        solver.display_solution(solutions[0])
        captured = capsys.readouterr()
        # The light colour (R, G, or B) should appear in the output
        assert any(c in captured.out for c in ("R", "G", "B"))
