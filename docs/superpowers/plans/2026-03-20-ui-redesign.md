# Sudoku-qt UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the single-file Sudoku app into a multi-file package with a sudoku.com-inspired two-panel layout, Catppuccin Mocha theme, notes mode, and hints.

**Architecture:** Split `sudoku.py` into a `sudoku/` package with 8 modules. The left panel is a custom-painted QWidget grid, the right panel is a QWidget with timer, action buttons, 3x3 number pad, and new game button. MainWindow coordinates all communication via Qt signals.

**Tech Stack:** Python 3.13, PySide6 6.10+, uv

**Spec:** `docs/superpowers/specs/2026-03-20-ui-redesign-design.md`

**Current source:** `sudoku.py` (610 lines, single file)

---

### Task 1: Create package structure and styles module

**Files:**
- Create: `sudoku/__init__.py`
- Create: `sudoku/styles.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p sudoku
```

- [ ] **Step 2: Create `sudoku/__init__.py`**

```python
# sudoku package
```

- [ ] **Step 3: Create `sudoku/styles.py`**

All color constants, font helpers, and dimension constants used across the app. Reference: spec Theme section.

```python
from PySide6.QtGui import QColor


# --- Catppuccin Mocha palette ---
BASE = QColor("#1e1e2e")
MANTLE = QColor("#181825")
CRUST = QColor("#11111b")
SURFACE0 = QColor("#313244")
SURFACE1 = QColor("#45475a")
SURFACE2 = QColor("#585b70")
OVERLAY0 = QColor("#6c7086")
OVERLAY1 = QColor("#7f849c")
TEXT = QColor("#cdd6f4")
SUBTEXT0 = QColor("#a6adc8")
SUBTEXT1 = QColor("#bac2de")
BLUE = QColor("#89b4fa")
RED = QColor("#f38ba8")
LAVENDER = QColor("#b4befe")

# --- Grid colors (white interior) ---
GRID_BG = QColor("#ffffff")
GRID_BOX_BORDER = QColor("#344861")
GRID_CELL_BORDER = QColor("#bec6d4")
GIVEN_NUMBER = QColor("#344861")
PLAYER_CORRECT = QColor("#3b5998")
PLAYER_WRONG = QColor("#f38ba8")
SELECTED_CELL = QColor("#e2ecf7")
SAME_NUMBER_HIGHLIGHT = QColor("#d4e4f7")
NOTES_COLOR = QColor("#7f849c")

# --- Overlay colors ---
PAUSE_OVERLAY = QColor(17, 17, 27, 204)  # Crust at 80%
LOCK_OVERLAY = QColor(49, 50, 68, 153)  # Surface0 at 60%

# --- Dimensions ---
GRID_CONTROLS_GAP = 8
CONTROL_PANEL_RATIO = 0.35  # right panel width as fraction of available
ACTION_BUTTON_SIZE = 40
NUMPAD_GAP = 6

# --- Difficulty levels ---
DIFFICULTIES = ["Leicht", "Mittel", "Schwer", "Experte", "Meister", "Extrem"]
```

- [ ] **Step 4: Update `pyproject.toml` entry point**

Change the entry point from `sudoku:main` to `sudoku.main:main`:

```toml
[project.scripts]
sudoku = "sudoku.main:main"
```

- [ ] **Step 5: Verify package structure**

```bash
ls sudoku/
# Expected: __init__.py  styles.py
python -c "from sudoku.styles import BASE; print(BASE.name())"
```

- [ ] **Step 6: Commit**

```bash
git add sudoku/__init__.py sudoku/styles.py pyproject.toml
git commit -m "feat: create sudoku package with styles module

Catppuccin Mocha color constants, grid colors, overlay colors,
and dimension constants."
```

---

### Task 2: Extract generator module

**Files:**
- Create: `sudoku/generator.py`

Extract `SudokuGenerator` and `GeneratorThread` from `sudoku.py`. Add the two new difficulty levels (Meister, Extrem).

- [ ] **Step 1: Create `sudoku/generator.py`**

Copy `SudokuGenerator` and `GeneratorThread` classes from `sudoku.py` (lines 16-348). Add the new difficulty levels to the `generate()` method:

```python
import random
from PySide6.QtCore import QThread, Signal


class SudokuGenerator:
	# ... (copy _solve_count, _is_valid, _generate_full_board, _fill_board exactly as-is)

	@staticmethod
	def generate(difficulty):
		"""Generate a puzzle. Returns (puzzle, solution) where puzzle has 0s for empty cells."""
		target_clues = {
			"Leicht": 36,
			"Mittel": 30,
			"Schwer": 25,
			"Experte": 22,
			"Meister": 20,
			"Extrem": 17,
		}
		target = target_clues[difficulty]
		# ... rest same as current
```

The only change vs the original is adding `"Meister": 20` and `"Extrem": 17` to `target_clues`.

- [ ] **Step 2: Create `GeneratorThread` in same file**

```python
class GeneratorThread(QThread):
	finished = Signal(list, list)  # puzzle, solution

	def __init__(self, difficulty):
		super().__init__()
		self.difficulty = difficulty

	def run(self):
		puzzle, solution = SudokuGenerator.generate(self.difficulty)
		self.finished.emit(puzzle, solution)
```

- [ ] **Step 3: Verify import works**

```bash
python -c "from sudoku.generator import SudokuGenerator; p, s = SudokuGenerator.generate('Meister'); print(f'Clues: {sum(c != 0 for row in p for c in row)}')"
```

- [ ] **Step 4: Commit**

```bash
git add sudoku/generator.py
git commit -m "feat: extract generator module with Meister/Extrem difficulties"
```

---

### Task 3: Rewrite game state module with notes and hints

**Files:**
- Create: `sudoku/game.py`

This is a rewrite of `SudokuGame` with new features: notes dict, hint support, and extended undo/redo with dict entries. Drop `get_conflicts()`.

- [ ] **Step 1: Create `sudoku/game.py`**

```python
class SudokuGame:
	HINTS_PER_GAME = 3

	def __init__(self, puzzle, solution, difficulty):
		self.board = [row[:] for row in puzzle]
		self.solution = solution
		self.given = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
		self.difficulty = difficulty
		self.undo_stack = []
		self.redo_stack = []
		self.elapsed_seconds = 0
		self.paused = False
		# new: notes and hints
		self.notes = [[set() for _ in range(9)] for _ in range(9)]
		self.hints_remaining = self.HINTS_PER_GAME

	def _clear_notes_for_placement(self, row, col, num):
		"""Remove num from notes in same row, col, and box. Returns dict of cleared notes for undo.
		Each key is (row, col), value is a set of cleared note numbers."""
		cleared = {}
		# clear the placed cell's own notes first
		if self.notes[row][col]:
			cleared[(row, col)] = set(self.notes[row][col])
			self.notes[row][col].clear()
		# row
		for c in range(9):
			if num in self.notes[row][c]:
				self.notes[row][c].discard(num)
				cleared.setdefault((row, c), set()).add(num)
		# col
		for r in range(9):
			if num in self.notes[r][col]:
				self.notes[r][col].discard(num)
				cleared.setdefault((r, col), set()).add(num)
		# box
		box_r, box_c = 3 * (row // 3), 3 * (col // 3)
		for r in range(box_r, box_r + 3):
			for c in range(box_c, box_c + 3):
				if num in self.notes[r][c]:
					self.notes[r][c].discard(num)
					cleared.setdefault((r, c), set()).add(num)
		return cleared

	def place_number(self, row, col, num):
		"""Place a number. Returns False if cell is given or same number."""
		if self.given[row][col]:
			return False
		old = self.board[row][col]
		if old == num:
			return False
		self.board[row][col] = num
		cleared_notes = self._clear_notes_for_placement(row, col, num)
		self.undo_stack.append({
			"type": "place",
			"row": row,
			"col": col,
			"old_num": old,
			"new_num": num,
			"cleared_notes": cleared_notes,
		})
		self.redo_stack.clear()
		return True

	def clear_cell(self, row, col):
		"""Clear a cell. Returns False if given or already empty."""
		if self.given[row][col]:
			return False
		old = self.board[row][col]
		if old == 0:
			return False
		self.board[row][col] = 0
		self.undo_stack.append({
			"type": "place",
			"row": row,
			"col": col,
			"old_num": old,
			"new_num": 0,
			"cleared_notes": {},
		})
		self.redo_stack.clear()
		return True

	def toggle_note(self, row, col, num):
		"""Toggle a pencil mark. Returns False if cell is given or has a number."""
		if self.given[row][col] or self.board[row][col] != 0:
			return False
		was_added = num not in self.notes[row][col]
		if was_added:
			self.notes[row][col].add(num)
		else:
			self.notes[row][col].discard(num)
		self.undo_stack.append({
			"type": "note",
			"row": row,
			"col": col,
			"num": num,
			"was_added": was_added,
		})
		self.redo_stack.clear()
		return True

	def use_hint(self, row, col):
		"""Use a hint on the given cell. Returns False if hint can't be used."""
		if self.hints_remaining <= 0:
			return False
		if self.given[row][col]:
			return False
		correct = self.solution[row][col]
		if self.board[row][col] == correct:
			return False
		old = self.board[row][col]
		self.board[row][col] = correct
		cleared_notes = self._clear_notes_for_placement(row, col, correct)
		self.undo_stack.append({
			"type": "hint",
			"row": row,
			"col": col,
			"old_num": old,
			"new_num": correct,
			"cleared_notes": cleared_notes,
		})
		self.redo_stack.clear()
		self.hints_remaining -= 1
		return True

	def undo(self):
		"""Undo last action. Returns (row, col) or None."""
		if not self.undo_stack:
			return None
		action = self.undo_stack.pop()
		row, col = action["row"], action["col"]

		if action["type"] in ("place", "hint"):
			self.board[row][col] = action["old_num"]
			# restore cleared notes
			for (r, c), nums in action["cleared_notes"].items():
				self.notes[r][c].update(nums)
			if action["type"] == "hint":
				self.hints_remaining += 1

		elif action["type"] == "note":
			if action["was_added"]:
				self.notes[row][col].discard(action["num"])
			else:
				self.notes[row][col].add(action["num"])

		self.redo_stack.append(action)
		return (row, col)

	def redo(self):
		"""Redo last undone action. Returns (row, col) or None."""
		if not self.redo_stack:
			return None
		action = self.redo_stack.pop()
		row, col = action["row"], action["col"]

		if action["type"] in ("place", "hint"):
			self.board[row][col] = action["new_num"]
			# re-clear notes
			for (r, c), nums in action["cleared_notes"].items():
				self.notes[r][c] -= nums
			if action["type"] == "hint":
				self.hints_remaining -= 1

		elif action["type"] == "note":
			if action["was_added"]:
				self.notes[row][col].add(action["num"])
			else:
				self.notes[row][col].discard(action["num"])

		self.undo_stack.append(action)
		return (row, col)

	def is_complete(self):
		"""Check if the board matches the solution."""
		return self.board == self.solution
```

- [ ] **Step 2: Verify import**

```bash
python -c "from sudoku.game import SudokuGame; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add sudoku/game.py
git commit -m "feat: game state module with notes, hints, and extended undo/redo"
```

---

### Task 4: Extract stats module

**Files:**
- Create: `sudoku/stats.py`

Copy `StatsManager` and `StatsDialog` from `sudoku.py`. Update `StatsDialog` with Catppuccin styling and add the two new difficulty levels to the summary line.

- [ ] **Step 1: Create `sudoku/stats.py`**

Copy `StatsManager` from `sudoku.py` (lines 188-219) as-is. Restyle `StatsDialog`:

```python
import json
from pathlib import Path
from datetime import date
from PySide6.QtWidgets import (
	QDialog, QVBoxLayout, QLabel, QPushButton,
	QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from sudoku.styles import (
	MANTLE, SURFACE0, TEXT, SUBTEXT0, BLUE, BASE, DIFFICULTIES,
)


class StatsManager:
	def __init__(self):
		self.stats_path = Path(__file__).parent / "stats.json"
		self.stats = self._load()

	def _load(self):
		try:
			return json.loads(self.stats_path.read_text())
		except (FileNotFoundError, json.JSONDecodeError, OSError):
			return []

	def save_game(self, difficulty, zeit_sekunden):
		entry = {
			"datum": date.today().isoformat(),
			"schwierigkeit": difficulty,
			"zeit_sekunden": zeit_sekunden,
		}
		self.stats.insert(0, entry)
		try:
			self.stats_path.write_text(json.dumps(self.stats, indent=2))
		except OSError:
			pass

	def get_best_times(self):
		"""Return dict of difficulty -> best time in seconds."""
		best = {}
		for entry in self.stats:
			d = entry["schwierigkeit"]
			t = entry["zeit_sekunden"]
			if d not in best or t < best[d]:
				best[d] = t
		return best


class StatsDialog(QDialog):
	def __init__(self, stats_manager, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Statistik")
		self.setMinimumSize(500, 450)
		self.setStyleSheet(f"""
			QDialog {{
				background-color: {MANTLE.name()};
			}}
			QLabel {{
				color: {TEXT.name()};
			}}
			QTableWidget {{
				background-color: {SURFACE0.name()};
				color: {TEXT.name()};
				border: none;
				gridline-color: {MANTLE.name()};
			}}
			QHeaderView::section {{
				background-color: {MANTLE.name()};
				color: {SUBTEXT0.name()};
				border: none;
				padding: 4px;
			}}
			QPushButton {{
				background-color: {BLUE.name()};
				color: {BASE.name()};
				border: none;
				border-radius: 6px;
				padding: 8px 16px;
				font-weight: bold;
			}}
			QPushButton:hover {{
				background-color: {BLUE.lighter(110).name()};
			}}
		""")
		layout = QVBoxLayout(self)

		# summary
		total = len(stats_manager.stats)
		best = stats_manager.get_best_times()
		summary = f"Gesamt: {total} Spiele"
		for diff in DIFFICULTIES:
			if diff in best:
				m, s = divmod(best[diff], 60)
				summary += f"  |  {diff}: {m:02d}:{s:02d}"
		summary_label = QLabel(summary)
		summary_label.setFont(QFont("Sans", 11))
		layout.addWidget(summary_label)

		# table
		table = QTableWidget(total, 3)
		table.setHorizontalHeaderLabels(["Datum", "Schwierigkeit", "Zeit"])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		table.setSelectionMode(QTableWidget.NoSelection)
		for i, entry in enumerate(stats_manager.stats):
			table.setItem(i, 0, QTableWidgetItem(entry["datum"]))
			table.setItem(i, 1, QTableWidgetItem(entry["schwierigkeit"]))
			m, s = divmod(entry["zeit_sekunden"], 60)
			table.setItem(i, 2, QTableWidgetItem(f"{m:02d}:{s:02d}"))
		layout.addWidget(table)

		close_btn = QPushButton("Schließen")
		close_btn.clicked.connect(self.close)
		layout.addWidget(close_btn)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from sudoku.stats import StatsManager, StatsDialog; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add sudoku/stats.py
git commit -m "feat: stats module with Catppuccin-styled dialog"
```

---

### Task 5: Build the board widget

**Files:**
- Create: `sudoku/board.py`

Rewrite `SudokuBoard` with: notes rendering, same-number highlighting, Catppuccin-themed overlays, selection signal, and locked state for "Neues Spiel" flow.

- [ ] **Step 1: Create `sudoku/board.py`**

```python
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from sudoku.styles import (
	GRID_BG, GRID_BOX_BORDER, GRID_CELL_BORDER,
	GIVEN_NUMBER, PLAYER_CORRECT, PLAYER_WRONG,
	SELECTED_CELL, SAME_NUMBER_HIGHLIGHT, NOTES_COLOR,
	PAUSE_OVERLAY, LOCK_OVERLAY, TEXT, BASE,
)


class SudokuBoard(QWidget):
	number_entered = Signal(int)  # 1-9
	clear_requested = Signal()
	cell_selected = Signal(int, int)

	def __init__(self):
		super().__init__()
		self.game = None  # SudokuGame reference
		self.selected = None  # (row, col) or None
		self.paused = False
		self.locked = False  # "Neues Spiel" selection mode
		self.setFocusPolicy(Qt.StrongFocus)
		self.setMinimumSize(300, 300)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

	def _grid_params(self):
		"""Calculate grid positioning: returns (cell_size, x_offset, y_offset)."""
		size = min(self.width(), self.height()) - 20
		cell = size // 9
		grid_size = cell * 9
		# right-align: push grid to the right side of the widget
		x_off = self.width() - grid_size - 10
		y_off = (self.height() - grid_size) // 2
		return cell, x_off, y_off

	def paintEvent(self, event):
		p = QPainter(self)
		p.setRenderHint(QPainter.Antialiasing)
		cell, x_off, y_off = self._grid_params()
		grid_size = cell * 9

		# background (Catppuccin Base behind grid)
		p.fillRect(self.rect(), BASE)
		p.fillRect(x_off, y_off, grid_size, grid_size, GRID_BG)

		if self.game:
			# same-number highlighting (before selected cell, so selected draws on top)
			if self.selected:
				sr, sc = self.selected
				selected_num = self.game.board[sr][sc]
				if selected_num != 0:
					for r in range(9):
						for c in range(9):
							if (r, c) != (sr, sc) and self.game.board[r][c] == selected_num:
								p.fillRect(x_off + c * cell, y_off + r * cell, cell, cell, SAME_NUMBER_HIGHLIGHT)

			# selected cell highlight
			if self.selected:
				r, c = self.selected
				p.fillRect(x_off + c * cell, y_off + r * cell, cell, cell, SELECTED_CELL)

			# numbers
			font_size = max(cell // 3, 10)
			font = QFont("Sans", font_size)
			p.setFont(font)
			for r in range(9):
				for c in range(9):
					num = self.game.board[r][c]
					x = x_off + c * cell
					y = y_off + r * cell
					if num != 0:
						if self.game.given[r][c]:
							p.setPen(GIVEN_NUMBER)
							font.setBold(True)
							p.setFont(font)
						elif num != self.game.solution[r][c]:
							p.setPen(PLAYER_WRONG)
							font.setBold(False)
							p.setFont(font)
						else:
							p.setPen(PLAYER_CORRECT)
							font.setBold(False)
							p.setFont(font)
						p.drawText(x, y, cell, cell, Qt.AlignCenter, str(num))
					elif self.game.notes[r][c]:
						# draw notes as 3x3 mini-grid
						note_font = QFont("Sans", max(cell // 6, 6))
						p.setFont(note_font)
						p.setPen(NOTES_COLOR)
						note_cell = cell // 3
						for n in range(1, 10):
							if n in self.game.notes[r][c]:
								nr = (n - 1) // 3
								nc = (n - 1) % 3
								nx = x + nc * note_cell
								ny = y + nr * note_cell
								p.drawText(nx, ny, note_cell, note_cell, Qt.AlignCenter, str(n))
						# restore main font
						p.setFont(font)

		# grid lines - thin
		p.setPen(QPen(GRID_CELL_BORDER, 1))
		for i in range(10):
			if i % 3 == 0:
				continue
			p.drawLine(x_off + i * cell, y_off, x_off + i * cell, y_off + grid_size)
			p.drawLine(x_off, y_off + i * cell, x_off + grid_size, y_off + i * cell)

		# grid lines - thick (3x3 box borders)
		p.setPen(QPen(GRID_BOX_BORDER, 3))
		for i in range(0, 10, 3):
			p.drawLine(x_off + i * cell, y_off, x_off + i * cell, y_off + grid_size)
			p.drawLine(x_off, y_off + i * cell, x_off + grid_size, y_off + i * cell)

		# pause overlay
		if self.paused:
			p.fillRect(x_off, y_off, grid_size, grid_size, PAUSE_OVERLAY)
			p.setPen(TEXT)
			p.setFont(QFont("Sans", 24, QFont.Bold))
			p.drawText(x_off, y_off, grid_size, grid_size, Qt.AlignCenter, "Pausiert")

		# locked overlay (Neues Spiel selection mode)
		if self.locked:
			p.fillRect(x_off, y_off, grid_size, grid_size, LOCK_OVERLAY)

		p.end()

	def mousePressEvent(self, event):
		if not self.game or self.paused or self.locked:
			return
		cell, x_off, y_off = self._grid_params()
		c = int((event.position().x() - x_off) // cell)
		r = int((event.position().y() - y_off) // cell)
		if 0 <= r < 9 and 0 <= c < 9:
			self.selected = (r, c)
			self.cell_selected.emit(r, c)
			self.update()

	def keyPressEvent(self, event):
		if not self.game or self.paused or self.locked:
			return
		key = event.key()
		# number input
		if Qt.Key_1 <= key <= Qt.Key_9:
			self.number_entered.emit(key - Qt.Key_0)
			return
		# clear
		if key in (Qt.Key_Delete, Qt.Key_Backspace):
			self.clear_requested.emit()
			return
		# notes toggle
		if key == Qt.Key_N:
			# handled by MainWindow via keyPressEvent propagation or shortcut
			event.ignore()
			return
		# arrow navigation
		if self.selected:
			r, c = self.selected
			if key == Qt.Key_Up and r > 0:
				self.selected = (r - 1, c)
			elif key == Qt.Key_Down and r < 8:
				self.selected = (r + 1, c)
			elif key == Qt.Key_Left and c > 0:
				self.selected = (r, c - 1)
			elif key == Qt.Key_Right and c < 8:
				self.selected = (r, c + 1)
			self.cell_selected.emit(*self.selected)
			self.update()
```

- [ ] **Step 2: Verify import**

```bash
python -c "from sudoku.board import SudokuBoard; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add sudoku/board.py
git commit -m "feat: board widget with notes rendering, same-number highlight, overlays"
```

---

### Task 6: Build the controls panel

**Files:**
- Create: `sudoku/controls.py`

Right-side panel: timer + pause, action buttons (undo, redo, erase, notes toggle, hint with badge), 3x3 number pad, "Neues Spiel" button. All Catppuccin-themed.

- [ ] **Step 1: Create `sudoku/controls.py`**

```python
from PySide6.QtWidgets import (
	QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
	QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from sudoku.styles import (
	BASE, SURFACE0, BLUE, TEXT, SUBTEXT0, OVERLAY0,
	ACTION_BUTTON_SIZE, NUMPAD_GAP,
)


class ActionButton(QPushButton):
	"""Circular action button with label below."""
	def __init__(self, icon_text, label_text, parent=None):
		super().__init__(icon_text, parent)
		self.label_text = label_text
		self.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
		self.setFocusPolicy(Qt.NoFocus)
		self._active = True
		self._update_style()

	def set_active(self, active):
		self._active = active
		self._update_style()

	def _update_style(self):
		border_color = BLUE.name() if self._active else OVERLAY0.name()
		text_color = BLUE.name() if self._active else OVERLAY0.name()
		bg = "transparent" if self._active else SURFACE0.name()
		self.setStyleSheet(f"""
			QPushButton {{
				border: 2px solid {border_color};
				border-radius: {ACTION_BUTTON_SIZE // 2}px;
				background: {bg};
				color: {text_color};
				font-size: 16px;
			}}
			QPushButton:hover {{
				background: {SURFACE0.name()};
			}}
		""")


class ControlPanel(QWidget):
	number_clicked = Signal(int)
	clear_clicked = Signal()
	undo_clicked = Signal()
	redo_clicked = Signal()
	notes_toggled = Signal(bool)
	hint_clicked = Signal()
	new_game_clicked = Signal()
	pause_clicked = Signal()

	def __init__(self):
		super().__init__()
		self.notes_mode = False
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		self._build_ui()

	def _build_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(12)

		# --- Timer row ---
		timer_row = QHBoxLayout()
		timer_row.addStretch()
		self.timer_label_prefix = QLabel("Zeit")
		self.timer_label_prefix.setStyleSheet(f"color: {SUBTEXT0.name()}; font-size: 13px;")
		timer_row.addWidget(self.timer_label_prefix)
		self.timer_label = QLabel("00:00")
		self.timer_label.setFont(QFont("Sans", 18, QFont.Bold))
		self.timer_label.setStyleSheet(f"color: {TEXT.name()};")
		timer_row.addWidget(self.timer_label)
		self.pause_btn = ActionButton("⏸", "Pause")
		self.pause_btn.setFixedSize(28, 28)
		self.pause_btn.setStyleSheet(f"""
			QPushButton {{
				border: 2px solid {BLUE.name()};
				border-radius: 14px;
				background: transparent;
				color: {BLUE.name()};
				font-size: 10px;
			}}
			QPushButton:hover {{ background: {SURFACE0.name()}; }}
		""")
		self.pause_btn.clicked.connect(self.pause_clicked.emit)
		timer_row.addWidget(self.pause_btn)
		layout.addLayout(timer_row)

		# --- Action buttons row ---
		action_row = QHBoxLayout()
		action_row.setSpacing(4)

		self.undo_btn = ActionButton("↩", "Rückg.")
		self.undo_btn.clicked.connect(self.undo_clicked.emit)
		self.redo_btn = ActionButton("↪", "Wdh.")
		self.redo_btn.clicked.connect(self.redo_clicked.emit)
		self.erase_btn = ActionButton("⌫", "Löschen")
		self.erase_btn.clicked.connect(self.clear_clicked.emit)
		self.notes_btn = ActionButton("✏", "Notizen")
		self.notes_btn.set_active(False)
		self.notes_btn.clicked.connect(self._toggle_notes)
		self.hint_btn = ActionButton("💡", "Hinweis")
		self.hint_btn.clicked.connect(self.hint_clicked.emit)

		for btn in [self.undo_btn, self.redo_btn, self.erase_btn, self.notes_btn, self.hint_btn]:
			col = QVBoxLayout()
			col.setAlignment(Qt.AlignCenter)
			col.addWidget(btn, alignment=Qt.AlignCenter)
			label = QLabel(btn.label_text)
			label.setStyleSheet(f"color: {SUBTEXT0.name()}; font-size: 10px;")
			label.setAlignment(Qt.AlignCenter)
			col.addWidget(label)
			action_row.addLayout(col)

		layout.addLayout(action_row)

		# --- Hint badge ---
		# We'll store the badge label to update count
		self.hint_badge = QLabel("3")
		self.hint_badge.setFixedSize(16, 16)
		self.hint_badge.setAlignment(Qt.AlignCenter)
		self.hint_badge.setStyleSheet(f"""
			background: {BLUE.name()};
			color: {BASE.name()};
			border-radius: 8px;
			font-size: 9px;
			font-weight: bold;
		""")
		# Position badge on hint button
		self.hint_badge.setParent(self.hint_btn)
		self.hint_badge.move(ACTION_BUTTON_SIZE - 12, -4)

		# --- Number pad (3x3) ---
		numpad = QGridLayout()
		numpad.setSpacing(NUMPAD_GAP)
		self.num_buttons = []
		for i in range(9):
			btn = QPushButton(str(i + 1))
			btn.setFocusPolicy(Qt.NoFocus)
			btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
			btn.setMinimumHeight(48)
			btn.setStyleSheet(f"""
				QPushButton {{
					background: {SURFACE0.name()};
					color: {BLUE.name()};
					border: none;
					border-radius: 8px;
					font-size: 26px;
					font-weight: bold;
				}}
				QPushButton:hover {{
					background: {SURFACE0.lighter(120).name()};
				}}
				QPushButton:disabled {{
					color: {OVERLAY0.name()};
				}}
			""")
			btn.clicked.connect(lambda checked, n=i+1: self.number_clicked.emit(n))
			numpad.addWidget(btn, i // 3, i % 3)
			self.num_buttons.append(btn)
		layout.addLayout(numpad, 1)  # stretch=1 so numpad fills space

		# --- New Game button ---
		self.new_game_btn = QPushButton("Neues Spiel")
		self.new_game_btn.setFocusPolicy(Qt.NoFocus)
		self.new_game_btn.setMinimumHeight(44)
		self.new_game_btn.setStyleSheet(f"""
			QPushButton {{
				background: {BLUE.name()};
				color: {BASE.name()};
				border: none;
				border-radius: 8px;
				font-size: 15px;
				font-weight: bold;
			}}
			QPushButton:hover {{
				background: {BLUE.lighter(110).name()};
			}}
		""")
		self.new_game_btn.clicked.connect(self.new_game_clicked.emit)
		layout.addWidget(self.new_game_btn)

	def _toggle_notes(self):
		self.notes_mode = not self.notes_mode
		self.notes_btn.set_active(self.notes_mode)
		self.notes_toggled.emit(self.notes_mode)

	def update_timer(self, seconds):
		m, s = divmod(seconds, 60)
		self.timer_label.setText(f"{m:02d}:{s:02d}")

	def update_hint_badge(self, remaining):
		self.hint_badge.setText(str(remaining))
		if remaining <= 0:
			self.hint_btn.set_active(False)
			self.hint_btn.setEnabled(False)
			self.hint_badge.hide()

	def set_controls_enabled(self, enabled):
		for btn in self.num_buttons:
			btn.setEnabled(enabled)
		self.undo_btn.setEnabled(enabled)
		self.redo_btn.setEnabled(enabled)
		self.erase_btn.setEnabled(enabled)
		self.notes_btn.setEnabled(enabled)
		self.hint_btn.setEnabled(enabled)
		self.pause_btn.setEnabled(enabled)

	def set_new_game_mode(self, selecting):
		"""Switch button between 'Neues Spiel' and 'Fortsetzen'."""
		if selecting:
			self.new_game_btn.setText("Fortsetzen")
		else:
			self.new_game_btn.setText("Neues Spiel")
```

- [ ] **Step 2: Verify import**

```bash
python -c "from sudoku.controls import ControlPanel; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add sudoku/controls.py
git commit -m "feat: control panel with action buttons, numpad, timer, Catppuccin theme"
```

---

### Task 7: Build the difficulty bar widget

**Files:**
- Create: `sudoku/difficulty_bar.py`

Horizontal tab bar across the top. Tabs are clickable labels. Supports enabled/disabled state and active tab highlighting.

- [ ] **Step 1: Create `sudoku/difficulty_bar.py`**

```python
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from sudoku.styles import MANTLE, SURFACE0, BLUE, SUBTEXT0, SUBTEXT1, OVERLAY0, TEXT, DIFFICULTIES


class DifficultyBar(QWidget):
	difficulty_selected = Signal(str)

	def __init__(self):
		super().__init__()
		self.current_difficulty = None
		self.tabs_enabled = True
		self.setFixedHeight(40)
		self.setStyleSheet(f"background: {MANTLE.name()}; border-bottom: 1px solid {SURFACE0.name()};")
		self._build_ui()

	def _build_ui(self):
		layout = QHBoxLayout(self)
		layout.setContentsMargins(20, 0, 20, 0)
		layout.setSpacing(16)

		prefix = QLabel("Schwierigkeit:")
		prefix.setStyleSheet(f"color: {SUBTEXT0.name()}; font-size: 13px; border: none;")
		layout.addWidget(prefix)

		self.tab_labels = {}
		for diff in DIFFICULTIES:
			label = QPushButton(diff)
			label.setFocusPolicy(Qt.NoFocus)
			label.setCursor(Qt.PointingHandCursor)
			label.setFlat(True)
			label.setStyleSheet(self._tab_style(False, True))
			label.clicked.connect(lambda checked, d=diff: self._on_tab_clicked(d))
			layout.addWidget(label)
			self.tab_labels[diff] = label

		layout.addStretch()

		# stats button (right-aligned)
		self.stats_btn = QPushButton("Statistik")
		self.stats_btn.setFocusPolicy(Qt.NoFocus)
		self.stats_btn.setFlat(True)
		self.stats_btn.setStyleSheet(f"""
			QPushButton {{
				color: {SUBTEXT1.name()};
				font-size: 13px;
				border: none;
				padding: 4px 8px;
			}}
			QPushButton:hover {{
				color: {TEXT.name()};
			}}
		""")
		layout.addWidget(self.stats_btn)

	def _tab_style(self, active, enabled):
		if not enabled:
			return f"""
				QPushButton {{
					color: {OVERLAY0.name()};
					font-size: 14px;
					border: none;
					border-bottom: 2px solid transparent;
					padding: 4px 0;
				}}
			"""
		if active:
			return f"""
				QPushButton {{
					color: {BLUE.name()};
					font-size: 14px;
					font-weight: bold;
					border: none;
					border-bottom: 2px solid {BLUE.name()};
					padding: 4px 0;
				}}
			"""
		return f"""
			QPushButton {{
				color: {SUBTEXT1.name()};
				font-size: 14px;
				border: none;
				border-bottom: 2px solid transparent;
				padding: 4px 0;
			}}
			QPushButton:hover {{
				color: {TEXT.name()};
			}}
		"""

	def _on_tab_clicked(self, difficulty):
		if not self.tabs_enabled:
			return
		self.difficulty_selected.emit(difficulty)

	def set_active(self, difficulty):
		"""Highlight the active difficulty tab."""
		self.current_difficulty = difficulty
		for diff, label in self.tab_labels.items():
			label.setStyleSheet(self._tab_style(diff == difficulty, self.tabs_enabled))

	def set_enabled(self, enabled):
		"""Enable or disable all tabs."""
		self.tabs_enabled = enabled
		for diff, label in self.tab_labels.items():
			active = diff == self.current_difficulty
			label.setStyleSheet(self._tab_style(active, enabled))
```

- [ ] **Step 2: Verify import**

```bash
python -c "from sudoku.difficulty_bar import DifficultyBar, DIFFICULTIES; print(DIFFICULTIES)"
```

- [ ] **Step 3: Commit**

```bash
git add sudoku/difficulty_bar.py
git commit -m "feat: difficulty bar with 6 levels, enable/disable, active highlight"
```

---

### Task 8: Build MainWindow and entry point

**Files:**
- Create: `sudoku/main.py`

The coordinator. Two-panel layout: board left, controls right. Difficulty bar on top. Wires all signals. Handles "Neues Spiel" flow with lock/unlock.

- [ ] **Step 1: Create `sudoku/main.py`**

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from sudoku.board import SudokuBoard
from sudoku.controls import ControlPanel
from sudoku.difficulty_bar import DifficultyBar
from sudoku.game import SudokuGame
from sudoku.generator import GeneratorThread
from sudoku.stats import StatsManager, StatsDialog
from sudoku.styles import BASE, GRID_CONTROLS_GAP


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Sudoku")
		self.resize(800, 600)
		self.setStyleSheet(f"background-color: {BASE.name()};")

		self.game = None
		self.generator_thread = None
		self.stats_manager = StatsManager()
		self.notes_mode = False
		self.selecting_difficulty = False  # "Neues Spiel" selection mode

		# central widget
		central = QWidget()
		self.setCentralWidget(central)
		outer_layout = QVBoxLayout(central)
		outer_layout.setContentsMargins(0, 0, 0, 0)
		outer_layout.setSpacing(0)

		# difficulty bar (top)
		self.difficulty_bar = DifficultyBar()
		self.difficulty_bar.difficulty_selected.connect(self.on_difficulty_selected)
		self.difficulty_bar.stats_btn.clicked.connect(self.show_stats)
		self.difficulty_bar.set_enabled(True)  # enabled when no game
		outer_layout.addWidget(self.difficulty_bar)

		# main content: board + controls
		content = QWidget()
		content_layout = QHBoxLayout(content)
		content_layout.setContentsMargins(16, 16, 16, 16)
		content_layout.setSpacing(GRID_CONTROLS_GAP)

		# board (left, expanding)
		self.board = SudokuBoard()
		self.board.number_entered.connect(self.on_number_entered)
		self.board.clear_requested.connect(self.on_clear_clicked)
		self.board.cell_selected.connect(self.on_cell_selected)
		content_layout.addWidget(self.board, 1)

		# controls (right)
		self.controls = ControlPanel()
		self.controls.number_clicked.connect(self.on_number_entered)
		self.controls.clear_clicked.connect(self.on_clear_clicked)
		self.controls.undo_clicked.connect(self.on_undo)
		self.controls.redo_clicked.connect(self.on_redo)
		self.controls.notes_toggled.connect(self.on_notes_toggled)
		self.controls.hint_clicked.connect(self.on_hint)
		self.controls.new_game_clicked.connect(self.on_new_game_clicked)
		self.controls.pause_clicked.connect(self.toggle_pause)
		self.controls.set_controls_enabled(False)
		content_layout.addWidget(self.controls)

		outer_layout.addWidget(content, 1)

		# game timer
		self.tick_timer = QTimer(self)
		self.tick_timer.setInterval(1000)
		self.tick_timer.timeout.connect(self.on_timer_tick)

		# keyboard shortcuts
		QShortcut(QKeySequence("Ctrl+Z"), self, self.on_undo)
		QShortcut(QKeySequence("Ctrl+Y"), self, self.on_redo)
		QShortcut(QKeySequence("N"), self, self._toggle_notes_shortcut)

	def _toggle_notes_shortcut(self):
		if not self.game or self.game.paused:
			return
		self.notes_mode = not self.notes_mode
		self.controls.notes_mode = self.notes_mode
		self.controls.notes_btn.set_active(self.notes_mode)

	def on_difficulty_selected(self, difficulty):
		"""User clicked a difficulty tab."""
		if self.selecting_difficulty and self.game:
			# confirm
			result = QMessageBox.question(
				self, "Neues Spiel",
				"Neues Spiel starten? Aktueller Fortschritt geht verloren.",
				QMessageBox.Yes | QMessageBox.No,
			)
			if result == QMessageBox.No:
				return
		# start generation
		self.selecting_difficulty = False
		self.board.locked = False
		self.controls.set_new_game_mode(False)
		self._start_generation(difficulty)

	def on_new_game_clicked(self):
		"""Toggle between selection mode and resume."""
		if self.selecting_difficulty:
			# resume current game
			self.selecting_difficulty = False
			self.board.locked = False
			self.board.update()
			self.difficulty_bar.set_enabled(False)
			self.controls.set_new_game_mode(False)
			if self.game and not self.game.paused:
				self.tick_timer.start()
		else:
			if self.game:
				# enter selection mode
				self.selecting_difficulty = True
				self.tick_timer.stop()
				self.board.locked = True
				self.board.update()
				self.difficulty_bar.set_enabled(True)
				self.controls.set_new_game_mode(True)
			else:
				# no game running, just enable tabs
				self.difficulty_bar.set_enabled(True)

	def _start_generation(self, difficulty):
		self.tick_timer.stop()
		self.game = None
		self.controls.set_controls_enabled(False)
		self.controls.update_timer(0)
		self.difficulty_bar.set_active(difficulty)
		self.difficulty_bar.set_enabled(False)

		if self.generator_thread and self.generator_thread.isRunning():
			self.generator_thread.finished.disconnect()
		self.generator_thread = GeneratorThread(difficulty)
		self.generator_thread.finished.connect(
			lambda p, s: self.on_puzzle_ready(p, s, difficulty)
		)
		self.generator_thread.start()

	def on_puzzle_ready(self, puzzle, solution, difficulty):
		self.game = SudokuGame(puzzle, solution, difficulty)
		self.board.game = self.game
		self.board.selected = None
		self.board.paused = False
		self.board.locked = False
		self.board.update()
		self.controls.set_controls_enabled(True)
		self.controls.update_timer(0)
		self.controls.update_hint_badge(self.game.hints_remaining)
		self.notes_mode = False
		self.controls.notes_mode = False
		self.controls.notes_btn.set_active(False)
		self.tick_timer.start()
		self.board.setFocus()

	def on_cell_selected(self, row, col):
		# board handles selection internally, we just need to know for routing
		pass

	def on_number_entered(self, num):
		if not self.game or self.game.paused or not self.board.selected:
			return
		r, c = self.board.selected
		if self.notes_mode:
			self.game.toggle_note(r, c, num)
		else:
			self.game.place_number(r, c, num)
		self.board.update()
		if not self.notes_mode:
			self.check_completion()

	def on_clear_clicked(self):
		if not self.game or self.game.paused or not self.board.selected:
			return
		r, c = self.board.selected
		self.game.clear_cell(r, c)
		self.board.update()

	def on_undo(self):
		if not self.game or self.game.paused:
			return
		result = self.game.undo()
		if result:
			self.board.selected = result
		self.board.update()
		self.controls.update_hint_badge(self.game.hints_remaining)

	def on_redo(self):
		if not self.game or self.game.paused:
			return
		result = self.game.redo()
		if result:
			self.board.selected = result
		self.board.update()
		self.controls.update_hint_badge(self.game.hints_remaining)

	def on_notes_toggled(self, active):
		self.notes_mode = active

	def on_hint(self):
		if not self.game or self.game.paused or not self.board.selected:
			return
		r, c = self.board.selected
		self.game.use_hint(r, c)
		self.board.update()
		self.controls.update_hint_badge(self.game.hints_remaining)
		self.check_completion()

	def toggle_pause(self):
		if not self.game:
			return
		self.game.paused = not self.game.paused
		self.board.paused = self.game.paused
		if self.game.paused:
			self.tick_timer.stop()
			self.controls.pause_btn.setText("▶")
		else:
			self.tick_timer.start()
			self.controls.pause_btn.setText("⏸")
		self.board.update()

	def on_timer_tick(self):
		if self.game:
			self.game.elapsed_seconds += 1
			self.controls.update_timer(self.game.elapsed_seconds)

	def check_completion(self):
		if not self.game or not self.game.is_complete():
			return
		self.tick_timer.stop()
		m, s = divmod(self.game.elapsed_seconds, 60)
		self.stats_manager.save_game(self.game.difficulty, self.game.elapsed_seconds)
		QMessageBox.information(self, "Gewonnen!", f"Gelöst in {m:02d}:{s:02d}!")
		self.controls.set_controls_enabled(False)
		self.game = None

	def show_stats(self):
		dialog = StatsDialog(self.stats_manager, self)
		dialog.exec()


def main():
	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
```

- [ ] **Step 2: Run the app to verify**

```bash
cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt"
uv run python -m sudoku.main
```

Verify: window opens with Catppuccin dark background, difficulty bar at top, empty board, controls on right. Click a difficulty tab to start a game.

- [ ] **Step 3: Commit**

```bash
git add sudoku/main.py
git commit -m "feat: MainWindow with two-panel layout, new game flow, all signal wiring"
```

---

### Task 9: Clean up old single file and update build config

**Files:**
- Remove: `sudoku.py` (old single-file app)
- Modify: `sudoku.spec` (PyInstaller config)
- Modify: `.gitignore`

- [ ] **Step 1: Remove old `sudoku.py`**

```bash
git rm sudoku.py
```

- [ ] **Step 2: Update `sudoku.spec`**

Change the entry point from `sudoku.py` to `sudoku/main.py`:

In `sudoku.spec`, update the `Analysis` call:
- Change `['sudoku.py']` to `['sudoku/main.py']`

- [ ] **Step 3: Update `.gitignore`**

The current `.gitignore` has `stats.json` which only matches at the repo root. Since `StatsManager` now writes to `sudoku/stats.json`, update the entry to `**/stats.json` to cover both locations.

- [ ] **Step 4: Verify the app still runs**

```bash
uv run python -m sudoku.main
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove old single-file app, update build config for package structure"
```

---

### Task 10: Integration testing and polish

**Files:**
- Modify: various files as needed for fixes

Manual testing checklist - run through each and fix any issues:

- [ ] **Step 1: Test basic game flow**

```bash
uv run python -m sudoku.main
```

1. Click "Leicht" tab -> game starts, timer runs
2. Click cells, enter numbers via keyboard and numpad
3. Wrong numbers appear red
4. Complete the game -> win dialog shows

- [ ] **Step 2: Test notes mode**

1. Press N or click notes button -> button highlights
2. Click empty cell, press numbers -> pencil marks appear
3. Place a real number -> notes in same row/col/box clear
4. Undo -> number removed, notes restored

- [ ] **Step 3: Test hints**

1. Select empty cell, click hint -> correct number filled, badge decrements
2. Select given cell, click hint -> nothing happens
3. Use all 3 hints -> button disables
4. Undo a hint -> hint count restores

- [ ] **Step 4: Test "Neues Spiel" flow**

1. Mid-game, click "Neues Spiel" -> board greys, tabs enable, button says "Fortsetzen"
2. Click "Fortsetzen" -> resume game
3. Click "Neues Spiel" again -> selection mode
4. Click a difficulty -> confirmation dialog
5. Confirm -> new game generates
6. Cancel -> resume, tabs grey out

- [ ] **Step 5: Test pause**

1. Click pause -> board overlaid with "Pausiert", timer stops
2. Click resume -> overlay clears, timer resumes

- [ ] **Step 6: Test statistics**

1. Complete a game
2. Click "Statistik" -> dialog shows with Catppuccin styling
3. Entry appears with correct difficulty and time

- [ ] **Step 7: Test fluid scaling**

1. Resize window small -> everything scales down, stays usable
2. Resize window large -> grid and controls scale up, stay centered
3. Grid remains square at all sizes

- [ ] **Step 8: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration testing fixes and polish"
```
