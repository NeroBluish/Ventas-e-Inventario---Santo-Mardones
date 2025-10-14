# app/ui/Inventario/inv_alertaStock_page.py
from PySide6.QtWidgets import QWidget


# ---------- wrapper mínimo para el sub-router ----------

def enter_inv_alerta_stock(root: QWidget):
    """Entry point al entrar a la subpágina de 'Bajo Inventario'."""
    page_inv = root.findChild(QWidget, "pageInventario")
    page_tab = page_inv.findChild(QWidget, "pageInvTabla") if page_inv else None
    if page_tab is None:
        return
