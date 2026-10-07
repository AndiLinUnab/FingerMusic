"""Versión simplificada del estribillo de Jingle Bells (Do mayor, solo 5 notas)."""

from __future__ import annotations

from fingermusic.music.song import Song, parse_notes

# Solo usa DO, RE, MI, FA y SOL, es decir, las cinco notas de una mano.
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

__all__ = ["Song", "build_jingle_bells", "parse_notes"]


def build_jingle_bells() -> Song:
    """Construye la canción Jingle Bells simplificada."""
    notes: tuple[str, ...] = ()
    for phrase in _PHRASES:
        notes += parse_notes(phrase)
    return Song(title="JINGLE BELLS", notes=notes)
