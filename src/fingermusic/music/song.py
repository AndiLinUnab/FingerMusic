"""Modelo de canción: una secuencia ordenada de notas."""

from __future__ import annotations

from dataclasses import dataclass

from fingermusic.audio.notes import HIGH_NOTES, NOTES_BY_KEY


def parse_notes(text: str) -> tuple[str, ...]:
    """Convierte ``"mi4 mi4 sol4"`` en una tupla de claves de nota."""
    return tuple(text.split())


@dataclass(frozen=True)
class Song:
    """Una canción como secuencia ordenada de claves de nota (ver ``audio/notes.py``)."""

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

    @property
    def both_hands(self) -> bool:
        """``True`` si usa notas agudas (LA..MI'), que están en la mano derecha."""
        return any(key in HIGH_NOTES for key in self.notes)
