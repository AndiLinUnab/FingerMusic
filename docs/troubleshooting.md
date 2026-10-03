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
| FPS bajos | CPU limitada | Reduce resolución en `CameraSettings`; mantén `model_complexity=0`; cierra otras apps |
| `ModuleNotFoundError` | Entorno sin activar | `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| Error al instalar mediapipe | Python no soportado (p. ej. 3.13) | Usa Python 3.11 |
| "La version instalada de mediapipe no incluye la API 'solutions'" | mediapipe más nuevo | `pip install -r requirements.txt` (fija 0.10.21) |
| PowerShell no activa `.venv` | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

Los logs están en `logs/fingermusic.log`. Para más detalle, ejecuta `python run.py --debug`.
