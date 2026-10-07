"""Pruebas de los efectos visuales de la interfaz (sin abrir ninguna ventana)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from fingermusic.config import UiSettings
from fingermusic.engine import Mode
from fingermusic.ui.interface import CANVAS_H, CANVAS_W, Action, Interface, ViewState


@pytest.fixture
def ui() -> Interface:
    return Interface(UiSettings())


def song_state(streak: int, best: int | None = None, finished: bool = False) -> ViewState:
    return ViewState(
        mode=Mode.SONG,
        camera_on=True,
        song_title="JINGLE BELLS",
        song_total=51,
        song_index=streak,
        streak=streak,
        best_streak=streak if best is None else best,
        song_finished=finished,
        current_label="MI",
        next_label="MI",
    )


def milestone_texts(ui: Interface) -> list[str]:
    return [p.text for p in ui._particles if p.text]


def test_render_returns_a_full_canvas(ui: Interface) -> None:
    canvas = ui.render(None, song_state(3))
    assert canvas.shape == (CANVAS_H, CANVAS_W, 3) and canvas.dtype == np.uint8


def test_confetti_when_reaching_ten_in_a_row(ui: Interface) -> None:
    ui.render(None, song_state(9))
    assert ui._particles == []
    ui.render(None, song_state(10))
    assert "RACHA x10!" in milestone_texts(ui)
    assert len(ui._particles) >= 60


def test_confetti_is_not_repeated_while_the_streak_is_unchanged(ui: Interface) -> None:
    ui.render(None, song_state(9))
    ui.render(None, song_state(10))
    count = len(milestone_texts(ui))
    ui.render(None, song_state(10))
    assert len(milestone_texts(ui)) == count


def test_no_confetti_for_non_milestones_or_free_mode(ui: Interface) -> None:
    ui.render(None, song_state(4))
    ui.render(None, song_state(5))
    assert ui._particles == []
    free = song_state(10)
    free.mode = Mode.FREE
    ui.render(None, song_state(9))
    ui.render(None, free)
    assert ui._particles == []


def test_confetti_again_at_twenty_after_a_reset(ui: Interface) -> None:
    ui.render(None, song_state(9))
    ui.render(None, song_state(10))
    ui.render(None, song_state(0, best=10))  # fallo: la racha se reinicia
    ui._particles.clear()
    ui.render(None, song_state(9, best=10))
    ui.render(None, song_state(10, best=10))
    assert "RACHA x10!" in milestone_texts(ui)


def test_confetti_when_the_song_is_completed(ui: Interface) -> None:
    ui.render(None, song_state(4))
    ui.render(None, song_state(5, finished=True))
    assert len(ui._particles) >= 90


def test_song_mode_shows_clickable_song_arrows(ui: Interface) -> None:
    ui.render(None, song_state(0))
    actions = {button.action for button in ui._buttons}
    assert {Action.NEXT_SONG, Action.PREVIOUS_SONG} <= actions


def test_clicking_the_arrows_queues_the_actions(ui: Interface) -> None:
    ui.render(None, song_state(0))
    for target in (Action.NEXT_SONG, Action.PREVIOUS_SONG):
        x, y, w, h = next(b.rect for b in ui._buttons if b.action is target)
        ui._on_mouse(cv2.EVENT_LBUTTONDOWN, x + w // 2, y + h // 2, 0, None)
    assert ui._pending == [Action.NEXT_SONG, Action.PREVIOUS_SONG]


def test_free_mode_has_no_song_arrows_and_buttons_do_not_accumulate(ui: Interface) -> None:
    free = song_state(0)
    free.mode = Mode.FREE
    ui.render(None, free)
    assert Action.NEXT_SONG not in {b.action for b in ui._buttons}
    count = len(ui._buttons)
    ui.render(None, free)
    assert len(ui._buttons) == count


def test_keyboard_shortcuts_for_songs() -> None:
    from fingermusic.ui.interface import _KEY_BINDINGS

    assert _KEY_BINDINGS[ord("n")] is Action.NEXT_SONG
    assert _KEY_BINDINGS[ord("p")] is Action.PREVIOUS_SONG
