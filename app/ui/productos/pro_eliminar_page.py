from PySide6.QtWidgets import QWidget

def enter_pro_eliminar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageProductos")
    page    = pagePro.findChild(QWidget, "pageProEliminar")
    if not page: return
    # future: confirmar/eliminar con soft-delete
