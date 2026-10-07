"""Instrumentos disponibles (timbres sintetizados)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    """Un instrumento: ``key`` nombra su carpeta de sonidos y ``label`` se muestra en pantalla."""

    key: str
    label: str


#: Instrumentos en el orden en que se recorren al cambiarlos.
INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument("piano", "PIANO"),
    Instrument("xilofono", "XILOFONO"),
    Instrument("flauta", "FLAUTA"),
)

DEFAULT_INSTRUMENT = "piano"


def get_instrument(key: str) -> Instrument:
    """Devuelve el instrumento con la clave indicada.

    Raises:
        KeyError: si no existe.
    """
    for instrument in INSTRUMENTS:
        if instrument.key == key:
            return instrument
    raise KeyError(f"Instrumento desconocido: {key!r}")


def next_instrument(key: str) -> Instrument:
    """Devuelve el instrumento que sigue a ``key`` (después del último vuelve al primero)."""
    index = INSTRUMENTS.index(get_instrument(key))
    return INSTRUMENTS[(index + 1) % len(INSTRUMENTS)]
