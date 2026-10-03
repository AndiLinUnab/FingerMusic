"""Pruebas de las funciones auxiliares."""

from __future__ import annotations

import numpy as np
import pytest

from fingermusic.utils.helpers import (
    angle_at,
    clamp,
    distance,
    exponential_smoothing,
    normalize_range,
    progress_bar,
)


def test_clamp() -> None:
    assert clamp(-1) == 0.0 and clamp(2) == 1.0 and clamp(0.4) == 0.4
    assert clamp(5, 0, 3) == 3


def test_normalize_range_both_directions() -> None:
    assert normalize_range(5, 0, 10) == pytest.approx(0.5)
    assert normalize_range(165, 165, 95) == 0.0
    assert normalize_range(95, 165, 95) == 1.0
    assert normalize_range(200, 165, 95) == 0.0  # recortado
    with pytest.raises(ValueError):
        normalize_range(1, 3, 3)


def test_distance() -> None:
    assert distance(np.array([0, 0, 0]), np.array([3, 4, 0])) == pytest.approx(5.0)


def test_angle_at() -> None:
    vertex = np.array([0.0, 0.0, 0.0])
    assert angle_at(vertex, np.array([1.0, 0, 0]), np.array([-1.0, 0, 0])) == pytest.approx(180.0)
    assert angle_at(vertex, np.array([1.0, 0, 0]), np.array([0, 1.0, 0])) == pytest.approx(90.0)
    assert angle_at(vertex, vertex, np.array([1.0, 0, 0])) == 180.0  # segmento nulo


def test_exponential_smoothing() -> None:
    assert exponential_smoothing(0.0, 1.0, 1.0) == 1.0
    assert exponential_smoothing(0.0, 1.0, 0.25) == pytest.approx(0.25)


def test_progress_bar() -> None:
    assert progress_bar(0.7) == "#######---"
    assert progress_bar(0) == "-" * 10
    assert progress_bar(2) == "#" * 10
