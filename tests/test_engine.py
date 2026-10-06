"""Pruebas del motor: de manos detectadas a notas y progreso de la canción."""

from __future__ import annotations

import pytest

from fingermusic.config import DetectionSettings
from fingermusic.engine import FrameResult, Mode, MusicEngine, PlayedNote
from fingermusic.music.jingle_bells import build_jingle_bells
from fingermusic.music.song_player import SongResult
from fingermusic.vision.landmarks import Finger, HandSide
from tests.hand_factory import make_hand

DT = 1 / 30


class Driver:
    """Alimenta el motor con frames sintéticos avanzando un reloj simulado."""

    def __init__(self, engine: MusicEngine) -> None:
        self.engine = engine
        self.now = 0.0

    def frames(self, count: int, curls=None, side=HandSide.LEFT, visible=True) -> list[PlayedNote]:
        played: list[PlayedNote] = []
        for _ in range(count):
            hands = [make_hand(curls, side)] if visible else []
            played += self.engine.process(hands, self.now).played
            self.now += DT
        return played

    def tap(self, finger: Finger, side=HandSide.LEFT) -> list[PlayedNote]:
        """Mano abierta -> dedo flexionado -> mano abierta."""
        played = self.frames(6, {}, side)
        played += self.frames(8, {finger: 1.0}, side)
        played += self.frames(8, {}, side)
        return played


@pytest.fixture
def engine() -> MusicEngine:
    return MusicEngine(DetectionSettings(), build_jingle_bells())


def test_flexing_a_finger_plays_its_note(engine: MusicEngine) -> None:
    played = Driver(engine).tap(Finger.MIDDLE)
    assert [p.note.label for p in played] == ["MI"]
    assert played[0].side is HandSide.LEFT and played[0].finger is Finger.MIDDLE


def test_right_hand_plays_high_notes(engine: MusicEngine) -> None:
    played = Driver(engine).tap(Finger.THUMB, HandSide.RIGHT)
    assert [p.note.label for p in played] == ["LA"]


def test_holding_a_finger_down_plays_once(engine: MusicEngine) -> None:
    driver = Driver(engine)
    driver.frames(6)
    played = driver.frames(120, {Finger.INDEX: 1.0})
    assert len(played) == 1


def test_open_hand_makes_no_sound(engine: MusicEngine) -> None:
    assert Driver(engine).frames(90) == []


def test_hand_appearing_with_flexed_finger_makes_no_sound(engine: MusicEngine) -> None:
    driver = Driver(engine)
    assert driver.frames(30, {Finger.RING: 1.0}) == []


def test_hand_reappearing_flexed_after_loss_makes_no_sound(engine: MusicEngine) -> None:
    driver = Driver(engine)
    driver.frames(8)
    driver.frames(10, visible=False)  # mano perdida >= hand_lost_reset_frames
    assert driver.frames(10, {Finger.INDEX: 1.0}) == []


def test_two_hands_play_independently(engine: MusicEngine) -> None:
    driver = Driver(engine)
    for _ in range(6):
        engine.process([make_hand({}, HandSide.LEFT), make_hand({}, HandSide.RIGHT)], driver.now)
        driver.now += DT
    played: list[PlayedNote] = []
    for _ in range(8):
        hands = [
            make_hand({Finger.INDEX: 1.0}, HandSide.LEFT),
            make_hand({Finger.PINKY: 1.0}, HandSide.RIGHT),
        ]
        played += engine.process(hands, driver.now).played
        driver.now += DT
    assert sorted(p.note.label for p in played) == ["FA", "MI'"]


def test_swap_hands(engine: MusicEngine) -> None:
    assert engine.toggle_swap_hands() is True
    played = Driver(engine).tap(Finger.THUMB, HandSide.RIGHT)
    assert played[0].note.label == "DO"


def test_free_mode_has_no_song_results(engine: MusicEngine) -> None:
    played = Driver(engine).tap(Finger.INDEX)
    assert played[0].song_result is None
    assert engine.song_player.index == 0


def test_song_mode_hit_and_miss(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    driver = Driver(engine)
    wrong = driver.tap(Finger.INDEX)  # FA, pero se espera MI
    assert wrong[0].song_result is SongResult.MISS and engine.song_player.index == 0
    right = driver.tap(Finger.MIDDLE)  # MI
    assert right[0].song_result is SongResult.HIT and engine.song_player.index == 1


def test_play_the_first_phrase_of_the_song(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    driver = Driver(engine)
    finger_for = {
        "do4": Finger.PINKY,
        "re4": Finger.RING,
        "mi4": Finger.MIDDLE,
        "fa4": Finger.INDEX,
        "sol4": Finger.THUMB,
    }
    for key in build_jingle_bells().notes[:11]:
        played = driver.tap(finger_for[key])
        assert played[0].song_result is SongResult.HIT
    assert engine.song_player.index == 11


def test_entering_song_mode_and_restart(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    Driver(engine).tap(Finger.MIDDLE)
    assert engine.song_player.index == 1
    engine.restart_song()
    assert engine.song_player.index == 0
    Driver(engine).tap(Finger.MIDDLE)
    engine.set_mode(Mode.FREE)
    engine.set_mode(Mode.SONG)  # volver a entrar reinicia
    assert engine.song_player.index == 0


def test_calibration_flow(engine: MusicEngine) -> None:
    driver = Driver(engine)
    engine.start_calibration(driver.now)
    assert engine.calibrating
    results: list[FrameResult] = []
    for _ in range(80):  # 2.6 s a 30 fps > 2 s de calibración
        results.append(engine.process([make_hand()], driver.now))
        driver.now += DT
    assert results[5].calibration_progress is not None
    assert any(r.message and "completada" in r.message for r in results)
    assert not engine.calibrating
    assert all(r.played == [] for r in results)


def test_calibration_without_hand_fails_gracefully(engine: MusicEngine) -> None:
    driver = Driver(engine)
    engine.start_calibration(driver.now)
    messages = []
    for _ in range(80):
        messages.append(engine.process([], driver.now).message)
        driver.now += DT
    assert any(m and "fallida" in m for m in messages)
    assert not engine.calibrating


def test_streak_counts_consecutive_hits_and_resets_on_miss(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    driver = Driver(engine)
    assert engine.streak == 0
    for expected in (1, 2, 3):
        played = driver.tap(Finger.MIDDLE)  # MI, MI, MI: las tres primeras notas
        assert played[0].streak == expected
    assert engine.streak == 3
    played = driver.tap(Finger.THUMB)  # SOL, pero se espera MI
    assert played[0].song_result is SongResult.MISS and played[0].streak == 0
    assert engine.streak == 0
    driver.tap(Finger.MIDDLE)
    assert engine.streak == 1


def test_streak_resets_on_restart_and_when_entering_song_mode(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    driver = Driver(engine)
    driver.tap(Finger.MIDDLE)
    driver.tap(Finger.MIDDLE)
    assert engine.streak == 2
    engine.restart_song()
    assert engine.streak == 0
    driver.tap(Finger.MIDDLE)
    engine.set_mode(Mode.FREE)
    engine.set_mode(Mode.SONG)
    assert engine.streak == 0


def test_streak_does_not_change_in_free_mode(engine: MusicEngine) -> None:
    driver = Driver(engine)
    played = driver.tap(Finger.MIDDLE)
    assert played[0].streak == 0 and engine.streak == 0
