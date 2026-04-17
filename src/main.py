import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from src.board import SudokuBoard
from src.controls import ControlPanel
from src.difficulty_bar import DifficultyBar
from src.game import SudokuGame
from src.generator import GeneratorThread
from src.stats import StatsManager, StatsDialog
from src.styles import BASE, GRID_CONTROLS_GAP


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
		self.board.hint_confirmed.connect(self.on_hint_confirmed)
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
		self.controls.new_game_btn.setEnabled(False)  # no game to restart yet
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
		if not self.game or self.game.paused or self.selecting_difficulty:
			return
		self.notes_mode = not self.notes_mode
		self.controls.notes_mode = self.notes_mode
		self.controls.notes_btn.set_active(self.notes_mode)

	def on_difficulty_selected(self, difficulty):
		"""User clicked a difficulty tab."""
		if self.game and not self.selecting_difficulty:
			return  # ignore clicks when game is running and not in selection mode
		if self.game:
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
			if self.game:
				self.difficulty_bar.set_active(self.game.difficulty)
			self.controls.set_new_game_mode(False)
			if self.game and not self.game.paused:
				self.tick_timer.start()
		elif self.game:
			# enter selection mode - clear any active overlay
			self.selecting_difficulty = True
			self.tick_timer.stop()
			self.board.overlay = None
			self.board.verstanden_btn.setVisible(False)
			self.board.locked = True
			self.board.update()
			self.difficulty_bar.set_enabled(True)
			self.controls.set_new_game_mode(True)

	def _start_generation(self, difficulty):
		self.tick_timer.stop()
		self.game = None
		self.controls.set_controls_enabled(False)
		self.controls.update_timer(0)
		self.difficulty_bar.set_active(difficulty)
		self.difficulty_bar.set_enabled(False)

		if self.generator_thread and self.generator_thread.isRunning():
			# stop the old thread before replacing it
			self.generator_thread.finished.disconnect()
			self.generator_thread.error.disconnect()
			self.generator_thread.quit()
			self.generator_thread.wait(3000)
		self.generator_thread = GeneratorThread(difficulty)
		self.generator_thread.finished.connect(
			lambda p, s: self.on_puzzle_ready(p, s, difficulty)
		)
		self.generator_thread.error.connect(self._on_generator_error)
		self.generator_thread.start()

	def _on_generator_error(self, msg):
		"""Shows error dialog; on_puzzle_ready(None, None) re-enables controls."""
		QMessageBox.critical(self, "Generation failed", f"Could not generate puzzle:\n{msg}")

	def on_puzzle_ready(self, puzzle, solution, difficulty):
		if puzzle is None:
			# generation failed — unblock UI without starting a game
			self.controls.set_controls_enabled(False)
			self.controls.new_game_btn.setEnabled(self.game is not None)
			self.difficulty_bar.set_enabled(True)
			return
		self.game = SudokuGame(puzzle, solution, difficulty)
		self.board.game = self.game
		self.board.selected = None
		self.board.paused = False
		self.board.locked = False
		self.board.overlay = None
		self.board.verstanden_btn.setVisible(False)
		self.board.update()
		self.controls.set_controls_enabled(True)
		self.controls.new_game_btn.setEnabled(True)
		self.controls.update_timer(0)
		self.controls.update_hint_badge(self.game.hints_remaining)
		self.difficulty_bar.set_active(difficulty)
		self.difficulty_bar.set_enabled(False)
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
		result = self.game.prepare_hint(r, c)
		if not result:
			return
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
