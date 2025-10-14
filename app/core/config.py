# app/core/config.py
import sys, os
from pathlib import Path

APP_NAME = "Ventas e Inventario - SM"

# Carpeta persistente en Windows (LocalAppData), fallback a HOME si no existe
appdata = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
appdata.mkdir(parents=True, exist_ok=True)

DB_PATH = appdata / "mi_app.db"

BASE_URL = "https://api.ejemplo.com"  # <- cámbiala cuando tengas backend
API_TOKEN = ""
HTTP_TIMEOUT = 5.0
