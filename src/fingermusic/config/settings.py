"""Parámetros configurables de FingerMusic.

Todos los "números mágicos" del proyecto viven aquí. Para ajustar la
sensibilidad, el cooldown, la cámara o el volumen basta con editar los valores
por defecto de estas clases (ver docs/decisiones_tecnicas.md y README).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fingermusic.audio.instruments import get_instrument

# Raíz del repositorio: .../FingerMusic (src/fingermusic/config/settings.py -> 4 niveles).
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
SOUNDS_DIR: Path = PROJECT_ROOT / "assets" / "sounds"
LOGS_DIR: Path = PROJECT_ROOT / "logs"


@dataclass(frozen=True)
class CameraSettings:
    """Parámetros de captura de video."""

    #: Índice de la cámara (0 = cámara integrada del portátil).
    index: int = 0
    width: int = 640
    height: int = 480
    #: FPS solicitados a la cámara (el driver puede ignorarlo).
    fps: int = 30
    #: Espejar la imagen (efecto "selfie"). Necesario para que la
    #: lateralidad (mano izquierda/derecha) coincida con la del usuario.
    mirror: bool = True
    #: Formato de video pedido a la cámara (4 letras). 'MJPG' evita el modo lento (~15 FPS)
    #: de muchas cámaras en Windows. Déjalo vacío ('') para usar el formato por defecto.
    fourcc: str = "MJPG"
    #: Frames fallidos consecutivos tolerados antes de dar la cámara por perdida.
    max_read_failures: int = 30


@dataclass(frozen=True)
class DetectionSettings:
    """Parámetros del modelo de manos y de la detección de flexión."""

    # --- Modelo MediaPipe Hands ---
    max_num_hands: int = 2
    #: 0 = modelo ligero (más rápido), 1 = modelo completo (más preciso).
    model_complexity: int = 0
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.5

    # --- Geometría de flexión de los 4 dedos largos ---
    #: Ángulo (grados) en la articulación PIP con el dedo extendido.
    pip_angle_extended: float = 165.0
    #: Ángulo (grados) en la articulación PIP con el dedo muy flexionado.
    pip_angle_flexed: float = 95.0
    #: Cociente distancia(punta, muñeca) / distancia(MCP, muñeca) con el dedo extendido.
    reach_ratio_extended: float = 1.90
    #: Mismo cociente con el dedo flexionado.
    reach_ratio_flexed: float = 1.10

    # --- Geometría del pulgar ---
    #: Cociente distancia(punta pulgar, MCP índice) / tamaño de palma, pulgar abierto.
    thumb_ratio_extended: float = 1.15
    #: Mismo cociente con el pulgar doblado hacia la palma.
    thumb_ratio_flexed: float = 0.60
    #: Ángulo (grados) en la articulación IP del pulgar extendido / flexionado.
    thumb_angle_extended: float = 170.0
    thumb_angle_flexed: float = 125.0

    #: Peso del ángulo frente a la distancia al combinar ambas medidas (0..1).
    angle_weight: float = 0.5

    # --- Filtrado y decisión de estado ---
    #: Factor de suavizado exponencial (1 = sin suavizado, menor = más suave).
    smoothing_alpha: float = 0.6
    #: Puntuación de flexión (0..1) a partir de la cual el dedo pasa a FLEXIONADO.
    flex_on_threshold: float = 0.60
    #: Puntuación por debajo de la cual el dedo vuelve a EXTENDIDO (histéresis).
    flex_off_threshold: float = 0.35
    #: Frames consecutivos que debe mantenerse un cambio para confirmarlo.
    state_confirmation_frames: int = 2
    #: Tiempo mínimo (s) entre dos notas del mismo dedo (anti-rebote).
    note_cooldown: float = 0.15
    #: Frames sin mano tras los cuales se reinician los estados de los dedos.
    hand_lost_reset_frames: int = 5

    # --- Calibración ---
    calibration_duration: float = 2.0
    calibration_min_samples: int = 10
    #: Máxima línea base de reposo aceptada (evita calibrar con el puño cerrado).
    calibration_max_baseline: float = 0.40


@dataclass(frozen=True)
class AudioSettings:
    """Parámetros de audio."""

    sample_rate: int = 44100
    #: Buffer pequeño = baja latencia (puede ajustarse a 512 si hay chasquidos).
    buffer_size: int = 256
    channels: int = 16
    volume: float = 0.8
    volume_step: float = 0.1
    #: Duración (s) de cada tono generado.
    note_duration: float = 0.7
    #: Duración (s) del sonido de error del modo canción.
    error_duration: float = 0.3
    #: Si es ``True``, al fallar suena también la nota tocada además del sonido de error.
    error_plays_note: bool = False
    sounds_dir: Path = SOUNDS_DIR
    #: Instrumento inicial: "piano", "xilofono" o "flauta" (se cambia con la tecla I).
    instrument: str = "piano"


@dataclass(frozen=True)
class UiSettings:
    """Parámetros de la interfaz."""

    window_title: str = "FingerMusic"
    show_landmarks: bool = True
    #: Segundos que permanece resaltada la nota que acaba de sonar.
    note_highlight_seconds: float = 0.5
    #: Segundos que se muestra el indicador de acierto / error.
    feedback_seconds: float = 0.7
    #: Segundos que se muestran los mensajes de estado.
    message_seconds: float = 4.0


@dataclass(frozen=True)
class Settings:
    """Agrupa toda la configuración de la aplicación."""

    camera: CameraSettings = field(default_factory=CameraSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    ui: UiSettings = field(default_factory=UiSettings)

    def validate(self) -> None:
        """Comprueba la coherencia de los parámetros.

        Raises:
            ValueError: si algún valor está fuera de rango o es incoherente.
        """
        det = self.detection
        if not det.flex_off_threshold < det.flex_on_threshold:
            raise ValueError("flex_off_threshold debe ser menor que flex_on_threshold")
        if not 0.0 < det.smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha debe estar en (0, 1]")
        if det.state_confirmation_frames < 1:
            raise ValueError("state_confirmation_frames debe ser >= 1")
        if det.note_cooldown < 0:
            raise ValueError("note_cooldown no puede ser negativo")
        if not 0.0 <= det.angle_weight <= 1.0:
            raise ValueError("angle_weight debe estar en [0, 1]")
        if det.pip_angle_flexed >= det.pip_angle_extended:
            raise ValueError("pip_angle_flexed debe ser menor que pip_angle_extended")
        if det.reach_ratio_flexed >= det.reach_ratio_extended:
            raise ValueError("reach_ratio_flexed debe ser menor que reach_ratio_extended")
        if det.thumb_ratio_flexed >= det.thumb_ratio_extended:
            raise ValueError("thumb_ratio_flexed debe ser menor que thumb_ratio_extended")
        if det.thumb_angle_flexed >= det.thumb_angle_extended:
            raise ValueError("thumb_angle_flexed debe ser menor que thumb_angle_extended")
        try:
            get_instrument(self.audio.instrument)
        except KeyError as exc:
            raise ValueError(f"Instrumento desconocido: {self.audio.instrument!r}") from exc
        if self.audio.error_duration <= 0:
            raise ValueError("error_duration debe ser positivo")
        if not 0.0 <= self.audio.volume <= 1.0:
            raise ValueError("volume debe estar en [0, 1]")
        if self.camera.width <= 0 or self.camera.height <= 0:
            raise ValueError("Resolución de cámara inválida")
        if self.camera.fourcc and len(self.camera.fourcc) != 4:
            raise ValueError("fourcc debe tener exactamente 4 caracteres (o estar vacío)")


def get_settings() -> Settings:
    """Devuelve la configuración por defecto, ya validada."""
    settings = Settings()
    settings.validate()
    return settings
