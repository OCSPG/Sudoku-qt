# Hint Explanations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "reveal answer" hint system with technique-based solving that visually explains why a number belongs in a cell.

**Architecture:** New `solver.py` module implements Sudoku solving techniques (Naked/Hidden Singles through X-Wing/Swordfish) and returns structured results. The board overlay dims irrelevant cells, highlights evidence, shows explanation text with a "Verstanden" dismiss button. Game logic splits hinting into prepare/confirm phases.

**Tech Stack:** Python 3, PySide6 (Qt), dataclasses

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `sudoku/solver.py` | Create | Candidate computation, solving techniques, hint result generation |
| `sudoku/styles.py` | Modify | Add hint overlay colors |
| `sudoku/game.py` | Modify | Split `use_hint()` into `prepare_hint()`/`confirm_hint()`, integrate solver |
| `sudoku/board.py` | Modify | Hint overlay rendering, "Verstanden" button, input blocking |
| `sudoku/main.py` | Modify | Wire two-phase hint flow, connect `hint_confirmed` signal |

---

### Task 1: Add Hint Overlay Colors to Styles

**Files:**
- Modify: `sudoku/styles.py:31-33`

- [ ] **Step 1: Add three hint colors**

Add after the existing overlay colors (line 33) in `sudoku/styles.py`:

```python
# --- Hint overlay colors ---
HINT_TARGET = QColor(166, 227, 161, 64)    # Catppuccin Green at ~25% opacity
HINT_EVIDENCE = QColor(243, 139, 168, 51)  # RED at ~20% opacity
HINT_DIM = QColor(17, 17, 27, 153)         # Crust at 60% opacity
```

- [ ] **Step 2: Commit**

```bash
git add sudoku/styles.py
git commit -m "feat: add hint overlay colors to styles"
```

---

### Task 2: Solver Module - Candidate Computation and Naked Single

**Files:**
- Create: `sudoku/solver.py`

- [ ] **Step 1: Create solver module with HintResult, candidate computation, and Naked Single**

Create `sudoku/solver.py`:

```python
from dataclasses import dataclass, field


@dataclass
class HintResult:
	cell: tuple[int, int]          # (row, col) being solved
	value: int                     # the number that goes there
	technique: str                 # e.g. "Naked Single"
	explanation: str               # human-readable German text
	highlight_cells: list[tuple] = field(default_factory=list)  # evidence cells


class SudokuSolver:
	"""Technique-based Sudoku solver that explains its reasoning."""

	# techniques available per difficulty tier
	DIFFICULTY_TIERS = {
		"Leicht": ["naked_single", "hidden_single"],
		"Mittel": ["naked_single", "hidden_single"],
		"Schwer": ["naked_single", "hidden_single", "naked_pair", "naked_triple", "pointing_pair", "box_line_reduction"],
		"Experte": ["naked_single", "hidden_single", "naked_pair", "naked_triple", "pointing_pair", "box_line_reduction"],
		"Meister": ["naked_single", "hidden_single", "naked_pair", "naked_triple", "pointing_pair", "box_line_reduction", "x_wing", "swordfish", "xy_wing"],
		"Extrem": ["naked_single", "hidden_single", "naked_pair", "naked_triple", "pointing_pair", "box_line_reduction", "x_wing", "swordfish", "xy_wing"],
	}

	def __init__(self, board, difficulty="Extrem"):
		# work on a copy
		self.board = [row[:] for row in board]
		self.difficulty = difficulty
		self.candidates = [[set() for _ in range(9)] for _ in range(9)]
		self._compute_candidates()

	def _compute_candidates(self):
		"""Compute possible values for every empty cell."""
		for r in range(9):
			for c in range(9):
				if self.board[r][c] != 0:
					continue
				possible = set(range(1, 10))
				# remove row values
				possible -= set(self.board[r])
				# remove column values
				possible -= {self.board[rr][c] for rr in range(9)}
				# remove box values
				box_r, box_c = 3 * (r // 3), 3 * (c // 3)
				for br in range(box_r, box_r + 3):
					for bc in range(box_c, box_c + 3):
						possible.discard(self.board[br][bc])
				self.candidates[r][c] = possible

	def _box_cells(self, row, col):
		"""Return all 9 cells in the 3x3 box containing (row, col)."""
		box_r, box_c = 3 * (row // 3), 3 * (col // 3)
		return [(r, c) for r in range(box_r, box_r + 3) for c in range(box_c, box_c + 3)]

	def _box_index(self, row, col):
		"""Return box index 0-8 for a cell."""
		return (row // 3) * 3 + col // 3

	def _box_name(self, row, col):
		"""Return human-readable box name (1-9)."""
		return str(self._box_index(row, col) + 1)

	def find_hint(self, target_cell=None):
		"""Find a hint, preferring target_cell. Returns HintResult or None.

		Args:
			target_cell: (row, col) the user selected, tried first.
		"""
		allowed = self.DIFFICULTY_TIERS.get(self.difficulty, self.DIFFICULTY_TIERS["Extrem"])
		technique_methods = {
			"naked_single": self._find_naked_single,
			"hidden_single": self._find_hidden_single,
			"naked_pair": self._find_naked_pair,
			"naked_triple": self._find_naked_triple,
			"pointing_pair": self._find_pointing_pair,
			"box_line_reduction": self._find_box_line_reduction,
			"x_wing": self._find_x_wing,
			"swordfish": self._find_swordfish,
			"xy_wing": self._find_xy_wing,
		}

		# try target cell first, then any cell
		for technique_name in allowed:
			method = technique_methods[technique_name]
			if target_cell:
				result = method(target_cell)
				if result:
					return result
			# search all empty cells
			for r in range(9):
				for c in range(9):
					if self.board[r][c] == 0 and (r, c) != target_cell:
						result = method((r, c))
						if result:
							return result
		return None

	def _find_naked_single(self, cell):
		"""A cell has only one candidate."""
		r, c = cell
		if len(self.candidates[r][c]) != 1:
			return None
		value = next(iter(self.candidates[r][c]))
		# collect evidence: all filled cells in same row, col, box
		evidence = []
		for cc in range(9):
			if cc != c and self.board[r][cc] != 0:
				evidence.append((r, cc))
		for rr in range(9):
			if rr != r and self.board[rr][c] != 0:
				evidence.append((rr, c))
		for br, bc in self._box_cells(r, c):
			if (br, bc) != (r, c) and self.board[br][bc] != 0 and (br, bc) not in evidence:
				evidence.append((br, bc))

		# build explanation
		row_nums = sorted(self.board[r][cc] for cc in range(9) if cc != c and self.board[r][cc] != 0)
		col_nums = sorted(self.board[rr][c] for rr in range(9) if rr != r and self.board[rr][c] != 0)
		box_nums = sorted(
			self.board[br][bc] for br, bc in self._box_cells(r, c)
			if (br, bc) != (r, c) and self.board[br][bc] != 0
		)
		all_blocking = sorted(set(row_nums + col_nums + box_nums))
		explanation = (
			f"Zeile {r + 1}, Spalte {c + 1} und Block {self._box_name(r, c)} "
			f"enthalten bereits {', '.join(str(n) for n in all_blocking)} - "
			f"nur {value} ist hier möglich."
		)
		return HintResult(
			cell=(r, c),
			value=value,
			technique="Naked Single",
			explanation=explanation,
			highlight_cells=evidence,
		)
```

- [ ] **Step 2: Verify module imports**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.solver import SudokuSolver, HintResult; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add sudoku/solver.py
git commit -m "feat: add solver module with candidate computation and Naked Single"
```

---

### Task 3: Solver - Hidden Single

**Files:**
- Modify: `sudoku/solver.py`

- [ ] **Step 1: Add Hidden Single method**

Add the following method to the `SudokuSolver` class in `sudoku/solver.py`, after `_find_naked_single`:

```python
	def _find_hidden_single(self, cell):
		"""A candidate appears in only one cell within a row, column, or box."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		for value in self.candidates[r][c]:
			# check row: is value only possible here in this row?
			row_positions = [cc for cc in range(9) if value in self.candidates[r][cc]]
			if len(row_positions) == 1 and row_positions[0] == c:
				evidence = [(r, cc) for cc in range(9) if cc != c and self.board[r][cc] != 0]
				other_with_candidates = [(r, cc) for cc in range(9) if cc != c and self.board[r][cc] == 0]
				explanation = (
					f"{value} kann in Zeile {r + 1} nur in dieses Feld - "
					f"alle anderen Positionen sind blockiert."
				)
				return HintResult(
					cell=(r, c), value=value, technique="Hidden Single",
					explanation=explanation, highlight_cells=evidence + other_with_candidates,
				)

			# check column
			col_positions = [rr for rr in range(9) if value in self.candidates[rr][c]]
			if len(col_positions) == 1 and col_positions[0] == r:
				evidence = [(rr, c) for rr in range(9) if rr != r and self.board[rr][c] != 0]
				other_with_candidates = [(rr, c) for rr in range(9) if rr != r and self.board[rr][c] == 0]
				explanation = (
					f"{value} kann in Spalte {c + 1} nur in dieses Feld - "
					f"alle anderen Positionen sind blockiert."
				)
				return HintResult(
					cell=(r, c), value=value, technique="Hidden Single",
					explanation=explanation, highlight_cells=evidence + other_with_candidates,
				)

			# check box
			box_cells = self._box_cells(r, c)
			box_positions = [(br, bc) for br, bc in box_cells if value in self.candidates[br][bc]]
			if len(box_positions) == 1 and box_positions[0] == (r, c):
				evidence = [(br, bc) for br, bc in box_cells if (br, bc) != (r, c) and self.board[br][bc] != 0]
				other_with_candidates = [(br, bc) for br, bc in box_cells if (br, bc) != (r, c) and self.board[br][bc] == 0]
				explanation = (
					f"{value} kann in Block {self._box_name(r, c)} nur in dieses Feld - "
					f"alle anderen Positionen sind blockiert."
				)
				return HintResult(
					cell=(r, c), value=value, technique="Hidden Single",
					explanation=explanation, highlight_cells=evidence + other_with_candidates,
				)
		return None
```

- [ ] **Step 2: Verify import still works**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.solver import SudokuSolver; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add sudoku/solver.py
git commit -m "feat: add Hidden Single technique to solver"
```

---

### Task 4: Solver - Intermediate Techniques (Naked Pair/Triple, Pointing Pair, Box/Line Reduction)

**Files:**
- Modify: `sudoku/solver.py`

These techniques don't directly place a number - they eliminate candidates. For hint purposes, we apply eliminations, then check if the target cell now has a Naked or Hidden Single. If not, return None.

- [ ] **Step 1: Add helper method for elimination-based techniques**

Add this helper to `SudokuSolver`, before the technique methods:

```python
	def _check_after_elimination(self, cell, eliminations, technique, explanation_prefix):
		"""After eliminating candidates, check if cell is now solvable.

		Args:
			cell: (row, col) to check
			eliminations: list of ((row, col), value) pairs that were eliminated
			technique: technique name string
			explanation_prefix: German text explaining the elimination
		"""
		r, c = cell
		if len(self.candidates[r][c]) != 1:
			return None
		value = next(iter(self.candidates[r][c]))
		evidence = [(er, ec) for (er, ec), _ in eliminations]
		explanation = f"{explanation_prefix} Daher muss hier {value} stehen."
		return HintResult(
			cell=(r, c), value=value, technique=technique,
			explanation=explanation, highlight_cells=evidence,
		)
```

- [ ] **Step 2: Add Naked Pair method**

Add to `SudokuSolver`:

```python
	def _find_naked_pair(self, cell):
		"""Two cells in a unit share exactly the same two candidates, eliminating those from other cells."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		# check each unit (row, col, box)
		units = [
			("Zeile", [(r, cc) for cc in range(9)]),
			("Spalte", [(rr, c) for rr in range(9)]),
			("Block", self._box_cells(r, c)),
		]
		for unit_name, unit_cells in units:
			# find pairs in this unit
			for c1r, c1c in unit_cells:
				if len(self.candidates[c1r][c1c]) != 2:
					continue
				pair = self.candidates[c1r][c1c]
				for c2r, c2c in unit_cells:
					if (c2r, c2c) <= (c1r, c1c):
						continue
					if self.candidates[c2r][c2c] != pair:
						continue
					# found a naked pair - eliminate from other cells
					eliminations = []
					for ur, uc in unit_cells:
						if (ur, uc) in ((c1r, c1c), (c2r, c2c)):
							continue
						for val in pair:
							if val in self.candidates[ur][uc]:
								self.candidates[ur][uc].discard(val)
								eliminations.append(((ur, uc), val))
					if not eliminations:
						continue
					pair_vals = sorted(pair)
					unit_label = unit_name
					if unit_name == "Zeile":
						unit_label = f"Zeile {r + 1}"
					elif unit_name == "Spalte":
						unit_label = f"Spalte {c + 1}"
					else:
						unit_label = f"Block {self._box_name(r, c)}"
					explanation_prefix = (
						f"In {unit_label} können nur die Felder "
						f"Z{c1r+1}S{c1c+1} und Z{c2r+1}S{c2c+1} "
						f"die Werte {pair_vals[0]} und {pair_vals[1]} enthalten. "
						f"Diese werden aus den anderen Feldern eliminiert."
					)
					result = self._check_after_elimination(
						cell, [((c1r, c1c), 0), ((c2r, c2c), 0)] + eliminations,
						"Naked Pair", explanation_prefix,
					)
					if result:
						return result
		return None
```

- [ ] **Step 3: Add Naked Triple method**

Add to `SudokuSolver`:

```python
	def _find_naked_triple(self, cell):
		"""Three cells in a unit have candidates that are a subset of three values."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		units = [
			("Zeile", [(r, cc) for cc in range(9)]),
			("Spalte", [(rr, c) for rr in range(9)]),
			("Block", self._box_cells(r, c)),
		]
		from itertools import combinations

		for unit_name, unit_cells in units:
			# cells with 2-3 candidates
			eligible = [(ur, uc) for ur, uc in unit_cells
						if 2 <= len(self.candidates[ur][uc]) <= 3]
			if len(eligible) < 3:
				continue
			for trio in combinations(eligible, 3):
				union = set()
				for tr, tc in trio:
					union |= self.candidates[tr][tc]
				if len(union) != 3:
					continue
				# found naked triple - eliminate from other cells
				eliminations = []
				for ur, uc in unit_cells:
					if (ur, uc) in trio:
						continue
					for val in union:
						if val in self.candidates[ur][uc]:
							self.candidates[ur][uc].discard(val)
							eliminations.append(((ur, uc), val))
				if not eliminations:
					continue
				triple_vals = sorted(union)
				trio_labels = ", ".join(f"Z{tr+1}S{tc+1}" for tr, tc in trio)
				if unit_name == "Zeile":
					unit_label = f"Zeile {r + 1}"
				elif unit_name == "Spalte":
					unit_label = f"Spalte {c + 1}"
				else:
					unit_label = f"Block {self._box_name(r, c)}"
				explanation_prefix = (
					f"In {unit_label} enthalten die Felder {trio_labels} "
					f"nur die Werte {', '.join(str(v) for v in triple_vals)}. "
					f"Diese werden aus den anderen Feldern eliminiert."
				)
				evidence = list(trio) + [(er, ec) for (er, ec), _ in eliminations]
				result = self._check_after_elimination(
					cell, [((tr, tc), 0) for tr, tc in trio] + eliminations,
					"Naked Triple", explanation_prefix,
				)
				if result:
					return result
		return None
```

- [ ] **Step 4: Add Pointing Pair method**

Add to `SudokuSolver`:

```python
	def _find_pointing_pair(self, cell):
		"""A candidate in a box is confined to one row or column, eliminating it from that row/column outside the box."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		for box_r_start in range(0, 9, 3):
			for box_c_start in range(0, 9, 3):
				box_cells = [(br, bc) for br in range(box_r_start, box_r_start + 3)
							 for bc in range(box_c_start, box_c_start + 3)]
				for value in range(1, 10):
					positions = [(br, bc) for br, bc in box_cells if value in self.candidates[br][bc]]
					if len(positions) < 2:
						continue
					# check if all in same row
					rows = {br for br, bc in positions}
					if len(rows) == 1:
						row = next(iter(rows))
						eliminations = []
						for cc in range(9):
							if cc < box_c_start or cc >= box_c_start + 3:
								if value in self.candidates[row][cc]:
									self.candidates[row][cc].discard(value)
									eliminations.append(((row, cc), value))
						if eliminations:
							explanation_prefix = (
								f"{value} kann in Block {self._box_name(box_r_start, box_c_start)} "
								f"nur in Zeile {row + 1} stehen und wird aus dem Rest der Zeile eliminiert."
							)
							result = self._check_after_elimination(
								cell, [((pr, pc), 0) for pr, pc in positions] + eliminations,
								"Pointing Pair", explanation_prefix,
							)
							if result:
								return result
					# check if all in same column
					cols = {bc for br, bc in positions}
					if len(cols) == 1:
						col = next(iter(cols))
						eliminations = []
						for rr in range(9):
							if rr < box_r_start or rr >= box_r_start + 3:
								if value in self.candidates[rr][col]:
									self.candidates[rr][col].discard(value)
									eliminations.append(((rr, col), value))
						if eliminations:
							explanation_prefix = (
								f"{value} kann in Block {self._box_name(box_r_start, box_c_start)} "
								f"nur in Spalte {col + 1} stehen und wird aus dem Rest der Spalte eliminiert."
							)
							result = self._check_after_elimination(
								cell, [((pr, pc), 0) for pr, pc in positions] + eliminations,
								"Pointing Pair", explanation_prefix,
							)
							if result:
								return result
		return None
```

- [ ] **Step 5: Add Box/Line Reduction method**

Add to `SudokuSolver`:

```python
	def _find_box_line_reduction(self, cell):
		"""A candidate in a row/column is confined to one box, eliminating it from that box's other cells."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		# check rows
		for row in range(9):
			for value in range(1, 10):
				positions = [(row, cc) for cc in range(9) if value in self.candidates[row][cc]]
				if len(positions) < 2:
					continue
				boxes = {cc // 3 for _, cc in positions}
				if len(boxes) == 1:
					box_c_start = next(iter(boxes)) * 3
					box_r_start = 3 * (row // 3)
					eliminations = []
					for br in range(box_r_start, box_r_start + 3):
						for bc in range(box_c_start, box_c_start + 3):
							if br != row and value in self.candidates[br][bc]:
								self.candidates[br][bc].discard(value)
								eliminations.append(((br, bc), value))
					if eliminations:
						explanation_prefix = (
							f"{value} ist in Zeile {row + 1} auf Block {self._box_name(row, box_c_start)} beschränkt "
							f"und wird aus den anderen Feldern des Blocks eliminiert."
						)
						result = self._check_after_elimination(
							cell, [((pr, pc), 0) for pr, pc in positions] + eliminations,
							"Box/Line Reduction", explanation_prefix,
						)
						if result:
							return result

		# check columns
		for col in range(9):
			for value in range(1, 10):
				positions = [(rr, col) for rr in range(9) if value in self.candidates[rr][col]]
				if len(positions) < 2:
					continue
				boxes = {rr // 3 for rr, _ in positions}
				if len(boxes) == 1:
					box_r_start = next(iter(boxes)) * 3
					box_c_start = 3 * (col // 3)
					eliminations = []
					for br in range(box_r_start, box_r_start + 3):
						for bc in range(box_c_start, box_c_start + 3):
							if bc != col and value in self.candidates[br][bc]:
								self.candidates[br][bc].discard(value)
								eliminations.append(((br, bc), value))
					if eliminations:
						explanation_prefix = (
							f"{value} ist in Spalte {col + 1} auf Block {self._box_name(box_r_start, col)} beschränkt "
							f"und wird aus den anderen Feldern des Blocks eliminiert."
						)
						result = self._check_after_elimination(
							cell, [((pr, pc), 0) for pr, pc in positions] + eliminations,
							"Box/Line Reduction", explanation_prefix,
						)
						if result:
							return result
		return None
```

- [ ] **Step 6: Verify import**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.solver import SudokuSolver; print('OK')"`

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add sudoku/solver.py
git commit -m "feat: add intermediate solving techniques (Naked Pair/Triple, Pointing Pair, Box/Line Reduction)"
```

---

### Task 5: Solver - Advanced Techniques (X-Wing, Swordfish, XY-Wing)

**Files:**
- Modify: `sudoku/solver.py`

- [ ] **Step 1: Add X-Wing method**

Add to `SudokuSolver`:

```python
	def _find_x_wing(self, cell):
		"""A candidate appears in exactly two positions in two rows, forming a rectangle - eliminates from columns."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		# row-based X-Wing
		for value in range(1, 10):
			# find rows where value appears in exactly 2 columns
			row_positions = {}
			for rr in range(9):
				cols = [cc for cc in range(9) if value in self.candidates[rr][cc]]
				if len(cols) == 2:
					row_positions[rr] = cols
			# find two rows with same column pair
			rows_list = list(row_positions.keys())
			for i in range(len(rows_list)):
				for j in range(i + 1, len(rows_list)):
					r1, r2 = rows_list[i], rows_list[j]
					if row_positions[r1] == row_positions[r2]:
						c1, c2 = row_positions[r1]
						# eliminate value from these columns in other rows
						eliminations = []
						for rr in range(9):
							if rr == r1 or rr == r2:
								continue
							for cc in (c1, c2):
								if value in self.candidates[rr][cc]:
									self.candidates[rr][cc].discard(value)
									eliminations.append(((rr, cc), value))
						if eliminations:
							corners = [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]
							explanation_prefix = (
								f"X-Wing: {value} bildet ein Rechteck in Zeile {r1+1}/{r2+1}, "
								f"Spalte {c1+1}/{c2+1} und wird aus dem Rest dieser Spalten eliminiert."
							)
							result = self._check_after_elimination(
								cell, [((cr, cc), 0) for cr, cc in corners] + eliminations,
								"X-Wing", explanation_prefix,
							)
							if result:
								return result

		# column-based X-Wing
		for value in range(1, 10):
			col_positions = {}
			for cc in range(9):
				rows = [rr for rr in range(9) if value in self.candidates[rr][cc]]
				if len(rows) == 2:
					col_positions[cc] = rows
			cols_list = list(col_positions.keys())
			for i in range(len(cols_list)):
				for j in range(i + 1, len(cols_list)):
					c1, c2 = cols_list[i], cols_list[j]
					if col_positions[c1] == col_positions[c2]:
						r1, r2 = col_positions[c1]
						eliminations = []
						for cc in range(9):
							if cc == c1 or cc == c2:
								continue
							for rr in (r1, r2):
								if value in self.candidates[rr][cc]:
									self.candidates[rr][cc].discard(value)
									eliminations.append(((rr, cc), value))
						if eliminations:
							corners = [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]
							explanation_prefix = (
								f"X-Wing: {value} bildet ein Rechteck in Spalte {c1+1}/{c2+1}, "
								f"Zeile {r1+1}/{r2+1} und wird aus dem Rest dieser Zeilen eliminiert."
							)
							result = self._check_after_elimination(
								cell, [((cr, cc), 0) for cr, cc in corners] + eliminations,
								"X-Wing", explanation_prefix,
							)
							if result:
								return result
		return None
```

- [ ] **Step 2: Add Swordfish method**

Add to `SudokuSolver`:

```python
	def _find_swordfish(self, cell):
		"""Like X-Wing but with three rows/columns."""
		r, c = cell
		if not self.candidates[r][c]:
			return None
		from itertools import combinations

		# row-based Swordfish
		for value in range(1, 10):
			row_positions = {}
			for rr in range(9):
				cols = [cc for cc in range(9) if value in self.candidates[rr][cc]]
				if 2 <= len(cols) <= 3:
					row_positions[rr] = cols
			if len(row_positions) < 3:
				continue
			for trio_rows in combinations(row_positions.keys(), 3):
				all_cols = set()
				for rr in trio_rows:
					all_cols.update(row_positions[rr])
				if len(all_cols) != 3:
					continue
				# eliminate from these columns in other rows
				eliminations = []
				for rr in range(9):
					if rr in trio_rows:
						continue
					for cc in all_cols:
						if value in self.candidates[rr][cc]:
							self.candidates[rr][cc].discard(value)
							eliminations.append(((rr, cc), value))
				if eliminations:
					fish_cells = [(rr, cc) for rr in trio_rows for cc in row_positions[rr]]
					rows_str = "/".join(str(rr+1) for rr in trio_rows)
					cols_str = "/".join(str(cc+1) for cc in sorted(all_cols))
					explanation_prefix = (
						f"Swordfish: {value} in Zeile {rows_str}, Spalte {cols_str} "
						f"wird aus dem Rest dieser Spalten eliminiert."
					)
					result = self._check_after_elimination(
						cell, [((fr, fc), 0) for fr, fc in fish_cells] + eliminations,
						"Swordfish", explanation_prefix,
					)
					if result:
						return result

		# column-based Swordfish
		for value in range(1, 10):
			col_positions = {}
			for cc in range(9):
				rows = [rr for rr in range(9) if value in self.candidates[rr][cc]]
				if 2 <= len(rows) <= 3:
					col_positions[cc] = rows
			if len(col_positions) < 3:
				continue
			for trio_cols in combinations(col_positions.keys(), 3):
				all_rows = set()
				for cc in trio_cols:
					all_rows.update(col_positions[cc])
				if len(all_rows) != 3:
					continue
				eliminations = []
				for cc in range(9):
					if cc in trio_cols:
						continue
					for rr in all_rows:
						if value in self.candidates[rr][cc]:
							self.candidates[rr][cc].discard(value)
							eliminations.append(((rr, cc), value))
				if eliminations:
					fish_cells = [(rr, cc) for cc in trio_cols for rr in col_positions[cc]]
					cols_str = "/".join(str(cc+1) for cc in trio_cols)
					rows_str = "/".join(str(rr+1) for rr in sorted(all_rows))
					explanation_prefix = (
						f"Swordfish: {value} in Spalte {cols_str}, Zeile {rows_str} "
						f"wird aus dem Rest dieser Zeilen eliminiert."
					)
					result = self._check_after_elimination(
						cell, [((fr, fc), 0) for fr, fc in fish_cells] + eliminations,
						"Swordfish", explanation_prefix,
					)
					if result:
						return result
		return None
```

- [ ] **Step 3: Add XY-Wing method**

Add to `SudokuSolver`:

```python
	def _find_xy_wing(self, cell):
		"""Three cells with two candidates each forming an XY-Wing pattern."""
		r, c = cell
		if not self.candidates[r][c]:
			return None

		# find all bi-value cells
		bi_cells = []
		for rr in range(9):
			for cc in range(9):
				if len(self.candidates[rr][cc]) == 2:
					bi_cells.append((rr, cc))

		def sees(cell1, cell2):
			"""Check if two cells share a row, column, or box."""
			r1, c1 = cell1
			r2, c2 = cell2
			if r1 == r2 or c1 == c2:
				return True
			return (r1 // 3 == r2 // 3) and (c1 // 3 == c2 // 3)

		for pivot_r, pivot_c in bi_cells:
			pivot_cands = self.candidates[pivot_r][pivot_c]
			x, y = sorted(pivot_cands)
			# find wings
			for w1r, w1c in bi_cells:
				if (w1r, w1c) == (pivot_r, pivot_c):
					continue
				if not sees((pivot_r, pivot_c), (w1r, w1c)):
					continue
				w1_cands = self.candidates[w1r][w1c]
				# wing1 must share one candidate with pivot and have one unique
				shared1 = pivot_cands & w1_cands
				if len(shared1) != 1:
					continue
				z_candidates = w1_cands - shared1
				if len(z_candidates) != 1:
					continue
				z = next(iter(z_candidates))
				if z in pivot_cands:
					continue  # z must not be in pivot

				for w2r, w2c in bi_cells:
					if (w2r, w2c) in ((pivot_r, pivot_c), (w1r, w1c)):
						continue
					if not sees((pivot_r, pivot_c), (w2r, w2c)):
						continue
					w2_cands = self.candidates[w2r][w2c]
					shared2 = pivot_cands & w2_cands
					if len(shared2) != 1:
						continue
					if shared2 == shared1:
						continue  # wings must share different candidates with pivot
					if z not in w2_cands:
						continue
					# found XY-Wing: eliminate z from cells that see both wings
					eliminations = []
					for rr in range(9):
						for cc in range(9):
							if (rr, cc) in ((pivot_r, pivot_c), (w1r, w1c), (w2r, w2c)):
								continue
							if z in self.candidates[rr][cc]:
								if sees((rr, cc), (w1r, w1c)) and sees((rr, cc), (w2r, w2c)):
									self.candidates[rr][cc].discard(z)
									eliminations.append(((rr, cc), z))
					if eliminations:
						explanation_prefix = (
							f"XY-Wing: Pivot Z{pivot_r+1}S{pivot_c+1} ({x}/{y}) mit "
							f"Flügel Z{w1r+1}S{w1c+1} und Z{w2r+1}S{w2c+1} - "
							f"{z} wird aus gemeinsam sichtbaren Feldern eliminiert."
						)
						result = self._check_after_elimination(
							cell,
							[((pivot_r, pivot_c), 0), ((w1r, w1c), 0), ((w2r, w2c), 0)] + eliminations,
							"XY-Wing", explanation_prefix,
						)
						if result:
							return result
		return None
```

- [ ] **Step 4: Verify import**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.solver import SudokuSolver; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add sudoku/solver.py
git commit -m "feat: add advanced solving techniques (X-Wing, Swordfish, XY-Wing)"
```

---

### Task 6: Integrate Solver into Game Logic

**Files:**
- Modify: `sudoku/game.py:1-124`

- [ ] **Step 1: Add solver import and split hint into prepare/confirm**

In `sudoku/game.py`, add the import at the top:

```python
from sudoku.solver import SudokuSolver, HintResult
```

Replace the existing `use_hint` method (lines 102-124) with two new methods:

```python
	def prepare_hint(self, row, col):
		"""Prepare a hint using technique-based solving. Returns HintResult or None.
		Does NOT place the number or consume the hint."""
		if self.hints_remaining <= 0:
			return None
		if self.given[row][col]:
			return None
		correct = self.solution[row][col]
		if self.board[row][col] == correct:
			return None

		# try solver
		solver = SudokuSolver(self.board, self.difficulty)
		result = solver.find_hint(target_cell=(row, col))
		if result:
			return result

		# fallback: use pre-computed solution
		return HintResult(
			cell=(row, col),
			value=correct,
			technique="Fallback",
			explanation=f"Die Lösung zeigt, dass hier eine {correct} hingehört.",
			highlight_cells=[],
		)

	def confirm_hint(self, hint_result):
		"""Confirm and place a prepared hint. Called after user clicks 'Verstanden'."""
		row, col = hint_result.cell
		correct = hint_result.value
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
			"technique": hint_result.technique,
		})
		self.redo_stack.clear()
		self.hints_remaining -= 1
		return True
```

- [ ] **Step 2: Verify import**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.game import SudokuGame; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add sudoku/game.py
git commit -m "feat: split hint into prepare/confirm phases with solver integration"
```

---

### Task 7: Board Overlay Rendering and Interaction

**Files:**
- Modify: `sudoku/board.py`

- [ ] **Step 1: Add overlay imports and attributes**

In `sudoku/board.py`, update the imports to add the hint overlay colors and QPushButton:

```python
from PySide6.QtWidgets import QWidget, QSizePolicy, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QFont, QColor, QPen, QFontMetrics
from sudoku.styles import (
	GRID_BG, GRID_BOX_BORDER, GRID_CELL_BORDER,
	GIVEN_NUMBER, PLAYER_CORRECT, PLAYER_WRONG,
	SELECTED_CELL, SAME_NUMBER_HIGHLIGHT, NOTES_COLOR,
	PAUSE_OVERLAY, LOCK_OVERLAY, TEXT, BASE, SURFACE0, BLUE,
	HINT_TARGET, HINT_EVIDENCE, HINT_DIM,
)
```

Add `hint_confirmed` signal to the class:

```python
class SudokuBoard(QWidget):
	number_entered = Signal(int)  # 1-9
	clear_requested = Signal()
	cell_selected = Signal(int, int)
	hint_confirmed = Signal()
```

In `__init__`, add overlay state and the "Verstanden" button:

```python
	def __init__(self):
		super().__init__()
		self.game = None  # SudokuGame reference
		self.selected = None  # (row, col) or None
		self.paused = False
		self.locked = False  # "Neues Spiel" selection mode
		self.overlay = None  # HintResult or None
		self.setFocusPolicy(Qt.StrongFocus)
		self.setMinimumSize(300, 300)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

		# "Verstanden" button (hidden until overlay active)
		self.verstanden_btn = QPushButton("Verstanden", self)
		self.verstanden_btn.setFocusPolicy(Qt.NoFocus)
		self.verstanden_btn.setVisible(False)
		self.verstanden_btn.setStyleSheet(f"""
			QPushButton {{
				background: {BLUE.name()};
				color: {BASE.name()};
				border: none;
				border-radius: 8px;
				font-size: 13px;
				font-weight: bold;
				padding: 6px 16px;
			}}
			QPushButton:hover {{
				background: {BLUE.lighter(110).name()};
			}}
		""")
		self.verstanden_btn.clicked.connect(self._on_verstanden)
```

- [ ] **Step 2: Add overlay rendering to paintEvent**

Add the following method and modify `paintEvent`. Insert this block at the end of `paintEvent`, just before `p.end()` and after the locked overlay block:

```python
		# hint overlay
		if self.overlay:
			involved = set(self.overlay.highlight_cells)
			involved.add(self.overlay.cell)
			# dim uninvolved cells
			for r in range(9):
				for c in range(9):
					if (r, c) not in involved:
						p.fillRect(x_off + c * cell, y_off + r * cell, cell, cell, HINT_DIM)
			# highlight evidence cells
			for r, c in self.overlay.highlight_cells:
				p.fillRect(x_off + c * cell, y_off + r * cell, cell, cell, HINT_EVIDENCE)
			# highlight target cell
			tr, tc = self.overlay.cell
			p.fillRect(x_off + tc * cell, y_off + tr * cell, cell, cell, HINT_TARGET)
			# draw target value in the target cell
			p.setPen(QColor("#a6e3a1"))  # Catppuccin Green
			font = QFont("Sans", max(cell // 3, 10))
			font.setBold(True)
			p.setFont(font)
			p.drawText(
				x_off + tc * cell, y_off + tr * cell, cell, cell,
				Qt.AlignCenter, str(self.overlay.value),
			)

			# explanation text bar below grid
			bar_y = y_off + grid_size + 8
			bar_h = 48
			bar_x = x_off
			bar_w = grid_size
			p.setBrush(SURFACE0)
			p.setPen(Qt.NoPen)
			p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 8, 8)
			# text
			p.setPen(TEXT)
			text_font = QFont("Sans", 10)
			p.setFont(text_font)
			text_rect_w = bar_w - 120  # leave room for button
			p.drawText(
				bar_x + 12, bar_y, text_rect_w, bar_h,
				Qt.AlignVCenter | Qt.TextWordWrap, self.overlay.explanation,
			)
			# position the Verstanden button
			self.verstanden_btn.setVisible(True)
			self.verstanden_btn.move(bar_x + bar_w - 110, bar_y + 8)
			self.verstanden_btn.setFixedSize(100, 32)
```

- [ ] **Step 3: Add input blocking and verstanden handler**

Modify `mousePressEvent` and `keyPressEvent` to block input during overlay. Add overlay guard at the top of each:

In `mousePressEvent`, change the guard:
```python
	def mousePressEvent(self, event):
		if not self.game or self.paused or self.locked or self.overlay:
			return
```

In `keyPressEvent`, change the guard:
```python
	def keyPressEvent(self, event):
		if not self.game or self.paused or self.locked or self.overlay:
			return
```

Add the verstanden handler:

```python
	def _on_verstanden(self):
		"""User clicked 'Verstanden' - dismiss overlay."""
		self.overlay = None
		self.verstanden_btn.setVisible(False)
		self.hint_confirmed.emit()
		self.update()
```

- [ ] **Step 4: Verify import**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.board import SudokuBoard; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add sudoku/board.py
git commit -m "feat: add hint overlay rendering and Verstanden button to board"
```

---

### Task 8: Wire Two-Phase Hint Flow in MainWindow

**Files:**
- Modify: `sudoku/main.py:61,205-212`

- [ ] **Step 1: Connect hint_confirmed signal**

In `sudoku/main.py`, add the `hint_confirmed` connection after the existing `cell_selected` connection (around line 51):

```python
		self.board.hint_confirmed.connect(self.on_hint_confirmed)
```

- [ ] **Step 2: Replace on_hint method**

Replace the existing `on_hint` method (lines 205-212) with:

```python
	def on_hint(self):
		if not self.game or self.game.paused or not self.board.selected:
			return
		r, c = self.board.selected
		result = self.game.prepare_hint(r, c)
		if not result:
			return
		# if solver found a different cell, move selection there
		if result.cell != (r, c):
			self.board.selected = result.cell
		self.board.overlay = result
		self.board.update()

	def on_hint_confirmed(self):
		"""Called when user clicks 'Verstanden' after seeing hint overlay."""
		if not self.game or not self.board.overlay:
			return
		result = self.board.overlay
		self.game.confirm_hint(result)
		self.board.update()
		self.controls.update_hint_badge(self.game.hints_remaining)
		self.check_completion()
```

- [ ] **Step 3: Verify the app launches**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -c "from sudoku.main import MainWindow; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add sudoku/main.py
git commit -m "feat: wire two-phase hint flow with overlay in MainWindow"
```

---

### Task 9: Manual Testing and Polish

**Files:**
- Possibly modify: `sudoku/board.py`, `sudoku/solver.py`

- [ ] **Step 1: Launch the app and test a hint on Leicht**

Run: `cd "/mnt/980 Pro/Projects/Programs/Sudoku-qt" && python -m sudoku.main`

Test: Start a Leicht game, select an empty cell, click Hinweis. Verify:
- Overlay appears with dimmed cells, highlighted evidence, green target cell
- Explanation text is readable
- "Verstanden" button is visible and dismisses overlay
- Number is placed after dismissal
- Hint badge decrements

- [ ] **Step 2: Test hint on higher difficulties**

Start Schwer and Experte games. Verify hints still work (may fall back more often since puzzles aren't generated by technique difficulty).

- [ ] **Step 3: Test undo/redo of hints**

After confirming a hint, press Ctrl+Z. Verify the number is removed and hint count restores. Press Ctrl+Y. Verify redo works.

- [ ] **Step 4: Test fallback behavior**

If a puzzle has no logically explainable cells for the selected cell, verify the fallback message appears: "Die Lösung zeigt, dass hier eine X hingehört."

- [ ] **Step 5: Fix any visual issues found during testing**

Adjust text bar height, button position, or font sizes as needed based on how the overlay looks at different window sizes.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "fix: polish hint overlay after manual testing"
```

Only commit this if changes were made during testing.
