from sudoku.solver import SudokuSolver, HintResult


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
		# notes and hints
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

	def prepare_hint(self, row, col):
		"""Prepare a hint using technique-based solving. Returns HintResult or None."""
		if self.hints_remaining <= 0:
			return None
		if self.given[row][col]:
			return None
		correct = self.solution[row][col]
		if self.board[row][col] == correct:
			return None

		# solve step by step until selected cell is explainable
		solver = SudokuSolver([r[:] for r in self.board], self.difficulty)
		result = solver.solve_until(row, col)
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
		"""Confirm and place a prepared hint. Called after 'Verstanden' click."""
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
