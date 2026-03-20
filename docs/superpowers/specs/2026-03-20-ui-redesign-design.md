# Sudoku-qt UI Redesign

## Overview

Redesign the single-file Sudoku app to match the two-panel layout of sudoku.com, using Catppuccin Mocha theme for the UI chrome and a white grid interior. Split the codebase into a multi-file Python package.

## Layout

### Two-panel structure
- **Top bar:** Horizontal difficulty tabs (Leicht | Mittel | Schwer | Experte | Meister | Extrem). Greyed out during gameplay, active when no game or in "Neues Spiel" selection mode.
- **Left panel:** Custom-painted square Sudoku grid, right-aligned to sit close to the controls.
- **Right panel:** Stacked vertically - timer + pause, action buttons row, 3x3 number pad, "Neues Spiel" button.
- **Fluid scaling:** Both panels scale with window size. Grid stays square and centered vertically. The grid and controls are centered together as a unit in the window, with minimal gap (8px) between them.

### Difficulty tabs
- 6 levels: Leicht (36 clues), Mittel (30), Schwer (25), Experte (22), Meister (20), Extrem (17)
- Meister and Extrem are new - add to SudokuGenerator's clue targets. At 17-20 clues, generation may be slow due to uniqueness checking. If generation takes >5s on average, consider capping retries or relaxing uniqueness slightly, but try the current approach first.
- Selected tab: Blue (#89b4fa) with underline
- Inactive tabs: Subtext1 (#bac2de)
- Disabled during play: Overlay0 (#6c7086), no click response

## Features

### Notes/Pencil Mode
- Toggle button in action bar. Active state: Blue border with slight background tint.
- In notes mode, pressing 1-9 toggles small pencil marks in the selected cell.
- Notes displayed as 3x3 mini-grid of small numbers inside the cell, Overlay1 color (#7f849c).
- Placing a final number clears notes in that cell.
- Auto-cleanup: when a number is placed, that number is removed from notes in the same row, column, and 3x3 box.
- Keyboard shortcut: N to toggle.

### Hints
- 3 per game. Badge on button shows remaining count.
- Fills in the correct number for the currently selected cell.
- No-op (hint not consumed) if: no cell selected, cell is a given, cell already correctly filled.
- Button disabled (dimmed) when count reaches 0.

### Undo/Redo
- Two-stack implementation (same as current).
- Covers number placement, cell clearing, note changes, and hint placements.
- Undo stack entries must be extended to support different action types. Each entry is a dict with a `type` key: `"place"` (row, col, old_num, new_num, cleared_notes - dict of notes removed by auto-cleanup), `"note"` (row, col, num, was_added), `"hint"` (row, col, old_num, new_num, cleared_notes). This replaces the current tuple format.
- A number placement and its associated note auto-cleanup undo as one atomic action. The `cleared_notes` field stores all notes removed so they can be restored on undo.
- Keyboard shortcuts preserved: Ctrl+Z (undo), Ctrl+Y (redo).

### Timer
- Pause button stops timer, overlays grid with semi-transparent Crust (#11111b at ~80%).
- "Pausiert" text centered on overlay.
- Display format: MM:SS.

### "Neues Spiel" Flow
1. Click "Neues Spiel" - board greys out and locks, difficulty tabs become active, button text changes to "Fortsetzen".
2. Click a difficulty tab - confirmation dialog: "Neues Spiel starten? Aktueller Fortschritt geht verloren."
3. Confirm - generates new puzzle, tabs grey out, button back to "Neues Spiel".
4. Cancel or click "Fortsetzen" - board unlocks, tabs grey out, resume current game. The selected tab highlight returns to the current game's difficulty.

### Wrong Number Feedback
- Wrong player entries shown in red (#f38ba8) immediately, compared against solution.
- Placing a wrong number still triggers note auto-cleanup in row/col/box (same behavior as correct placement). The player chose to place the number; notes for that number are cleared regardless.

### Same-Number Highlighting
- When a cell is selected, all other cells containing the same number get a subtle highlight. The selected cell itself uses the selected-cell color (#e2ecf7), not the same-number highlight.

### Statistics
- "Statistik" button placed in the top bar, right-aligned (after the difficulty tabs).
- StatsDialog styled with Catppuccin colors (see Theme section). Same data as current: total games, best times per difficulty, sortable history table.

## Theme: Catppuccin Mocha

### Chrome (outside grid)
| Element | Color | Hex |
|---------|-------|-----|
| Window background | Base | #1e1e2e |
| Top bar background | Mantle | #181825 |
| Top bar border | Surface0 | #313244 |
| Primary accent | Blue | #89b4fa |
| Text | Text | #cdd6f4 |
| Labels / secondary text | Subtext0 | #a6adc8 |
| Inactive tabs | Subtext1 | #bac2de |
| Disabled elements | Overlay0 | #6c7086 |
| Number pad buttons | Surface0 bg | #313244 |
| Notes toggle (off) | Surface0 bg, Overlay0 text | #313244, #6c7086 |
| "Neues Spiel" button | Blue bg, Base text | #89b4fa, #1e1e2e |
| Action button borders | Blue | #89b4fa |
| Hint badge | Blue bg, Base text | #89b4fa, #1e1e2e |

### Grid (white interior)
| Element | Color | Hex |
|---------|-------|-----|
| Background | White | #ffffff |
| Box borders | Dark blue | #344861 |
| Cell borders | Light grey | #bec6d4 |
| Given numbers | Bold, dark | #344861 |
| Player numbers (correct) | Blue | #3b5998 |
| Player numbers (wrong) | Catppuccin Red | #f38ba8 |
| Selected cell highlight | Light blue | #e2ecf7 |
| Notes text | Overlay1 | #7f849c |

### Overlays
| State | Style |
|-------|-------|
| Pause | Crust (#11111b) at 80% opacity, "Pausiert" in Text color |
| Board locked (Neues Spiel) | Surface0 at ~60% opacity, slightly dimmer than pause |

### Stats Dialog
- Mantle (#181825) background
- Surface0 (#313244) table rows
- Text/Subtext for content

## File Structure

```
sudoku/
  __init__.py      - package marker
  main.py          - entry point, MainWindow, app setup
  generator.py     - SudokuGenerator (static methods), GeneratorThread
  game.py          - SudokuGame (board, notes, undo/redo, hints)
  board.py         - SudokuBoard(QWidget) - custom-painted grid
  controls.py      - ControlPanel(QWidget) - timer, actions, numpad, new game
  stats.py         - StatsManager, StatsDialog
  styles.py        - Catppuccin color constants, font sizes, dimensions
```

Entry point in pyproject.toml: `sudoku.main:main`

## Signals & Data Flow

```
ControlPanel -> MainWindow:
  number_clicked(int)
  clear_clicked()
  undo_clicked()
  redo_clicked()
  notes_toggled(bool)
  hint_clicked()
  new_game_clicked()
  pause_clicked()

SudokuBoard -> MainWindow:
  cell_selected(int, int)
  number_entered(int)
  clear_requested()

DifficultyBar -> MainWindow:
  difficulty_selected(str)
```

MainWindow is the sole coordinator. Board and ControlPanel never communicate directly. After any state change, MainWindow calls `board.update()` which triggers `paintEvent`. The board reads display state from the SudokuGame object.

**Selection state:** SudokuBoard owns `self.selected` (row, col) internally. It emits `cell_selected` to notify MainWindow so it can route number input to the right cell. The board handles selection highlighting and same-number highlighting in its own `paintEvent`.

**Removed:** `get_conflicts()` is dead code in the current app and is not carried forward. Wrong-number detection is purely solution-comparison.

## Out of Scope
- Dark-themed grid interior (grid stays white for readability)
- Mistakes counter / game-over-at-3
- Animations
- Sound effects
