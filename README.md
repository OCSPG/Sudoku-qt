# Sudoku

Ein Sudoku-Spiel mit PySide6.

## Features

- 4 Schwierigkeitsgrade: Leicht, Mittel, Schwer, Experte
- Timer mit Pause
- Rückgängig/Wiederholen (auch Ctrl+Z/Ctrl+Y)
- Falsche Zahlen werden sofort rot markiert
- Statistik mit Bestzeiten pro Schwierigkeit

## Installation

Voraussetzung: [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/OCSPG/Sudoku-qt.git
cd Sudoku-qt
uv run sudoku
```

Oder global installieren:

```bash
uv tool install git+https://github.com/OCSPG/Sudoku-qt.git
sudoku
```

## Standalone Binary

```bash
uv run pyinstaller --onefile --name sudoku --windowed sudoku.py
cp dist/sudoku ~/.local/bin/
```

## Lizenz

MIT
