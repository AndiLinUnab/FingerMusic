"""Definición de las 10 notas de la escala y del mapeo dedo -> nota."""

from __future__ import annotations

from dataclasses import dataclass

from fingermusic.vision.landmarks import Finger, HandSide


@dataclass(frozen=True)
class Note:
    """Una nota musical.

    Attributes:
        key: identificador único, también nombre del archivo ``.wav`` (``"do4"``).
        label: nombre que se muestra al usuario (``"DO"``, ``"DO'"`` para la octava aguda).
        frequency: frecuencia en Hz (afinación estándar, La4 = 440 Hz).
    """

    key: str
    label: str
    frequency: float


#: Escala diatónica de Do mayor: de DO4 a MI5 (10 notas).
NOTES: tuple[Note, ...] = (
    Note("do4", "DO", 261.63),
    Note("re4", "RE", 293.66),
    Note("mi4", "MI", 329.63),
    Note("fa4", "FA", 349.23),
    Note("sol4", "SOL", 392.00),
    Note("la4", "LA", 440.00),
    Note("si4", "SI", 493.88),
    Note("do5", "DO'", 523.25),
    Note("re5", "RE'", 587.33),
    Note("mi5", "MI'", 659.25),
)

NOTES_BY_KEY: dict[str, Note] = {note.key: note for note in NOTES}

#: Las 5 notas graves (mano izquierda) y las 5 agudas (mano derecha), de izquierda a derecha.
LOW_NOTES: tuple[str, ...] = ("do4", "re4", "mi4", "fa4", "sol4")
HIGH_NOTES: tuple[str, ...] = ("la4", "si4", "do5", "re5", "mi5")

#: Orden de los dedos de izquierda a derecha **en pantalla** (vista espejo).
#: Mano izquierda: el pulgar queda a la derecha; mano derecha: queda a la izquierda.
SCREEN_FINGER_ORDER: dict[HandSide, tuple[Finger, ...]] = {
    HandSide.LEFT: (Finger.PINKY, Finger.RING, Finger.MIDDLE, Finger.INDEX, Finger.THUMB),
    HandSide.RIGHT: (Finger.THUMB, Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY),
}

FingerMap = dict[HandSide, dict[Finger, Note]]


def screen_finger_order(side: HandSide) -> tuple[Finger, ...]:
    """Dedos de una mano ordenados de izquierda a derecha en pantalla."""
    return SCREEN_FINGER_ORDER[side]


def get_note(key: str) -> Note:
    """Devuelve la nota con la clave indicada.

    Raises:
        KeyError: si la clave no existe.
    """
    try:
        return NOTES_BY_KEY[key]
    except KeyError:
        raise KeyError(f"Nota desconocida: {key!r}") from None


def build_finger_map(swap_hands: bool = False) -> FingerMap:
    """Construye el mapeo (mano, dedo) -> nota.

    Las notas ascienden de izquierda a derecha en pantalla: mano izquierda
    (meñique DO ... pulgar SOL) y mano derecha (pulgar LA ... meñique MI').

    Args:
        swap_hands: si es ``True`` cada mano toca el grupo de notas de la otra
            (útil para tocar la canción con la mano derecha), conservando
            también el orden ascendente de izquierda a derecha.
    """
    mapping: FingerMap = {}
    for side in HandSide:
        is_low = (side is HandSide.LEFT) != swap_hands
        group = LOW_NOTES if is_low else HIGH_NOTES
        mapping[side] = {
            finger: get_note(key)
            for finger, key in zip(SCREEN_FINGER_ORDER[side], group, strict=True)
        }
    return mapping
