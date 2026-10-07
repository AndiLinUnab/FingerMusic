"""Síntesis de tonos musicales y escritura de archivos WAV.

Los sonidos se generan matemáticamente, por lo que no hay material con derechos de
autor ni archivos externos que descargar. Cada instrumento se modela distinto:

* **Piano**: parciales ligeramente inarmónicos; los agudos se apagan antes.
* **Xilófono**: tres parciales en proporción 1 : 3 : 6, caída muy rápida y un "golpe" inicial.
* **Flauta**: casi un tono puro con vibrato suave, soplido y entrada/salida lentas.
"""

from __future__ import annotations

import logging
import math
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fingermusic.audio.instruments import DEFAULT_INSTRUMENT, INSTRUMENTS, get_instrument
from fingermusic.audio.notes import NOTES, Note

logger = logging.getLogger(__name__)

_PEAK = 0.8
_SEED = 7  # el ruido (golpe, soplido) es reproducible: mismos archivos en cada generación

# --- Piano ---
_PIANO_PARTIALS = 8
_PIANO_INHARMONICITY = 0.0004
# --- Xilófono: (proporción respecto a la fundamental, amplitud, caída por segundo) ---
_XYLOPHONE_PARTIALS = ((1.0, 1.0, 7.0), (3.0, 0.40, 22.0), (6.0, 0.15, 40.0))
_XYLOPHONE_CLICK_AMPLITUDE = 0.25
_XYLOPHONE_CLICK_DECAY = 900.0
# --- Flauta ---
_FLUTE_HARMONICS = ((1, 1.0), (2, 0.22), (3, 0.07))
_FLUTE_VIBRATO_HZ = 5.5
_FLUTE_VIBRATO_DEPTH = 0.005
_FLUTE_VIBRATO_RAMP = 0.25
_FLUTE_BREATH = 0.04
_FLUTE_BREATH_SMOOTHING = 8

# --- Sonido de error ---
_ERROR_START_HZ = 220.0
_ERROR_END_HZ = 110.0
_ERROR_HARMONICS = 6
_ERROR_DECAY_RATE = 6.0
_ERROR_PEAK = 0.7
#: Nombre del archivo (sin extensión) del sonido de error.
ERROR_SOUND_NAME = "error"


@dataclass(frozen=True)
class _Voice:
    """Generador de la forma de onda de un instrumento y su envolvente de entrada/salida."""

    wave: Callable[[float, np.ndarray, int], np.ndarray]
    attack: float
    release: float


def _piano(frequency: float, t: np.ndarray, sample_rate: int) -> np.ndarray:
    signal = np.zeros_like(t)
    for n in range(1, _PIANO_PARTIALS + 1):
        partial = n * frequency * math.sqrt(1.0 + _PIANO_INHARMONICITY * n * n)
        if partial >= sample_rate / 2:
            break
        decay = 2.2 + 1.1 * n  # los parciales agudos se apagan antes
        signal += np.exp(-decay * t) * np.sin(2 * np.pi * partial * t) / n**1.2
    return signal


def _xylophone(frequency: float, t: np.ndarray, sample_rate: int) -> np.ndarray:
    signal = np.zeros_like(t)
    for ratio, amplitude, decay in _XYLOPHONE_PARTIALS:
        partial = frequency * ratio
        if partial < sample_rate / 2:
            signal += amplitude * np.exp(-decay * t) * np.sin(2 * np.pi * partial * t)
    rng = np.random.default_rng(_SEED)
    click = rng.standard_normal(len(t)) * np.exp(-_XYLOPHONE_CLICK_DECAY * t)
    return signal + _XYLOPHONE_CLICK_AMPLITUDE * click


def _flute(frequency: float, t: np.ndarray, sample_rate: int) -> np.ndarray:
    ramp = np.clip(t / _FLUTE_VIBRATO_RAMP, 0.0, 1.0)  # el vibrato aparece poco a poco
    vibrato = 1.0 + _FLUTE_VIBRATO_DEPTH * ramp * np.sin(2 * np.pi * _FLUTE_VIBRATO_HZ * t)
    phase = 2 * np.pi * np.cumsum(frequency * vibrato) / sample_rate
    signal = sum(amplitude * np.sin(n * phase) for n, amplitude in _FLUTE_HARMONICS)
    rng = np.random.default_rng(_SEED)
    kernel = np.ones(_FLUTE_BREATH_SMOOTHING) / _FLUTE_BREATH_SMOOTHING
    breath = np.convolve(rng.standard_normal(len(t)), kernel, mode="same")
    return signal + _FLUTE_BREATH * breath / max(float(np.std(breath)), 1e-9)


_VOICES: dict[str, _Voice] = {
    "piano": _Voice(_piano, attack=0.003, release=0.06),
    "xilofono": _Voice(_xylophone, attack=0.001, release=0.04),
    "flauta": _Voice(_flute, attack=0.06, release=0.14),
}


def _shape(
    signal: np.ndarray, sample_rate: int, attack: float, release: float, peak: float
) -> np.ndarray:
    """Aplica entrada/salida lineales, normaliza al pico indicado y convierte a ``int16``."""
    count = len(signal)
    attack_n = min(count, max(1, int(attack * sample_rate)))
    release_n = min(count, max(1, int(release * sample_rate)))
    signal = signal.copy()
    signal[:attack_n] *= np.linspace(0.0, 1.0, attack_n)
    signal[count - release_n :] *= np.linspace(1.0, 0.0, release_n)
    signal = signal / np.max(np.abs(signal)) * peak
    return (signal * 32767).astype(np.int16)


def synthesize_tone(
    frequency: float,
    duration: float = 0.7,
    sample_rate: int = 44100,
    instrument: str = DEFAULT_INSTRUMENT,
) -> np.ndarray:
    """Genera una nota como array ``int16`` mono.

    Args:
        frequency: frecuencia fundamental en Hz.
        duration: duración en segundos.
        sample_rate: frecuencia de muestreo en Hz.
        instrument: clave del instrumento (``piano``, ``xilofono`` o ``flauta``).

    Raises:
        ValueError: si algún número no es positivo.
        KeyError: si el instrumento no existe.
    """
    if frequency <= 0 or duration <= 0 or sample_rate <= 0:
        raise ValueError("frequency, duration y sample_rate deben ser positivos")
    get_instrument(instrument)
    voice = _VOICES[instrument]
    t = np.arange(int(sample_rate * duration)) / sample_rate
    signal = voice.wave(frequency, t, sample_rate)
    return _shape(signal, sample_rate, voice.attack, voice.release, _PEAK)


def synthesize_error_tone(duration: float = 0.3, sample_rate: int = 44100) -> np.ndarray:
    """Genera el sonido de error: un "buzzer" grave que desciende de 220 a 110 Hz.

    Es una onda tipo diente de sierra (áspera) con caída rápida, muy distinta de las
    notas suaves, para que se reconozca al instante como un fallo.
    """
    if duration <= 0 or sample_rate <= 0:
        raise ValueError("duration y sample_rate deben ser positivos")
    count = int(sample_rate * duration)
    t = np.arange(count) / sample_rate
    frequency = np.linspace(_ERROR_START_HZ, _ERROR_END_HZ, count)
    phase = 2 * np.pi * np.cumsum(frequency) / sample_rate
    signal = sum(np.sin(n * phase) / n for n in range(1, _ERROR_HARMONICS + 1))
    signal = signal * np.exp(-_ERROR_DECAY_RATE * t)
    return _shape(signal, sample_rate, attack=0.002, release=0.03, peak=_ERROR_PEAK)


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = 44100) -> None:
    """Escribe un array ``int16`` mono como archivo WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


def note_path(directory: Path, instrument: str, note: Note) -> Path:
    """Ruta del archivo de una nota: ``<directory>/<instrumento>/<nota>.wav``."""
    return directory / instrument / f"{note.key}.wav"


def generate_note_file(
    note: Note,
    directory: Path,
    duration: float = 0.7,
    sample_rate: int = 44100,
    instrument: str = DEFAULT_INSTRUMENT,
) -> Path:
    """Genera el ``.wav`` de una nota con el instrumento indicado y devuelve su ruta."""
    path = note_path(directory, instrument, note)
    write_wav(path, synthesize_tone(note.frequency, duration, sample_rate, instrument), sample_rate)
    return path


def generate_all_notes(
    directory: Path,
    duration: float = 0.7,
    sample_rate: int = 44100,
    overwrite: bool = False,
    instrument: str = DEFAULT_INSTRUMENT,
) -> list[Path]:
    """Genera las 10 notas de un instrumento (solo las que falten, salvo ``overwrite``)."""
    paths: list[Path] = []
    for note in NOTES:
        path = note_path(directory, instrument, note)
        if overwrite or not path.exists():
            generate_note_file(note, directory, duration, sample_rate, instrument)
            logger.info("Sonido generado: %s/%s", instrument, path.name)
        paths.append(path)
    return paths


def generate_error_file(directory: Path, duration: float = 0.3, sample_rate: int = 44100) -> Path:
    """Genera ``<directory>/error.wav`` y devuelve su ruta."""
    path = directory / f"{ERROR_SOUND_NAME}.wav"
    write_wav(path, synthesize_error_tone(duration, sample_rate), sample_rate)
    return path


def generate_all_sounds(
    directory: Path,
    note_duration: float = 0.7,
    error_duration: float = 0.3,
    sample_rate: int = 44100,
    overwrite: bool = False,
) -> list[Path]:
    """Genera las notas de todos los instrumentos y el sonido de error (solo los que falten)."""
    paths: list[Path] = []
    for instrument in INSTRUMENTS:
        paths += generate_all_notes(
            directory, note_duration, sample_rate, overwrite, instrument.key
        )
    error_path = directory / f"{ERROR_SOUND_NAME}.wav"
    if overwrite or not error_path.exists():
        generate_error_file(directory, error_duration, sample_rate)
        logger.info("Sonido generado: %s", error_path.name)
    return [*paths, error_path]
