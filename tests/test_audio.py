"""Pruebas de la síntesis y del gestor de audio (con el driver de audio 'dummy')."""

from __future__ import annotations

import dataclasses
import os
import wave
from pathlib import Path

import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")  # sin dispositivo de audio real
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from fingermusic.audio.audio_manager import AudioManager  # noqa: E402
from fingermusic.audio.notes import NOTES  # noqa: E402
from fingermusic.audio.synth import generate_all_notes, synthesize_tone, write_wav  # noqa: E402
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
