# Reproducción de audio

## Instrumentos

Cada instrumento se modela de forma distinta en `audio/synth.py` (todos mono, 16 bits, 44.1 kHz, 0.7 s, pico normalizado a 0.8):

| Instrumento | Cómo se sintetiza | Cómo suena |
|---|---|---|
| **Piano** (`piano`) | 8 parciales ligeramente inarmónicos (`f·n·√(1+0.0004·n²)`); cada parcial cae con rapidez `2.2 + 1.1·n`, así que los agudos se apagan antes. Ataque de 3 ms | Cálido, con cola larga |
| **Xilófono** (`xilofono`) | 3 parciales en proporción 1 : 3 : 6 (como las láminas afinadas de un xilófono) con caídas de 7, 22 y 40 por segundo, más un "golpe" de ruido de 3 ms | Seco, brillante y corto; sin segundo armónico |
| **Flauta** (`flauta`) | Fundamental + 2.º (0.22) y 3.º (0.07) armónico, vibrato de 5.5 Hz (0.5 %) que aparece poco a poco, ruido de soplido suave y entrada/salida de 60/140 ms | Casi un tono puro, sostenido y suave |

El ruido usa una semilla fija, así que los archivos generados son siempre idénticos. **Cambiar de instrumento:** botón del panel o tecla `I` (recorre piano → xilófono → flauta); suena una nota de muestra. El inicial se define en `AudioSettings.instrument`.

Los archivos están en `assets/sounds/<instrumento>/<nota>.wav` (30 archivos) más `assets/sounds/error.wav`. `AudioManager` carga **todos** los instrumentos al iniciar (≈ 2.6 MB en memoria), por lo que el cambio es instantáneo y no hay lectura de disco al tocar.

Para añadir un instrumento: crea su función de onda en `synth.py`, regístrala en `_VOICES` y en `INSTRUMENTS` (`audio/instruments.py`) y ejecuta `python run.py --regenerate-sounds`.

## Generación de las notas

| Nota | Clave | Hz | | Nota | Clave | Hz |
|---|---|---|---|---|---|---|
| DO | do4 | 261.63 | | LA | la4 | 440.00 |
| RE | re4 | 293.66 | | SI | si4 | 493.88 |
| MI | mi4 | 329.63 | | DO' | do5 | 523.25 |
| FA | fa4 | 349.23 | | RE' | re5 | 587.33 |
| SOL | sol4 | 392.00 | | MI' | mi5 | 659.25 |

Los archivos `assets/sounds/**/*.wav` están incluidos en el repositorio y fueron generados por este
mismo código; **no hay material con derechos de autor** (origen: síntesis propia del proyecto).
Se regeneran (notas y sonido de error) con `python run.py --regenerate-sounds` o automáticamente si faltan.

## Sonido de error (modo canción)

Al tocar una nota equivocada en el modo canción suena `assets/sounds/error.wav`, un *buzzer* de 0.3 s que
desciende de 220 Hz a 110 Hz (más grave que la nota más baja, DO4 = 261.63 Hz). Se genera con una onda tipo
diente de sierra (6 armónicos, caída exponencial rápida), por lo que es áspero y se distingue al instante de
las notas suaves. Se genera por síntesis propia, sin material con derechos de autor.

| Parámetro (`AudioSettings`) | Efecto |
|---|---|
| `error_plays_note = False` (por defecto) | Un fallo suena solo como el buzzer |
| `error_plays_note = True` | Suenan el buzzer y la nota tocada |
| `error_duration` | Duración del buzzer en segundos (regenera con `--regenerate-sounds`) |

El modo libre y los aciertos siguen sonando como la nota. `AudioManager.play_result(nota, fallo)` decide
qué suena. El sonido respeta el volumen y el silencio (`S`).

## Reproducción

`audio/audio_manager.py` usa `pygame.mixer`:

- `pre_init(44100, -16, 1, 256)`: buffer de 256 muestras (≈ 6 ms de buffer teórico) para baja latencia.
- 16 canales: varias notas pueden sonar a la vez (acordes entre manos).
- Los `Sound` se cargan una sola vez al inicio y `play()` es una llamada inmediata.
- Volumen 0–1 aplicado a todos los sonidos.

La latencia real depende del driver de audio de Windows y **no se midió** en este proyecto.
Si hay chasquidos, sube `AudioSettings.buffer_size` a 512.

Sin dispositivo de audio, `AudioManager.available` es `False`; la aplicación sigue funcionando
y lo indica en pantalla.
