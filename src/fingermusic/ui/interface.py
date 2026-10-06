"""Interfaz gráfica de FingerMusic dibujada con OpenCV.

Diseño "juguetón": cada nota tiene su color, las tarjetas de los dedos rebotan
al tocar, salen notas y chispas desde la punta del dedo y hay confeti al
completar la canción.

OpenCV usa fuentes Hershey que no soportan acentos ni la letra Ñ; por eso los
textos de la interfaz están escritos sin tildes ("Menique", "CANCION").
"""

from __future__ import annotations

import colorsys
import math
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum

import cv2
import numpy as np

from fingermusic.audio.notes import NOTES, FingerMap, screen_finger_order
from fingermusic.config import UiSettings
from fingermusic.engine import HandView, Mode
from fingermusic.music.song_player import SongResult
from fingermusic.vision.finger_detector import FingerState
from fingermusic.vision.landmarks import (
    FINGER_JOINTS,
    HAND_CONNECTIONS,
    Finger,
    HandSide,
    Landmark,
)

# --- Geometría de la ventana ------------------------------------------------
VIDEO_W, VIDEO_H = 640, 480
SIDEBAR_W = 300
HEADER_H = 56
FOOTER_H = 170
CANVAS_W = VIDEO_W + SIDEBAR_W
CANVAS_H = HEADER_H + VIDEO_H + FOOTER_H

# --- Colores (BGR) ----------------------------------------------------------
BG_TOP = (66, 36, 52)
BG_BOTTOM = (36, 22, 30)
PANEL = (84, 50, 70)
PANEL_LIGHT = (116, 78, 100)
TEXT = (245, 245, 245)
TEXT_DIM = (190, 160, 175)
DARK = (28, 20, 26)
ACCENT = (70, 200, 255)
GREEN = (120, 225, 130)
RED = (90, 90, 245)
YELLOW = (80, 225, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX

#: Color de cada nota (BGR), como las teclas de un xilófono infantil.
NOTE_COLORS: dict[str, tuple[int, int, int]] = {
    "do4": (90, 90, 240),
    "re4": (70, 160, 250),
    "mi4": (70, 225, 250),
    "fa4": (120, 215, 110),
    "sol4": (215, 205, 70),
    "la4": (245, 140, 70),
    "si4": (210, 90, 160),
    "do5": (200, 120, 240),
    "re5": (160, 120, 250),
    "mi5": (150, 235, 190),
}
_COLOR_BY_LABEL = {note.label: NOTE_COLORS[note.key] for note in NOTES}
_RAINBOW = tuple(NOTE_COLORS[note.key] for note in NOTES)

_FINGER_TIPS = {
    Finger.THUMB: Landmark.THUMB_TIP,
    Finger.INDEX: Landmark.INDEX_TIP,
    Finger.MIDDLE: Landmark.MIDDLE_TIP,
    Finger.RING: Landmark.RING_TIP,
    Finger.PINKY: Landmark.PINKY_TIP,
}

_BOUNCE_SECONDS = 0.3
_BOUNCE_PIXELS = 9
_STREAK_MILESTONE = 10  # cada cuántos aciertos seguidos hay confeti


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
    streak: int = 0
    best_streak: int = 0
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


@dataclass
class _Particle:
    """Nota flotante, chispa o pieza de confeti."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: int
    text: str | None = None
    gravity: float = 0.0
    scale: float = 0.9


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


def blend(
    color: tuple[int, int, int], other: tuple[int, int, int], amount: float
) -> tuple[int, int, int]:
    """Mezcla ``color`` con ``other``: ``amount`` = 1 devuelve ``color``, 0 devuelve ``other``."""
    return tuple(int(c * amount + o * (1.0 - amount)) for c, o in zip(color, other, strict=True))  # type: ignore[return-value]


def rounded_rect(
    img: np.ndarray,
    rect: tuple[int, int, int, int],
    radius: int,
    color: tuple[int, int, int],
    thickness: int = -1,
) -> None:
    """Rectángulo con esquinas redondeadas (relleno si ``thickness`` < 0)."""
    x, y, w, h = rect
    r = max(1, min(radius, w // 2, h // 2))
    corners = (
        (x + r, y + r, 180),
        (x + w - r, y + r, 270),
        (x + w - r, y + h - r, 0),
        (x + r, y + h - r, 90),
    )
    if thickness < 0:
        cv2.rectangle(img, (x + r, y), (x + w - r, y + h), color, -1)
        cv2.rectangle(img, (x, y + r), (x + w, y + h - r), color, -1)
        for cx, cy, _ in corners:
            cv2.circle(img, (cx, cy), r, color, -1, cv2.LINE_AA)
        return
    cv2.line(img, (x + r, y), (x + w - r, y), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + r, y + h), (x + w - r, y + h), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x, y + r), (x, y + h - r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + w, y + r), (x + w, y + h - r), color, thickness, cv2.LINE_AA)
    for cx, cy, start in corners:
        cv2.ellipse(img, (cx, cy), (r, r), 0, start, start + 90, color, thickness, cv2.LINE_AA)


def draw_music_note(
    img: np.ndarray, center: tuple[int, int], size: int, color: tuple[int, int, int]
) -> None:
    """Dibuja una corchea simple (cabeza, plica y bandera)."""
    cx, cy = center
    cv2.ellipse(img, (cx, cy), (size, int(size * 0.7)), -20, 0, 360, color, -1, cv2.LINE_AA)
    stem_x = cx + size - 1
    cv2.line(img, (stem_x, cy - 2), (stem_x, cy - size * 3), color, max(2, size // 3), cv2.LINE_AA)
    cv2.line(
        img,
        (stem_x, cy - size * 3),
        (stem_x + size, cy - size * 2),
        color,
        max(2, size // 3),
        cv2.LINE_AA,
    )


def _gradient_background() -> np.ndarray:
    """Fondo con degradado vertical, calculado una sola vez."""
    t = np.linspace(0.0, 1.0, CANVAS_H)[:, None, None]
    top = np.array(BG_TOP, dtype=np.float32)
    bottom = np.array(BG_BOTTOM, dtype=np.float32)
    column = (top * (1 - t) + bottom * t).astype(np.uint8)
    return np.repeat(column, CANVAS_W, axis=1)


def _hue_color(fraction: float) -> tuple[int, int, int]:
    """Color arcoíris (BGR) para ``fraction`` en [0, 1]."""
    r, g, b = colorsys.hsv_to_rgb(fraction % 1.0, 0.65, 1.0)
    return int(b * 255), int(g * 255), int(r * 255)


class Interface:
    """Ventana principal: dibuja el estado y recoge las acciones del usuario."""

    def __init__(self, settings: UiSettings) -> None:
        self._settings = settings
        self._window = settings.window_title
        self._pending: list[Action] = []
        self._buttons: list[_Button] = []
        self._window_open = False
        self._background = _gradient_background()
        self._particles: list[_Particle] = []
        self._spawned: dict[tuple[HandSide, Finger], float] = {}
        self._was_finished = False
        self._last_streak = 0
        self._last_render = time.monotonic()
        self._rng = random.Random(7)

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
        now = time.monotonic()
        dt = min(0.1, max(0.0, now - self._last_render))
        self._last_render = now
        canvas = self._background.copy()
        self._draw_header(canvas, state)
        self._draw_video(canvas, frame, state, now, dt)
        self._draw_sidebar(canvas, state)
        self._draw_footer(canvas, state)
        return canvas

    def _draw_header(self, canvas: np.ndarray, state: ViewState) -> None:
        cv2.rectangle(canvas, (0, 0), (CANVAS_W, HEADER_H), PANEL, -1)
        x = 52
        for i, letter in enumerate("FINGERMUSIC"):
            put_text(canvas, letter, (x, 38), 1.0, _RAINBOW[i % len(_RAINBOW)], 3)
            (width, _), _ = cv2.getTextSize(letter, FONT, 1.0, 3)
            x += width + 3
        draw_music_note(canvas, (24, 38), 7, ACCENT)
        put_text(canvas, "Toca musica con tus dedos!", (380, 36), 0.5, TEXT_DIM)
        put_text(canvas, f"{state.fps:4.1f} FPS", (CANVAS_W - 100, 36), 0.5, TEXT_DIM)
        for i, color in enumerate(_RAINBOW):  # tira de color bajo la cabecera
            cv2.rectangle(
                canvas,
                (i * CANVAS_W // 10, HEADER_H - 4),
                ((i + 1) * CANVAS_W // 10, HEADER_H),
                color,
                -1,
            )

    def _draw_video(
        self, canvas: np.ndarray, frame: np.ndarray | None, state: ViewState, now: float, dt: float
    ) -> None:
        x0, y0 = 0, HEADER_H
        area = canvas[y0 : y0 + VIDEO_H, x0 : x0 + VIDEO_W]
        if frame is None:
            area[:] = (44, 30, 38)
            text = "Camara detenida (pulsa ESPACIO)" if not state.camera_on else "Sin imagen..."
            put_text(area, text, (0, VIDEO_H // 2), 0.7, TEXT_DIM, 1, center_width=VIDEO_W)
        else:
            height, width = frame.shape[:2]
            if (width, height) != (VIDEO_W, VIDEO_H):
                area[:] = cv2.resize(frame, (VIDEO_W, VIDEO_H))
            else:
                area[:] = frame
            scale = (VIDEO_W / width, VIDEO_H / height)
            if state.landmarks_on:
                for view in state.hands:
                    self._draw_hand(area, view, scale, state)
            self._spawn_press_particles(state, scale, now)
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
        self._update_confetti(state)
        self._draw_particles(area, dt)
        self._draw_feedback_border(area, state)
        self._draw_calibration(area, state)

    def _draw_hand(
        self,
        area: np.ndarray,
        view: HandView,
        scale: tuple[float, float],
        state: ViewState,
    ) -> None:
        points = [(int(x * scale[0]), int(y * scale[1])) for x, y, _ in view.hand.points]
        for start, end in HAND_CONNECTIONS:
            cv2.line(area, points[start], points[end], (250, 250, 250), 2, cv2.LINE_AA)
        for finger, reading in view.readings.items():
            color = NOTE_COLORS[view.notes[finger].key]
            for landmark in FINGER_JOINTS[finger][:-1]:
                cv2.circle(area, points[int(landmark)], 4, color, -1, cv2.LINE_AA)
            tip = points[int(_FINGER_TIPS[finger])]
            flexed = reading.state is FingerState.FLEXED
            age = state.recent_presses.get((view.hand.side, finger), 999.0)
            pulse = int(8 * max(0.0, 1.0 - age / _BOUNCE_SECONDS))
            radius = (12 if flexed else 9) + pulse
            cv2.circle(area, tip, radius + 3, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(area, tip, radius, color, -1, cv2.LINE_AA)
            label = view.notes[finger].label
            put_text(area, label, (tip[0] - 14, tip[1] - radius - 8), 0.55, color, 2)

    def _spawn_press_particles(
        self, state: ViewState, scale: tuple[float, float], now: float
    ) -> None:
        """Lanza una nota flotante y chispas desde la punta de cada dedo recién flexionado."""
        for (side, finger), age in state.recent_presses.items():
            press_time = now - age
            if age > 0.15 or press_time <= self._spawned.get((side, finger), -1.0) + 0.05:
                continue
            view = next((v for v in state.hands if v.hand.side is side), None)
            if view is None:
                continue
            self._spawned[(side, finger)] = press_time
            note = view.notes[finger]
            color = NOTE_COLORS[note.key]
            px, py, _ = view.hand.points[int(_FINGER_TIPS[finger])]
            x, y = px * scale[0], py * scale[1]
            self._particles.append(
                _Particle(x, y - 20, 0.0, -70.0, 1.0, 1.0, color, 2, text=note.label)
            )
            for _ in range(10):
                angle = self._rng.uniform(0, 2 * math.pi)
                speed = self._rng.uniform(40, 130)
                self._particles.append(
                    _Particle(
                        x,
                        y,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        0.5,
                        0.5,
                        color,
                        self._rng.randint(2, 4),
                    )
                )

    def _spawn_confetti(self, count: int) -> None:
        """Lanza ``count`` piezas de confeti desde la parte superior del video."""
        for _ in range(count):
            self._particles.append(
                _Particle(
                    self._rng.uniform(0, VIDEO_W),
                    self._rng.uniform(-40, 10),
                    self._rng.uniform(-30, 30),
                    self._rng.uniform(40, 140),
                    2.5,
                    2.5,
                    _hue_color(self._rng.random()),
                    self._rng.randint(3, 6),
                    gravity=60.0,
                )
            )

    def _update_confetti(self, state: ViewState) -> None:
        """Lanza confeti al completar la canción y cada ``_STREAK_MILESTONE`` aciertos seguidos."""
        in_song = state.mode is Mode.SONG
        if state.song_finished and not self._was_finished and in_song:
            self._spawn_confetti(90)
        self._was_finished = state.song_finished

        reached_milestone = (
            in_song
            and state.streak > self._last_streak
            and state.streak > 0
            and state.streak % _STREAK_MILESTONE == 0
        )
        if reached_milestone:
            self._spawn_confetti(60)
            self._particles.append(
                _Particle(
                    VIDEO_W / 2,
                    VIDEO_H / 2,
                    0.0,
                    -40.0,
                    1.6,
                    1.6,
                    _hue_color((state.streak // _STREAK_MILESTONE) * 0.17),
                    2,
                    text=f"RACHA x{state.streak}!",
                    scale=1.5,
                )
            )
        self._last_streak = state.streak

    def _draw_particles(self, area: np.ndarray, dt: float) -> None:
        alive: list[_Particle] = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            fade = p.life / p.max_life
            color = blend(p.color, (40, 30, 36), 0.35 + 0.65 * fade)
            if p.text is not None:
                (text_w, _), _ = cv2.getTextSize(p.text, FONT, p.scale, 2)
                put_text(area, p.text, (int(p.x) - text_w // 2, int(p.y)), p.scale, color, 2)
            else:
                cv2.circle(area, (int(p.x), int(p.y)), p.size, color, -1, cv2.LINE_AA)
            alive.append(p)
        self._particles = alive[-400:]

    def _draw_feedback_border(self, area: np.ndarray, state: ViewState) -> None:
        if state.mode is not Mode.SONG or state.feedback is None:
            return
        if state.feedback_age > self._settings.feedback_seconds:
            return
        color = RED if state.feedback is SongResult.MISS else GREEN
        cv2.rectangle(area, (0, 0), (VIDEO_W - 1, VIDEO_H - 1), color, 8)

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
        self._draw_rainbow_bar(area, (120, 42, VIDEO_W - 240, 14), state.calibration_progress)

    def _draw_rainbow_bar(
        self, img: np.ndarray, rect: tuple[int, int, int, int], fraction: float
    ) -> None:
        """Barra de progreso redondeada con degradado de arcoíris."""
        x, y, w, h = rect
        rounded_rect(img, rect, h // 2, PANEL_LIGHT)
        filled = int(w * max(0.0, min(1.0, fraction)))
        for dx in range(0, filled, 2):
            color = _hue_color(0.95 * dx / max(1, w))
            cv2.line(img, (x + dx, y + 2), (x + dx, y + h - 2), color, 2)
        if filled > 0:
            cv2.circle(img, (x + filled, y + h // 2), h // 2, TEXT, -1, cv2.LINE_AA)

    def _draw_bar(
        self,
        img: np.ndarray,
        rect: tuple[int, int, int, int],
        fraction: float,
        color: tuple[int, int, int],
    ) -> None:
        x, y, w, h = rect
        rounded_rect(img, rect, h // 2, blend(DARK, color, 0.65))
        filled = int(w * max(0.0, min(1.0, fraction)))
        if filled >= h:
            rounded_rect(img, (x, y, filled, h), h // 2, color)

    def _draw_sidebar(self, canvas: np.ndarray, state: ViewState) -> None:
        x0, y0 = VIDEO_W, HEADER_H
        cv2.rectangle(canvas, (x0, y0), (CANVAS_W, y0 + VIDEO_H), PANEL, -1)
        title_color = ACCENT if state.mode is Mode.FREE else _RAINBOW[5]
        put_text(canvas, state.mode.value, (x0 + 16, y0 + 30), 0.75, title_color, 2)
        if state.mode is Mode.SONG:
            self._draw_song_panel(canvas, state, x0, y0)
        else:
            self._draw_free_panel(canvas, state, x0, y0)
        self._draw_buttons(canvas, state, x0, y0 + 250)

    def _draw_note_bubble(
        self,
        canvas: np.ndarray,
        center: tuple[int, int],
        radius: int,
        label: str | None,
        scale: float,
        active: bool = True,
    ) -> None:
        color = _COLOR_BY_LABEL.get(label or "", PANEL_LIGHT)
        if not active:
            color = blend(color, PANEL, 0.4)
        cv2.circle(canvas, center, radius + 4, TEXT if active else PANEL_LIGHT, -1, cv2.LINE_AA)
        cv2.circle(canvas, center, radius, color, -1, cv2.LINE_AA)
        text = label or "-"
        (text_w, text_h), _ = cv2.getTextSize(text, FONT, scale, 3)
        cv2.putText(
            canvas,
            text,
            (center[0] - text_w // 2, center[1] + text_h // 2),
            FONT,
            scale,
            DARK,
            3,
            cv2.LINE_AA,
        )

    def _draw_free_panel(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        playing = state.last_note_age <= self._settings.note_highlight_seconds
        put_text(canvas, "NOTA SONANDO", (x0 + 16, y0 + 62), 0.5, TEXT_DIM)
        bounce = int(8 * max(0.0, 1.0 - state.last_note_age / _BOUNCE_SECONDS)) if playing else 0
        label = state.last_note_label if playing else None
        self._draw_note_bubble(canvas, (x0 + 80, y0 + 125 - bounce), 42, label, 1.1, playing)
        put_text(canvas, "Flexiona un dedo para", (x0 + 150, y0 + 115), 0.45, TEXT_DIM)
        put_text(canvas, "tocar su nota!", (x0 + 150, y0 + 135), 0.45, TEXT_DIM)
        put_text(canvas, "Mano izq: DO -> SOL", (x0 + 16, y0 + 215), 0.45, TEXT_DIM)
        put_text(canvas, "(de menique a pulgar)", (x0 + 16, y0 + 232), 0.4, TEXT_DIM)
        put_text(canvas, "Mano der: LA -> MI'", (x0 + 160, y0 + 215), 0.45, TEXT_DIM)
        put_text(canvas, "(de pulgar a menique)", (x0 + 160, y0 + 232), 0.4, TEXT_DIM)

    def _draw_song_panel(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        put_text(canvas, state.song_title, (x0 + 16, y0 + 55), 0.55, TEXT)
        self._draw_best_streak(canvas, state, x0 + 175, y0 + 55)
        if state.song_finished:
            put_text(canvas, "COMPLETADA!", (x0 + 16, y0 + 118), 1.1, GREEN, 3)
            put_text(canvas, "Pulsa REINICIAR (R)", (x0 + 16, y0 + 150), 0.5, TEXT_DIM)
        else:
            put_text(canvas, "TOCA", (x0 + 16, y0 + 82), 0.5, TEXT_DIM)
            self._draw_note_bubble(canvas, (x0 + 70, y0 + 120), 36, state.current_label, 1.0)
            put_text(canvas, "LUEGO", (x0 + 168, y0 + 82), 0.5, TEXT_DIM)
            self._draw_note_bubble(
                canvas, (x0 + 212, y0 + 116), 24, state.next_label or "FIN", 0.6, active=False
            )
        count = min(state.song_index + (0 if state.song_finished else 1), state.song_total)
        put_text(canvas, f"Nota {count} / {state.song_total}", (x0 + 16, y0 + 180), 0.5, TEXT)
        self._draw_streak(canvas, state, x0 + 170, y0 + 180)
        self._draw_rainbow_bar(canvas, (x0 + 16, y0 + 190, SIDEBAR_W - 32, 14), state.song_progress)
        put_text(canvas, f"{round(state.song_progress * 100)}%", (x0 + 16, y0 + 232), 0.5, TEXT)
        self._draw_feedback_box(canvas, state, x0, y0)

    def _draw_streak(self, canvas: np.ndarray, state: ViewState, x: int, y: int) -> None:
        """Contador de aciertos seguidos; crece un poco con cada acierto."""
        if state.streak >= 10:
            color = _RAINBOW[7]
        elif state.streak >= 5:
            color = _RAINBOW[1]
        elif state.streak >= 1:
            color = YELLOW
        else:
            color = TEXT_DIM
        hit = state.feedback in (SongResult.HIT, SongResult.FINISHED)
        pop = max(0.0, 1.0 - state.feedback_age / _BOUNCE_SECONDS) if hit else 0.0
        put_text(canvas, f"RACHA x{state.streak}", (x, y), 0.5 + 0.15 * pop, color, 2)

    def _draw_best_streak(self, canvas: np.ndarray, state: ViewState, x: int, y: int) -> None:
        """Mejor racha de la sesión; se resalta mientras la racha actual la iguala."""
        is_record = state.best_streak > 0 and state.streak == state.best_streak
        color = YELLOW if is_record else TEXT_DIM
        put_text(canvas, f"MEJOR x{state.best_streak}", (x, y), 0.5, color, 2 if is_record else 1)

    def _draw_feedback_box(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        box = (x0 + 100, y0 + 210, SIDEBAR_W - 116, 32)
        active = (
            state.feedback is not None and state.feedback_age <= self._settings.feedback_seconds
        )
        if not active:
            return
        miss = state.feedback is SongResult.MISS
        shake = int(5 * math.sin(state.feedback_age * 50)) if miss else 0
        rect = (box[0] + shake, box[1], box[2], box[3])
        rounded_rect(canvas, rect, 14, RED if miss else GREEN)
        put_text(
            canvas,
            "UPS! OTRA" if miss else "GENIAL!",
            (rect[0], rect[1] + 23),
            0.65,
            DARK,
            2,
            center_width=rect[2],
        )

    def _draw_buttons(self, canvas: np.ndarray, state: ViewState, x0: int, y0: int) -> None:
        specs: list[tuple[Action, str, bool, tuple[int, int, int]]] = [
            (Action.MODE_FREE, "MODO LIBRE [1]", state.mode is Mode.FREE, _RAINBOW[3]),
            (Action.MODE_SONG, "MODO CANCION [2]", state.mode is Mode.SONG, _RAINBOW[5]),
            (Action.RESTART_SONG, "REINICIAR [R]", False, _RAINBOW[1]),
            (Action.CALIBRATE, "CALIBRAR [C]", state.calibration_progress is not None, _RAINBOW[2]),
            (
                Action.TOGGLE_CAMERA,
                "CAMARA " + ("ON" if state.camera_on else "OFF") + " [ESP]",
                state.camera_on,
                _RAINBOW[4],
            ),
            (
                Action.TOGGLE_LANDMARKS,
                "PUNTOS " + ("SI" if state.landmarks_on else "NO") + " [L]",
                state.landmarks_on,
                _RAINBOW[7],
            ),
            (
                Action.TOGGLE_SOUND,
                "SONIDO " + ("SI" if state.sound_on else "NO") + " [S]",
                state.sound_on and state.audio_available,
                _RAINBOW[0],
            ),
            (Action.SWAP_HANDS, "CAMBIAR MANOS [H]", state.swap_hands, _RAINBOW[9]),
            (Action.VOLUME_DOWN, "VOL - [-]", False, _RAINBOW[6]),
            (Action.VOLUME_UP, "VOL + [+]", False, _RAINBOW[8]),
            (Action.QUIT, "SALIR [Q]", False, (90, 90, 190)),
        ]
        self._buttons = []
        width, height, gap = (SIDEBAR_W - 36) // 2, 32, 6
        for i, (action, label, active, color) in enumerate(specs):
            col, row = i % 2, i // 2
            bx = x0 + 12 + col * (width + 12)
            by = y0 + row * (height + gap)
            bw = SIDEBAR_W - 24 if action is Action.QUIT else width
            self._buttons.append(_Button(action, (bx, by, bw, height)))
            rounded_rect(
                canvas,
                (bx, by, bw, height),
                12,
                color if active else blend(color, PANEL_LIGHT, 0.3),
            )
            if active:
                rounded_rect(canvas, (bx, by, bw, height), 12, TEXT, 2)
            put_text(
                canvas, label, (bx, by + 21), 0.42, DARK if active else TEXT, 1, center_width=bw
            )

    def _draw_footer(self, canvas: np.ndarray, state: ViewState) -> None:
        y0 = HEADER_H + VIDEO_H
        panel_w = (CANVAS_W - 30) // 2
        for i, side in enumerate((HandSide.LEFT, HandSide.RIGHT)):
            self._draw_hand_panel(canvas, state, side, 10 + i * (panel_w + 10), y0 + 6, panel_w)
        self._draw_status_line(canvas, state, y0 + FOOTER_H - 10)

    def _draw_hand_panel(
        self, canvas: np.ndarray, state: ViewState, side: HandSide, x: int, y: int, width: int
    ) -> None:
        view = next((v for v in state.hands if v.hand.side is side), None)
        title = f"MANO {side.label}" + ("" if view else "  (no detectada)")
        put_text(canvas, title, (x, y + 14), 0.5, TEXT if view else TEXT_DIM)
        cell_w = (width - 4 * 4) // 5
        notes = state.finger_map.get(side, {})
        # Las tarjetas siguen el orden real de la mano en pantalla (notas ascendentes).
        for position, finger in enumerate(screen_finger_order(side)):
            cx = x + position * (cell_w + 4)
            self._draw_finger_cell(
                canvas, state, view, side, finger, notes, (cx, y + 30, cell_w, 100)
            )

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
        note = notes.get(finger)
        base = NOTE_COLORS[note.key] if note else PANEL_LIGHT
        age = state.recent_presses.get((side, finger), 999.0)
        bounce = int(_BOUNCE_PIXELS * max(0.0, 1.0 - age / _BOUNCE_SECONDS))
        lift = (4 if flexed else 0) + bounce
        y -= lift
        if reading is None:
            color = blend(base, PANEL, 0.30)
        elif flexed:
            color = base
        else:
            color = blend(base, PANEL, 0.62)
        rounded_rect(canvas, (x + 2, y + 5 + lift, w, h), 14, (20, 14, 18))  # sombra
        rounded_rect(canvas, (x, y, w, h), 14, color)
        if flexed:
            rounded_rect(canvas, (x, y, w, h), 14, TEXT, 3)
        fg = DARK if (flexed or reading is not None) else TEXT_DIM
        put_text(canvas, finger.label, (x, y + 18), 0.42, fg, 1, center_width=w)
        put_text(canvas, note.label if note else "-", (x, y + 55), 0.95, fg, 2, center_width=w)
        status = "FLEXIONADO" if flexed else ("EXTENDIDO" if reading else "---")
        put_text(canvas, status, (x, y + 75), 0.36, fg, 1, center_width=w)
        score = reading.score if reading else 0.0
        self._draw_bar(canvas, (x + 8, y + 83, w - 16, 8), score, DARK)

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
        if not state.audio_available:
            sound = "Sin audio"
        elif not state.sound_on:
            sound = "Silencio"
        else:
            sound = f"Vol {round(state.volume * 100)}%"
        put_text(canvas, sound, (CANVAS_W - 110, y), 0.5, TEXT_DIM)
