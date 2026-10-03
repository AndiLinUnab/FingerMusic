"""Síntesis de tonos musicales y escritura de archivos WAV.

Los sonidos se generan matemáticamente (suma de armónicos con una envolvente
de ataque rápido y caída exponencial), por lo que no hay material con derechos
de autor ni archivos externos que descargar.
"""

from __future__ import annotations

import logging
import wave
from pathlib import Path

import numpy as np

from fingermusic.audio.notes import NOTES, Note

logger = logging.getLogger(__name__)

# (número de armónico, amplitud relativa): timbre suave, similar a un piano eléctrico.
_HARMONICS: tuple[tuple[int, float], ...] = ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.08))
_ATTACK_SECONDS = 0.005
_RELEASE_SECONDS = 0.05
_DECAY_RATE = 4.0
_PEAK = 0.8


def synthesize_tone(
    frequency: float, duration: float = 0.7, sample_rate: int = 44100
) -> np.ndarray:
    """Genera un tono como array ``int16`` mono.

    Args:
        frequency: frecuencia fundamental en Hz.
        duration: duración en segundos.
        sample_rate: frecuencia de muestreo en Hz.
    """
    if frequency <= 0 or duration <= 0 or sample_rate <= 0:
        raise ValueError("frequency, duration y sample_rate deben ser positivos")
    count = int(sample_rate * duration)
    t = np.arange(count) / sample_rate
    wave_data = sum(amp * np.sin(2 * np.pi * frequency * n * t) for n, amp in _HARMONICS)
    envelope = np.exp(-_DECAY_RATE * t)
    attack = min(count, int(_ATTACK_SECONDS * sample_rate))
    release = min(count, int(_RELEASE_SECONDS * sample_rate))
    envelope[:attack] *= np.linspace(0.0, 1.0, attack)
    envelope[count - release :] *= np.linspace(1.0, 0.0, release)
    signal = wave_data * envelope
    signal = signal / np.max(np.abs(signal)) * _PEAK
    return (signal * 32767).astype(np.int16)


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = 44100) -> None:
    """Escribe un array ``int16`` mono como archivo WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


def generate_note_file(
    note: Note, directory: Path, duration: float = 0.7, sample_rate: int = 44100
) -> Path:
    """Genera ``<directory>/<note.key>.wav`` y devuelve su ruta."""
    path = directory / f"{note.key}.wav"
    write_wav(path, synthesize_tone(note.frequency, duration, sample_rate), sample_rate)
    return path


def generate_all_notes(
    directory: Path, duration: float = 0.7, sample_rate: int = 44100, overwrite: bool = False
) -> list[Path]:
    """Genera los 10 archivos de las notas (solo los que falten, salvo ``overwrite``)."""
    paths: list[Path] = []
    for note in NOTES:
        path = directory / f"{note.key}.wav"
        if overwrite or not path.exists():
            generate_note_file(note, directory, duration, sample_rate)
            logger.info("Sonido generado: %s", path.name)
        paths.append(path)
    return paths
