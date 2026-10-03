"""Detector de manos basado en el modelo preentrenado MediaPipe Hands."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from fingermusic.config import DetectionSettings
from fingermusic.vision.landmarks import HandLandmarks, HandSide, normalized_to_pixels

logger = logging.getLogger(__name__)


class HandDetectorError(RuntimeError):
    """El modelo de detección de manos no pudo cargarse o ejecutarse."""


class HandDetector:
    """Envuelve ``mediapipe.solutions.hands`` y devuelve ``HandLandmarks``.

    La imagen que recibe ``detect`` debe estar ya espejada (vista "selfie"):
    MediaPipe asume esa orientación al clasificar mano izquierda/derecha.
    """

    def __init__(self, settings: DetectionSettings) -> None:
        self._settings = settings
        self._hands: Any = None
        try:
            import mediapipe as mp  # importación diferida: error claro si falta
        except ImportError as exc:
            raise HandDetectorError(
                "No se encontró la biblioteca 'mediapipe'. "
                "Instala las dependencias con: pip install -r requirements.txt"
            ) from exc
        if not hasattr(mp, "solutions"):
            raise HandDetectorError(
                "La versión instalada de mediapipe no incluye la API 'solutions'. "
                "Usa la versión fijada en requirements.txt (mediapipe==0.10.21)."
            )
        try:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=settings.max_num_hands,
                model_complexity=settings.model_complexity,
                min_detection_confidence=settings.min_detection_confidence,
                min_tracking_confidence=settings.min_tracking_confidence,
            )
        except Exception as exc:  # noqa: BLE001 - mediapipe lanza tipos variados
            raise HandDetectorError(f"No se pudo cargar el modelo de manos: {exc}") from exc
        logger.info("Modelo MediaPipe Hands cargado (complejidad=%d)", settings.model_complexity)

    def detect(self, frame_bgr: np.ndarray) -> list[HandLandmarks]:
        """Detecta las manos de un frame BGR (ya espejado).

        Si MediaPipe etiqueta dos manos con el mismo lado, se conserva la de
        mayor confianza para que cada lado tenga como máximo una mano.
        """
        if self._hands is None:
            raise HandDetectorError("El detector ya fue cerrado")
        height, width = frame_bgr.shape[:2]
        rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])  # BGR -> RGB
        rgb.flags.writeable = False
        try:
            result = self._hands.process(rgb)
        except Exception as exc:  # noqa: BLE001
            raise HandDetectorError(f"Fallo al ejecutar el modelo: {exc}") from exc

        if not result.multi_hand_landmarks:
            return []

        best: dict[HandSide, HandLandmarks] = {}
        for landmarks, handedness in zip(
            result.multi_hand_landmarks, result.multi_handedness, strict=True
        ):
            classification = handedness.classification[0]
            side = HandSide(classification.label)
            points = normalized_to_pixels(
                ((lm.x, lm.y, lm.z) for lm in landmarks.landmark), width, height
            )
            hand = HandLandmarks(points=points, side=side, score=float(classification.score))
            if side not in best or hand.score > best[side].score:
                best[side] = hand
        return list(best.values())

    def close(self) -> None:
        """Libera los recursos del modelo."""
        if self._hands is not None:
            self._hands.close()
            self._hands = None
