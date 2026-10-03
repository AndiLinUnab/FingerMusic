"""Pruebas de la detección geométrica de dedos y de los cambios de estado."""

from __future__ import annotations

import dataclasses

import pytest

from fingermusic.config import DetectionSettings
from fingermusic.vision.finger_detector import (
    CalibrationSession,
    FingerAnalyzer,
    FingerState,
    FingerStateTracker,
    HandFingerTracker,
    Transition,
)
from fingermusic.vision.landmarks import Finger, HandSide
from tests.hand_factory import make_hand

DT = 1 / 30


@pytest.fixture
def settings() -> DetectionSettings:
    return DetectionSettings()


@pytest.fixture
def analyzer(settings: DetectionSettings) -> FingerAnalyzer:
    return FingerAnalyzer(settings)


# --- Geometría ---------------------------------------------------------------
def test_open_hand_has_low_scores(analyzer: FingerAnalyzer) -> None:
    scores = analyzer.flexion_scores(make_hand())
    assert all(score < 0.25 for score in scores.values()), scores


@pytest.mark.parametrize("finger", list(Finger))
def test_only_the_flexed_finger_scores_high(analyzer: FingerAnalyzer, finger: Finger) -> None:
    scores = analyzer.flexion_scores(make_hand({finger: 1.0}))
    assert scores[finger] > 0.7, scores
    for other, score in scores.items():
        if other is not finger:
            assert score < 0.3, (other, scores)


@pytest.mark.parametrize("finger", [Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY])
def test_score_increases_with_curl(analyzer: FingerAnalyzer, finger: Finger) -> None:
    values = [analyzer.flexion_score(make_hand({finger: c}), finger) for c in (0.0, 0.4, 0.7, 1.0)]
    assert values == sorted(values)
    assert values[-1] - values[0] > 0.7


def test_score_is_scale_and_translation_invariant(analyzer: FingerAnalyzer) -> None:
    hand = make_hand({Finger.INDEX: 1.0})
    scaled = dataclasses.replace(hand, points=hand.points * 2.5 + [40.0, -30.0, 0.0])
    assert analyzer.flexion_score(scaled, Finger.INDEX) == pytest.approx(
        analyzer.flexion_score(hand, Finger.INDEX), abs=1e-6
    )


def test_degenerate_hand_does_not_crash(analyzer: FingerAnalyzer) -> None:
    flat = make_hand()
    flat = dataclasses.replace(flat, points=flat.points * 0.0)
    assert all(score == 0.0 for score in analyzer.flexion_scores(flat).values())


# --- Transiciones de estado --------------------------------------------------
def feed(tracker: FingerStateTracker, values: list[float], start: float = 0.0) -> list:
    return [tracker.update(value, start + i * DT) for i, value in enumerate(values)]


def test_press_triggers_exactly_one_event(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] * 5 + [0.95] * 30)
    assert events.count(Transition.PRESSED) == 1
    assert tracker.state is FingerState.FLEXED


def test_holding_flexed_does_not_repeat(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] * 3 + [0.95] * 200)
    assert events.count(Transition.PRESSED) == 1


def test_release_then_press_again(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] * 3 + [0.95] * 10 + [0.0] * 10 + [0.95] * 10)
    assert events.count(Transition.PRESSED) == 2
    assert events.count(Transition.RELEASED) == 1


def test_starting_flexed_does_not_trigger(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.95] * 30)
    assert all(event is None for event in events)
    assert tracker.state is FingerState.FLEXED


def test_single_frame_spike_is_filtered(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] * 5 + [1.0] + [0.0] * 10)
    assert all(event is None for event in events)


def test_hysteresis_keeps_state_between_thresholds(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] * 3 + [0.95] * 8 + [0.5] * 30)
    assert Transition.RELEASED not in events
    assert tracker.state is FingerState.FLEXED


def test_jitter_below_threshold_does_nothing(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    noisy = [0.1, 0.5, 0.2, 0.55, 0.15, 0.5] * 10
    assert all(event is None for event in feed(tracker, noisy))


def test_confirmation_frames_delay_the_event() -> None:
    settings = dataclasses.replace(
        DetectionSettings(), state_confirmation_frames=4, smoothing_alpha=1.0
    )
    tracker = FingerStateTracker(settings)
    events = feed(tracker, [0.0] + [0.95] * 6)
    assert events.index(Transition.PRESSED) == 4


def test_cooldown_suppresses_fast_repeats() -> None:
    settings = dataclasses.replace(
        DetectionSettings(), note_cooldown=1.0, state_confirmation_frames=1, smoothing_alpha=1.0
    )
    tracker = FingerStateTracker(settings)
    assert tracker.update(0.0, 0.0) is None
    assert tracker.update(0.95, 0.1) is Transition.PRESSED
    assert tracker.update(0.0, 0.2) is Transition.RELEASED
    assert tracker.update(0.95, 0.4) is None  # dentro del cooldown
    assert tracker.update(0.0, 0.6) is Transition.RELEASED
    assert tracker.update(0.95, 2.0) is Transition.PRESSED


def test_reset_forgets_state(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    feed(tracker, [0.0] * 3 + [0.95] * 5)
    tracker.reset()
    assert tracker.state is None
    assert feed(tracker, [0.95] * 5) == [None] * 5


# --- Calibración -------------------------------------------------------------
def test_baseline_normalizes_resting_posture(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    tracker.set_baseline(0.3)
    tracker.update(0.3, 0.0)
    assert tracker.score == pytest.approx(0.0)
    tracker.reset()
    tracker.update(0.65, 0.0)
    assert tracker.score == pytest.approx(0.5)


def test_baseline_is_clamped(settings: DetectionSettings) -> None:
    tracker = FingerStateTracker(settings)
    tracker.set_baseline(0.9)  # puño cerrado: no se acepta como reposo
    tracker.update(1.0, 0.0)
    assert tracker.state is FingerState.FLEXED


def test_calibration_session_computes_median(settings: DetectionSettings) -> None:
    session = CalibrationSession(settings, start_time=10.0)
    for value in [0.1, 0.2, 0.3, 0.2, 0.2, 0.2, 0.25, 0.15, 0.2, 0.2, 0.2, 0.2]:
        session.add_sample(HandSide.LEFT, {finger: value for finger in Finger})
    assert not session.is_done(11.0)
    assert session.progress(11.0) == pytest.approx(0.5)
    assert session.is_done(12.0)
    result = session.result()
    assert result[HandSide.LEFT][Finger.INDEX] == pytest.approx(0.2)
    assert HandSide.RIGHT not in result


def test_calibration_needs_enough_samples(settings: DetectionSettings) -> None:
    session = CalibrationSession(settings, start_time=0.0)
    for _ in range(settings.calibration_min_samples - 1):
        session.add_sample(HandSide.LEFT, {finger: 0.1 for finger in Finger})
    assert session.result() == {}


def test_calibration_baseline_capped(settings: DetectionSettings) -> None:
    session = CalibrationSession(settings, start_time=0.0)
    for _ in range(settings.calibration_min_samples):
        session.add_sample(HandSide.RIGHT, {finger: 0.9 for finger in Finger})
    assert session.result()[HandSide.RIGHT][Finger.THUMB] == settings.calibration_max_baseline


# --- Mano completa -----------------------------------------------------------
def test_hand_tracker_emits_event_for_the_right_finger(settings: DetectionSettings) -> None:
    tracker = HandFingerTracker(settings)
    pressed = []
    for i in range(60):
        curls = {Finger.MIDDLE: 1.0} if i >= 10 else {}
        readings = tracker.update(make_hand(curls), i * DT)
        pressed += [r.finger for r in readings.values() if r.transition is Transition.PRESSED]
    assert pressed == [Finger.MIDDLE]
