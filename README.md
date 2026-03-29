# Sudoku

A Sudoku game built with PySide6.

## Features

- 4 difficulty levels: Leicht, Mittel, Schwer, Experte
- Timer with pause
- Undo/redo (also Ctrl+Z/Ctrl+Y)
- Wrong numbers are immediately highlighted in red
- Stats with best times per difficulty

## Installation

Requires: [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/OCSPG/Sudoku-qt.git
cd Sudoku-qt
uv run sudoku
```

Or install globally:

```bash
uv tool install git+https://github.com/OCSPG/Sudoku-qt.git
sudoku
```

## Standalone Binary

```bash
uv add --dev pyinstaller
uv run pyinstaller --onefile --name sudoku --windowed --collect-submodules src src/main.py
cp dist/sudoku ~/.local/bin/
```

## License

MIT
