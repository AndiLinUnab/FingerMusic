"""Pruebas de la conversión y representación de landmarks."""

from __future__ import annotations

import numpy as np
import pytest

from fingermusic.vision.landmarks import (
    NUM_LANDMARKS,
    Finger,
    HandLandmarks,
    HandSide,
    Landmark,
    normalized_to_pixels,
)


def test_normalized_to_pixels_scales_each_axis() -> None:
    normalized = [(0.5, 0.5, 0.1)] * NUM_LANDMARKS
    pixels = normalized_to_pixels(normalized, width=640, height=480)
    assert pixels.shape == (NUM_LANDMARKS, 3)
    assert pixels[0] == pytest.approx([320.0, 240.0, 64.0])  # z usa la escala del ancho


def test_normalized_to_pixels_validates_input() -> None:
    with pytest.raises(ValueError):
        normalized_to_pixels([(0.0, 0.0, 0.0)] * 5, 640, 480)
    with pytest.raises(ValueError):
        normalized_to_pixels([(0.0, 0.0, 0.0)] * NUM_LANDMARKS, 0, 480)


def test_hand_landmarks_validates_shape() -> None:
    with pytest.raises(ValueError):
        HandLandmarks(points=np.zeros((20, 3)), side=HandSide.LEFT)


def test_hand_landmarks_accessors() -> None:
    points = np.arange(63, dtype=float).reshape(21, 3)
    hand = HandLandmarks(points=points, side=HandSide.RIGHT)
    assert hand.point(Landmark.INDEX_TIP).tolist() == [24.0, 25.0, 26.0]
    assert hand.pixel_points()[1] == (3, 4)


def test_finger_labels_and_order() -> None:
    assert [f.label for f in Finger] == ["Pulgar", "Indice", "Medio", "Anular", "Menique"]
    assert HandSide("Left") is HandSide.LEFT
    assert HandSide.RIGHT.label == "DERECHA"
