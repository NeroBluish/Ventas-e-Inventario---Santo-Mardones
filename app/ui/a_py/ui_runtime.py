# app/ui/a_py/ui_runtime.py
import os, sys
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice

def _resource_path(relative: str) -> str:
    # Soporta ejecución normal y ejecutable PyInstaller (onefile)
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)

def load_ui(relative_path: str, parent=None):
    ui_path = _resource_path(relative_path)
    f = QFile(ui_path)
    if not f.open(QIODevice.ReadOnly):
        raise FileNotFoundError(f"No se pudo abrir: {ui_path}")
    try:
        loader = QUiLoader()
        w = loader.load(f, parent)
        if w is None:
            raise RuntimeError(f"Fallo al cargar UI: {ui_path}")
        return w
    finally:
        f.close()
