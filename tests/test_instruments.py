"""Pruebas de los instrumentos: registro, timbres sintetizados y cambio en el gestor de audio."""

from __future__ import annotations

import dataclasses
import os

import numpy as np
import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from fingermusic.audio.audio_manager import AudioManager  # noqa: E402
from fingermusic.audio.instruments import (  # noqa: E402
    DEFAULT_INSTRUMENT,
    INSTRUMENTS,
    get_instrument,
    next_instrument,
)
from fingermusic.audio.notes import NOTES  # noqa: E402
from fingermusic.audio.synth import synthesize_tone  # noqa: E402
from fingermusic.config import AudioSettings, Settings  # noqa: E402

SAMPLE_RATE = 44100
MI4 = 329.63


def rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(samples.astype(float) ** 2)))


def spectrum_peak_hz(samples: np.ndarray) -> float:
    window = samples.astype(float) * np.hanning(len(samples))
    return float(np.argmax(np.abs(np.fft.rfft(window))) * SAMPLE_RATE / len(samples))


def band_amplitude(samples: np.ndarray, frequency: float) -> float:
    spectrum = np.abs(np.fft.rfft(samples.astype(float) * np.hanning(len(samples))))
    freqs = np.fft.rfftfreq(len(samples), 1 / SAMPLE_RATE)
    return float(spectrum[(freqs > frequency * 0.97) & (freqs < frequency * 1.03)].max())


def decay_ratio(samples: np.ndarray) -> float:
    """Volumen entre 0.25 y 0.35 s respecto a los primeros 0.1 s (menor = se apaga antes)."""
    early = rms(samples[: int(0.1 * SAMPLE_RATE)])
    late = rms(samples[int(0.25 * SAMPLE_RATE) : int(0.35 * SAMPLE_RATE)])
    return late / early


# --- Registro ---------------------------------------------------------------
def test_registry_has_the_three_instruments() -> None:
    assert [i.key for i in INSTRUMENTS] == ["piano", "xilofono", "flauta"]
    assert DEFAULT_INSTRUMENT == "piano"
    assert all(i.label.isascii() and i.label == i.label.upper() for i in INSTRUMENTS)


def test_get_and_next_instrument_wrap_around() -> None:
    assert get_instrument("flauta").label == "FLAUTA"
    with pytest.raises(KeyError):
        get_instrument("tuba")
    assert next_instrument("piano").key == "xilofono"
    assert next_instrument("flauta").key == "piano"


# --- Síntesis ---------------------------------------------------------------
@pytest.mark.parametrize("instrument", [i.key for i in INSTRUMENTS])
def test_every_instrument_plays_every_note_at_the_right_pitch(instrument: str) -> None:
    for note in NOTES:
        samples = synthesize_tone(note.frequency, 0.7, SAMPLE_RATE, instrument)
        assert samples.dtype.name == "int16" and len(samples) == int(0.7 * SAMPLE_RATE)
        assert 20000 < int(np.abs(samples).max()) <= 32767
        peak = spectrum_peak_hz(samples[: int(0.4 * SAMPLE_RATE)])
        assert peak == pytest.approx(note.frequency, rel=0.03), (instrument, note.label)


def test_synthesis_is_deterministic() -> None:
    for instrument in (i.key for i in INSTRUMENTS):
        first = synthesize_tone(MI4, 0.3, SAMPLE_RATE, instrument)
        assert np.array_equal(first, synthesize_tone(MI4, 0.3, SAMPLE_RATE, instrument))


def test_unknown_instrument_is_rejected() -> None:
    with pytest.raises(KeyError):
        synthesize_tone(MI4, 0.3, SAMPLE_RATE, "tuba")


def test_the_three_timbres_are_different() -> None:
    tones = {i.key: synthesize_tone(MI4, 0.7, SAMPLE_RATE, i.key) for i in INSTRUMENTS}
    keys = list(tones)
    for a in keys:
        for b in keys:
            if a < b:
                assert not np.array_equal(tones[a], tones[b]), (a, b)


def test_xylophone_dies_out_faster_than_piano_and_flute_sustains() -> None:
    ratios = {
        i.key: decay_ratio(synthesize_tone(MI4, 0.7, SAMPLE_RATE, i.key)) for i in INSTRUMENTS
    }
    assert ratios["xilofono"] < ratios["piano"] < 1.0
    assert ratios["flauta"] > 0.8  # se mantiene mientras suena


def test_xylophone_has_no_second_harmonic_but_piano_does() -> None:
    def second_harmonic(instrument: str) -> float:
        samples = synthesize_tone(MI4, 0.7, SAMPLE_RATE, instrument)
        return band_amplitude(samples, 2 * MI4) / band_amplitude(samples, MI4)

    assert second_harmonic("xilofono") < 0.05
    assert second_harmonic("piano") > 0.15


def test_flute_starts_softly_while_xylophone_strikes() -> None:
    flute = synthesize_tone(MI4, 0.7, SAMPLE_RATE, "flauta")
    xylophone = synthesize_tone(MI4, 0.7, SAMPLE_RATE, "xilofono")
    first_5ms = int(0.005 * SAMPLE_RATE)
    assert np.abs(flute[:first_5ms]).max() < 0.2 * np.abs(flute).max()
    assert np.abs(xylophone[: int(0.02 * SAMPLE_RATE)]).max() > 0.8 * np.abs(xylophone).max()


# --- Gestor de audio --------------------------------------------------------
class Spy:
    def __init__(self) -> None:
        self.plays = 0

    def play(self) -> None:
        self.plays += 1

    def set_volume(self, _volume: float) -> None:
        pass


@pytest.fixture
def manager(tmp_path):
    manager = AudioManager(dataclasses.replace(AudioSettings(), sounds_dir=tmp_path))
    assert manager.available, manager.error
    yield manager
    manager.close()


def test_loads_all_instruments(manager: AudioManager) -> None:
    assert set(manager._banks) == {"piano", "xilofono", "flauta"}
    assert all(len(bank) == len(NOTES) for bank in manager._banks.values())


def test_play_uses_the_selected_instrument(manager: AudioManager) -> None:
    spies = {key: Spy() for key in manager._banks}
    for key, spy in spies.items():
        manager._banks[key]["mi4"] = spy
    manager.play("mi4")
    assert (spies["piano"].plays, spies["xilofono"].plays, spies["flauta"].plays) == (1, 0, 0)
    manager.set_instrument("flauta")
    manager.play("mi4")
    assert (spies["piano"].plays, spies["xilofono"].plays, spies["flauta"].plays) == (1, 0, 1)


def test_next_instrument_cycles(manager: AudioManager) -> None:
    assert manager.instrument.key == "piano"
    assert [manager.next_instrument().key for _ in range(4)] == [
        "xilofono",
        "flauta",
        "piano",
        "xilofono",
    ]


def test_unknown_instrument_raises(manager: AudioManager) -> None:
    with pytest.raises(KeyError):
        manager.set_instrument("tuba")
    assert manager.instrument.key == "piano"


def test_initial_instrument_comes_from_the_settings(tmp_path) -> None:
    manager = AudioManager(
        dataclasses.replace(AudioSettings(), sounds_dir=tmp_path, instrument="xilofono")
    )
    try:
        assert manager.instrument.label == "XILOFONO"
    finally:
        manager.close()


def test_invalid_instrument_in_settings_is_rejected() -> None:
    settings = Settings(audio=dataclasses.replace(AudioSettings(), instrument="tuba"))
    with pytest.raises(ValueError, match="Instrumento"):
        settings.validate()
