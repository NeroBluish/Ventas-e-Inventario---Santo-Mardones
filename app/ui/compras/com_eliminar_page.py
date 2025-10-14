from PySide6.QtWidgets import QWidget

def enter_com_eliminar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageCompras")
    page    = pagePro.findChild(QWidget, "pageComElim")
    if not page: return
    # future: confirmar/eliminar con soft-delete
