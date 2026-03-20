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
		bg = SURFACE0.lighter(130).name() if self._active else SURFACE0.name()
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
		else:
			self.hint_btn.set_active(True)
			self.hint_btn.setEnabled(True)
			self.hint_badge.show()

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
