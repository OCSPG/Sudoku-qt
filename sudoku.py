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


class SudokuBoard(QWidget):
	number_entered = Signal(int)  # 1-9
	clear_requested = Signal()

	def __init__(self):
		super().__init__()
		self.game: SudokuGame | None = None
		self.selected: tuple[int, int] | None = None
		self.paused = False
		self.setFocusPolicy(Qt.StrongFocus)
		self.setMinimumSize(400, 400)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

	def _grid_params(self):
		"""Calculate grid positioning: returns (cell_size, x_offset, y_offset)."""
		size = min(self.width(), self.height()) - 20  # 10px margin each side
		cell = size // 9
		grid_size = cell * 9
		x_off = (self.width() - grid_size) // 2
		y_off = (self.height() - grid_size) // 2
		return cell, x_off, y_off

	def paintEvent(self, event):
		p = QPainter(self)
		p.setRenderHint(QPainter.Antialiasing)
		cell, x_off, y_off = self._grid_params()
		grid_size = cell * 9
		conflicts = self.game.get_conflicts() if self.game else set()

		# background
		p.fillRect(self.rect(), QColor("#f0f0f0"))
		p.fillRect(x_off, y_off, grid_size, grid_size, QColor("white"))

		if self.game:
			# selected cell highlight
			if self.selected:
				r, c = self.selected
				p.fillRect(x_off + c * cell, y_off + r * cell, cell, cell, QColor("#cce0ff"))

			# numbers
			font = QFont("Sans", max(cell // 3, 10))
			p.setFont(font)
			for r in range(9):
				for c in range(9):
					num = self.game.board[r][c]
					if num == 0:
						continue
					x = x_off + c * cell
					y = y_off + r * cell
					if (r, c) in conflicts:
						p.setPen(QColor("red"))
					elif self.game.given[r][c]:
						p.setPen(QColor("black"))
					else:
						p.setPen(QColor("#1a3a6b"))
					p.drawText(x, y, cell, cell, Qt.AlignCenter, str(num))

		# grid lines
		# thin lines for cells
		p.setPen(QPen(QColor("black"), 1))
		for i in range(10):
			if i % 3 == 0:
				continue  # draw thick ones separately
			p.drawLine(x_off + i * cell, y_off, x_off + i * cell, y_off + grid_size)
			p.drawLine(x_off, y_off + i * cell, x_off + grid_size, y_off + i * cell)
		# thick lines for 3x3 boxes
		p.setPen(QPen(QColor("black"), 3))
		for i in range(0, 10, 3):
			p.drawLine(x_off + i * cell, y_off, x_off + i * cell, y_off + grid_size)
			p.drawLine(x_off, y_off + i * cell, x_off + grid_size, y_off + i * cell)

		# pause overlay
		if self.paused:
			p.fillRect(x_off, y_off, grid_size, grid_size, QColor(255, 255, 255, 220))
			p.setPen(QColor("#333"))
			p.setFont(QFont("Sans", 24, QFont.Bold))
			p.drawText(x_off, y_off, grid_size, grid_size, Qt.AlignCenter, "Pausiert")

		p.end()

	def mousePressEvent(self, event):
		if not self.game or self.paused:
			return
		cell, x_off, y_off = self._grid_params()
		c = (event.position().x() - x_off) // cell
		r = (event.position().y() - y_off) // cell
		if 0 <= r < 9 and 0 <= c < 9:
			self.selected = (int(r), int(c))
			self.update()

	def keyPressEvent(self, event):
		if not self.game or self.paused:
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
			self.update()


class GeneratorThread(QThread):
	finished = Signal(list, list)  # puzzle, solution

	def __init__(self, difficulty):
		super().__init__()
		self.difficulty = difficulty

	def run(self):
		puzzle, solution = SudokuGenerator.generate(self.difficulty)
		self.finished.emit(puzzle, solution)


class StatsDialog(QDialog):
	def __init__(self, stats_manager, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Statistik")
		self.setMinimumSize(450, 400)
		layout = QVBoxLayout(self)

		# summary
		total = len(stats_manager.stats)
		best = stats_manager.get_best_times()
		summary = f"Gesamt: {total} Spiele"
		for diff in ["Leicht", "Mittel", "Schwer", "Experte"]:
			if diff in best:
				m, s = divmod(best[diff], 60)
				summary += f"  |  {diff}: {m:02d}:{s:02d}"
		summary_label = QLabel(summary)
		layout.addWidget(summary_label)

		# table
		table = QTableWidget(total, 3)
		table.setHorizontalHeaderLabels(["Datum", "Schwierigkeit", "Zeit"])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		for i, entry in enumerate(stats_manager.stats):
			table.setItem(i, 0, QTableWidgetItem(entry["datum"]))
			table.setItem(i, 1, QTableWidgetItem(entry["schwierigkeit"]))
			m, s = divmod(entry["zeit_sekunden"], 60)
			table.setItem(i, 2, QTableWidgetItem(f"{m:02d}:{s:02d}"))
		layout.addWidget(table)

		# close button
		close_btn = QPushButton("Schließen")
		close_btn.clicked.connect(self.close)
		layout.addWidget(close_btn)


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Sudoku")
		self.setMinimumSize(500, 600)
		self.resize(600, 750)

		self.game = None
		self.generator_thread = None
		self.stats_manager = StatsManager()

		# central widget with vertical layout
		central = QWidget()
		self.setCentralWidget(central)
		main_layout = QVBoxLayout(central)

		# --- top toolbar ---
		toolbar = QHBoxLayout()
		main_layout.addLayout(toolbar)

		# "Neues Spiel" with difficulty menu
		self.new_game_btn = QPushButton("Neues Spiel")
		menu = QMenu(self)
		for diff in ["Leicht", "Mittel", "Schwer", "Experte"]:
			menu.addAction(diff, lambda d=diff: self.start_new_game(d))
		self.new_game_btn.setMenu(menu)
		toolbar.addWidget(self.new_game_btn)

		toolbar.addStretch()

		# timer label
		self.timer_label = QLabel("00:00")
		self.timer_label.setFont(QFont("Sans", 16, QFont.Bold))
		toolbar.addWidget(self.timer_label)

		toolbar.addStretch()

		# pause button
		self.pause_btn = QPushButton("Pause")
		self.pause_btn.setEnabled(False)
		self.pause_btn.clicked.connect(self.toggle_pause)
		toolbar.addWidget(self.pause_btn)

		# stats button
		stats_btn = QPushButton("Statistik")
		stats_btn.setFocusPolicy(Qt.NoFocus)
		stats_btn.clicked.connect(self.show_stats)
		toolbar.addWidget(stats_btn)

		# --- board ---
		self.board = SudokuBoard()
		self.board.number_entered.connect(self.on_number_entered)
		self.board.clear_requested.connect(self.on_clear_clicked)
		main_layout.addWidget(self.board, 1)

		# --- bottom bar ---
		bottom = QHBoxLayout()
		main_layout.addLayout(bottom)

		# number buttons 1-9
		self.num_buttons = []
		for i in range(1, 10):
			btn = QPushButton(str(i))
			btn.setFocusPolicy(Qt.NoFocus)
			btn.setEnabled(False)
			btn.clicked.connect(lambda checked, n=i: self.on_number_entered(n))
			bottom.addWidget(btn)
			self.num_buttons.append(btn)

		# separator
		bottom.addSpacing(10)

		# clear button
		self.clear_btn = QPushButton("Löschen")
		self.clear_btn.setFocusPolicy(Qt.NoFocus)
		self.clear_btn.setEnabled(False)
		self.clear_btn.clicked.connect(self.on_clear_clicked)
		bottom.addWidget(self.clear_btn)

		# undo button
		self.undo_btn = QPushButton("Rückgängig")
		self.undo_btn.setFocusPolicy(Qt.NoFocus)
		self.undo_btn.setEnabled(False)
		self.undo_btn.clicked.connect(self.on_undo)
		bottom.addWidget(self.undo_btn)

		# redo button
		self.redo_btn = QPushButton("Wiederholen")
		self.redo_btn.setFocusPolicy(Qt.NoFocus)
		self.redo_btn.setEnabled(False)
		self.redo_btn.clicked.connect(self.on_redo)
		bottom.addWidget(self.redo_btn)

		# game timer (1 second tick)
		self.tick_timer = QTimer(self)
		self.tick_timer.setInterval(1000)
		self.tick_timer.timeout.connect(self.on_timer_tick)

		# keyboard shortcuts
		QShortcut(QKeySequence("Ctrl+Z"), self, self.on_undo)
		QShortcut(QKeySequence("Ctrl+Y"), self, self.on_redo)

	def _set_controls_enabled(self, enabled):
		"""Enable/disable all game controls."""
		for btn in self.num_buttons:
			btn.setEnabled(enabled)
		self.clear_btn.setEnabled(enabled)
		self.undo_btn.setEnabled(enabled)
		self.redo_btn.setEnabled(enabled)
		self.pause_btn.setEnabled(enabled)

	def start_new_game(self, difficulty):
		# confirm if game in progress
		if self.game:
			result = QMessageBox.question(
				self, "Neues Spiel",
				"Aktuelles Spiel abbrechen?",
				QMessageBox.Yes | QMessageBox.No
			)
			if result == QMessageBox.No:
				return

		# stop current game
		self.tick_timer.stop()
		self.game = None
		self._set_controls_enabled(False)
		self.timer_label.setText("Generiere...")

		# generate in background (disconnect old thread if still running)
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
		self.board.update()
		self._set_controls_enabled(True)
		self.pause_btn.setText("Pause")
		self.timer_label.setText("00:00")
		self.tick_timer.start()
		self.board.setFocus()

	def on_number_entered(self, num):
		if not self.game or self.game.paused or not self.board.selected:
			return
		r, c = self.board.selected
		self.game.place_number(r, c, num)
		self.board.update()
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

	def on_redo(self):
		if not self.game or self.game.paused:
			return
		result = self.game.redo()
		if result:
			self.board.selected = result
		self.board.update()

	def toggle_pause(self):
		if not self.game:
			return
		self.game.paused = not self.game.paused
		self.board.paused = self.game.paused
		if self.game.paused:
			self.tick_timer.stop()
			self.pause_btn.setText("Fortsetzen")
		else:
			self.tick_timer.start()
			self.pause_btn.setText("Pause")
		self.board.update()

	def on_timer_tick(self):
		if self.game:
			self.game.elapsed_seconds += 1
			m, s = divmod(self.game.elapsed_seconds, 60)
			self.timer_label.setText(f"{m:02d}:{s:02d}")

	def check_completion(self):
		if not self.game or not self.game.is_complete():
			return
		self.tick_timer.stop()
		m, s = divmod(self.game.elapsed_seconds, 60)
		self.stats_manager.save_game(self.game.difficulty, self.game.elapsed_seconds)
		QMessageBox.information(self, "Gewonnen!", f"Gelöst in {m:02d}:{s:02d}!")
		self._set_controls_enabled(False)
		# keep board.game so the solved puzzle stays visible
		self.game = None

	def show_stats(self):
		dialog = StatsDialog(self.stats_manager, self)
		dialog.exec()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
