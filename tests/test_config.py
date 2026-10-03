"""Pruebas de la configuración centralizada."""

from __future__ import annotations

import dataclasses

import pytest

from fingermusic.config import DetectionSettings, Settings, get_settings
from fingermusic.config.settings import PROJECT_ROOT, SOUNDS_DIR


def test_default_settings_are_valid() -> None:
    settings = get_settings()
    assert settings.camera.index == 0
    assert settings.detection.flex_off_threshold < settings.detection.flex_on_threshold


def test_paths_are_relative_to_the_repository() -> None:
    assert (PROJECT_ROOT / "src" / "fingermusic").is_dir()
    assert SOUNDS_DIR == PROJECT_ROOT / "assets" / "sounds"


@pytest.mark.parametrize(
    "overrides",
    [
        {"flex_on_threshold": 0.3, "flex_off_threshold": 0.5},
        {"smoothing_alpha": 0.0},
        {"state_confirmation_frames": 0},
        {"note_cooldown": -1.0},
        {"angle_weight": 1.5},
        {"pip_angle_flexed": 170.0},
        {"thumb_ratio_flexed": 2.0},
    ],
)
def test_invalid_detection_settings_are_rejected(overrides: dict) -> None:
    settings = Settings(detection=dataclasses.replace(DetectionSettings(), **overrides))
    with pytest.raises(ValueError):
        settings.validate()


def test_settings_are_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        get_settings().detection.note_cooldown = 5  # type: ignore[misc]
