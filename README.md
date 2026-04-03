# Akari — Coloured Lights Puzzle Solver

A Python solver that finds **all** valid arrangements of coloured lights for
any Akari (Light Up) grid.

---

## Puzzle rules

| Symbol | Meaning |
|--------|---------|
| `.`    | Empty cell — must be illuminated |
| `#`    | Opaque block — blocks light; no light may be placed here |
| `0`    | Flammable block — blocks light; no light may be placed in any orthogonally adjacent cell |

### Lights

There are three light colours: **R** (Red), **G** (Green), **B** (Blue).

Each light shines outward in all four orthogonal directions until it hits a
block or the edge of the grid.

### Colour mixing

When beams from two differently-coloured lights overlap on a cell, they mix:

| Combination | Result |
|-------------|--------|
| R + G | **Y** — Yellow |
| G + B | **C** — Cyan |
| B + R | **M** — Magenta |
| R + G + B | **W** — White |

### Constraints

1. **No fire hazards** — Two lights may never be in each other's unobstructed
   line of sight (same row or column segment with no block between them).
2. **Flammable blocks** — No light may be placed orthogonally adjacent to a `0`
   block.
3. **Full illumination** — Every non-block cell must be illuminated by at least
   one light.
4. **Required colours** — Certain cells are pre-marked with a colour
   (`R`, `G`, `B`, `Y`, `C`, `M`) that their illumination must exactly match.

---

## Project structure

```
akari/
├── solver.py          # Core back-tracking solver (AkariSolver class)
├── main.py            # Interactive CLI + built-in example puzzles
└── tests/
    └── test_solver.py # pytest unit tests (50 tests)
```

---

## Quick start

```bash
# Run the interactive CLI
python main.py

# Run the built-in examples directly
python -c "from main import run_example; run_example('1')"
python -c "from main import run_example; run_example('2')"
python -c "from main import run_example; run_example('3')"

# Run the tests
pytest tests/
```

---

## Using the solver programmatically

```python
from solver import AkariSolver

# 3×3 grid with a centre block
grid = [
    ['.', '.', '.'],
    ['.', '#', '.'],
    ['.', '.', '.'],
]

# Optional: require specific illumination colours at certain cells
required_colors = {
    (0, 0): 'R',   # top-left must be illuminated Red
    (2, 2): 'G',   # bottom-right must be illuminated Green
}

solver = AkariSolver(grid, required_colors)
solutions = solver.solve()

print(f"Found {len(solutions)} solution(s)")
for i, sol in enumerate(solutions, 1):
    solver.display_solution(sol, solution_num=i)
```

### Grid notation quick reference

```python
grid = [
    ['.', '.', '#', '.'],   # row 0 — '#' is an opaque block
    ['.', '0', '.', '.'],   # row 1 — '0' is a flammable block
    ['.', '.', '.', '.'],   # row 2
]
```

### Required colour values

| Value | Meaning |
|-------|---------|
| `'R'` | Red |
| `'G'` | Green |
| `'B'` | Blue |
| `'Y'` | Yellow (R + G) |
| `'C'` | Cyan (G + B) |
| `'M'` | Magenta (B + R) |
| `'W'` | White (R + G + B) |

---

## Interactive CLI walkthrough

```
$ python main.py
AKARI SOLVER
============
1. Solve a puzzle interactively
2. Run built-in examples

Choice (1/2): 1

Grid rows    (1–20): 3
Grid columns (1–20): 3

── Add blocks ─────────────────────────────────────────────
  '#'  opaque block    '0'  flammable block
  Format: row col type   (1-based, e.g. '2 3 #')
  Type 'done' when finished.
  block> 2 2 #
  block> done

── Set required illumination colours ───────────────────────
  Colours: R  G  B  Y (yellow)  C (cyan)  M (magenta)
  Format: row col colour   (e.g. '2 3 Y')
  Type 'done' when finished.
  colour> 1 1 R
  colour> done
```

---

## Algorithm

The solver uses **backtracking with constraint propagation**:

1. Candidate cells are enumerated in row-major order.
2. At each cell, the algorithm tries placing no light or a light of colour R,
   G, or B.
3. **Pruning rule A** — `can_place_light` rejects a placement immediately if
   the cell is a block, already holds a light, has an existing light in its
   line of sight, or is adjacent to a flammable block.
4. **Pruning rule B** — after every placement, `_required_colors_feasible`
   checks that no required-colour cell has already received an incompatible
   colour beam (one that can never be removed by adding more lights).
5. At the leaf node, `_is_valid_solution` verifies that every non-block cell is
   illuminated and every required-colour cell displays the correct colour.
