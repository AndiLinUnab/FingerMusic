# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.1.4] - 2026-10-06

### Added

- Monitor de rendimiento: a los ~5 s de iniciar la cámara el programa registra el tiempo medio de cada etapa (cámara, modelo, motor, interfaz, teclado) y, si va por debajo de ~22 FPS, indica cuál es el cuello de botella y qué hacer.
- `CameraSettings.fourcc` (por defecto `MJPG`): se pide ese formato a la cámara, que evita el modo lento (~15 FPS) de muchas cámaras en Windows; si la cámara no lo soporta se vuelve automáticamente al formato por defecto.

## [0.1.3] - 2026-10-06

### Added

- Mejor racha de la sesión (`MEJOR xN`), que se conserva al fallar o reiniciar la canción y se resalta cuando la racha actual la iguala.
- Efecto de confeti y cartel `RACHA xN!` cada 10 aciertos seguidos.
- Pruebas de la mejor racha y de los efectos de la interfaz (`tests/test_ui.py`).

## [0.1.2] - 2026-10-06

### Added

- Racha de aciertos en el modo canción: cuenta las notas correctas seguidas, se reinicia al fallar, al reiniciar la canción o al entrar al modo canción, y avisa cada 10 aciertos.

## [0.1.1] - 2026-10-06

### Changed

- Mano izquierda: las notas siguen el orden visual de la mano (meñique DO … pulgar SOL) para que las 10 notas suban de izquierda a derecha en pantalla. Con `H` se conserva el orden ascendente.
- Las tarjetas de dedos se dibujan en el orden real de cada mano.
- Interfaz rediseñada: color por nota, tarjetas redondeadas con rebote, notas y chispas desde la punta del dedo, barra de progreso arcoíris y confeti al completar la canción.

## [0.1.0] - 2026-10-02

### Added

- Captura de video con OpenCV y manejo de errores de cámara.
- Detección de manos y 21 landmarks con el modelo preentrenado MediaPipe Hands (hasta dos manos).
- Detección geométrica de flexión de los cinco dedos (ángulos y distancias).
- Suavizado, histéresis, confirmación por frames y cooldown por dedo.
- Detección de transición EXTENDIDO → FLEXIONADO como evento musical.
- Calibración de la posición de reposo con la mano abierta.
- 10 notas (DO4–MI5) generadas por síntesis, reproducidas con `pygame.mixer`.
- Modo libre y modo canción (Jingle Bells simplificado) con nota actual, siguiente, progreso y acierto/error.
- Interfaz gráfica con OpenCV: botones, atajos de teclado, estado de cada dedo.
- Configuración centralizada, logging, pruebas con `pytest` y documentación.
