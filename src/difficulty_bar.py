from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from src.styles import MANTLE, SURFACE0, BLUE, SUBTEXT0, SUBTEXT1, OVERLAY0, TEXT, DIFFICULTIES


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
					background: transparent;
					font-size: 13px;
					border: 1px solid transparent;
					border-radius: 6px;
					padding: 4px 10px;
				}}
			"""
		if active:
			return f"""
				QPushButton {{
					color: {BLUE.name()};
					background: {SURFACE0.name()};
					font-size: 13px;
					font-weight: bold;
					border: 1px solid {BLUE.name()};
					border-radius: 6px;
					padding: 4px 10px;
				}}
			"""
		return f"""
			QPushButton {{
				color: {SUBTEXT1.name()};
				background: transparent;
				font-size: 13px;
				border: 1px solid {SURFACE0.name()};
				border-radius: 6px;
				padding: 4px 10px;
			}}
			QPushButton:hover {{
				color: {TEXT.name()};
				background: {SURFACE0.name()};
				border: 1px solid {SUBTEXT0.name()};
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
