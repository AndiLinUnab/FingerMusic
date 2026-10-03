# Instalación (Windows + Visual Studio Code)

## 1. Requisitos previos

- Python 3.11 (`python --version`). Descarga: <https://www.python.org/downloads/> (marca *Add Python to PATH*).
- Visual Studio Code con la extensión *Python* (Microsoft).
- Cámara web y salida de audio.

## 2. Entorno virtual

En una terminal dentro de la carpeta `FingerMusic`:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si PowerShell indica que la ejecución de scripts está deshabilitada:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Seleccionar el intérprete en VS Code

`Ctrl+Shift+P` → **Python: Select Interpreter** → elegir `.venv\Scripts\python.exe`.
(`.vscode/settings.json` ya lo configura por defecto.)

## 4. Ejecutar

```
python run.py
```

o **F5** en VS Code (configuración *FingerMusic* de `.vscode/launch.json`).

## 5. Pruebas (opcional)

```
pip install -r requirements-dev.txt
pytest
```

## Notas

- Todas las rutas son relativas al repositorio: puedes clonarlo en cualquier carpeta.
- No hace falta Internet para ejecutar; solo para `pip install`.
- No se necesita archivo `.env`: no hay variables de entorno ni secretos.
- Si borras `assets/sounds/*.wav`, se regeneran solos (o con `python run.py --regenerate-sounds`).
