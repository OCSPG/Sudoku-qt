# Sudoku Qt App - Design Spec

## Overview

A desktop Sudoku game built with Python and PySide6. All UI text in German. Single-file architecture (`sudoku.py`). Stats persisted to `stats.json`.

## Scope

- 9x9 Sudoku grid, black on white
- 4 difficulty levels: Leicht, Mittel, Schwer, Experte
- Algorithmic puzzle generation with unique-solution validation
- Input via clickable number pad and keyboard
- Timer with pause functionality
- Undo/redo
- Conflict highlighting
- Stat tracker (date, difficulty, completion time)
- No pencil marks, no themes, no hints

## Architecture

Single file `sudoku.py` with these classes:

### SudokuGenerator

- Generates complete solved boards via backtracking with randomized candidate ordering
- Creates puzzles by removing cells one at a time in random order from a solved board
- After each removal, runs the solver to verify exactly one solution remains; if not, restores the cell and tries the next
- Clue counts by difficulty: Leicht ~36, Mittel ~30, Schwer ~25, Experte ~22
- Generation runs in a QThread to avoid freezing the UI
- All static/class methods (except the QThread wrapper)

### SudokuGame

- Holds game state: current board (9x9), solution, given cells (immutable), difficulty, timer state
- Move history as a stack of `(row, col, old_value, new_value)` tuples for undo/redo
- Clearing a cell is treated as a move with `new_value=0`, so it participates in undo/redo
- Undo stack and redo stack - making a new move clears the redo stack
- Conflict detection: checks row, column, and 3x3 box for duplicate numbers
- Methods: `place_number()`, `clear_cell()`, `undo()`, `redo()`, `is_complete()`, `get_conflicts()`

### SudokuBoard (QWidget)

- Custom-painted 9x9 grid using `QPainter` in `paintEvent`
- Visual style:
  - White background, black grid lines
  - Thicker lines (3px) for 3x3 box borders, thin lines (1px) for cell borders
  - Given numbers in black
  - Player-entered numbers in dark blue
  - Selected cell: light blue background highlight
  - Conflicting cells: red text color
- Interaction:
  - Click to select a cell (given cells are selectable but not editable)
  - Arrow keys to move selection
  - Keyboard 1-9 to enter a number (ignored on given cells)
  - Delete/Backspace to clear a cell
  - Number pad buttons use `setFocusPolicy(Qt.NoFocus)` so they don't steal keyboard focus from the grid
- Pause overlay: when paused, grid is covered with a painted overlay displaying "Pausiert"

### StatsManager

- Loads/saves completed games from/to `stats.json` (same directory as script)
- Each entry: `{"datum": "2026-03-16", "schwierigkeit": "Mittel", "zeit_sekunden": 342}`
- If `stats.json` is missing or corrupted, silently starts with an empty list
- Methods: `save_game()`, `load_stats()`, `get_best_times()`

### MainWindow (QMainWindow)

- **Window**: title "Sudoku", minimum size 500x600, reasonable default ~600x750
- **Toolbar** (top):
  - "Neues Spiel" button with dropdown menu: Leicht, Mittel, Schwer, Experte
  - Timer label (MM:SS format), shows "00:00" when no game is active
  - "Pause" / "Fortsetzen" toggle button
  - "Statistik" button
- **Central widget**: SudokuBoard
- **Bottom bar**: Number pad as a single horizontal row of buttons: 1-9, then "Löschen" (clear), "Rückgängig" (undo), "Wiederholen" (redo)
- **Initial state**: empty grid, bottom bar and pause button disabled until a game starts
- **Close behavior**: closing the window exits immediately, no confirmation

## Game Flow

1. App starts showing an empty board with the toolbar. Number pad, undo/redo, and pause are disabled.
2. Player clicks "Neues Spiel" and selects a difficulty
3. Puzzle generation runs in a background thread; toolbar shows "Generiere..." in the timer label
4. Timer starts automatically when the puzzle is ready
5. Number pad and controls become enabled
6. Player interacts via mouse clicks on number pad or keyboard input
7. "Pause" hides the grid behind an overlay and stops the timer; "Fortsetzen" resumes
8. Conflicts are highlighted in real-time as numbers are placed
9. When the board is complete and correct:
   - Timer stops
   - Congratulations dialog: "Gelöst in MM:SS!"
   - Game is saved to stats
   - Controls return to disabled state
10. Starting a new game while one is in progress shows confirmation: "Aktuelles Spiel abbrechen?"

## Stats Dialog

- Opened via "Statistik" button
- QDialog with a QTableWidget and a "Schließen" button
- Columns: Datum, Schwierigkeit, Zeit (formatted MM:SS)
- Sorted newest first
- Summary at top: total games played, best time per difficulty

## Technical Details

- Python 3, PySide6
- Virtual environment (uv)
- `stats.json` stored next to `sudoku.py`
- No external dependencies beyond PySide6
- MIT license
