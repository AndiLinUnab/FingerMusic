"""Medición del tiempo de cada etapa del bucle principal y diagnóstico de FPS bajos."""

from __future__ import annotations

from dataclasses import dataclass

#: Por debajo de estos FPS se considera que la aplicación va lenta.
SLOW_FPS = 22.0
MIN_FRAMES_FOR_REPORT = 30

_ADVICE = {
    "camara": (
        "La camara tarda mucho en entregar cada imagen, asi que ella limita los FPS "
        "(no el programa). Causas habituales: poca luz (la camara baja sola a ~15 FPS), "
        "otra aplicacion usando la camara o un modo de video lento del driver. "
        "Prueba con mas luz, cierra Zoom/Teams/Camara de Windows y revisa CameraSettings.fourcc."
    ),
    "modelo": (
        "El modelo de manos es la etapa lenta: el procesador va justo. Conecta el portatil "
        "a la corriente, desactiva el modo ahorro de energia, cierra otras aplicaciones "
        "o baja la resolucion en CameraSettings."
    ),
    "interfaz": (
        "Dibujar/mostrar la ventana es la etapa lenta. Prueba a ocultar los puntos (tecla L) "
        "o a reducir la resolucion de la camara."
    ),
    "teclado": (
        "La espera de teclado/raton de la ventana (cv2.waitKey) consume mucho tiempo; "
        "es un comportamiento del sistema. Reporta este dato si persiste."
    ),
    "motor": "La logica de dedos/audio tarda demasiado; reporta este dato (no es lo esperable).",
}


@dataclass(frozen=True)
class PerformanceReport:
    """Resumen del rendimiento de un periodo."""

    fps: float
    averages_ms: dict[str, float]
    bottleneck: str
    slow: bool

    @property
    def advice(self) -> str:
        """Recomendación según la etapa más lenta (vacía si el rendimiento es bueno)."""
        return _ADVICE.get(self.bottleneck, "") if self.slow else ""

    def summary(self) -> str:
        """Línea de texto con los FPS y el tiempo medio por etapa."""
        stages = " | ".join(f"{name} {ms:.0f} ms" for name, ms in self.averages_ms.items())
        return f"Rendimiento: {self.fps:.1f} FPS  ({stages})"


class PerformanceMonitor:
    """Acumula tiempos por etapa y genera un informe cada cierto intervalo."""

    def __init__(self, interval: float = 5.0) -> None:
        self._interval = interval
        self._totals: dict[str, float] = {}
        self._frames = 0
        self._start: float | None = None

    def record(self, stage: str, seconds: float) -> None:
        """Suma ``seconds`` al tiempo acumulado de ``stage``."""
        self._totals[stage] = self._totals.get(stage, 0.0) + seconds

    def end_frame(self, now: float) -> None:
        """Marca el final de un frame del bucle."""
        if self._start is None:
            self._start = now
        self._frames += 1

    def report(self, now: float) -> PerformanceReport | None:
        """Devuelve un informe si pasó el intervalo y hay suficientes frames; si no, ``None``.

        Al generarlo se reinician los acumuladores.
        """
        if self._start is None or self._frames < MIN_FRAMES_FOR_REPORT:
            return None
        elapsed = now - self._start
        if elapsed < self._interval:
            return None
        averages = {name: total / self._frames * 1000 for name, total in self._totals.items()}
        fps = self._frames / elapsed
        bottleneck = max(averages, key=averages.__getitem__) if averages else ""
        report = PerformanceReport(fps, averages, bottleneck, slow=fps < SLOW_FPS)
        self._totals.clear()
        self._frames = 0
        self._start = None
        return report
