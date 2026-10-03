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

#: Notas de cada mano, del pulgar al meñique. Mano izquierda: notas 1-5; derecha: 6-10.
DEFAULT_HAND_NOTES: dict[HandSide, tuple[str, str, str, str, str]] = {
    HandSide.LEFT: ("do4", "re4", "mi4", "fa4", "sol4"),
    HandSide.RIGHT: ("la4", "si4", "do5", "re5", "mi5"),
}

FingerMap = dict[HandSide, dict[Finger, Note]]


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

    Args:
        swap_hands: si es ``True`` se intercambian las notas de ambas manos
            (útil para tocar la canción con la mano derecha).
    """
    mapping: FingerMap = {}
    for side, keys in DEFAULT_HAND_NOTES.items():
        source = keys
        if swap_hands:
            other = HandSide.RIGHT if side is HandSide.LEFT else HandSide.LEFT
            source = DEFAULT_HAND_NOTES[other]
        mapping[side] = {finger: get_note(source[finger]) for finger in Finger}
    return mapping
