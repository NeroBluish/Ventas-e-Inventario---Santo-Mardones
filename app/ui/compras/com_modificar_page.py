from PySide6.QtWidgets import QWidget

def enter_com_modificar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageCompras")
    page    = pagePro.findChild(QWidget, "pageComMod")
    if not page: return
    # future: confirmar/eliminar con soft-delete
