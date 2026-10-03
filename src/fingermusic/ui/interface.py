"""Interfaz gráfica de FingerMusic dibujada con OpenCV.

OpenCV usa fuentes Hershey que no soportan acentos ni la letra Ñ; por eso los
textos de la interfaz están escritos sin tildes ("Menique", "CANCION").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

import cv2
import numpy as np

from fingermusic.audio.notes import FingerMap
from fingermusic.config import UiSettings
from fingermusic.engine import HandView, Mode
from fingermusic.music.song_player import SongResult
from fingermusic.vision.finger_detector import FingerState
from fingermusic.vision.landmarks import HAND_CONNECTIONS, Finger, HandSide, Landmark

logger = logging.getLogger(__name__)

# --- Geometría de la ventana ------------------------------------------------
VIDEO_W, VIDEO_H = 640, 480
SIDEBAR_W = 300
HEADER_H = 56
FOOTER_H = 170
CANVAS_W = VIDEO_W + SIDEBAR_W
CANVAS_H = HEADER_H + VIDEO_H + FOOTER_H

# --- Colores (BGR) ----------------------------------------------------------
BG = (34, 30, 28)
PANEL = (52, 46, 44)
PANEL_LIGHT = (72, 64, 60)
TEXT = (240, 240, 240)
TEXT_DIM = (150, 145, 140)
ACCENT = (230, 170, 60)
GREEN = (110, 210, 120)
RED = (80, 80, 235)
YELLOW = (70, 215, 250)
FONT = cv2.FONT_HERSHEY_SIMPLEX

_FINGER_TIPS = {
    Finger.THUMB: Landmark.THUMB_TIP,
    Finger.INDEX: Landmark.INDEX_TIP,
    Finger.MIDDLE: Landmark.MIDDLE_TIP,
    Finger.RING: Landmark.RING_TIP,
    Finger.PINKY: Landmark.PINKY_TIP,
}


class Action(StrEnum):
    """Acciones que el usuario puede pedir desde la interfaz."""

    TOGGLE_CAMERA = "toggle_camera"
    MODE_FREE = "mode_free"
    MODE_SONG = "mode_song"
    RESTART_SONG = "restart_song"
    CALIBRATE = "calibrate"
    TOGGLE_LANDMARKS = "toggle_landmarks"
    TOGGLE_SOUND = "toggle_sound"
    SWAP_HANDS = "swap_hands"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    QUIT = "quit"


_KEY_BINDINGS: dict[int, Action] = {
    ord("q"): Action.QUIT,
    27: Action.QUIT,  # ESC
    ord(" "): Action.TOGGLE_CAMERA,
    ord("1"): Action.MODE_FREE,
    ord("2"): Action.MODE_SONG,
    ord("r"): Action.RESTART_SONG,
    ord("c"): Action.CALIBRATE,
    ord("l"): Action.TOGGLE_LANDMARKS,
    ord("s"): Action.TOGGLE_SOUND,
    ord("h"): Action.SWAP_HANDS,
    ord("+"): Action.VOLUME_UP,
    ord("="): Action.VOLUME_UP,
    ord("-"): Action.VOLUME_DOWN,
}


@dataclass
class ViewState:
    """Todo lo que la interfaz necesita para dibujar un frame."""

    mode: Mode = Mode.FREE
    camera_on: bool = False
    landmarks_on: bool = True
    sound_on: bool = True
    audio_available: bool = True
    volume: float = 0.8
    swap_hands: bool = False
    fps: float = 0.0
    finger_map: FingerMap = field(default_factory=dict)
    hands: list[HandView] = field(default_factory=list)
    #: Edad (s) de la última pulsación de cada (mano, dedo), para resaltarlo.
    recent_presses: dict[tuple[HandSide, Finger], float] = field(default_factory=dict)
    last_note_label: str | None = None
    last_note_age: float = 999.0
    # Modo canción
    song_title: str = ""
    song_index: int = 0
    song_total: int = 0
    song_progress: float = 0.0
    song_finished: bool = False
    current_label: str | None = None
    next_label: str | None = None
    feedback: SongResult | None = None
    feedback_age: float = 999.0
    # Mensajes y calibración
    message: str | None = None
    message_is_error: bool = False
    calibration_progress: float | None = None


@dataclass(frozen=True)
class _Button:
    action: Action
    rect: tuple[int, int, int, int]  # x, y, ancho, alto


def put_text(
    img: np.ndarray,
    text: str,
    origin: tuple[int, int],
    scale: float = 0.5,
    color: tuple[int, int, int] = TEXT,
    thickness: int = 1,
    center_width: int | None = None,
) -> None:
    """Dibuja texto; si ``center_width`` se indica, lo centra en ese ancho desde ``origin``."""
    x, y = origin
    if center_width is not None:
        (text_w, _), _ = cv2.getTextSize(text, FONT, scale, thickness)
        x += max(0, (center_width - text_w) // 2)
    cv2.putText(img, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


class Interface:
    """Ventana principal: dibuja el estado y recoge las acciones del usuario."""

    def __init__(self, settings: UiSettings) -> None:
        self._settings = settings
        self._window = settings.window_title
        self._pending: list[Action] = []
        self._buttons: list[_Button] = []
        self._window_open = False

    # --- Ventana ----------------------------------------------------------
    def open(self) -> None:
        """Crea la ventana y registra el ratón."""
        cv2.namedWindow(self._window, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self._window, self._on_mouse)
        self._window_open = True

    def close(self) -> None:
        """Destruye la ventana."""
        if self._window_open:
            cv2.destroyAllWindows()
            self._window_open = False

    def show(self, canvas: np.ndarray) -> None:
        """Muestra un lienzo ya dibujado."""
        cv2.imshow(self._window, canvas)

    def poll_actions(self) -> list[Action]:
        """Procesa eventos de teclado/ratón y devuelve las acciones pendientes."""
        key = cv2.waitKey(1) & 0xFF
        if key in _KEY_BINDINGS:
            self._pending.append(_KEY_BINDINGS[key])
        if self._window_open and cv2.getWindowProperty(self._window, cv2.WND_PROP_VISIBLE) < 1:
            self._pending.append(Action.QUIT)  # el usuario cerró la ventana con la X
        actions, self._pending = self._pending, []
        return actions

    def _on_mouse(self, event: int, x: int, y: int, _flags: int, _param: object) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        for button in self._buttons:
            bx, by, bw, bh = button.rect
            if bx <= x <= bx + bw and by <= y <= by + bh:
                self._pending.append(button.action)
                return

    # --- Dibujo -----------------------------------------------------------
    def render(self, frame: np.ndarray | None, state: ViewState) -> np.ndarray:
        """Compone la imagen completa de la interfaz."""
        canvas = np.full((CANVAS_H, CANVAS_W, 3), BG, dtype=np.uint8)
        self._draw_header(canvas, state)
        self._draw_video(canvas, frame, state)
        self._draw_sidebar(canvas, state)
        self._draw_footer(canvas, state)
        return canvas

    def _draw_header(self, canvas: np.ndarray, state: ViewState) -> None:
        cv2.rectangle(canvas, (0, 0), (CANVAS_W, HEADER_H), PANEL, -1)
        put_text(canvas, "FINGERMUSIC", (18, 38), 1.0, ACCENT, 2)
        put_text(canvas, "Instrumento musical virtual", (260, 36), 0.5, TEXT_DIM)
        put_text(canvas, f"{state.fps:4.1f} FPS", (CANVAS_W - 100, 36), 0.5, TEXT_DIM)

    def _draw_video(self, canvas: np.ndarray, frame: np.ndarray | None, state: ViewState) -> None:
        x0, y0 = 0, HEADER_H
        area = canvas[y0 : y0 + VIDEO_H, x0 : x0 + VIDEO_W]
        if frame is None:
            area[:] = (24, 22, 20)
            text = "Camara detenida (pulsa ESPACIO)" if not state.camera_on else "Sin imagen..."
            put_text(area, text, (0, VIDEO_H // 2), 0.7, TEXT_DIM, 1, center_width=VIDEO_W)
        else:
            height, width = frame.shape[:2]
            area[:] = (
                cv2.resize(frame, (VIDEO_W, VIDEO_H))
                if (width, height) != (VIDEO_W, VIDEO_H)
                else frame
            )
            if state.landmarks_on:
                scale = (VIDEO_W / width, VIDEO_H / height)
                for view in state.hands:
                    self._draw_hand(area, view, scale)
            if not state.hands:
                put_text(
                    area,
                    "Coloca la mano frente a la camara",
                    (0, 30),
                    0.6,
                    YELLOW,
                    1,
                    center_width=VIDEO_W,
                )
        self._draw_feedback_border(area, state)
        self._draw_calibration(area, state)

    def _draw_hand(self, area: np.ndarray, view: HandView, scale: tuple[float, float]) -> None:
        points = [(int(x * scale[0]), int(y * scale[1])) for x, y, _ in view.hand.points]
        for start, end in HAND_CONNECTIONS:
            cv2.line(area, points[start], points[end], (230, 230, 230), 1, cv2.LINE_AA)
        for point in points:
            cv2.circle(area, point, 3, (60, 60, 60), -1, cv2.LINE_AA)
        for finger, reading in view.readings.items():
            tip = points[int(_FINGER_TIPS[finger])]
            flexed = reading.state is FingerState.FLEXED
            cv2.circle(area, tip, 9, GREEN if flexed else ACCENT, -1, cv2.LINE_AA)
            note = view.notes[finger]
            put_text(
                area, f"{finger.label} {note.label}", (tip[0] - 25, tip[1] - 16), 0.45, TEXT, 1
            )

    def _draw_feedback_border(self, area: np.ndarray, state: ViewState) -> None:
        if state.mode is not Mode.SONG or state.feedback is None:
            return
        if state.feedback_age > self._settings.feedback_seconds:
            return
        color = RED if state.feedback is SongResult.MISS else GREEN
        cv2.rectangle(area, (0, 0), (VIDEO_W - 1, VIDEO_H - 1), color, 6)

    def _draw_calibration(self, area: np.ndarray, state: ViewState) -> None:
        if state.calibration_progress is None:
            return
        overlay = area.copy()
        cv2.rectangle(overlay, (0, 0), (VIDEO_W, 70), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, area, 0.4, 0, area)
        put_text(
            area,
            "CALIBRANDO: manten la mano abierta y quieta",
            (0, 28),
            0.65,
            YELLOW,
            1,
            center_width=VIDEO_W,
        )
        self._draw_bar(area, (120, 42, VIDEO_W - 240, 14), state.calibration_progress, YELLOW)

    def _draw_bar(
        self,
        img: np.ndarray,
        rect: tuple[int, int, int, int],
        fraction: float,
        color: tuple[int, int, int],
    ) -> None:
        x, y, w, h = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), PANEL_LIGHT, -1)
        cv2.rectangle(img, (x, y), (x + int(w * max(0.0, min(1.0, fraction))), y + h), color, -1)

    def _draw_sidebar(self, canvas: np.ndarray, state: ViewState) -> None:
        x0, y0 = VIDEO_W, HEADER_H
        cv2.rectangle(canvas, (x0, y0), (CANVAS_W, y0 + VIDEO_H), PANEL, -1)
        put_text(canvas, state.mode.value, (x0 + 16, y0 + 30), 0.75, ACCENT, 2)
        if state.mode is Mode.SONG:
            self._draw_song_panel(canvas, state, x0, y0)
        else:
            self._draw_free_panel(canvas, state, x0, y0)
        self._draw_buttons(canvas, state, x0, y0 + 250)

    def _draw_free_panel(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        put_text(canvas, "NOTA SONANDO", (x0 + 16, y0 + 68), 0.5, TEXT_DIM)
        playing = state.last_note_age <= self._settings.note_highlight_seconds
        label = state.last_note_label if playing and state.last_note_label else "-"
        put_text(canvas, label, (x0 + 16, y0 + 125), 1.8, GREEN if playing else TEXT_DIM, 3)
        put_text(canvas, "Flexiona un dedo para", (x0 + 16, y0 + 175), 0.5, TEXT_DIM)
        put_text(canvas, "tocar su nota.", (x0 + 16, y0 + 197), 0.5, TEXT_DIM)
        put_text(canvas, "Mano izq: DO..SOL", (x0 + 16, y0 + 225), 0.45, TEXT_DIM)
        put_text(canvas, "Mano der: LA..MI'", (x0 + 16, y0 + 243), 0.45, TEXT_DIM)

    def _draw_song_panel(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        put_text(canvas, state.song_title, (x0 + 16, y0 + 55), 0.55, TEXT)
        if state.song_finished:
            put_text(canvas, "COMPLETADA!", (x0 + 16, y0 + 115), 1.1, GREEN, 3)
            put_text(canvas, "Pulsa REINICIAR (R)", (x0 + 16, y0 + 150), 0.5, TEXT_DIM)
        else:
            put_text(canvas, "NOTA ACTUAL", (x0 + 16, y0 + 80), 0.5, TEXT_DIM)
            put_text(canvas, state.current_label or "-", (x0 + 16, y0 + 130), 1.6, YELLOW, 3)
            put_text(canvas, "SIGUIENTE:", (x0 + 170, y0 + 80), 0.5, TEXT_DIM)
            put_text(canvas, state.next_label or "FIN", (x0 + 170, y0 + 125), 1.0, TEXT, 2)
        count = min(state.song_index + (0 if state.song_finished else 1), state.song_total)
        put_text(canvas, f"Nota {count} / {state.song_total}", (x0 + 16, y0 + 168), 0.5, TEXT)
        self._draw_bar(canvas, (x0 + 16, y0 + 180, SIDEBAR_W - 32, 16), state.song_progress, GREEN)
        put_text(canvas, f"{round(state.song_progress * 100)}%", (x0 + 16, y0 + 216), 0.5, TEXT)
        self._draw_feedback_box(canvas, state, x0, y0)

    def _draw_feedback_box(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        box = (x0 + 100, y0 + 202, SIDEBAR_W - 116, 36)
        active = (
            state.feedback is not None and state.feedback_age <= self._settings.feedback_seconds
        )
        if not active:
            return
        miss = state.feedback is SongResult.MISS
        color = RED if miss else GREEN
        cv2.rectangle(canvas, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), color, -1)
        put_text(
            canvas,
            "ERROR" if miss else "ACIERTO!",
            (box[0], box[1] + 25),
            0.7,
            (20, 20, 20),
            2,
            center_width=box[2],
        )

    def _draw_buttons(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        specs: list[tuple[Action, str, bool]] = [
            (Action.MODE_FREE, "MODO LIBRE [1]", state.mode is Mode.FREE),
            (Action.MODE_SONG, "MODO CANCION [2]", state.mode is Mode.SONG),
            (Action.RESTART_SONG, "REINICIAR [R]", False),
            (Action.CALIBRATE, "CALIBRAR [C]", state.calibration_progress is not None),
            (
                Action.TOGGLE_CAMERA,
                "CAMARA " + ("ON" if state.camera_on else "OFF") + " [ESP]",
                state.camera_on,
            ),
            (
                Action.TOGGLE_LANDMARKS,
                "PUNTOS " + ("SI" if state.landmarks_on else "NO") + " [L]",
                state.landmarks_on,
            ),
            (
                Action.TOGGLE_SOUND,
                "SONIDO " + ("SI" if state.sound_on else "NO") + " [S]",
                state.sound_on and state.audio_available,
            ),
            (Action.SWAP_HANDS, "CAMBIAR MANOS [H]", state.swap_hands),
            (Action.VOLUME_DOWN, "VOL - [-]", False),
            (Action.VOLUME_UP, "VOL + [+]", False),
            (Action.QUIT, "SALIR [Q]", False),
        ]
        self._buttons = []
        width, height, gap = (SIDEBAR_W - 36) // 2, 32, 6
        for i, (action, label, active) in enumerate(specs):
            col, row = i % 2, i // 2
            is_last_alone = action is Action.QUIT
            bx = x0 + 12 + col * (width + 12)
            by = y0 + row * (height + gap)
            bw = SIDEBAR_W - 24 if is_last_alone else width
            self._buttons.append(_Button(action, (bx, by, bw, height)))
            color = ACCENT if active else PANEL_LIGHT
            if action is Action.QUIT:
                color = (70, 70, 150)
            cv2.rectangle(canvas, (bx, by), (bx + bw, by + height), color, -1)
            text_color = (20, 20, 20) if active else TEXT
            put_text(canvas, label, (bx, by + 21), 0.42, text_color, 1, center_width=bw)

    def _draw_footer(self, canvas: np.ndarray, state: ViewState) -> None:
        y0 = HEADER_H + VIDEO_H
        cv2.rectangle(canvas, (0, y0), (CANVAS_W, CANVAS_H), BG, -1)
        panel_w = (CANVAS_W - 30) // 2
        for i, side in enumerate((HandSide.LEFT, HandSide.RIGHT)):
            self._draw_hand_panel(canvas, state, side, 10 + i * (panel_w + 10), y0 + 6, panel_w)
        self._draw_status_line(canvas, state, y0 + FOOTER_H - 12)

    def _draw_hand_panel(
        self, canvas: np.ndarray, state: ViewState, side: HandSide, x: int, y: int, width: int
    ) -> None:
        view = next((v for v in state.hands if v.hand.side is side), None)
        title = f"MANO {side.label}" + ("" if view else "  (no detectada)")
        put_text(canvas, title, (x, y + 14), 0.5, TEXT if view else TEXT_DIM)
        cell_w = (width - 4 * 4) // 5
        notes = state.finger_map.get(side, {})
        for finger in Finger:
            cx = x + finger * (cell_w + 4)
            cy = y + 22
            self._draw_finger_cell(canvas, state, view, side, finger, notes, (cx, cy, cell_w, 108))

    def _draw_finger_cell(
        self,
        canvas: np.ndarray,
        state: ViewState,
        view: HandView | None,
        side: HandSide,
        finger: Finger,
        notes: dict,
        rect: tuple[int, int, int, int],
    ) -> None:
        x, y, w, h = rect
        reading = view.readings.get(finger) if view else None
        flexed = reading is not None and reading.state is FingerState.FLEXED
        recent = (
            state.recent_presses.get((side, finger), 999.0) <= self._settings.note_highlight_seconds
        )
        cv2.rectangle(canvas, (x, y), (x + w, y + h), GREEN if flexed else PANEL, -1)
        if recent:
            cv2.rectangle(canvas, (x, y), (x + w, y + h), YELLOW, 3)
        fg = (20, 20, 20) if flexed else (TEXT if reading else TEXT_DIM)
        put_text(canvas, finger.label, (x, y + 18), 0.42, fg, 1, center_width=w)
        note = notes.get(finger)
        put_text(canvas, note.label if note else "-", (x, y + 56), 0.9, fg, 2, center_width=w)
        status = "FLEXIONADO" if flexed else ("EXTENDIDO" if reading else "---")
        put_text(canvas, status, (x, y + 78), 0.36, fg, 1, center_width=w)
        score = reading.score if reading else 0.0
        self._draw_bar(
            canvas, (x + 6, y + 88, w - 12, 8), score, (20, 20, 20) if flexed else ACCENT
        )

    def _draw_status_line(self, canvas: np.ndarray, state: ViewState, y: int) -> None:
        if state.message:
            put_text(canvas, state.message, (12, y), 0.5, RED if state.message_is_error else YELLOW)
        else:
            put_text(
                canvas,
                "Flexiona un dedo (extendido -> flexionado) para tocar su nota.",
                (12, y),
                0.45,
                TEXT_DIM,
            )
        sound = (
            f"Vol {round(state.volume * 100)}%"
            if state.sound_on and state.audio_available
            else ("Sin audio" if not state.audio_available else "Silencio")
        )
        put_text(canvas, sound, (CANVAS_W - 110, y), 0.5, TEXT_DIM)
