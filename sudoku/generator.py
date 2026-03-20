import random
from PySide6.QtCore import QThread, Signal


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
		target_clues = {
			"Leicht": 36,
			"Mittel": 30,
			"Schwer": 25,
			"Experte": 22,
			"Meister": 20,
			"Extrem": 17,
		}
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


class GeneratorThread(QThread):
	finished = Signal(list, list)  # puzzle, solution

	def __init__(self, difficulty):
		super().__init__()
		self.difficulty = difficulty

	def run(self):
		puzzle, solution = SudokuGenerator.generate(self.difficulty)
		self.finished.emit(puzzle, solution)
