# Hint Explanations Design

## Overview

Replace the current "reveal answer" hint system with technique-based solving that explains WHY a number belongs in a cell. The board shows a visual overlay highlighting evidence cells and a text explanation before placing the number.

## Solver Module (`sudoku/solver.py`)

New standalone module implementing Sudoku solving techniques.

### HintResult

```python
@dataclass
class HintResult:
    cell: tuple[int, int]        # (row, col) being solved
    value: int                   # the number that goes there
    technique: str               # e.g. "Naked Single"
    explanation: str             # human-readable German text
    highlight_cells: list[tuple] # cells to highlight as "evidence"
```

### Techniques by Difficulty Tier

| Tier | Techniques | Difficulty Levels |
|------|-----------|-------------------|
| Basic | Naked Single, Hidden Single | Leicht, Mittel |
| Intermediate | Naked Pair/Triple, Pointing Pair, Box/Line Reduction | Schwer, Experte |
| Advanced | X-Wing, Swordfish, XY-Wing | Meister, Extrem |

### Solving Flow

1. Compute candidates for all empty cells from current board state
2. Apply techniques in order from simplest to most complex
3. Stop at the first technique that resolves a cell

### Hint Target Selection

When a hint is requested for a specific cell:

1. Try to solve the selected cell using techniques up to the game's difficulty tier
2. If that fails, search all empty cells for one that CAN be explained
3. If nothing is explainable, fall back to the pre-computed solution with a generic message: "Die Lösung zeigt, dass hier eine [X] hingehört."

When the solver finds an explainable cell different from the selected one, the hint targets that cell instead. The overlay and board selection move to the new cell.

The fallback (no explainable cell found) uses the originally selected cell.

### Error Handling

If the player has placed wrong numbers, the solver works on the current (possibly invalid) board state. If conflicts prevent finding any solution, the system falls back to the pre-computed solution.

## Board Overlay

When a hint is used, the board enters overlay mode instead of immediately placing the number.

### Visual Elements

1. **Dim layer** - all cells not involved in the explanation get a semi-transparent dark overlay (similar to existing pause overlay)
2. **Evidence cells** - cells that eliminate candidates, tinted with a soft red/coral highlight (~20% opacity, based on existing RED palette color)
3. **Target cell** - the cell receiving the hint, tinted with a soft green highlight (~25% opacity, Catppuccin Green #a6e3a1)
4. **Text bar** - rounded rectangle below the grid with the explanation text in German. SURFACE0 background, TEXT color.
5. **"Verstanden" button** - right-aligned in the text bar. Styled like the "Neues Spiel" button (BLUE background, rounded).

### Interaction

- While overlay is active: all input is blocked (no cell selection, no number entry, no other actions)
- Only the "Verstanden" button is interactive
- Clicking "Verstanden" dismisses the overlay and places the number

## Game Logic Changes

### `game.py`

Split `use_hint()` into two phases:

- `prepare_hint(row, col)` - calls the solver, returns a `HintResult` (or fallback). Does NOT place the number or consume the hint.
- `confirm_hint(hint_result)` - places the number, decrements `hints_remaining`, pushes to undo stack. Called when "Verstanden" is clicked.

The undo stack entry gains an optional `"technique"` field. Undo/redo behavior stays identical to current implementation.

### `board.py`

- New `overlay` attribute (`HintResult` or `None`)
- When `overlay` is set, `paintEvent` draws the overlay visuals
- New signal `hint_confirmed` emitted when "Verstanden" is clicked
- Input events (mouse, keyboard) are blocked while overlay is active

### `main.py`

`on_hint()` flow becomes:

1. Call `game.prepare_hint(r, c)`
2. If result returned, set `board.overlay = result`
3. On `hint_confirmed` signal: call `game.confirm_hint(result)`, clear overlay, update hint badge, check completion

### `controls.py`

No changes. The hint button still emits `hint_clicked`.

### `styles.py`

Add three new colors:

- `HINT_TARGET` - green highlight for the target cell (Catppuccin Green at ~25% opacity)
- `HINT_EVIDENCE` - red/coral highlight for evidence cells (existing RED at ~20% opacity)
- `HINT_DIM` - dim overlay for uninvolved cells

## Explanation Text Examples

- **Naked Single:** "Zeile 3 enthält bereits 1,2,4,5,7,8,9 und Spalte 5 enthält 3 - nur 6 ist hier möglich."
- **Hidden Single:** "6 kann in Block 5 nur in dieses Feld - alle anderen Positionen sind blockiert."
- **Naked Pair:** "Die Felder R1C2 und R1C7 können nur 3 oder 7 enthalten, daher kann 5 hier nicht stehen - es bleibt nur 9."
- **Fallback:** "Die Lösung zeigt, dass hier eine 6 hingehört."
