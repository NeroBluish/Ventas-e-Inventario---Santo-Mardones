# app/ui/compras/com_ingresar_page.py

from PySide6.QtWidgets import QWidget

def enter_com_ingresar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageCompras")
    page    = pagePro.findChild(QWidget, "pageComIng")
    if not page: return
    # future: confirmar/eliminar con soft-delete
