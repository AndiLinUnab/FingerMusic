"""Pruebas de la síntesis y del gestor de audio (con el driver de audio 'dummy')."""

from __future__ import annotations

import dataclasses
import os
import wave
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")  # sin dispositivo de audio real
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from fingermusic.audio.audio_manager import AudioManager  # noqa: E402
from fingermusic.audio.notes import NOTES  # noqa: E402
from fingermusic.audio.synth import (  # noqa: E402
    generate_all_notes,
    generate_all_sounds,
    synthesize_error_tone,
    synthesize_tone,
    write_wav,
)
from fingermusic.config import AudioSettings  # noqa: E402


def test_synthesize_tone_shape_and_range() -> None:
    samples = synthesize_tone(440.0, duration=0.5, sample_rate=22050)
    assert samples.dtype.name == "int16"
    assert len(samples) == 11025
    assert 20000 < int(abs(samples).max()) <= 32767


def test_synthesize_tone_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        synthesize_tone(0.0)


def test_write_wav_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "x.wav"
    write_wav(path, synthesize_tone(261.63, 0.2, 8000), 8000)
    with wave.open(str(path)) as handle:
        assert handle.getframerate() == 8000
        assert handle.getnchannels() == 1
        assert handle.getnframes() == 1600


def test_generate_all_notes_only_creates_missing(tmp_path: Path) -> None:
    paths = generate_all_notes(tmp_path, duration=0.1)
    assert len(paths) == 10 and all(p.exists() for p in paths)
    marker = paths[0].stat().st_mtime_ns
    generate_all_notes(tmp_path, duration=0.1)
    assert paths[0].stat().st_mtime_ns == marker


def test_audio_manager_loads_and_plays(tmp_path: Path) -> None:
    manager = AudioManager(dataclasses.replace(AudioSettings(), sounds_dir=tmp_path))
    try:
        assert manager.available, manager.error
        assert manager.play(NOTES[0].key) is True  # falta el .wav: se genera y se carga
        assert manager.play("nota_inexistente") is False
        assert manager.set_volume(3.0) == 1.0
        assert manager.toggle_enabled() is False
        assert manager.play(NOTES[1].key) is False  # silenciado
    finally:
        manager.close()
    assert not manager.available


def dominant_frequency(samples: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(samples.astype(float) * np.hanning(len(samples))))
    return float(np.argmax(spectrum) * sample_rate / len(samples))


def test_error_tone_shape_and_range() -> None:
    samples = synthesize_error_tone(0.3, 44100)
    assert samples.dtype.name == "int16" and len(samples) == 13230
    assert 15000 < int(abs(samples).max()) <= 32767
    with pytest.raises(ValueError):
        synthesize_error_tone(0.0)


def test_error_tone_is_low_and_descending() -> None:
    rate = 44100
    samples = synthesize_error_tone(0.3, rate)
    start = dominant_frequency(samples[: rate // 20], rate)  # primeros 50 ms
    end = dominant_frequency(samples[-rate // 10 : -rate // 40], rate)
    assert start > end
    assert start < 261.63  # más grave que la nota más baja (DO4)


def test_error_tone_is_harsher_than_a_note() -> None:
    """El buzzer tiene mucha más energía en armónicos altos que una nota suave."""

    def high_energy_ratio(samples: np.ndarray) -> float:
        spectrum = np.abs(np.fft.rfft(samples.astype(float))) ** 2
        freqs = np.fft.rfftfreq(len(samples), 1 / 44100)
        return float(spectrum[freqs > 600].sum() / spectrum.sum())

    error = high_energy_ratio(synthesize_error_tone(0.3))
    note = high_energy_ratio(synthesize_tone(261.63, 0.3))
    assert error > note


def test_generate_all_sounds_includes_the_error_file(tmp_path: Path) -> None:
    paths = generate_all_sounds(tmp_path, note_duration=0.1, error_duration=0.1)
    assert len(paths) == 31  # 3 instrumentos x 10 notas + el sonido de error
    assert (tmp_path / "error.wav").exists()
    for instrument in ("piano", "xilofono", "flauta"):
        assert (tmp_path / instrument / "do4.wav").exists()


def test_the_repository_ships_the_error_sound() -> None:
    from fingermusic.config.settings import SOUNDS_DIR

    assert (SOUNDS_DIR / "error.wav").is_file()


class Spy:
    def __init__(self) -> None:
        self.plays = 0

    def play(self) -> None:
        self.plays += 1

    def set_volume(self, _volume: float) -> None:
        pass


def spied_manager(tmp_path: Path, **overrides: object) -> tuple[AudioManager, Spy, Spy]:
    manager = AudioManager(dataclasses.replace(AudioSettings(), sounds_dir=tmp_path, **overrides))
    assert manager.available, manager.error
    note, error = Spy(), Spy()
    manager._banks[manager.instrument.key]["mi4"] = note
    manager._error_sound = error
    return manager, note, error


def test_error_sound_is_loaded_and_playable(tmp_path: Path) -> None:
    manager = AudioManager(dataclasses.replace(AudioSettings(), sounds_dir=tmp_path))
    try:
        assert (tmp_path / "error.wav").exists()  # se generó al faltar
        assert (tmp_path / "piano" / "do4.wav").exists()
        assert manager.play_error() is True
    finally:
        manager.close()


def test_a_hit_plays_the_note(tmp_path: Path) -> None:
    manager, note, error = spied_manager(tmp_path)
    try:
        assert manager.play_result("mi4", missed=False) is True
        assert (note.plays, error.plays) == (1, 0)
    finally:
        manager.close()


def test_a_miss_plays_only_the_error_by_default(tmp_path: Path) -> None:
    manager, note, error = spied_manager(tmp_path)
    try:
        assert manager.play_result("mi4", missed=True) is True
        assert (note.plays, error.plays) == (0, 1)
    finally:
        manager.close()


def test_a_miss_can_also_play_the_note(tmp_path: Path) -> None:
    manager, note, error = spied_manager(tmp_path, error_plays_note=True)
    try:
        manager.play_result("mi4", missed=True)
        assert (note.plays, error.plays) == (1, 1)
    finally:
        manager.close()


def test_muted_manager_plays_no_error(tmp_path: Path) -> None:
    manager, note, error = spied_manager(tmp_path)
    try:
        manager.toggle_enabled()
        assert manager.play_result("mi4", missed=True) is False
        assert (note.plays, error.plays) == (0, 0)
    finally:
        manager.close()
