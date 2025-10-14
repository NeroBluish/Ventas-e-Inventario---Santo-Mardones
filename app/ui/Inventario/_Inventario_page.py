# app/ui/Inventario/_Inventario_page.py
from PySide6.QtWidgets import QWidget, QStackedWidget, QPushButton, QMessageBox

from app.ui.Inventario.inv_agregar_page import enter_inv_agregar
from app.ui.Inventario.inv_alertaStock_page import enter_inv_alerta_stock
from app.ui.Inventario.inv_ajustes_page import enter_inv_ajustes

#Devuelve el QStackedWidget
def _get_inv_stack(root):
    page_inv = root.findChild(QWidget, "pageInventario")
    if page_inv is None:
        raise RuntimeError("No existe 'pageInventario' en el .ui")
    stk = page_inv.findChild(QStackedWidget, "invStack")
    if stk is None:
        raise RuntimeError("Falta QStackedWidget 'invStack' dentro de pageInventario")
    return stk

# Marca/desmarca y habilita/deshabilita los botones de navegación según la página activa del stack.
def _sync_inv_state(root):
    try:
        current = _get_inv_stack(root).currentWidget().objectName()
    except Exception:
        return

    def _find(name): 
        return root.findChild(QPushButton, name)

    btnAgregar  = _find("btnAgregar")
    btnTabla   = _find("btnInvTabla") or _find("btnBajoInventario")
    btnAjustes = _find("btnAjustes")

    mapping = {
        "pageInvAgregar":  btnAgregar,
        "pageInvTabla":   btnTabla,
        "pageInvAjustes": btnAjustes,
    }

    for b in mapping.values():
        if b:
            b.setCheckable(True); b.setChecked(False); b.setEnabled(True)

    active = mapping.get(current)
    if active:
        active.setCheckable(True)
        active.setChecked(True)
        active.setEnabled(False)

# para inicializar paginas
def show_inv_page(root, page_object_name: str):
    """Sub-router: cambia de subpágina y delega init/refresh a su enter_*."""
    stk = _get_inv_stack(root)
    page = stk.findChild(QWidget, page_object_name)
    if page is None:
        QMessageBox.critical(root, "UI", f"No existe la página interna '{page_object_name}'")
        return

    # Igual que en main_window: if/elif, sin mapa extra
    if page_object_name == "pageInvTabla":
        enter_inv_alerta_stock(root)     # esta función se auto-encarga (init + refresh)
    elif page_object_name == "pageInvAjustes":
        enter_inv_ajustes(root)        # esta también se auto-encarga
    elif page_object_name == "pageInvAgregar":
        enter_inv_agregar(root)    

    stk.setCurrentWidget(page)
    _sync_inv_state(root)

def init_inventory_page(root):
    """Cablea SOLO los botones internos y el sync visual."""
    btnAgregar = root.findChild(QPushButton, "btnAgregar")
    btnAjustes  = root.findChild(QPushButton, "btnAjustes")
    btnInvTabla = root.findChild(QPushButton, "btnInvTabla") or root.findChild(QPushButton, "btnBajoInventario")

    if btnAgregar:
        btnAgregar.clicked.connect(lambda: show_inv_page(root, "pageInvAgregar"))
    if btnAjustes:
        btnAjustes.clicked.connect(lambda: show_inv_page(root, "pageInvAjustes"))
    if btnInvTabla:
        btnInvTabla.clicked.connect(lambda: show_inv_page(root, "pageInvTabla"))

    # como en main_window: al cambiar la subpágina, solo sincroniza visual
    try:
        _get_inv_stack(root).currentChanged.connect(lambda _i: _sync_inv_state(root))
    except Exception:
        pass


# ---------- wrapper mínimo para el router ----------
def enter_inventory(root):
    """
    Llamado por el router principal al entrar a 'pageInventario'.
    - 1ª vez: inicializa sub-router y muestra la subpágina por defecto.
    """
    page = root.findChild(QWidget, "pageInventario")
    if page is None:
        return

    if not getattr(page, "_inv_inited", False):
        init_inventory_page(root)
        setattr(page, "_inv_inited", True)
        # Página inicial por defecto (como en main_window):
        show_inv_page(root, "pageInvTabla")
    
