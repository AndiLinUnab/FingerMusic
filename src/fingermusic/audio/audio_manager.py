"""Reproducción de notas con baja latencia mediante ``pygame.mixer``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fingermusic.audio.notes import NOTES
from fingermusic.audio.synth import ERROR_SOUND_NAME, generate_error_file, generate_note_file
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
        loaded = sum(note.key in self._sounds for note in NOTES)
        logger.info("Audio listo: %d/%d notas y sonido de error", loaded, len(NOTES))

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
        self._load_error_sound(directory)
        self._apply_volume()
        if any(note.key not in self._sounds for note in NOTES):
            self.error = "Algunos sonidos no pudieron cargarse (ver logs)."

    def _load_error_sound(self, directory: Path) -> None:
        path = directory / f"{ERROR_SOUND_NAME}.wav"
        try:
            if not path.exists():
                logger.warning("Falta %s; se genera automáticamente", path.name)
                generate_error_file(
                    directory, self._settings.error_duration, self._settings.sample_rate
                )
            self._sounds[ERROR_SOUND_NAME] = self._pygame.mixer.Sound(str(path))
        except (OSError, self._pygame.error) as exc:
            logger.error("No se pudo cargar el sonido de error: %s", exc)

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

    def play_error(self) -> bool:
        """Reproduce el sonido de error (nota fallada en el modo canción)."""
        return self.play(ERROR_SOUND_NAME)

    def play_result(self, note_key: str, missed: bool) -> bool:
        """Reproduce el sonido que corresponde a una nota tocada.

        Un acierto (o el modo libre) suena como la nota. Un fallo suena como el
        sonido de error y, si ``error_plays_note`` está activo, también la nota.
        """
        if not missed:
            return self.play(note_key)
        played = self.play_error()
        if self._settings.error_plays_note:
            played = self.play(note_key) or played
        return played

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
