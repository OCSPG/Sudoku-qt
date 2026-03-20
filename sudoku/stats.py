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
		table.setSortingEnabled(True)
		for i, entry in enumerate(stats_manager.stats):
			table.setItem(i, 0, QTableWidgetItem(entry["datum"]))
			table.setItem(i, 1, QTableWidgetItem(entry["schwierigkeit"]))
			m, s = divmod(entry["zeit_sekunden"], 60)
			table.setItem(i, 2, QTableWidgetItem(f"{m:02d}:{s:02d}"))
		layout.addWidget(table)

		close_btn = QPushButton("Schließen")
		close_btn.clicked.connect(self.close)
		layout.addWidget(close_btn)
