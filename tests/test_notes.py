"""Pruebas de las notas, el mapeo dedo -> nota y los sonidos incluidos."""

from __future__ import annotations

import pytest

from fingermusic.audio.notes import NOTES, build_finger_map, get_note
from fingermusic.config.settings import SOUNDS_DIR
from fingermusic.vision.landmarks import Finger, HandSide


def test_there_are_ten_unique_ascending_notes() -> None:
    assert len(NOTES) == 10
    assert len({note.key for note in NOTES}) == 10
    frequencies = [note.frequency for note in NOTES]
    assert frequencies == sorted(frequencies)


def test_default_finger_mapping() -> None:
    mapping = build_finger_map()
    left = [mapping[HandSide.LEFT][finger].label for finger in Finger]
    right = [mapping[HandSide.RIGHT][finger].label for finger in Finger]
    assert left == ["DO", "RE", "MI", "FA", "SOL"]
    assert right == ["LA", "SI", "DO'", "RE'", "MI'"]


def test_swap_hands_exchanges_notes() -> None:
    mapping = build_finger_map(swap_hands=True)
    assert mapping[HandSide.RIGHT][Finger.THUMB].label == "DO"
    assert mapping[HandSide.LEFT][Finger.THUMB].label == "LA"


def test_every_note_is_reachable_by_exactly_one_finger() -> None:
    mapping = build_finger_map()
    keys = [note.key for per_hand in mapping.values() for note in per_hand.values()]
    assert sorted(keys) == sorted(note.key for note in NOTES)


def test_get_note() -> None:
    assert get_note("mi4").label == "MI"
    with pytest.raises(KeyError):
        get_note("xx9")


def test_wav_files_are_included_in_the_repository() -> None:
    for note in NOTES:
        assert (SOUNDS_DIR / f"{note.key}.wav").is_file(), note.key
