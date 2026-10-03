"""Reproducción de notas con baja latencia mediante ``pygame.mixer``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fingermusic.audio.notes import NOTES
from fingermusic.audio.synth import generate_note_file
from fingermusic.config import AudioSettings
from fingermusic.utils.helpers import clamp

logger = logging.getLogger(__name__)


class AudioError(RuntimeError):
    """El sistema de audio no está disponible."""


class AudioManager:
    """Carga los sonidos de las notas y los reproduce al instante.

    Si el dispositivo de audio no está disponible, ``available`` es ``False`` y
    ``play`` no hace nada: la aplicación sigue funcionando sin sonido.
    """

    def __init__(self, settings: AudioSettings) -> None:
        self._settings = settings
        self._volume = clamp(settings.volume)
        self._enabled = True
        self._sounds: dict[str, Any] = {}
        self._pygame: Any = None
        self.error: str | None = None
        self._initialize()

    # --- Propiedades ------------------------------------------------------
    @property
    def available(self) -> bool:
        """``True`` si el mezclador de audio está operativo."""
        return self._pygame is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def volume(self) -> float:
        return self._volume

    # --- Inicialización ---------------------------------------------------
    def _initialize(self) -> None:
        try:
            import pygame
        except ImportError:
            self.error = "Falta la dependencia 'pygame' (pip install -r requirements.txt)."
            logger.error(self.error)
            return
        s = self._settings
        try:
            pygame.mixer.pre_init(s.sample_rate, -16, 1, s.buffer_size)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(s.channels)
        except pygame.error as exc:
            self.error = f"Dispositivo de audio no disponible: {exc}"
            logger.error(self.error)
            return
        self._pygame = pygame
        self._load_sounds()
        logger.info("Audio listo: %d/%d sonidos cargados", len(self._sounds), len(NOTES))

    def _load_sounds(self) -> None:
        directory: Path = self._settings.sounds_dir
        for note in NOTES:
            path = directory / f"{note.key}.wav"
            try:
                if not path.exists():
                    logger.warning("Falta %s; se genera automáticamente", path.name)
                    generate_note_file(
                        note, directory, self._settings.note_duration, self._settings.sample_rate
                    )
                self._sounds[note.key] = self._pygame.mixer.Sound(str(path))
            except (OSError, self._pygame.error) as exc:
                logger.error("No se pudo cargar el sonido %s: %s", path.name, exc)
        self._apply_volume()
        if len(self._sounds) < len(NOTES):
            self.error = "Algunos sonidos no pudieron cargarse (ver logs)."

    def _apply_volume(self) -> None:
        for sound in self._sounds.values():
            sound.set_volume(self._volume)

    # --- Control ----------------------------------------------------------
    def play(self, note_key: str) -> bool:
        """Reproduce una nota. Devuelve ``True`` si realmente se envió al mezclador."""
        if not (self.available and self._enabled):
            return False
        sound = self._sounds.get(note_key)
        if sound is None:
            logger.warning("Nota sin sonido cargado: %s", note_key)
            return False
        sound.play()
        return True

    def set_volume(self, volume: float) -> float:
        """Fija el volumen (0..1) y devuelve el valor aplicado."""
        self._volume = clamp(volume)
        self._apply_volume()
        return self._volume

    def toggle_enabled(self) -> bool:
        """Activa/desactiva el sonido. Devuelve el nuevo estado."""
        self._enabled = not self._enabled
        return self._enabled

    def close(self) -> None:
        """Libera el mezclador de audio."""
        if self._pygame is not None:
            self._pygame.mixer.quit()
            self._pygame = None
            self._sounds.clear()
