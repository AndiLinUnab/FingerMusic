# Funcionamiento y configuración

## Ciclo de uso

1. La cámara captura video; la imagen se **espeja** (efecto selfie) para que izquierda/derecha
   coincidan con tus manos.
2. MediaPipe devuelve los landmarks de cada mano.
3. Se calcula la flexión de cada dedo y su estado.
4. Una transición **EXTENDIDO → FLEXIONADO** genera una nota; **FLEXIONADO → FLEXIONADO** no repite;
   **FLEXIONADO → EXTENDIDO** "arma" el dedo para la siguiente pulsación.

## Interfaz

| Zona | Contenido |
|---|---|
| Cabecera | Nombre y FPS |
| Video | Cámara, landmarks, nombre y nota sobre cada punta de dedo, borde verde/rojo (acierto/error) |
| Panel lateral | Modo, nota sonando (libre) o nota actual / siguiente / progreso / acierto-error (canción) y botones |
| Parte inferior | Una tarjeta por dedo y mano: nombre, nota, estado y barra de flexión; mensajes y volumen |

## Calibración

Con la mano abierta y quieta 2 s se mide la puntuación de reposo de cada dedo (mediana).
Esa línea base se resta de la puntuación: `normalizada = (cruda − base) / (1 − base)`.
Ayuda con manos de distinta forma (dedos naturalmente curvados) y reduce disparos falsos.
La base se limita a `calibration_max_baseline` (0.40) para que no se calibre con el puño cerrado.
La distancia a la cámara y el tamaño de la mano ya se compensan en la geometría (ver
[deteccion_dedos.md](deteccion_dedos.md)): ángulos y cocientes no dependen de la escala.

## Dónde cambiar cada cosa

Todo en `src/fingermusic/config/settings.py` salvo notas y canción.

| Qué | Dónde |
|---|---|
| Sensibilidad (más fácil/difícil disparar) | `flex_on_threshold` (↓ = más sensible), `flex_off_threshold` |
| Evitar notas dobles | `note_cooldown` (↑), `state_confirmation_frames` (↑) |
| Respuesta más suave / más rápida | `smoothing_alpha` (↓ más suave pero con más retraso) |
| Rangos geométricos | `pip_angle_*`, `reach_ratio_*`, `thumb_*`, `angle_weight` |
| Cámara | `CameraSettings.index`, `width`, `height`, `fps`, `mirror` (o `--camera N`) |
| Volumen | `AudioSettings.volume`, `volume_step` |
| Instrumento inicial | `AudioSettings.instrument` (`piano`, `xilofono`, `flauta`); en ejecución, tecla `I` |
| Latencia de audio | `AudioSettings.buffer_size` (256; sube a 512 si hay chasquidos) |
| Notas y mapeo por dedo | `audio/notes.py` (`NOTES`, `DEFAULT_HAND_NOTES`) |
| Canciones | `music/catalog.py` (`build_songs()` y una función por canción) |

`Settings.validate()` comprueba la coherencia de los valores al arrancar.

## Logging

Consola (INFO por defecto; `--debug` para DEBUG) y archivo `logs/fingermusic.log`
(rotativo, nivel DEBUG, ignorado por Git). No se registran mensajes por frame.
