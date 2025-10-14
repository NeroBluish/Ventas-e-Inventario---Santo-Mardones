from PySide6.QtWidgets import QWidget

def enter_pro_modificar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageProductos")
    page    = pagePro.findChild(QWidget, "pageProModificar")
    if not page: return
    # future: preparar buscador/selector y formulario de edición
