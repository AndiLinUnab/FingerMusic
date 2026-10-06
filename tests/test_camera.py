"""Pruebas de CameraManager con una cámara simulada (sin hardware)."""

from __future__ import annotations

import dataclasses

import cv2
import numpy as np
import pytest

from fingermusic.camera.camera_manager import CameraError, CameraManager
from fingermusic.config import CameraSettings


class FakeCapture:
    """Cámara falsa; ``mjpg_works`` controla si entrega imagen con el formato MJPG."""

    instances: list[FakeCapture] = []
    opens = True
    mjpg_works = True

    def __init__(self, *_args: object) -> None:
        self.props: dict[int, float] = {}
        self.released = False
        FakeCapture.instances.append(self)

    def isOpened(self) -> bool:  # noqa: N802 - API de OpenCV
        return FakeCapture.opens

    def set(self, prop: int, value: float) -> bool:
        self.props[prop] = value
        return True

    def get(self, prop: int) -> float:
        return self.props.get(prop, 0.0)

    def read(self) -> tuple[bool, np.ndarray | None]:
        if cv2.CAP_PROP_FOURCC in self.props and not FakeCapture.mjpg_works:
            return False, None
        return True, np.arange(12, dtype=np.uint8).reshape(2, 2, 3)

    def release(self) -> None:
        self.released = True


@pytest.fixture(autouse=True)
def fake_camera(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeCapture.instances = []
    FakeCapture.opens = True
    FakeCapture.mjpg_works = True
    monkeypatch.setattr(cv2, "VideoCapture", FakeCapture)


def test_requests_mjpg_by_default() -> None:
    camera = CameraManager(CameraSettings())
    camera.open()
    assert camera.is_open
    assert FakeCapture.instances[-1].props[cv2.CAP_PROP_FOURCC] == cv2.VideoWriter_fourcc(*"MJPG")


def test_falls_back_when_the_camera_rejects_the_format() -> None:
    FakeCapture.mjpg_works = False
    camera = CameraManager(CameraSettings())
    camera.open()
    assert len(FakeCapture.instances) == 2
    assert FakeCapture.instances[0].released
    assert cv2.CAP_PROP_FOURCC not in FakeCapture.instances[1].props
    assert camera.read() is not None


def test_empty_fourcc_does_not_set_the_format() -> None:
    camera = CameraManager(dataclasses.replace(CameraSettings(), fourcc=""))
    camera.open()
    assert cv2.CAP_PROP_FOURCC not in FakeCapture.instances[-1].props


def test_missing_camera_raises_a_clear_error() -> None:
    FakeCapture.opens = False
    with pytest.raises(CameraError, match="No se pudo abrir la camara"):
        CameraManager(CameraSettings()).open()


def test_frames_are_mirrored_and_release_closes() -> None:
    camera = CameraManager(CameraSettings())
    camera.open()
    frame = camera.read()
    assert frame is not None
    assert frame[0, 0].tolist() == [3, 4, 5]  # espejado horizontal del 2x2 original
    camera.release()
    assert not camera.is_open


def test_read_fails_after_too_many_missing_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = dataclasses.replace(CameraSettings(), fourcc="", max_read_failures=3)
    camera = CameraManager(settings)
    camera.open()
    monkeypatch.setattr(FakeCapture, "read", lambda self: (False, None))
    assert camera.read() is None and camera.read() is None
    with pytest.raises(CameraError):
        camera.read()
