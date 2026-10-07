# Reproducción de audio

## Generación de las notas

`audio/synth.py` sintetiza cada nota como suma de 4 armónicos (1, 2, 3 y 4 veces la frecuencia
fundamental) con amplitudes 1, 0.45, 0.2 y 0.08, ataque de 5 ms, caída exponencial y cierre de 50 ms.
Se normaliza a un pico de 0.8 y se guarda como WAV mono de 16 bits a 44.1 kHz (0.7 s).

| Nota | Clave | Hz | | Nota | Clave | Hz |
|---|---|---|---|---|---|---|
| DO | do4 | 261.63 | | LA | la4 | 440.00 |
| RE | re4 | 293.66 | | SI | si4 | 493.88 |
| MI | mi4 | 329.63 | | DO' | do5 | 523.25 |
| FA | fa4 | 349.23 | | RE' | re5 | 587.33 |
| SOL | sol4 | 392.00 | | MI' | mi5 | 659.25 |

Los archivos `assets/sounds/*.wav` están incluidos en el repositorio y fueron generados por este
mismo código; **no hay material con derechos de autor** (origen: síntesis propia, licencia MIT del proyecto).
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
