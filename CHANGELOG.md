# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.1.9] - 2026-10-09

### Changed

- `LICENSE` pasa a ser un aviso de derechos de autor (todos los derechos reservados) y se quita la insignia de licencia del README.

## [0.1.8] - 2026-10-08

### Changed

- **La interfaz migra de OpenCV a Tkinter**: los textos y paneles son elementos de un `Canvas`, así que ahora llevan **tildes y ñ** (Índice, Meñique, MODO CANCIÓN, CÁMARA, ¡GENIAL!, mensajes de error…). Tkinter viene incluido con Python: no hay dependencias nuevas.
- El video (mano, notas flotantes y confeti) se sigue componiendo con OpenCV (`ui/video_painter.py`) y se muestra como imagen.
- La interfaz se divide en `ui/common.py` (tipos y colores), `ui/layout.py` (botones y teclas, sin pantalla), `ui/video_painter.py` e `ui/interface.py` (ventana Tkinter).
- Los textos de la ventana se reutilizan entre frames (solo se reconfiguran los que cambian), lo que reduce el coste de dibujar los paneles de ~13 ms a ~1-2 ms.
- Los mensajes largos del pie (p. ej. errores de cámara) se ajustan a dos líneas.
- Títulos con tilde: `HIMNO A LA ALEGRÍA`, `XILÓFONO`; `Finger.label` pasa a `Índice` y `Meñique`.

### Added

- Teclas `←` / `→` para cambiar de canción.
- Si falta Tkinter o no hay pantalla, el programa muestra un mensaje claro en lugar de un traceback.
- Pruebas de la ventana (`tests/test_tk_interface.py`, se omiten sin pantalla), del diseño (`test_layout.py`) y del pintor de video (`test_video_painter.py`); `tests/test_ui.py` se reduce a las pruebas de la API pública.


## [0.1.7] - 2026-10-07

### Added

- Tres instrumentos con timbre propio, sintetizados: **piano** (parciales inarmónicos que se apagan más rápido en los agudos), **xilófono** (parciales 1:3:6, caída muy rápida y golpe inicial) y **flauta** (tono casi puro con vibrato, soplido y entrada/salida suaves).
- Selector de instrumento: botón en el panel o tecla `I`; al cambiar suena una nota de muestra. `AudioSettings.instrument` define el inicial.
- Todos los instrumentos se cargan al iniciar, por lo que el cambio es instantáneo.

### Changed

- Los sonidos de las notas ahora están en `assets/sounds/<instrumento>/<nota>.wav` (antes `assets/sounds/<nota>.wav`; esos archivos sueltos ya no se usan y pueden borrarse).
- El botón SALIR comparte fila con el de instrumento.
- Corregido el texto del panel del modo libre, que se solapaba y se cortaba por el borde.

## [0.1.6] - 2026-10-07

### Added

- Sonido de error en el modo canción: al tocar una nota equivocada suena un "buzzer" grave que desciende de 220 a 110 Hz, distinto de cualquier nota. Por defecto reemplaza a la nota fallada; con `AudioSettings.error_plays_note = True` suenan los dos.
- `assets/sounds/error.wav`, generado por síntesis (sin material con copyright); se regenera solo si falta o con `--regenerate-sounds`.

## [0.1.5] - 2026-10-07

### Added

- Catálogo de 4 canciones de dominio público: Jingle Bells, Estrellita, Himno a la Alegría y Mary y su corderito.
- Selector de canción en el modo canción: flechas `<` `>` en el panel o teclas `N` (siguiente) / `P` (anterior), con vuelta circular.
- El panel indica cuántas manos necesita cada canción (Estrellita usa LA, por lo que requiere las dos manos).
- Cambiar de canción reinicia su progreso y la racha; la mejor racha de la sesión se conserva.

### Changed

- `Song` y `parse_notes` pasan a `music/song.py`; `MusicEngine` acepta una canción o una lista de canciones.

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
