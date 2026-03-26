# Technique-Validated Generator Design

## Overview

Replace the clue-count-based puzzle generator with one that validates every removal against the solver's technique set. This ensures every cell in a generated puzzle is logically explainable using techniques allowed for that difficulty, and difficulty labels reflect actual solving complexity.

## Algorithm

1. Generate a full solved board (existing `_generate_full_board()` / `_fill_board()`)
2. Shuffle all 81 cells
3. For each cell, tentatively remove it (set to 0)
4. Attempt to fully solve the resulting puzzle using only techniques allowed for the difficulty tier
5. If solvable: keep the removal
6. If not: restore the clue
7. Continue until all 81 cells have been tried

Clue counts are emergent - no target numbers. Leicht puzzles naturally retain more clues (fewer techniques available for validation), Extrem puzzles retain fewer.

## Solver Changes

### New method: `solve_fully()`

Add to `SudokuSolver`:

```python
def solve_fully(self):
    """Repeatedly apply techniques until solved or stuck.
    Returns True if the board is completely solved."""
```

This chains `find_hint` calls (without `only_target`), applying each result to the board and recomputing candidates, until either the board is full or no technique can make progress.

The existing `find_hint(only_target=False)` already scans all cells - `solve_fully` just loops it.

### Board mutation for solve_fully

`solve_fully` needs to actually place numbers and recompute candidates after each step. Since the solver currently works read-only, `solve_fully` will mutate `self.board` and `self.candidates` internally. This is fine because the solver instance is created fresh for each generation attempt.

## Generator Changes

### `generator.py`

Replace the `generate()` method:

- Remove the `target_clues` dict
- Import `SudokuSolver` and `DIFFICULTY_TIER`, `TIER_TECHNIQUES`
- New logic: remove clues one at a time, validate with `SudokuSolver(puzzle, difficulty).solve_fully()`
- Uniqueness check stays (still need exactly one solution)

### Generation speed

Runs on existing `GeneratorThread` (off UI thread). Expected to be slower than current approach but acceptable (a few seconds). No timeout or fallback needed.

## Files Changed

| File | Action | Change |
|------|--------|--------|
| `sudoku/solver.py` | Modify | Add `solve_fully()` method |
| `sudoku/generator.py` | Modify | Replace `generate()` to use technique validation, remove `target_clues` |
