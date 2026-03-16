import sys
import json
import random
import time
from pathlib import Path
from PySide6.QtWidgets import (
	QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QPushButton, QLabel, QDialog, QTableWidget, QTableWidgetItem,
	QMessageBox, QMenu, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPainter, QFont, QColor, QPen, QKeySequence, QShortcut
from datetime import date


class SudokuGenerator:
	@staticmethod
	def _solve_count(board, limit=2):
		"""Count solutions up to limit. board is modified in place."""
		# find first empty cell
		for r in range(9):
			for c in range(9):
				if board[r][c] == 0:
					count = 0
					for num in range(1, 10):
						if SudokuGenerator._is_valid(board, r, c, num):
							board[r][c] = num
							count += SudokuGenerator._solve_count(board, limit - count)
							board[r][c] = 0
							if count >= limit:
								return count
					return count
		return 1  # complete board = 1 solution

	@staticmethod
	def _is_valid(board, row, col, num):
		"""Check if num can be placed at (row, col)."""
		# check row
		if num in board[row]:
			return False
		# check column
		if num in [board[r][col] for r in range(9)]:
			return False
		# check 3x3 box
		box_r, box_c = 3 * (row // 3), 3 * (col // 3)
		for r in range(box_r, box_r + 3):
			for c in range(box_c, box_c + 3):
				if board[r][c] == num:
					return False
		return True

	@staticmethod
	def _generate_full_board():
		"""Generate a complete valid 9x9 board."""
		board = [[0] * 9 for _ in range(9)]
		SudokuGenerator._fill_board(board)
		return board

	@staticmethod
	def _fill_board(board):
		for r in range(9):
			for c in range(9):
				if board[r][c] == 0:
					nums = list(range(1, 10))
					random.shuffle(nums)
					for num in nums:
						if SudokuGenerator._is_valid(board, r, c, num):
							board[r][c] = num
							if SudokuGenerator._fill_board(board):
								return True
							board[r][c] = 0
					return False
		return True

	@staticmethod
	def generate(difficulty):
		"""Generate a puzzle. Returns (puzzle, solution) where puzzle has 0s for empty cells."""
		target_clues = {"Leicht": 36, "Mittel": 30, "Schwer": 25, "Experte": 22}
		target = target_clues[difficulty]

		solution = SudokuGenerator._generate_full_board()
		puzzle = [row[:] for row in solution]

		cells = [(r, c) for r in range(9) for c in range(9)]
		random.shuffle(cells)

		clues = 81
		for r, c in cells:
			if clues <= target:
				break
			backup = puzzle[r][c]
			puzzle[r][c] = 0
			# check uniqueness
			test = [row[:] for row in puzzle]
			if SudokuGenerator._solve_count(test, 2) != 1:
				puzzle[r][c] = backup  # restore
			else:
				clues -= 1

		return puzzle, solution


class SudokuGame:
	def __init__(self, puzzle, solution, difficulty):
		self.board = [row[:] for row in puzzle]
		self.solution = solution
		self.given = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
		self.difficulty = difficulty
		self.undo_stack = []
		self.redo_stack = []
		self.elapsed_seconds = 0
		self.paused = False

	def place_number(self, row, col, num):
		"""Place a number. Returns False if cell is given."""
		if self.given[row][col]:
			return False
		old = self.board[row][col]
		if old == num:
			return False
		self.board[row][col] = num
		self.undo_stack.append((row, col, old, num))
		self.redo_stack.clear()
		return True

	def clear_cell(self, row, col):
		"""Clear a cell. Treated as placing 0."""
		if self.given[row][col]:
			return False
		old = self.board[row][col]
		if old == 0:
			return False
		self.board[row][col] = 0
		self.undo_stack.append((row, col, old, 0))
		self.redo_stack.clear()
		return True

	def undo(self):
		"""Undo last move. Returns (row, col) or None."""
		if not self.undo_stack:
			return None
		row, col, old, new = self.undo_stack.pop()
		self.board[row][col] = old
		self.redo_stack.append((row, col, old, new))
		return (row, col)

	def redo(self):
		"""Redo last undone move. Returns (row, col) or None."""
		if not self.redo_stack:
			return None
		row, col, old, new = self.redo_stack.pop()
		self.board[row][col] = new
		self.undo_stack.append((row, col, old, new))
		return (row, col)

	def get_conflicts(self):
		"""Return set of (row, col) that have conflicts."""
		conflicts = set()
		for r in range(9):
			for c in range(9):
				num = self.board[r][c]
				if num == 0:
					continue
				# check row
				for c2 in range(9):
					if c2 != c and self.board[r][c2] == num:
						conflicts.add((r, c))
						conflicts.add((r, c2))
				# check col
				for r2 in range(9):
					if r2 != r and self.board[r2][c] == num:
						conflicts.add((r, c))
						conflicts.add((r2, c))
				# check box
				box_r, box_c = 3 * (r // 3), 3 * (c // 3)
				for r2 in range(box_r, box_r + 3):
					for c2 in range(box_c, box_c + 3):
						if (r2, c2) != (r, c) and self.board[r2][c2] == num:
							conflicts.add((r, c))
							conflicts.add((r2, c2))
		return conflicts

	def is_complete(self):
		"""Check if the board matches the solution."""
		return self.board == self.solution


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
			"zeit_sekunden": zeit_sekunden
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


if __name__ == "__main__":
	puzzle, solution = SudokuGenerator.generate("Leicht")
	for row in puzzle:
		print(" ".join(str(x) if x else "." for x in row))
