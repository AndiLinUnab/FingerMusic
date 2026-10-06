# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

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
