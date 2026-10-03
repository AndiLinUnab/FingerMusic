"""Representación de los 21 landmarks de una mano y conversión de coordenadas."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import IntEnum, StrEnum

import numpy as np

NUM_LANDMARKS = 21


class HandSide(StrEnum):
    """Lateralidad de la mano **del usuario** (la imagen se procesa en espejo)."""

    LEFT = "Left"
    RIGHT = "Right"

    @property
    def label(self) -> str:
        return "IZQUIERDA" if self is HandSide.LEFT else "DERECHA"


class Finger(IntEnum):
    """Dedos de la mano, ordenados del pulgar al meñique."""

    THUMB = 0
    INDEX = 1
    MIDDLE = 2
    RING = 3
    PINKY = 4

    @property
    def label(self) -> str:
        """Nombre en español sin acentos (la fuente de OpenCV no los soporta)."""
        return _FINGER_LABELS[self]


_FINGER_LABELS = {
    Finger.THUMB: "Pulgar",
    Finger.INDEX: "Indice",
    Finger.MIDDLE: "Medio",
    Finger.RING: "Anular",
    Finger.PINKY: "Menique",
}


class Landmark(IntEnum):
    """Índices de los landmarks según el modelo MediaPipe Hands."""

    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


#: Cadena de articulaciones de cada dedo: (base, articulación media, articulación distal, punta).
FINGER_JOINTS: dict[Finger, tuple[Landmark, Landmark, Landmark, Landmark]] = {
    Finger.THUMB: (
        Landmark.THUMB_CMC,
        Landmark.THUMB_MCP,
        Landmark.THUMB_IP,
        Landmark.THUMB_TIP,
    ),
    Finger.INDEX: (
        Landmark.INDEX_MCP,
        Landmark.INDEX_PIP,
        Landmark.INDEX_DIP,
        Landmark.INDEX_TIP,
    ),
    Finger.MIDDLE: (
        Landmark.MIDDLE_MCP,
        Landmark.MIDDLE_PIP,
        Landmark.MIDDLE_DIP,
        Landmark.MIDDLE_TIP,
    ),
    Finger.RING: (
        Landmark.RING_MCP,
        Landmark.RING_PIP,
        Landmark.RING_DIP,
        Landmark.RING_TIP,
    ),
    Finger.PINKY: (
        Landmark.PINKY_MCP,
        Landmark.PINKY_PIP,
        Landmark.PINKY_DIP,
        Landmark.PINKY_TIP,
    ),
}

#: Conexiones del esqueleto de la mano (para dibujarlo).
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


@dataclass(frozen=True)
class HandLandmarks:
    """Landmarks de una mano en coordenadas de píxel.

    Attributes:
        points: array ``(21, 3)`` con (x, y, z) en píxeles. ``z`` se escala con
            el ancho de la imagen, igual que ``x`` (convención de MediaPipe).
        side: lateralidad de la mano del usuario.
        score: confianza de la clasificación de lateralidad (0..1).
    """

    points: np.ndarray
    side: HandSide
    score: float = 1.0

    def __post_init__(self) -> None:
        if self.points.shape != (NUM_LANDMARKS, 3):
            raise ValueError(
                f"Se esperaban {NUM_LANDMARKS} landmarks (21, 3), llegó {self.points.shape}"
            )

    def point(self, landmark: Landmark) -> np.ndarray:
        """Devuelve las coordenadas (x, y, z) de un landmark."""
        return self.points[int(landmark)]

    def pixel_points(self) -> list[tuple[int, int]]:
        """Lista de (x, y) enteros, útil para dibujar."""
        return [(int(p[0]), int(p[1])) for p in self.points]


def normalized_to_pixels(
    normalized: Iterable[Sequence[float]], width: int, height: int
) -> np.ndarray:
    """Convierte landmarks normalizados (0..1) de MediaPipe a píxeles.

    MediaPipe normaliza ``x`` por el ancho y ``y`` por el alto de la imagen. Si
    no se corrige la relación de aspecto, las distancias y los ángulos 3D salen
    deformados en imágenes no cuadradas. ``z`` usa la misma escala que ``x``.

    Args:
        normalized: iterable de 21 tuplas (x, y, z) normalizadas.
        width: ancho de la imagen en píxeles.
        height: alto de la imagen en píxeles.

    Returns:
        Array ``(21, 3)`` en píxeles.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width y height deben ser positivos")
    array = np.asarray(list(normalized), dtype=float)
    if array.shape != (NUM_LANDMARKS, 3):
        raise ValueError(f"Se esperaban 21 landmarks de 3 coordenadas, llegó {array.shape}")
    return array * np.array([width, height, width], dtype=float)
