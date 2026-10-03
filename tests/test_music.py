"""Pruebas de la secuencia de Jingle Bells y del avance de la canción."""

from __future__ import annotations

import pytest

from fingermusic.audio.notes import NOTES_BY_KEY
from fingermusic.music.jingle_bells import Song, build_jingle_bells, parse_notes
from fingermusic.music.song_player import SongPlayer, SongResult


@pytest.fixture
def song() -> Song:
    return build_jingle_bells()


def test_jingle_bells_sequence(song: Song) -> None:
    assert song.title == "JINGLE BELLS"
    assert len(song) == 51
    assert song.notes[:11] == parse_notes("mi4 mi4 mi4 mi4 mi4 mi4 mi4 sol4 do4 re4 mi4")
    assert song.notes[-3:] == ("fa4", "re4", "do4")


def test_jingle_bells_uses_only_five_valid_notes(song: Song) -> None:
    assert set(song.notes) <= set(NOTES_BY_KEY)
    assert set(song.notes) == {"do4", "re4", "mi4", "fa4", "sol4"}


def test_song_validation() -> None:
    with pytest.raises(ValueError):
        Song("vacia", ())
    with pytest.raises(ValueError):
        Song("mala", ("mi4", "zz1"))


def test_player_initial_state(song: Song) -> None:
    player = SongPlayer(song)
    assert (player.index, player.total) == (0, 51)
    assert player.current == "mi4" and player.next == "mi4"
    assert player.progress == 0.0 and not player.finished


def test_correct_note_advances(song: Song) -> None:
    player = SongPlayer(song)
    assert player.play_note("mi4") is SongResult.HIT
    assert player.index == 1
    assert player.progress == pytest.approx(1 / 51)


def test_wrong_note_does_not_advance(song: Song) -> None:
    player = SongPlayer(song)
    assert player.play_note("do4") is SongResult.MISS
    assert player.index == 0


def test_full_song_finishes(song: Song) -> None:
    player = SongPlayer(song)
    results = [player.play_note(key) for key in song.notes]
    assert results[:-1] == [SongResult.HIT] * (len(song) - 1)
    assert results[-1] is SongResult.FINISHED
    assert player.finished and player.current is None and player.progress == 1.0
    assert player.play_note("mi4") is SongResult.IGNORED


def test_next_is_none_on_last_note(song: Song) -> None:
    player = SongPlayer(song)
    for key in song.notes[:-1]:
        player.play_note(key)
    assert player.current == "do4" and player.next is None


def test_restart(song: Song) -> None:
    player = SongPlayer(song)
    for key in song.notes[:10]:
        player.play_note(key)
    player.restart()
    assert player.index == 0 and player.current == "mi4"
