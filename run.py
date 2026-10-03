"""Lanzador para ejecutar FingerMusic sin instalar el paquete (F5 en VS Code).

Uso:  python run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fingermusic.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
