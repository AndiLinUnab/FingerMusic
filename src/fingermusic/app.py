"""Aplicación principal: une cámara, modelo, motor, audio e interfaz."""

from __future__ import annotations

import logging
import time

import numpy as np

from fingermusic.audio.audio_manager import AudioManager
from fingermusic.audio.notes import NOTES_BY_KEY
from fingermusic.camera.camera_manager import CameraError, CameraManager
from fingermusic.config import Settings
from fingermusic.engine import FrameResult, Mode, MusicEngine
from fingermusic.music.jingle_bells import build_jingle_bells
from fingermusic.music.song_player import SongResult
from fingermusic.ui.interface import Action, Interface, ViewState
from fingermusic.utils.helpers import exponential_smoothing
from fingermusic.vision.hand_detector import HandDetector, HandDetectorError
from fingermusic.vision.landmarks import Finger, HandSide

logger = logging.getLogger(__name__)

_FPS_SMOOTHING = 0.1
_MAX_DETECTION_ERRORS = 30
_STREAK_MILESTONE = 10  # cada cuántos aciertos seguidos se muestra un mensaje


class Application:
    """Bucle principal de FingerMusic.

    Flujo por frame: cámara -> modelo -> motor (dedos, notas, canción) -> audio -> interfaz.
    """

    def __init__(self, settings: Settings, swap_hands: bool = False) -> None:
        self._settings = settings
        self._detector = HandDetector(settings.detection)  # puede lanzar HandDetectorError
        self._camera = CameraManager(settings.camera)
        self._audio = AudioManager(settings.audio)
        self._engine = MusicEngine(settings.detection, build_jingle_bells(), swap_hands)
        self._ui = Interface(settings.ui)

        self._running = False
        self._camera_on = False
        self._landmarks_on = settings.ui.show_landmarks
        self._last_frame: np.ndarray | None = None
        self._last_result = FrameResult()
        self._fps = 0.0
        self._detection_errors = 0

        self._press_times: dict[tuple[HandSide, Finger], float] = {}
        self._last_note_label: str | None = None
        self._last_note_time = float("-inf")
        self._feedback: SongResult | None = None
        self._feedback_time = float("-inf")
        self._message: str | None = None
        self._message_error = False
        self._message_until = 0.0

    # --- Ciclo de vida ----------------------------------------------------
    def run(self) -> int:
        """Ejecuta la aplicación hasta que el usuario sale. Devuelve el código de salida."""
        self._ui.open()
        if self._audio.error:
            self._set_message(self._audio.error, error=True)
        self._start_camera()
        self._running = True
        previous = time.monotonic()
        try:
            while self._running:
                now = time.monotonic()
                self._fps = exponential_smoothing(
                    self._fps, 1.0 / max(now - previous, 1e-3), _FPS_SMOOTHING
                )
                previous = now
                self._step(now)
                for action in self._ui.poll_actions():
                    self._handle_action(action, now)
        finally:
            self._shutdown()
        return 0

    def _shutdown(self) -> None:
        self._camera.release()
        self._detector.close()
        self._audio.close()
        self._ui.close()
        logger.info("Aplicacion cerrada")

    # --- Un frame ---------------------------------------------------------
    def _step(self, now: float) -> None:
        if self._camera_on:
            frame = self._read_frame()
            if frame is not None:
                self._last_frame = frame
                self._last_result = self._analyze(frame, now)
        self._ui.show(self._ui.render(self._last_frame, self._build_state(now)))

    def _read_frame(self) -> np.ndarray | None:
        try:
            return self._camera.read()
        except CameraError as exc:
            logger.error("%s", exc)
            self._stop_camera()
            self._set_message(str(exc), error=True)
            return None

    def _analyze(self, frame: np.ndarray, now: float) -> FrameResult:
        try:
            hands = self._detector.detect(frame)
            self._detection_errors = 0
        except HandDetectorError as exc:
            self._detection_errors += 1
            logger.warning("Error de deteccion (%d): %s", self._detection_errors, exc)
            if self._detection_errors >= _MAX_DETECTION_ERRORS:
                self._stop_camera()
                self._set_message("El modelo de manos fallo repetidamente. Revisa los logs.", True)
            hands = []

        result = self._engine.process(hands, now)
        for played in result.played:
            self._audio.play(played.note.key)
            self._press_times[(played.side, played.finger)] = now
            self._last_note_label = played.note.label
            self._last_note_time = now
            if played.song_result is not None and played.song_result is not SongResult.IGNORED:
                self._feedback = played.song_result
                self._feedback_time = now
                if (
                    played.song_result in (SongResult.HIT, SongResult.FINISHED)
                    and played.streak % _STREAK_MILESTONE == 0
                ):
                    self._set_message(f"Racha de {played.streak} aciertos seguidos!")
        if result.message:
            self._set_message(result.message, error="fallida" in result.message)
        return result

    # --- Acciones ---------------------------------------------------------
    def _handle_action(self, action: Action, now: float) -> None:
        if action is Action.QUIT:
            self._running = False
        elif action is Action.TOGGLE_CAMERA:
            self._stop_camera() if self._camera_on else self._start_camera()
        elif action is Action.MODE_FREE:
            self._engine.set_mode(Mode.FREE)
        elif action is Action.MODE_SONG:
            self._engine.set_mode(Mode.SONG)
            self._feedback = None
        elif action is Action.RESTART_SONG:
            self._engine.restart_song()
            self._feedback = None
            self._set_message("Cancion reiniciada.")
        elif action is Action.CALIBRATE:
            self._start_calibration(now)
        elif action is Action.TOGGLE_LANDMARKS:
            self._landmarks_on = not self._landmarks_on
        elif action is Action.TOGGLE_SOUND:
            self._toggle_sound()
        elif action is Action.SWAP_HANDS:
            swapped = self._engine.toggle_swap_hands()
            self._set_message(
                "Notas intercambiadas: mano DERECHA = DO..SOL"
                if swapped
                else "Notas por defecto: mano IZQUIERDA = DO..SOL"
            )
        elif action in (Action.VOLUME_UP, Action.VOLUME_DOWN):
            step = self._settings.audio.volume_step
            delta = step if action is Action.VOLUME_UP else -step
            self._audio.set_volume(self._audio.volume + delta)

    def _start_camera(self) -> None:
        try:
            self._camera.open()
        except CameraError as exc:
            logger.error("%s", exc)
            self._set_message(str(exc), error=True)
            return
        self._camera_on = True
        self._engine.reset_trackers()

    def _stop_camera(self) -> None:
        self._camera.release()
        self._camera_on = False
        self._last_frame = None
        self._last_result = FrameResult()
        self._engine.reset_trackers()

    def _start_calibration(self, now: float) -> None:
        if not self._camera_on:
            self._set_message("Inicia la camara antes de calibrar.", error=True)
            return
        self._engine.start_calibration(now)

    def _toggle_sound(self) -> None:
        if not self._audio.available:
            self._set_message(self._audio.error or "Audio no disponible.", error=True)
            return
        self._audio.toggle_enabled()

    # --- Estado de la interfaz -------------------------------------------
    def _set_message(self, text: str, error: bool = False) -> None:
        self._message = text
        self._message_error = error
        self._message_until = time.monotonic() + self._settings.ui.message_seconds

    def _build_state(self, now: float) -> ViewState:
        player = self._engine.song_player
        current = player.current
        upcoming = player.next

        def label(key: str | None) -> str | None:
            return NOTES_BY_KEY[key].label if key else None

        message = self._message if now < self._message_until else None
        return ViewState(
            mode=self._engine.mode,
            camera_on=self._camera_on,
            landmarks_on=self._landmarks_on,
            sound_on=self._audio.enabled,
            audio_available=self._audio.available,
            volume=self._audio.volume,
            swap_hands=self._engine.swap_hands,
            fps=self._fps,
            finger_map=self._engine.finger_map,
            hands=self._last_result.hands if self._camera_on else [],
            recent_presses={key: now - t for key, t in self._press_times.items()},
            last_note_label=self._last_note_label,
            last_note_age=now - self._last_note_time,
            song_title=player.title,
            song_index=player.index,
            song_total=player.total,
            song_progress=player.progress,
            song_finished=player.finished,
            streak=self._engine.streak,
            current_label=label(current),
            next_label=label(upcoming),
            feedback=self._feedback,
            feedback_age=now - self._feedback_time,
            message=message,
            message_is_error=self._message_error,
            calibration_progress=self._last_result.calibration_progress
            if self._camera_on
            else None,
        )
