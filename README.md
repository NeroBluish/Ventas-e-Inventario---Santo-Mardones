# Ventas e Inventario - Santo Mardones (Offline-First)

- PySide6 (GUI)
- SQLAlchemy + SQLite (local)
- httpx (sync HTTP)
- Alembic (migraciones, opcional)
- PyInstaller (empaquetado .exe)

## Comandos
python -m app.main
pyinstaller --noconsole --onefile --name "Ventas e Inventario - SM" app/main.py
