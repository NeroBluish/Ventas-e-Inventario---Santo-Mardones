# app/ui/main_window.py
from app.ui.a_py.ui_runtime import load_ui
from PySide6.QtWidgets import QWidget, QStackedWidget, QPushButton

from app.ui.Ventas._Ventas_page import enter_ventas
from app.ui.productos._producto_page import enter_productos
from app.ui.Inventario._Inventario_page import enter_inventory
from app.ui.compras._compras_page import enter_compras

#Devuelve el QStackedWidget principal
def _get_stack(root):
    stk = root.findChild(QStackedWidget, "stack")
    if stk is None:
        raise RuntimeError("Falta QStackedWidget 'stack' en el .ui")
    return stk


# Marca/desmarca y habilita/deshabilita los botones de navegación según la página activa del stack.
def _sync_nav_state(root):
    try:
        current = _get_stack(root).currentWidget().objectName()
    except Exception:
        return
    
    # Helper para encontrar tanto QPushButton como QToolButton
    def _find(name):
        return root.findChild(QPushButton, name)
    
    # Botones de navegación (asegúrate de que los objectName coinciden en el .ui)
    btnVentas   = _find("btnVentas")
    btnProducto = _find("btnProducto")
    btnInvent   = _find("btnInventario")
    btnCompras   = _find("btnCompras")

    # Mapeo página → botón asociado
    mapping = {"pageVentas": btnVentas, 
               "pageProductos": btnProducto, 
               "pageInventario": btnInvent, 
               "pageCompras" :btnCompras}

    for b in mapping.values():
        if b:
            b.setCheckable(True); b.setChecked(False); b.setEnabled(True)
    active = mapping.get(current)
    if active:
        active.setCheckable(True); active.setChecked(True); active.setEnabled(False)

# para inicializar paginas 
def _show_page(root, page_object_name: str):
    stk = _get_stack(root)
    page = root.findChild(QWidget, page_object_name)
    if page is None:
        raise RuntimeError(f"No existe la página '{page_object_name}' en el .ui")

    # Ventas: delega al módulo de Ventas (init o repaint)
    if page_object_name == "pageVentas":
        enter_ventas(root)
    
    if page_object_name == "pageProductos":
        enter_productos(root)

    # Al entrar a Inventario, asegúrate de tenerlo inicializado y refrescado
    if page_object_name == "pageInventario":
        enter_inventory(root)

    if page_object_name == "pageCompras":
        enter_compras(root)

    stk.setCurrentWidget(page)
    _sync_nav_state(root)


def create_main_window(username="admin"):
    w = load_ui("app/ui/main_window.ui")
    w.setWindowTitle(f"Ventas e Inventario - Santo Mardones — {username}")

    #botones de navegación principal
    btnVentas = w.findChild(QPushButton, "btnVentas")
    btnProducto = w.findChild(QPushButton, "btnProducto")
    btnInventario = w.findChild(QPushButton, "btnInventario")
    btnCompras = w.findChild(QPushButton, "btnCompras")

    if btnVentas:     btnVentas.clicked.connect(lambda: _show_page(w, "pageVentas"))
    if btnProducto:   btnProducto.clicked.connect(lambda: _show_page(w, "pageProductos"))
    if btnInventario: btnInventario.clicked.connect(lambda: _show_page(w, "pageInventario"))
    if btnCompras:    btnCompras.clicked.connect(lambda: _show_page(w, "pageCompras"))

    # Página inicial
    _show_page(w, "pageVentas")  # también inicializa inventario
    try:
        _get_stack(w).currentChanged.connect(lambda _i: _sync_nav_state(w))
    except Exception:
        pass
    return w
