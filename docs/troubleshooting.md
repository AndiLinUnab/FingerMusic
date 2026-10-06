# Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| "No se pudo abrir la camara" | Cámara ocupada, otro índice o permiso denegado | Cierra Zoom/Teams/Cámara; *Configuración → Privacidad → Cámara*; `python run.py --camera 1`; pulsa `Espacio` para reintentar |
| Imagen negra | Driver de cámara | Cambia el índice; reinicia la cámara; actualiza el driver |
| "Se perdio la senal de la camara" | Cámara desconectada | Reconecta y pulsa `Espacio` |
| No se detecta la mano | Poca luz, mano de canto, fondo confuso | Más luz, palma hacia la cámara, a 40–70 cm |
| Notas que se disparan solas | Umbral bajo / ruido | Calibra (`C`); sube `flex_on_threshold`; sube `note_cooldown` o `state_confirmation_frames` |
| Una nota no se dispara | Umbral alto / flexión pequeña | Calibra; baja `flex_on_threshold` (p. ej. 0.5); flexiona más |
| El pulgar no responde | Es el dedo más difícil | Dóblalo claramente hacia la palma; ajusta `thumb_ratio_*` |
| Izquierda y derecha invertidas | Imagen sin espejar | Verifica `CameraSettings.mirror = True` |
| No suena | Volumen, sonido desactivado, sin dispositivo | Volumen de Windows; tecla `S`; la barra inferior dice "Sin audio" si falla el dispositivo |
| Sonido entrecortado | Buffer pequeño | `AudioSettings.buffer_size = 512` |
| FPS bajos (~15 FPS) | Ver el diagnóstico automático (abajo) | Depende de la etapa lenta |
| `ModuleNotFoundError` | Entorno sin activar | `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| Error al instalar mediapipe | Python no soportado (p. ej. 3.13) | Usa Python 3.11 |
| "La version instalada de mediapipe no incluye la API 'solutions'" | mediapipe más nuevo | `pip install -r requirements.txt` (fija 0.10.21) |
| PowerShell no activa `.venv` | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

Los logs están en `logs/fingermusic.log`. Para más detalle, ejecuta `python run.py --debug`.

## Diagnóstico de FPS bajos

A los ~5 segundos de iniciar la cámara, el programa escribe en la consola una línea como:

```
Rendimiento: 11.8 FPS  (camara 69 ms | modelo 14 ms | motor 0 ms | interfaz 5 ms | teclado 0 ms)
```

Cada número es el tiempo medio por frame de esa etapa. Si los FPS son bajos (< 22) aparece además un aviso con la causa probable:

| Etapa más lenta | Qué significa | Qué hacer |
|---|---|---|
| `camara` | La cámara entrega pocas imágenes por segundo (no es el programa). Muy común: **poca luz** (la cámara baja sola a ~15 FPS), otra app usando la cámara o un modo de video lento | Más luz frontal; cierra Zoom/Teams/Cámara de Windows; el programa ya pide formato `MJPG` (`CameraSettings.fourcc`); prueba también `fourcc = ""` por si tu cámara va mejor sin él |
| `modelo` | El procesador va justo con MediaPipe | Conecta el portátil a la corriente y desactiva el ahorro de energía; cierra otras apps; baja la resolución en `CameraSettings` |
| `interfaz` | Dibujar la ventana es lo lento | Oculta los puntos (`L`); reduce la resolución |
| `teclado` | La espera de eventos de la ventana (`cv2.waitKey`) tarda mucho | Reporta el dato si persiste |

Para ver más detalle usa `python run.py --debug`. Si tu cámara declara `30 FPS` pero la etapa `camara` marca ~66 ms, la cámara está limitando.
