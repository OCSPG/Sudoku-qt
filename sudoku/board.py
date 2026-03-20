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
		# notes toggle - pass to parent
		if key == Qt.Key_N:
			event.ignore()
			return
		# arrow navigation
		if self.selected:
			r, c = self.selected
			new_sel = self.selected
			if key == Qt.Key_Up and r > 0:
				new_sel = (r - 1, c)
			elif key == Qt.Key_Down and r < 8:
				new_sel = (r + 1, c)
			elif key == Qt.Key_Left and c > 0:
				new_sel = (r, c - 1)
			elif key == Qt.Key_Right and c < 8:
				new_sel = (r, c + 1)
			if new_sel != self.selected:
				self.selected = new_sel
				self.cell_selected.emit(*self.selected)
				self.update()
