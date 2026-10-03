"""Fábrica de manos sintéticas con geometría realista para las pruebas.

No simula la cámara ni el modelo: construye landmarks (21, 3) coherentes con una
mano abierta y permite doblar cada dedo con un parámetro ``curl`` de 0 a 1.
"""

from __future__ import annotations

import math

import numpy as np

from fingermusic.vision.landmarks import (
    FINGER_JOINTS,
    Finger,
    HandLandmarks,
    HandSide,
    Landmark,
)

WRIST = np.array([320.0, 440.0, 0.0])

# Base (MCP) y longitudes de los tres segmentos de cada dedo largo.
_LONG_FINGERS = {
    Finger.INDEX: ((280.0, 330.0), (45.0, 28.0, 24.0)),
    Finger.MIDDLE: ((320.0, 320.0), (50.0, 32.0, 25.0)),
    Finger.RING: ((360.0, 330.0), (46.0, 30.0, 24.0)),
    Finger.PINKY: ((395.0, 350.0), (36.0, 22.0, 20.0)),
}

# Pulgar: poses abierta y cerrada (CMC, MCP, IP, TIP), se interpolan con ``curl``.
_THUMB_OPEN = np.array([[290.0, 415.0, 0], [240.0, 395.0, 0], [195.0, 365.0, 0], [150.0, 335.0, 0]])
_THUMB_CLOSED = np.array(
    [[290.0, 415.0, 0], [265.0, 385.0, 0], [275.0, 355.0, 0], [300.0, 375.0, 0]]
)


def _direction(angle_degrees: float) -> np.ndarray:
    """Dirección de un segmento tras doblarse ``angle_degrees`` hacia la palma."""
    a = math.radians(angle_degrees)
    return np.array([0.0, -math.cos(a), -math.sin(a)])


def make_hand(
    curls: dict[Finger, float] | None = None,
    side: HandSide = HandSide.LEFT,
    score: float = 0.99,
) -> HandLandmarks:
    """Construye una mano con los dedos indicados doblados (``curl`` 0..1)."""
    curls = curls or {}
    points = np.zeros((21, 3))
    points[Landmark.WRIST] = WRIST

    for finger, ((mcp_x, mcp_y), lengths) in _LONG_FINGERS.items():
        curl = curls.get(finger, 0.0)
        mcp, pip, dip, tip = (int(lm) for lm in FINGER_JOINTS[finger])
        position = np.array([mcp_x, mcp_y, 0.0])
        points[mcp] = position
        cumulative = 0.0
        for index, (length, bend) in zip(
            (pip, dip, tip), zip(lengths, (70.0, 90.0, 60.0), strict=True), strict=True
        ):
            cumulative += curl * bend
            position = position + length * _direction(cumulative)
            points[index] = position

    thumb_curl = curls.get(Finger.THUMB, 0.0)
    pose = _THUMB_OPEN + thumb_curl * (_THUMB_CLOSED - _THUMB_OPEN)
    for landmark, coordinates in zip(FINGER_JOINTS[Finger.THUMB], pose, strict=True):
        points[int(landmark)] = coordinates

    return HandLandmarks(points=points, side=side, score=score)
