"""Catálogo de canciones disponibles.

Todas son melodías tradicionales o compuestas hace más de 100 años, es decir, de
dominio público. Están simplificadas (sin ritmo) y transcritas por el autor del
proyecto; el usuario marca el tempo.
"""

from __future__ import annotations

from fingermusic.music.jingle_bells import build_jingle_bells
from fingermusic.music.song import Song, parse_notes


def build_estrellita() -> Song:
    """Estrellita (melodía tradicional francesa del siglo XVIII). Usa LA: requiere las dos manos."""
    phrases = (
        "do4 do4 sol4 sol4 la4 la4 sol4",
        "fa4 fa4 mi4 mi4 re4 re4 do4",
        "sol4 sol4 fa4 fa4 mi4 mi4 re4",
        "sol4 sol4 fa4 fa4 mi4 mi4 re4",
        "do4 do4 sol4 sol4 la4 la4 sol4",
        "fa4 fa4 mi4 mi4 re4 re4 do4",
    )
    return Song("ESTRELLITA", parse_notes(" ".join(phrases)))


def build_ode_to_joy() -> Song:
    """Himno a la Alegría (Beethoven, 1824), tema principal. Solo DO..SOL: una mano."""
    phrases = (
        "mi4 mi4 fa4 sol4 sol4 fa4 mi4 re4 do4 do4 re4 mi4 mi4 re4 re4",
        "mi4 mi4 fa4 sol4 sol4 fa4 mi4 re4 do4 do4 re4 mi4 re4 do4 do4",
        "re4 re4 mi4 do4 re4 mi4 fa4 mi4 do4 re4 mi4 fa4 mi4 re4 do4 re4 sol4",
        "mi4 mi4 fa4 sol4 sol4 fa4 mi4 re4 do4 do4 re4 mi4 re4 do4 do4",
    )
    return Song("HIMNO A LA ALEGRIA", parse_notes(" ".join(phrases)))


def build_mary_lamb() -> Song:
    """Mary tenía un corderito (tradicional, 1830). Solo DO..SOL: una mano."""
    phrases = (
        "mi4 re4 do4 re4 mi4 mi4 mi4",
        "re4 re4 re4",
        "mi4 sol4 sol4",
        "mi4 re4 do4 re4 mi4 mi4 mi4 mi4",
        "re4 re4 mi4 re4 do4",
    )
    return Song("MARY Y SU CORDERITO", parse_notes(" ".join(phrases)))


def build_songs() -> tuple[Song, ...]:
    """Devuelve todas las canciones, en el orden en que se ofrecen al usuario."""
    return (build_jingle_bells(), build_estrellita(), build_ode_to_joy(), build_mary_lamb())
