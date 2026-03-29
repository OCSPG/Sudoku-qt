from PySide6.QtGui import QColor


# --- Catppuccin Mocha palette ---
BASE = QColor("#1e1e2e")
MANTLE = QColor("#181825")
CRUST = QColor("#11111b")
SURFACE0 = QColor("#313244")
SURFACE1 = QColor("#45475a")
SURFACE2 = QColor("#585b70")
OVERLAY0 = QColor("#6c7086")
OVERLAY1 = QColor("#7f849c")
TEXT = QColor("#cdd6f4")
SUBTEXT0 = QColor("#a6adc8")
SUBTEXT1 = QColor("#bac2de")
BLUE = QColor("#89b4fa")
RED = QColor("#f38ba8")
LAVENDER = QColor("#b4befe")

# --- Grid colors (white interior) ---
GRID_BG = QColor("#ffffff")
GRID_BOX_BORDER = QColor("#344861")
GRID_CELL_BORDER = QColor("#bec6d4")
GIVEN_NUMBER = QColor("#344861")
PLAYER_CORRECT = QColor("#3b5998")
PLAYER_WRONG = QColor("#f38ba8")
SELECTED_CELL = QColor("#e2ecf7")
SAME_NUMBER_HIGHLIGHT = QColor("#d4e4f7")
NOTES_COLOR = QColor("#7f849c")

# --- Overlay colors ---
PAUSE_OVERLAY = QColor(17, 17, 27, 204)  # Crust at 80%
LOCK_OVERLAY = QColor(49, 50, 68, 153)  # Surface0 at 60%

# --- Hint overlay colors ---
HINT_TARGET = QColor(166, 227, 161, 64)    # Catppuccin Green at ~25% opacity
HINT_EVIDENCE = QColor(243, 139, 168, 51)  # RED at ~20% opacity
HINT_DIM = QColor(17, 17, 27, 153)         # Crust at 60% opacity

# --- Dimensions ---
GRID_CONTROLS_GAP = 8
CONTROL_PANEL_RATIO = 0.35  # right panel width as fraction of available
ACTION_BUTTON_SIZE = 40
NUMPAD_GAP = 6

# --- Difficulty levels ---
DIFFICULTIES = ["Leicht", "Mittel", "Schwer", "Experte", "Meister", "Extrem"]
