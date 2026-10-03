# Modelo de inteligencia artificial

## Qué modelo se usa

**MediaPipe Hands** (paquete `mediapipe==0.10.21`, API `mediapipe.solutions.hands`), modelo
preentrenado incluido en el paquete. **No se entrena nada.**

## Quién lo desarrolló

**Google** (equipo de MediaPipe). Descrito en el artículo *"MediaPipe Hands: On-device Real-time
Hand Tracking"* (Zhang et al., 2020). Licencia Apache 2.0.

## Para qué sirve

Localizar una mano en una imagen y estimar la posición de sus articulaciones en tiempo real y en CPU.

## Cómo funciona (resumen)

Dos etapas: (1) un **detector de palmas** localiza la mano; (2) un **modelo de landmarks** regresa 21 puntos 3D
sobre la región recortada. Entre frames se sigue la mano sin repetir la detección completa, lo que
ahorra cómputo.

## Qué información proporciona

- 21 landmarks por mano: `x`, `y` normalizadas (0–1) y `z` relativa a la muñeca.
- Lateralidad (izquierda/derecha) con una confianza.
- Hasta `max_num_hands` manos (aquí 2).

## Cómo se usa en el proyecto

`vision/hand_detector.py` convierte el frame BGR a RGB, llama a `Hands.process()`, convierte los
landmarks a píxeles y los entrega como `HandLandmarks`. La imagen se **espeja antes** de procesarla,
porque el modelo asume vista selfie al decidir la lateralidad.

Parámetros usados (`DetectionSettings`): `model_complexity=0` (ligero, más FPS),
`min_detection_confidence=0.6`, `min_tracking_confidence=0.5`.

## Qué es IA y qué es lógica programada

| Inteligencia artificial (MediaPipe) | Lógica programada (este proyecto) |
|---|---|
| Detectar la mano | Calcular ángulos y distancias |
| Estimar los 21 landmarks | Decidir EXTENDIDO / FLEXIONADO |
| Clasificar izquierda/derecha | Suavizado, histéresis, cooldown, calibración |
| | Mapeo dedo → nota, audio, modo canción, interfaz |

El modelo **no sabe** qué es "un dedo flexionado" ni "una nota": solo entrega puntos.

## Limitaciones

- La coordenada `z` es relativa y aproximada: la flexión hacia la cámara se estima peor que la lateral.
- Oclusiones (dedos tapados por otros), manos de canto, movimientos rápidos o poca luz degradan los landmarks.
- Puede confundir una mano con objetos o perder el seguimiento con fondos complejos.
- La lateralidad se pierde si la imagen no está espejada.
- El rendimiento depende de la CPU del portátil.
- Google considera `mediapipe.solutions` una API *legacy*; ver [decisiones_tecnicas.md](decisiones_tecnicas.md).
