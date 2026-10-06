"""Pruebas del monitor de rendimiento y su diagnóstico."""

from __future__ import annotations

from fingermusic.utils.perf import MIN_FRAMES_FOR_REPORT, PerformanceMonitor


def run(monitor: PerformanceMonitor, frames: int, frame_time: float, **stages: float) -> float:
    """Simula ``frames`` frames de ``frame_time`` s con los tiempos por etapa indicados."""
    now = 100.0
    for _ in range(frames):
        for stage, seconds in stages.items():
            monitor.record(stage, seconds)
        now += frame_time
        monitor.end_frame(now)
    return now


def test_no_report_before_interval_or_enough_frames() -> None:
    monitor = PerformanceMonitor(interval=5.0)
    now = run(monitor, MIN_FRAMES_FOR_REPORT - 1, 0.2, camara=0.1)
    assert monitor.report(now) is None
    short = PerformanceMonitor(interval=5.0)
    now = run(short, 60, 0.01, camara=0.005)  # 0.6 s < 5 s
    assert short.report(now) is None


def test_slow_camera_is_identified() -> None:
    monitor = PerformanceMonitor(interval=5.0)
    now = run(monitor, 80, 0.066, camara=0.060, modelo=0.008, interfaz=0.004)  # ~15 FPS
    report = monitor.report(now)
    assert report is not None and report.slow
    assert report.bottleneck == "camara"
    assert 14 < report.fps < 16
    assert "camara" in report.advice.lower() and "luz" in report.advice
    assert "15." in report.summary() or "FPS" in report.summary()


def test_slow_model_is_identified() -> None:
    monitor = PerformanceMonitor(interval=5.0)
    now = run(monitor, 100, 0.07, camara=0.005, modelo=0.060, interfaz=0.004)
    report = monitor.report(now)
    assert report is not None and report.slow and report.bottleneck == "modelo"
    assert "procesador" in report.advice


def test_good_performance_has_no_advice() -> None:
    monitor = PerformanceMonitor(interval=5.0)
    now = run(monitor, 200, 0.033, camara=0.025, modelo=0.006, interfaz=0.002)
    report = monitor.report(now)
    assert report is not None and not report.slow and report.advice == ""


def test_report_resets_the_counters() -> None:
    monitor = PerformanceMonitor(interval=5.0)
    now = run(monitor, 200, 0.033, camara=0.025)
    assert monitor.report(now) is not None
    assert monitor.report(now + 10) is None
