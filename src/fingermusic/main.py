"""Punto de entrada de FingerMusic."""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from fingermusic import __version__
from fingermusic.config import get_settings
from fingermusic.config.settings import LOGS_DIR
from fingermusic.utils.logger import setup_logging

logger = logging.getLogger("fingermusic")


def build_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="fingermusic",
        description=(
            "Instrumento musical virtual: toca notas flexionando los dedos frente a la cámara."
        ),
    )
    parser.add_argument(
        "--camera", type=int, default=None, help="índice de la cámara (por defecto 0)"
    )
    parser.add_argument("--debug", action="store_true", help="muestra mensajes DEBUG en consola")
    parser.add_argument(
        "--swap-hands",
        action="store_true",
        help="la mano derecha toca DO..SOL y la izquierda LA..MI'",
    )
    parser.add_argument(
        "--regenerate-sounds",
        action="store_true",
        help="vuelve a generar los 10 archivos .wav de assets/sounds y termina",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ejecuta FingerMusic. Devuelve el código de salida del proceso."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.debug else logging.INFO, LOGS_DIR / "fingermusic.log")

    try:
        settings = get_settings()
        if args.camera is not None:
            settings = dataclasses.replace(
                settings, camera=dataclasses.replace(settings.camera, index=args.camera)
            )
            settings.validate()

        if args.regenerate_sounds:
            from fingermusic.audio.synth import generate_all_sounds

            generate_all_sounds(
                settings.audio.sounds_dir,
                settings.audio.note_duration,
                settings.audio.error_duration,
                settings.audio.sample_rate,
                overwrite=True,
            )
            logger.info("Sonidos regenerados en %s", settings.audio.sounds_dir)
            return 0

        from fingermusic.app import Application
        from fingermusic.vision.hand_detector import HandDetectorError

        try:
            return Application(settings, swap_hands=args.swap_hands).run()
        except HandDetectorError as exc:
            logger.error("%s", exc)
            print(f"\nERROR: {exc}", file=sys.stderr)
            return 1
    except ImportError as exc:
        print(
            f"\nERROR: falta una dependencia ({exc}).\n"
            "Activa el entorno virtual e instala: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"\nERROR de configuración: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception:  # noqa: BLE001 - último recurso: evitar un traceback al usuario
        logger.exception("Error inesperado")
        print(
            f"\nOcurrió un error inesperado. Detalles en {LOGS_DIR / 'fingermusic.log'}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
