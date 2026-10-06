# Jingle Bells

## Representación

`music/jingle_bells.py` define la melodía como cuatro frases de **claves de nota** (`mi4`, `sol4`…),
convertidas en un objeto inmutable `Song(title, notes)` que valida que todas las notas existan.

Es una versión **simplificada del estribillo** en Do mayor (51 notas) que solo usa DO, RE, MI, FA y SOL,
es decir, las cinco notas de una mano. No incluye ritmo ni duraciones: el usuario marca el tempo.

| Frase | Notas |
|---|---|
| 1 | MI MI MI · MI MI MI · MI SOL DO RE MI |
| 2 | FA FA FA FA FA · MI MI MI MI MI · RE RE MI RE SOL |
| 3 | = frase 1 |
| 4 | FA FA FA FA FA · MI MI MI MI · SOL SOL FA RE DO |

## Seguimiento (`music/song_player.py`)

`SongPlayer` guarda la posición. `play_note(clave)` devuelve:

| Resultado | Cuándo | Efecto |
|---|---|---|
| `HIT` | La nota coincide con la esperada | Avanza |
| `MISS` | Es otra nota | No avanza; se muestra ERROR |
| `FINISHED` | Era la última | Muestra "COMPLETADA!" |
| `IGNORED` | La canción ya terminó | Nada |

La **racha** (`MusicEngine.streak`) suma 1 con cada `HIT`/`FINISHED` y vuelve a 0 con un `MISS`, al reiniciar o al entrar al modo canción; cada 10 aciertos seguidos se muestra un mensaje. Cambia de color a partir de 5 y de 10, y cada 10 aciertos seguidos lanza confeti con el cartel `RACHA xN!`. La **mejor racha** de la sesión (`MusicEngine.best_streak`, `MEJOR xN` en pantalla) no se reinicia al fallar ni al reiniciar la canción; se resalta mientras la racha actual la iguala.

La nota **suena siempre**, acierte o no. Entrar al modo canción o pulsar `R` reinicia la melodía.

## Dedos necesarios

Mano izquierda: DO → meñique, RE → anular, MI → medio, FA → índice, SOL → pulgar (así suben de izquierda a derecha en pantalla). Con `H` se usa la mano derecha: DO → pulgar … SOL → meñique.

## Cambiar la canción

Edita `_PHRASES` en `music/jingle_bells.py` con claves de `audio/notes.py`. Si usas notas de la mano
derecha (`la4`…`mi5`) necesitarás las dos manos.
