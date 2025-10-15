# app/ui/Inventario/_Inventario_page.py
from PySide6.QtWidgets import QWidget, QStackedWidget, QPushButton, QMessageBox

from app.ui.compras.com_ingresar_page import enter_com_ingresar
from app.ui.compras.com_modificar_page import enter_com_modificar
from app.ui.compras.com_eliminar_page import enter_com_eliminar
from app.ui.compras.com_lis_page import enter_com_listar

#Devuelve el QStackedWidget
def _get_inv_stack(root):
    page_inv = root.findChild(QWidget, "pageCompras")
    if page_inv is None:
        raise RuntimeError("No existe 'pageCompras' en el .ui")
    stk = page_inv.findChild(QStackedWidget, "comStack")
    if stk is None:
        raise RuntimeError("Falta QStackedWidget 'comStack' dentro de pageCompras")
    return stk

# Marca/desmarca y habilita/deshabilita los botones de navegación según la página activa del stack.
def _sync_inv_state(root):
    try:
        current = _get_inv_stack(root).currentWidget().objectName()
    except Exception:
        return

    def _find(name): 
        return root.findChild(QPushButton, name)

    btnComIng  = _find("btnComIng")
    btnComMod  = _find("btnComMod")
    btnComElim = _find("btnComElim")
    btnComLis = _find("btnComLis")


    mapping = {
        "pageComIng"    :   btnComIng,
        "pageComMod"    :   btnComMod,
        "pageComElim"   :   btnComElim,
        "pageComLis"    :   btnComLis,

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
    if page_object_name == "pageComIng":
        enter_com_ingresar(root)     # esta función se auto-encarga (init + refresh)
    elif page_object_name == "pageComMod":
        enter_com_modificar(root)
    elif page_object_name == "pageComElim":
        enter_com_eliminar(root)
    elif page_object_name == "pageComLis":
        enter_com_listar(root)   


    stk.setCurrentWidget(page)
    _sync_inv_state(root)

def init_inventory_page(root):
    """Cablea SOLO los botones internos y el sync visual."""
    btnComIng   = root.findChild(QPushButton, "btnComIng")
    btnComMod   = root.findChild(QPushButton, "btnComMod")
    btnComElim  = root.findChild(QPushButton, "btnComElim")
    btnComLis   = root.findChild(QPushButton, "btnComLis")
 

    if btnComIng:
        btnComIng.clicked.connect(lambda: show_inv_page(root, "pageComIng"))
    if btnComMod:
        btnComMod.clicked.connect(lambda: show_inv_page(root, "pageComMod"))
    if btnComElim:
        btnComElim.clicked.connect(lambda: show_inv_page(root, "pageComElim"))
    if btnComLis:
        btnComLis.clicked.connect(lambda: show_inv_page(root, "pageComLis"))


    # como en main_window: al cambiar la subpágina, solo sincroniza visual
    try:
        _get_inv_stack(root).currentChanged.connect(lambda _i: _sync_inv_state(root))
    except Exception:
        pass


# ---------- wrapper mínimo para el router ----------
def enter_compras(root):
    """
    Llamado por el router principal al entrar a 'pageInventario'.
    - 1ª vez: inicializa sub-router y muestra la subpágina por defecto.
    """
    page = root.findChild(QWidget, "pageCompras")
    if page is None:
        return

    if not getattr(page, "_inv_inited", False):
        init_inventory_page(root)
        setattr(page, "_inv_inited", True)
        # Página inicial por defecto (como en main_window):
        show_inv_page(root, "pageComIng")
    
