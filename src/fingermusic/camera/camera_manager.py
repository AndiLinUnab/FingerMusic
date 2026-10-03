"""Captura de video con OpenCV y manejo de errores de cámara."""

from __future__ import annotations

import logging
import sys

import cv2
import numpy as np

from fingermusic.config import CameraSettings

logger = logging.getLogger(__name__)


class CameraError(RuntimeError):
    """No se pudo abrir o leer la cámara."""


class CameraManager:
    """Abre la cámara web y entrega frames BGR (opcionalmente espejados)."""

    def __init__(self, settings: CameraSettings) -> None:
        self._settings = settings
        self._capture: cv2.VideoCapture | None = None
        self._failures = 0

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    def open(self) -> None:
        """Abre la cámara.

        Raises:
            CameraError: si no existe, está ocupada o no hay permiso de acceso.
        """
        if self.is_open:
            return
        s = self._settings
        # En Windows, DirectShow abre más rápido y es más estable que MSMF.
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        capture = cv2.VideoCapture(s.index, backend)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"No se pudo abrir la camara {s.index}. Comprueba que existe, que no la usa "
                "otra aplicacion (Zoom, Teams...) y que Windows permite el acceso: "
                "Configuracion > Privacidad > Camara."
            )
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, s.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, s.height)
        capture.set(cv2.CAP_PROP_FPS, s.fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # menos latencia
        self._capture = capture
        self._failures = 0
        logger.info(
            "Camara %d abierta (%dx%d)",
            s.index,
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def read(self) -> np.ndarray | None:
        """Lee un frame.

        Returns:
            El frame BGR, o ``None`` si este frame falló (error transitorio).

        Raises:
            CameraError: si la cámara no está abierta o falla demasiadas veces seguidas.
        """
        if self._capture is None:
            raise CameraError("La camara no esta abierta")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._failures += 1
            if self._failures >= self._settings.max_read_failures:
                raise CameraError("Se perdio la senal de la camara (¿desconectada o en uso?).")
            return None
        self._failures = 0
        return cv2.flip(frame, 1) if self._settings.mirror else frame

    def release(self) -> None:
        """Cierra la cámara si está abierta."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Camara liberada")
