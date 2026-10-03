# Cómo contribuir

¡Gracias por tu interés en FingerMusic!

1. **Fork**: haz un fork del repositorio en GitHub y clónalo.
2. **Entorno**: crea el entorno virtual e instala las dependencias de desarrollo
   (ver [docs/instalacion.md](docs/instalacion.md)):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```
3. **Branch**: crea una rama descriptiva, por ejemplo `git checkout -b feature/nuevo-instrumento`.
4. **Cambios**: mantén el estilo del proyecto (type hints, docstrings, sin números
   mágicos: los parámetros van en `src/fingermusic/config/settings.py`).
5. **Pruebas**: ejecuta `pytest` y `ruff check .`; ambos deben terminar sin errores.
   Añade pruebas para el código nuevo.
6. **Documentación**: actualiza el README, `docs/` y `CHANGELOG.md` si corresponde.
7. **Pull Request**: sube tu rama y abre un Pull Request explicando qué cambia y por qué.
