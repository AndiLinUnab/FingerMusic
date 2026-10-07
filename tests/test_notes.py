"""Pruebas de las notas, el mapeo dedo -> nota y los sonidos incluidos."""

from __future__ import annotations

import pytest

from fingermusic.audio.notes import NOTES, build_finger_map, get_note, screen_finger_order
from fingermusic.config.settings import SOUNDS_DIR
from fingermusic.vision.landmarks import Finger, HandSide


def test_there_are_ten_unique_ascending_notes() -> None:
    assert len(NOTES) == 10
    assert len({note.key for note in NOTES}) == 10
    frequencies = [note.frequency for note in NOTES]
    assert frequencies == sorted(frequencies)


def test_default_finger_mapping() -> None:
    mapping = build_finger_map()
    # Orden de dedos tal como se ven en pantalla (de izquierda a derecha).
    left = [mapping[HandSide.LEFT][f].label for f in screen_finger_order(HandSide.LEFT)]
    right = [mapping[HandSide.RIGHT][f].label for f in screen_finger_order(HandSide.RIGHT)]
    assert left == ["DO", "RE", "MI", "FA", "SOL"]
    assert right == ["LA", "SI", "DO'", "RE'", "MI'"]


def test_left_hand_runs_from_pinky_to_thumb() -> None:
    left = build_finger_map()[HandSide.LEFT]
    assert left[Finger.PINKY].label == "DO"
    assert left[Finger.THUMB].label == "SOL"
    assert left[Finger.MIDDLE].label == "MI"


def test_right_hand_runs_from_thumb_to_pinky() -> None:
    right = build_finger_map()[HandSide.RIGHT]
    assert right[Finger.THUMB].label == "LA"
    assert right[Finger.PINKY].label == "MI'"


def test_notes_ascend_left_to_right_across_both_hands() -> None:
    mapping = build_finger_map()
    ordered = [
        mapping[side][f]
        for side in (HandSide.LEFT, HandSide.RIGHT)
        for f in screen_finger_order(side)
    ]
    assert [n.key for n in ordered] == [n.key for n in NOTES]


def test_swap_hands_exchanges_notes_keeping_screen_order() -> None:
    mapping = build_finger_map(swap_hands=True)
    right = [mapping[HandSide.RIGHT][f].label for f in screen_finger_order(HandSide.RIGHT)]
    left = [mapping[HandSide.LEFT][f].label for f in screen_finger_order(HandSide.LEFT)]
    assert right == ["DO", "RE", "MI", "FA", "SOL"]
    assert left == ["LA", "SI", "DO'", "RE'", "MI'"]
    assert mapping[HandSide.RIGHT][Finger.THUMB].label == "DO"


def test_every_note_is_reachable_by_exactly_one_finger() -> None:
    mapping = build_finger_map()
    keys = [note.key for per_hand in mapping.values() for note in per_hand.values()]
    assert sorted(keys) == sorted(note.key for note in NOTES)


def test_get_note() -> None:
    assert get_note("mi4").label == "MI"
    with pytest.raises(KeyError):
        get_note("xx9")


def test_wav_files_are_included_in_the_repository() -> None:
    for instrument in ("piano", "xilofono", "flauta"):
        for note in NOTES:
            assert (SOUNDS_DIR / instrument / f"{note.key}.wav").is_file(), (instrument, note.key)
