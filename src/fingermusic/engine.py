"""Motor de FingerMusic: convierte landmarks en eventos musicales.

No usa cámara, audio ni interfaz; solo recibe manos detectadas y devuelve qué
dedos se flexionaron y qué notas deben sonar. Esto lo hace fácil de probar.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from fingermusic.audio.notes import FingerMap, Note, build_finger_map
from fingermusic.config import DetectionSettings
from fingermusic.music.song import Song
from fingermusic.music.song_player import SongPlayer, SongResult
from fingermusic.vision.finger_detector import (
    CalibrationSession,
    FingerReading,
    HandFingerTracker,
    Transition,
)
from fingermusic.vision.landmarks import Finger, HandLandmarks, HandSide

logger = logging.getLogger(__name__)


class Mode(StrEnum):
    """Modo de uso de la aplicación."""

    FREE = "MODO LIBRE"
    SONG = "MODO CANCION"


@dataclass(frozen=True)
class PlayedNote:
    """Una nota generada por la flexión de un dedo."""

    note: Note
    side: HandSide
    finger: Finger
    song_result: SongResult | None = None
    #: Aciertos seguidos tras esta nota (solo tiene sentido en modo canción).
    streak: int = 0


@dataclass(frozen=True)
class HandView:
    """Estado de una mano en el frame actual, listo para dibujar."""

    hand: HandLandmarks
    readings: dict[Finger, FingerReading]
    notes: dict[Finger, Note]


@dataclass
class FrameResult:
    """Resultado de procesar un frame."""

    hands: list[HandView] = field(default_factory=list)
    played: list[PlayedNote] = field(default_factory=list)
    #: Avance de la calibración (0..1) mientras está en curso, si no ``None``.
    calibration_progress: float | None = None
    #: Mensaje informativo puntual (p. ej. fin de calibración).
    message: str | None = None


class MusicEngine:
    """Coordina trackers de dedos, mapeo a notas, modos y calibración."""

    def __init__(
        self,
        settings: DetectionSettings,
        songs: Song | Sequence[Song],
        swap_hands: bool = False,
    ) -> None:
        self._settings = settings
        self._songs: tuple[Song, ...] = (songs,) if isinstance(songs, Song) else tuple(songs)
        if not self._songs:
            raise ValueError("Se necesita al menos una canción")
        self._song_index = 0
        self._trackers: dict[HandSide, HandFingerTracker] = {
            side: HandFingerTracker(settings) for side in HandSide
        }
        self._frames_missing: dict[HandSide, int] = {side: 0 for side in HandSide}
        self._swap_hands = swap_hands
        self._finger_map: FingerMap = build_finger_map(swap_hands)
        self._mode = Mode.FREE
        self._song_player = SongPlayer(self._songs[0])
        self._streak = 0
        self._best_streak = 0
        self._calibration: CalibrationSession | None = None

    # --- Propiedades ------------------------------------------------------
    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def song_player(self) -> SongPlayer:
        return self._song_player

    @property
    def songs(self) -> tuple[Song, ...]:
        """Canciones disponibles."""
        return self._songs

    @property
    def song_index(self) -> int:
        """Posición (0-based) de la canción seleccionada."""
        return self._song_index

    @property
    def best_streak(self) -> int:
        """Mejor racha de la sesión (no se reinicia al reiniciar la canción)."""
        return self._best_streak

    @property
    def streak(self) -> int:
        """Aciertos seguidos en el modo canción (se reinicia al fallar)."""
        return self._streak

    @property
    def swap_hands(self) -> bool:
        return self._swap_hands

    @property
    def finger_map(self) -> FingerMap:
        return self._finger_map

    @property
    def calibrating(self) -> bool:
        return self._calibration is not None

    # --- Control ----------------------------------------------------------
    def set_mode(self, mode: Mode) -> None:
        """Cambia de modo. Al entrar en modo canción se reinicia la canción."""
        if mode is Mode.SONG and self._mode is not Mode.SONG:
            self._song_player.restart()
            self._streak = 0
        self._mode = mode
        logger.info("Modo: %s", mode.value)

    def select_song(self, index: int) -> Song:
        """Selecciona una canción (con vuelta circular), reiniciando su progreso y la racha."""
        self._song_index = index % len(self._songs)
        self._song_player = SongPlayer(self._songs[self._song_index])
        self._streak = 0
        logger.info("Cancion: %s", self._songs[self._song_index].title)
        return self._songs[self._song_index]

    def next_song(self) -> Song:
        """Pasa a la canción siguiente (después de la última vuelve a la primera)."""
        return self.select_song(self._song_index + 1)

    def previous_song(self) -> Song:
        """Vuelve a la canción anterior (antes de la primera va a la última)."""
        return self.select_song(self._song_index - 1)

    def restart_song(self) -> None:
        """Reinicia la canción desde la primera nota y la racha."""
        self._song_player.restart()
        self._streak = 0

    def toggle_swap_hands(self) -> bool:
        """Intercambia las notas de las manos. Devuelve el nuevo estado."""
        self._swap_hands = not self._swap_hands
        self._finger_map = build_finger_map(self._swap_hands)
        return self._swap_hands

    def start_calibration(self, now: float) -> None:
        """Inicia la calibración con la mano abierta."""
        self._calibration = CalibrationSession(self._settings, now)
        logger.info("Calibracion iniciada")

    def reset_trackers(self) -> None:
        """Reinicia el estado de todos los dedos (p. ej. al reanudar la cámara)."""
        for tracker in self._trackers.values():
            tracker.reset()
        self._frames_missing = {side: 0 for side in HandSide}

    # --- Procesamiento ----------------------------------------------------
    def process(self, hands: list[HandLandmarks], now: float) -> FrameResult:
        """Procesa las manos detectadas en un frame.

        Args:
            hands: manos detectadas (como máximo una por lado).
            now: instante actual en segundos (reloj monotónico).
        """
        result = FrameResult()
        self._handle_missing_hands({hand.side for hand in hands})

        for hand in hands:
            tracker = self._trackers[hand.side]
            readings = tracker.update(hand, now)
            notes = self._finger_map[hand.side]
            result.hands.append(HandView(hand, readings, notes))

            if self._calibration is not None:
                self._calibration.add_sample(hand.side, tracker.raw_scores(hand))
                continue  # durante la calibración no suenan notas
            for finger, reading in readings.items():
                if reading.transition is Transition.PRESSED:
                    result.played.append(self._build_played_note(hand.side, finger, notes))

        self._update_calibration(now, result)
        return result

    def _build_played_note(
        self, side: HandSide, finger: Finger, notes: dict[Finger, Note]
    ) -> PlayedNote:
        note = notes[finger]
        song_result = None
        if self._mode is Mode.SONG:
            song_result = self._song_player.play_note(note.key)
            if song_result in (SongResult.HIT, SongResult.FINISHED):
                self._streak += 1
                self._best_streak = max(self._best_streak, self._streak)
            elif song_result is SongResult.MISS:
                self._streak = 0
        logger.debug(
            "Nota %s (%s, %s) resultado=%s", note.label, side.value, finger.name, song_result
        )
        return PlayedNote(note, side, finger, song_result, self._streak)

    def _handle_missing_hands(self, present: set[HandSide]) -> None:
        for side in HandSide:
            if side in present:
                self._frames_missing[side] = 0
                continue
            self._frames_missing[side] += 1
            if self._frames_missing[side] == self._settings.hand_lost_reset_frames:
                self._trackers[side].reset()

    def _update_calibration(self, now: float, result: FrameResult) -> None:
        session = self._calibration
        if session is None:
            return
        if not session.is_done(now):
            result.calibration_progress = session.progress(now)
            return
        baselines = session.result()
        self._calibration = None
        if not baselines:
            result.message = "Calibracion fallida: no se vio ninguna mano. Intenta de nuevo."
            logger.warning(result.message)
            return
        for side, per_finger in baselines.items():
            self._trackers[side].set_baselines(per_finger)
            self._trackers[side].reset()
        sides = ", ".join(side.label for side in baselines)
        result.message = f"Calibracion completada (mano {sides})."
        logger.info(result.message)
