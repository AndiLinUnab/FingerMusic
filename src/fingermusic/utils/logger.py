"""Configuración del sistema de logging."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: int = logging.INFO, log_file: Path | None = None) -> None:
    """Configura el logging de la aplicación.

    Args:
        level: nivel mínimo mostrado en consola.
        log_file: si se indica, también se escribe un archivo rotativo (DEBUG).
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file, maxBytes=512_000, backupCount=2, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(_FORMAT))
            root.addHandler(file_handler)
        except OSError as exc:
            logging.getLogger(__name__).warning("No se pudo crear el archivo de log: %s", exc)

    # Las bibliotecas externas son muy verbosas.
    for noisy in ("matplotlib", "PIL", "absl"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
