"""Detección geométrica de la flexión de los dedos y de sus transiciones.

Este módulo es lógica programada pura (NumPy, sin cámara ni IA): recibe los
landmarks que entrega el modelo y decide el estado de cada dedo.

Flujo por dedo y por frame::

    landmarks -> puntuación cruda de flexión (0..1)       FingerAnalyzer
              -> normalización con la calibración           FingerStateTracker
              -> suavizado exponencial
              -> histéresis (umbral de subida y de bajada)
              -> confirmación durante N frames
              -> transición EXTENDIDO -> FLEXIONADO (+ cooldown) = evento
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from statistics import median

from fingermusic.config import DetectionSettings
from fingermusic.utils.helpers import (
    angle_at,
    clamp,
    distance,
    exponential_smoothing,
    normalize_range,
)
from fingermusic.vision.landmarks import (
    FINGER_JOINTS,
    Finger,
    HandLandmarks,
    HandSide,
    Landmark,
)

logger = logging.getLogger(__name__)


class FingerState(StrEnum):
    """Estado discreto de un dedo."""

    EXTENDED = "EXTENDIDO"
    FLEXED = "FLEXIONADO"


class Transition(StrEnum):
    """Cambio de estado confirmado de un dedo."""

    PRESSED = "EXTENDIDO->FLEXIONADO"
    RELEASED = "FLEXIONADO->EXTENDIDO"


class FingerAnalyzer:
    """Calcula la puntuación cruda de flexión (0 = extendido, 1 = flexionado)."""

    def __init__(self, settings: DetectionSettings) -> None:
        self._s = settings

    def flexion_scores(self, hand: HandLandmarks) -> dict[Finger, float]:
        """Puntuación cruda de flexión de los cinco dedos de una mano."""
        return {finger: self.flexion_score(hand, finger) for finger in Finger}

    def flexion_score(self, hand: HandLandmarks, finger: Finger) -> float:
        """Puntuación de flexión (0..1) de un dedo.

        Combina una medida angular y una medida de distancia, ambas invariantes
        a la escala y a la rotación de la mano en la imagen.
        """
        if finger is Finger.THUMB:
            return self._thumb_score(hand)
        return self._long_finger_score(hand, finger)

    def _long_finger_score(self, hand: HandLandmarks, finger: Finger) -> float:
        """Índice, medio, anular y meñique.

        * Ángulo en la articulación PIP (MCP-PIP-DIP): ~180 grados recto, baja al flexionar.
        * Alcance: distancia(punta, muñeca) / distancia(MCP, muñeca): disminuye al flexionar.
        """
        s = self._s
        mcp, pip, dip, tip = (hand.point(lm) for lm in FINGER_JOINTS[finger])
        wrist = hand.point(Landmark.WRIST)

        pip_angle = angle_at(pip, mcp, dip)
        angle_score = normalize_range(pip_angle, s.pip_angle_extended, s.pip_angle_flexed)

        base_reach = distance(mcp, wrist)
        if base_reach < 1e-6:
            return 0.0
        reach_ratio = distance(tip, wrist) / base_reach
        reach_score = normalize_range(reach_ratio, s.reach_ratio_extended, s.reach_ratio_flexed)

        return s.angle_weight * angle_score + (1.0 - s.angle_weight) * reach_score

    def _thumb_score(self, hand: HandLandmarks) -> float:
        """Pulgar.

        El pulgar flexiona hacia la palma, no hacia abajo, así que se mide:

        * Distancia punta del pulgar - MCP del índice, normalizada por el tamaño
          de la palma (muñeca - MCP del medio): disminuye al cerrarlo.
        * Ángulo en la articulación IP (MCP-IP-TIP).
        """
        s = self._s
        palm_size = distance(hand.point(Landmark.WRIST), hand.point(Landmark.MIDDLE_MCP))
        if palm_size < 1e-6:
            return 0.0
        tip_to_index = distance(hand.point(Landmark.THUMB_TIP), hand.point(Landmark.INDEX_MCP))
        ratio_score = normalize_range(
            tip_to_index / palm_size, s.thumb_ratio_extended, s.thumb_ratio_flexed
        )
        ip_angle = angle_at(
            hand.point(Landmark.THUMB_IP),
            hand.point(Landmark.THUMB_MCP),
            hand.point(Landmark.THUMB_TIP),
        )
        angle_score = normalize_range(ip_angle, s.thumb_angle_extended, s.thumb_angle_flexed)
        return s.angle_weight * angle_score + (1.0 - s.angle_weight) * ratio_score


class FingerStateTracker:
    """Máquina de estados de un dedo con suavizado, histéresis y anti-rebote."""

    def __init__(self, settings: DetectionSettings) -> None:
        self._s = settings
        self._baseline = 0.0
        self.reset()

    # --- Estado público (solo lectura) -----------------------------------
    @property
    def state(self) -> FingerState | None:
        """Estado actual, o ``None`` si aún no hay datos."""
        return self._state

    @property
    def score(self) -> float:
        """Última puntuación suavizada y normalizada (0..1)."""
        return self._smoothed if self._smoothed is not None else 0.0

    # --- Control ----------------------------------------------------------
    def reset(self) -> None:
        """Olvida el estado (p. ej. cuando la mano desaparece).

        Al reaparecer, el primer estado observado se adopta **sin** generar
        evento, de modo que aparecer con un dedo doblado no dispara una nota.
        """
        self._state: FingerState | None = None
        self._smoothed: float | None = None
        self._pending = 0
        self._last_trigger = float("-inf")

    def set_baseline(self, baseline: float) -> None:
        """Fija la puntuación cruda del dedo en reposo (calibración)."""
        self._baseline = clamp(baseline, 0.0, self._s.calibration_max_baseline)

    def _normalize(self, raw: float) -> float:
        return clamp((raw - self._baseline) / (1.0 - self._baseline))

    def update(self, raw_score: float, now: float) -> Transition | None:
        """Procesa una puntuación cruda y devuelve la transición confirmada, si la hay.

        Args:
            raw_score: puntuación de flexión del frame actual (0..1).
            now: instante actual en segundos (reloj monotónico).
        """
        s = self._s
        value = self._normalize(raw_score)

        if self._smoothed is None:  # primer dato: adoptar estado sin evento
            self._smoothed = value
            self._state = (
                FingerState.FLEXED if value >= s.flex_on_threshold else FingerState.EXTENDED
            )
            return None

        self._smoothed = exponential_smoothing(self._smoothed, value, s.smoothing_alpha)

        # Histéresis: solo se propone un cambio al cruzar el umbral "lejano".
        candidate = self._state
        if self._state is FingerState.EXTENDED and self._smoothed >= s.flex_on_threshold:
            candidate = FingerState.FLEXED
        elif self._state is FingerState.FLEXED and self._smoothed <= s.flex_off_threshold:
            candidate = FingerState.EXTENDED

        if candidate is self._state:
            self._pending = 0
            return None

        self._pending += 1  # confirmación durante varios frames
        if self._pending < s.state_confirmation_frames:
            return None

        self._pending = 0
        self._state = candidate
        if candidate is FingerState.EXTENDED:
            return Transition.RELEASED
        if now - self._last_trigger < s.note_cooldown:
            logger.debug("Pulsación ignorada por cooldown")
            return None
        self._last_trigger = now
        return Transition.PRESSED


@dataclass(frozen=True)
class FingerReading:
    """Resultado de un dedo en un frame."""

    finger: Finger
    state: FingerState
    score: float
    transition: Transition | None


@dataclass
class HandFingerTracker:
    """Agrupa los cinco ``FingerStateTracker`` de una mano."""

    settings: DetectionSettings
    analyzer: FingerAnalyzer = field(init=False)
    trackers: dict[Finger, FingerStateTracker] = field(init=False)

    def __post_init__(self) -> None:
        self.analyzer = FingerAnalyzer(self.settings)
        self.trackers = {finger: FingerStateTracker(self.settings) for finger in Finger}

    def raw_scores(self, hand: HandLandmarks) -> dict[Finger, float]:
        """Puntuaciones crudas de los cinco dedos (útil para calibrar)."""
        return self.analyzer.flexion_scores(hand)

    def set_baselines(self, baselines: dict[Finger, float]) -> None:
        """Aplica la línea base de reposo de cada dedo."""
        for finger, value in baselines.items():
            self.trackers[finger].set_baseline(value)

    def reset(self) -> None:
        """Reinicia los estados (no la calibración)."""
        for tracker in self.trackers.values():
            tracker.reset()

    def update(self, hand: HandLandmarks, now: float) -> dict[Finger, FingerReading]:
        """Analiza una mano y actualiza el estado de sus cinco dedos."""
        readings: dict[Finger, FingerReading] = {}
        for finger, raw in self.raw_scores(hand).items():
            tracker = self.trackers[finger]
            transition = tracker.update(raw, now)
            assert tracker.state is not None  # tras update() siempre hay estado
            readings[finger] = FingerReading(finger, tracker.state, tracker.score, transition)
        return readings


class CalibrationSession:
    """Mide la posición de reposo (mano abierta) de cada dedo durante unos segundos."""

    def __init__(self, settings: DetectionSettings, start_time: float) -> None:
        self._s = settings
        self._start = start_time
        self._samples: dict[HandSide, dict[Finger, list[float]]] = {}

    def progress(self, now: float) -> float:
        """Avance de la calibración (0..1)."""
        return clamp((now - self._start) / self._s.calibration_duration)

    def is_done(self, now: float) -> bool:
        """``True`` cuando ha transcurrido la duración de calibración."""
        return now - self._start >= self._s.calibration_duration

    def add_sample(self, side: HandSide, raw_scores: dict[Finger, float]) -> None:
        """Registra las puntuaciones crudas de una mano en este frame."""
        per_finger = self._samples.setdefault(side, {f: [] for f in Finger})
        for finger, value in raw_scores.items():
            per_finger[finger].append(value)

    def result(self) -> dict[HandSide, dict[Finger, float]]:
        """Línea base (mediana) de cada dedo para las manos con muestras suficientes."""
        output: dict[HandSide, dict[Finger, float]] = {}
        for side, per_finger in self._samples.items():
            if min(len(values) for values in per_finger.values()) < self._s.calibration_min_samples:
                continue
            output[side] = {
                finger: clamp(median(values), 0.0, self._s.calibration_max_baseline)
                for finger, values in per_finger.items()
            }
        return output
