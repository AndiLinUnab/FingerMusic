"""Pruebas del catálogo de canciones y de la selección de canción."""

from __future__ import annotations

import pytest

from fingermusic.audio.notes import LOW_NOTES, NOTES_BY_KEY
from fingermusic.config import DetectionSettings
from fingermusic.engine import Mode, MusicEngine
from fingermusic.music.catalog import build_songs
from fingermusic.music.song import Song
from fingermusic.music.song_player import SongPlayer, SongResult
from fingermusic.vision.landmarks import Finger
from tests.test_engine import Driver


@pytest.fixture
def songs() -> tuple[Song, ...]:
    return build_songs()


@pytest.fixture
def engine(songs: tuple[Song, ...]) -> MusicEngine:
    return MusicEngine(DetectionSettings(), songs)


def by_title(songs: tuple[Song, ...], title: str) -> Song:
    return next(song for song in songs if song.title == title)


def test_catalog_has_four_songs_with_jingle_bells_first(songs: tuple[Song, ...]) -> None:
    assert [s.title for s in songs] == [
        "JINGLE BELLS",
        "ESTRELLITA",
        "HIMNO A LA ALEGRIA",
        "MARY Y SU CORDERITO",
    ]


def test_every_song_uses_valid_notes_and_fits_the_screen(songs: tuple[Song, ...]) -> None:
    for song in songs:
        assert set(song.notes) <= set(NOTES_BY_KEY), song.title
        assert 10 <= len(song) <= 80, song.title
        assert len(song.title) <= 22, song.title  # cabe entre las flechas del panel
        assert song.title.isascii() and song.title == song.title.upper()


def test_expected_lengths(songs: tuple[Song, ...]) -> None:
    assert len(by_title(songs, "JINGLE BELLS")) == 51
    assert len(by_title(songs, "ESTRELLITA")) == 42
    assert len(by_title(songs, "HIMNO A LA ALEGRIA")) == 62
    assert len(by_title(songs, "MARY Y SU CORDERITO")) == 26


def test_known_openings(songs: tuple[Song, ...]) -> None:
    assert by_title(songs, "ESTRELLITA").notes[:7] == (
        "do4", "do4", "sol4", "sol4", "la4", "la4", "sol4",
    )  # fmt: skip
    assert by_title(songs, "HIMNO A LA ALEGRIA").notes[:5] == ("mi4", "mi4", "fa4", "sol4", "sol4")
    assert by_title(songs, "MARY Y SU CORDERITO").notes[:7] == (
        "mi4", "re4", "do4", "re4", "mi4", "mi4", "mi4",
    )  # fmt: skip


def test_which_songs_need_both_hands(songs: tuple[Song, ...]) -> None:
    assert by_title(songs, "ESTRELLITA").both_hands is True  # usa LA
    for title in ("JINGLE BELLS", "HIMNO A LA ALEGRIA", "MARY Y SU CORDERITO"):
        song = by_title(songs, title)
        assert song.both_hands is False
        assert set(song.notes) <= set(LOW_NOTES)


def test_player_can_finish_every_song(songs: tuple[Song, ...]) -> None:
    for song in songs:
        player = SongPlayer(song)
        results = [player.play_note(key) for key in song.notes]
        assert results[-1] is SongResult.FINISHED and player.finished, song.title


def test_engine_requires_at_least_one_song() -> None:
    with pytest.raises(ValueError):
        MusicEngine(DetectionSettings(), [])


def test_engine_accepts_a_single_song(songs: tuple[Song, ...]) -> None:
    single = MusicEngine(DetectionSettings(), songs[0])
    assert len(single.songs) == 1 and single.next_song() is songs[0]


def test_next_and_previous_wrap_around(engine: MusicEngine, songs: tuple[Song, ...]) -> None:
    assert engine.song_index == 0
    assert engine.next_song() is songs[1] and engine.song_index == 1
    assert engine.previous_song() is songs[0]
    assert engine.previous_song() is songs[-1] and engine.song_index == len(songs) - 1
    assert engine.next_song() is songs[0] and engine.song_index == 0


def test_changing_song_resets_progress_and_streak_but_not_the_record(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    driver = Driver(engine)
    driver.tap(Finger.MIDDLE)
    driver.tap(Finger.MIDDLE)
    assert engine.song_player.index == 2 and engine.streak == 2
    engine.next_song()
    assert engine.song_player.index == 0 and engine.streak == 0
    assert engine.song_player.title == "ESTRELLITA"
    assert engine.best_streak == 2


def test_play_a_new_song_after_switching(engine: MusicEngine) -> None:
    engine.set_mode(Mode.SONG)
    engine.select_song(3)  # Mary: empieza con MI (dedo medio)
    played = Driver(engine).tap(Finger.MIDDLE)
    assert played[0].song_result is SongResult.HIT and engine.song_player.index == 1
