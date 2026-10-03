"""Versión simplificada del estribillo de Jingle Bells (Do mayor, solo 5 notas)."""

from __future__ import annotations

from dataclasses import dataclass

from fingermusic.audio.notes import NOTES_BY_KEY

# Frases en notación de claves (ver audio/notes.py). Solo usa DO, RE, MI, FA y SOL,
# es decir, las cinco notas de una mano.
_PHRASES: tuple[str, ...] = (
    # "Jingle bells, jingle bells, jingle all the way"
    "mi4 mi4 mi4  mi4 mi4 mi4  mi4 sol4 do4 re4 mi4",
    # "Oh what fun it is to ride in a one-horse open sleigh"
    "fa4 fa4 fa4 fa4 fa4  mi4 mi4 mi4 mi4 mi4  re4 re4 mi4 re4 sol4",
    # "Jingle bells, jingle bells, jingle all the way"
    "mi4 mi4 mi4  mi4 mi4 mi4  mi4 sol4 do4 re4 mi4",
    # "Oh what fun it is to ride in a one-horse open sleigh"
    "fa4 fa4 fa4 fa4 fa4  mi4 mi4 mi4 mi4  sol4 sol4 fa4 re4 do4",
)


@dataclass(frozen=True)
class Song:
    """Una canción como secuencia ordenada de claves de nota."""

    title: str
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.notes:
            raise ValueError("Una canción debe tener al menos una nota")
        unknown = [key for key in self.notes if key not in NOTES_BY_KEY]
        if unknown:
            raise ValueError(f"Notas desconocidas en la canción: {sorted(set(unknown))}")

    def __len__(self) -> int:
        return len(self.notes)


def parse_notes(text: str) -> tuple[str, ...]:
    """Convierte ``"mi4 mi4 sol4"`` en una tupla de claves."""
    return tuple(text.split())


def build_jingle_bells() -> Song:
    """Construye la canción Jingle Bells simplificada."""
    notes: tuple[str, ...] = ()
    for phrase in _PHRASES:
        notes += parse_notes(phrase)
    return Song(title="JINGLE BELLS", notes=notes)
