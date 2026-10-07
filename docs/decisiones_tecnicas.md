# Decisiones técnicas

| Decisión | Alternativa | Motivo |
|---|---|---|
| **MediaPipe 0.10.21 con `mediapipe.solutions.hands`** | Última versión (Hand Landmarker, API *Tasks*) | Las versiones recientes eliminaron `solutions` y exigen descargar el modelo `.task` desde Internet. La 0.10.21 trae el modelo embebido: instalación con un solo `pip`, ejecución sin Internet y sin rutas de modelo. Coste: API *legacy*; el cambio a Tasks está en mejoras futuras |
| **`opencv-contrib-python`** | `opencv-python` | `mediapipe` ya depende de él; instalar ambos genera conflictos del módulo `cv2` |
| **`numpy==1.26.4`** | NumPy 2.x | mediapipe 0.10.21 requiere NumPy < 2 |
| **Interfaz con OpenCV (estilo juguetón: colores por nota, partículas, rebotes)** | Tkinter / PySide | Un solo bucle, sin hilos ni conversión de imágenes, mínima latencia y menos dependencias. Coste: sin tildes ni ñ en los textos |
| **pygame.mixer para audio** | winsound, sounddevice, simpleaudio | Multiplataforma, rueda binaria para Windows, polifonía y buffer ajustable; instalación trivial |
| **Tonos sintetizados** (3 instrumentos: piano, xilófono, flauta) | Samples descargados | Sin problemas de licencia ni Internet; reproducible y documentado. Cada timbre se distingue por sus parciales y su envolvente, no por grabaciones |
| **Cargar todos los instrumentos al iniciar** | Cargar solo el seleccionado | El cambio de timbre es instantáneo y tocar no accede al disco; el coste es ~2.6 MB de memoria |
| **Notas por mano (izq. DO–SOL, der. LA–MI')** | Un solo juego de dedos con gestos o selección de octava | Es lo más intuitivo y simple: cada dedo, una nota fija. Con una mano hay 5 notas; las 10 requieren dos manos |
| **Notas ascendentes de izquierda a derecha en pantalla** (izq.: meñique=DO … pulgar=SOL; der.: pulgar=LA … meñique=MI') | Pulgar=DO en ambas manos | Con la vista espejo el pulgar izquierdo queda a la derecha; el orden "de piano" hace que las 10 notas coincidan con el orden visual. Las tarjetas de dedos se dibujan en ese mismo orden |
| **Puntuación continua + histéresis** | Umbral único por dedo | Evita el parpadeo de estado y los disparos múltiples |
| **Arranque sin evento** | Disparar al aparecer | Evita notas falsas al entrar la mano o al recuperar el seguimiento |
| **Calibración de línea base (mano abierta)** | Calibrar también el puño | Simple y robusta; reduce el sesgo por mano sin pedir al usuario gestos extra |
| **`engine.py` independiente** | Lógica dentro de `app.py` | Permite probar la lógica sin cámara ni audio |
| **`frozen dataclass` para configuración** | `.env`, JSON | Tipado, validación y sin archivos que olvidar; no hay secretos ni necesidad de `.env` |
| **`src/` layout + `run.py`** | Paquete instalable | `run.py` y `pytest.ini` (`pythonpath = src`) evitan instalar nada |
| **`StrEnum` / Python ≥ 3.11** | `(str, Enum)` | Requisito pedido (3.11) y código más limpio |

## Compatibilidad

- Probado en Python 3.12 (Linux). Python 3.11 (Windows) es el objetivo pero no se instaló allí.
- mediapipe 0.10.21 no soporta Python 3.13+.
