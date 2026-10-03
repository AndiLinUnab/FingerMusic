"""Funciones matemáticas y de apoyo reutilizables."""

from __future__ import annotations

import math

import numpy as np


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Limita ``value`` al intervalo ``[low, high]``."""
    return max(low, min(high, value))


def normalize_range(value: float, at_zero: float, at_one: float) -> float:
    """Mapea linealmente ``value`` de ``[at_zero, at_one]`` a ``[0, 1]`` (recortado).

    Funciona también si ``at_one < at_zero`` (escala invertida).
    """
    if at_zero == at_one:
        raise ValueError("at_zero y at_one no pueden ser iguales")
    return clamp((value - at_zero) / (at_one - at_zero))


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """Distancia euclídea entre dos puntos (2D o 3D)."""
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def angle_at(vertex: np.ndarray, first: np.ndarray, second: np.ndarray) -> float:
    """Ángulo en grados formado en ``vertex`` por los segmentos hacia ``first`` y ``second``.

    Devuelve 180 para tres puntos alineados (dedo recto) y valores menores
    cuando la articulación se dobla. Si algún segmento tiene longitud cero
    devuelve 180 (se asume "sin flexión").
    """
    v1 = np.asarray(first, dtype=float) - np.asarray(vertex, dtype=float)
    v2 = np.asarray(second, dtype=float) - np.asarray(vertex, dtype=float)
    norm = float(np.linalg.norm(v1) * np.linalg.norm(v2))
    if norm < 1e-9:
        return 180.0
    cos_angle = clamp(float(np.dot(v1, v2)) / norm, -1.0, 1.0)
    return math.degrees(math.acos(cos_angle))


def exponential_smoothing(previous: float, new: float, alpha: float) -> float:
    """Media móvil exponencial: ``alpha * new + (1 - alpha) * previous``."""
    return alpha * new + (1.0 - alpha) * previous


def progress_bar(fraction: float, width: int = 10) -> str:
    """Barra de texto, por ejemplo ``'#######---'`` para 0.7 con ancho 10."""
    filled = round(clamp(fraction) * width)
    return "#" * filled + "-" * (width - filled)
