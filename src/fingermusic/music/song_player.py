"""Seguimiento del avance del usuario dentro de una canción."""

from __future__ import annotations

from enum import StrEnum

from fingermusic.music.jingle_bells import Song


class SongResult(StrEnum):
    """Resultado de comparar una nota tocada con la esperada."""

    HIT = "acierto"
    MISS = "error"
    FINISHED = "terminada"
    IGNORED = "ignorada"  # la canción ya había terminado


class SongPlayer:
    """Guía al usuario nota a nota por una canción."""

    def __init__(self, song: Song) -> None:
        self._song = song
        self._index = 0

    @property
    def title(self) -> str:
        return self._song.title

    @property
    def index(self) -> int:
        """Posición de la nota esperada (0-based)."""
        return self._index

    @property
    def total(self) -> int:
        return len(self._song)

    @property
    def finished(self) -> bool:
        return self._index >= self.total

    @property
    def current(self) -> str | None:
        """Clave de la nota que hay que tocar ahora (``None`` si terminó)."""
        return None if self.finished else self._song.notes[self._index]

    @property
    def next(self) -> str | None:
        """Clave de la nota siguiente a la actual (``None`` si no hay)."""
        position = self._index + 1
        return self._song.notes[position] if position < self.total else None

    @property
    def progress(self) -> float:
        """Fracción completada (0..1)."""
        return self._index / self.total

    def restart(self) -> None:
        """Vuelve al principio de la canción."""
        self._index = 0

    def play_note(self, note_key: str) -> SongResult:
        """Registra una nota tocada.

        Returns:
            ``HIT`` si coincide con la esperada (y avanza), ``FINISHED`` si era la
            última, ``MISS`` si no coincide (no avanza) o ``IGNORED`` si la
            canción ya había terminado.
        """
        if self.finished:
            return SongResult.IGNORED
        if note_key != self.current:
            return SongResult.MISS
        self._index += 1
        return SongResult.FINISHED if self.finished else SongResult.HIT
