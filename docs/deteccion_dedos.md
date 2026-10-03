# Detección de dedos

Todo este módulo es **lógica programada** (`vision/finger_detector.py`). El modelo solo aporta los landmarks.

## 1. Landmarks

Cada mano tiene 21 puntos. Para cada dedo se usan 4: base (MCP), articulación media (PIP),
articulación distal (DIP) y punta (TIP). El pulgar usa CMC, MCP, IP y TIP. `x` e `y` se
convierten de coordenadas normalizadas a **píxeles** (`x·ancho`, `y·alto`, `z·ancho`) para no
deformar ángulos ni distancias en imágenes que no son cuadradas.

## 2. Puntuación de flexión (0 = extendido, 1 = flexionado)

### Índice, medio, anular y meñique

1. **Ángulo en el PIP** entre los segmentos PIP→MCP y PIP→DIP. Dedo recto ≈ 180°; al flexionar baja.
   `puntuación_ángulo = (ángulo − 165°) / (95° − 165°)`, recortada a [0, 1].
2. **Alcance**: `distancia(TIP, muñeca) / distancia(MCP, muñeca)`. Extendido ≈ 1.9, flexionado ≈ 1.1.
   `puntuación_alcance = (alcance − 1.90) / (1.10 − 1.90)`, recortada a [0, 1].
3. Combinación: `0.5·ángulo + 0.5·alcance` (`angle_weight`).

### Pulgar

Flexiona hacia la palma, no "hacia abajo", así que se usa:

1. `distancia(TIP pulgar, MCP índice) / tamaño de palma` (tamaño = distancia muñeca–MCP medio):
   1.15 abierto → 0.60 doblado.
2. Ángulo en la articulación IP: 170° → 125°.
3. Combinación con el mismo peso.

### Por qué es robusto

- Ángulos y cocientes **no dependen de la escala** (distancia a la cámara, tamaño de mano) ni de la **rotación** en la imagen.
- Se usa 3D (x, y, z), no solo una comparación de alturas de la punta.
- Dos medidas independientes se compensan entre sí.
- Los rangos son configurables.

## 3. Del valor a un evento

```
cruda → normalización (calibración) → suavizado exponencial → histéresis
      → confirmación N frames → transición → cooldown → evento PRESSED
```

| Etapa | Parámetro | Efecto |
|---|---|---|
| Suavizado | `smoothing_alpha` = 0.6 | `s = α·nuevo + (1−α)·s_anterior`; filtra el ruido de un frame |
| Histéresis | `flex_on` 0.60 / `flex_off` 0.35 | Para pasar a FLEXIONADO hay que superar 0.60; para volver, bajar de 0.35. Entre ambos, no cambia |
| Confirmación | `state_confirmation_frames` = 2 | El cambio debe mantenerse 2 frames seguidos |
| Cooldown | `note_cooldown` = 0.15 s | Mínimo entre dos notas del mismo dedo |
| Arranque | — | El primer estado observado se adopta **sin** evento: aparecer con un dedo doblado no suena |
| Mano perdida | `hand_lost_reset_frames` = 5 | Se olvidan los estados; al volver no hay notas falsas |

## 4. Estados

| Transición | Resultado |
|---|---|
| EXTENDIDO → FLEXIONADO | **Reproduce la nota** (`Transition.PRESSED`) |
| FLEXIONADO → FLEXIONADO | Nada (no repite) |
| FLEXIONADO → EXTENDIDO | Prepara la siguiente activación (`Transition.RELEASED`) |

## 5. Ajuste con manos reales

Los valores por defecto son estimaciones geométricas, probadas con manos sintéticas y no con
personas reales. Si una nota no se dispara, baja `flex_on_threshold` (p. ej. 0.5) o recalibra; si se
disparan notas solas, súbelo o aumenta `state_confirmation_frames` / `note_cooldown`. La barra de
cada tarjeta de dedo muestra la puntuación en vivo para ayudar a ajustar.
