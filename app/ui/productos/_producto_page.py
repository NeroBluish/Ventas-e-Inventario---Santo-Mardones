from PySide6.QtWidgets import QWidget, QStackedWidget, QPushButton, QMessageBox

# stubs (subpáginas)
from app.ui.productos.pro_catalogo_page import enter_pro_catalogo, refresh_pro_catalogo
from app.ui.productos.pro_nuevo_page    import enter_pro_nuevo
from app.ui.productos.pro_modificar_page import enter_pro_modificar
from app.ui.productos.pro_eliminar_page  import enter_pro_eliminar


# ------- helpers internos -------
def _get_pro_stack(root: QWidget) -> QStackedWidget:
    page = root.findChild(QWidget, "pageProductos")
    if page is None:
        raise RuntimeError("Falta 'pageProductos' en el .ui")
    stk = page.findChild(QStackedWidget, "proStack")
    if stk is None:
        raise RuntimeError("Falta QStackedWidget 'proStack' dentro de pageProductos")
    return stk

def _sync_pro_buttons(root: QWidget):
    """Marca/desmarca y deshabilita el botón de la subpágina activa."""
    try:
        cur = _get_pro_stack(root).currentWidget().objectName()
    except Exception:
        return

    def _f(name): return root.findChild(QPushButton, name)

    btnCat  = _f("btnProCatalogo")
    btnNew  = _f("btnProNuevo")
    btnEdit = _f("btnProModificar")
    btnDel  = _f("btnProEliminar")

    mapping = {
        "pageProCatalogo": btnCat,
        "pageProNuevo":    btnNew,
        "pageProModificar":btnEdit,
        "pageProEliminar": btnDel,
    }

    for b in mapping.values():
        if b:
            b.setCheckable(True); b.setChecked(False); b.setEnabled(True)

    active = mapping.get(cur)
    if active:
        active.setCheckable(True); active.setChecked(True); active.setEnabled(False)


# ------- API del sub-router -------
def show_pro_page(root: QWidget, page_object_name: str):
    """Cambia a una subpágina de proStack haciendo lazy-init la primera vez."""
    stk  = _get_pro_stack(root)
    page = stk.findChild(QWidget, page_object_name)
    if page is None:
        QMessageBox.critical(root, "UI", f"No existe la subpágina '{page_object_name}'")
        return

    # Lazy init por subpágina
    if page_object_name == "pageProCatalogo" and not getattr(page, "_pro_cat_inited", False):
        enter_pro_catalogo(root); setattr(page, "_pro_cat_inited", True)
    if page_object_name == "pageProNuevo" and not getattr(page, "_pro_new_inited", False):
        enter_pro_nuevo(root);    setattr(page, "_pro_new_inited", True)
    if page_object_name == "pageProModificar" and not getattr(page, "_pro_mod_inited", False):
        enter_pro_modificar(root); setattr(page, "_pro_mod_inited", True)
    if page_object_name == "pageProEliminar" and not getattr(page, "_pro_del_inited", False):
        enter_pro_eliminar(root);  setattr(page, "_pro_del_inited", True)

    stk.setCurrentWidget(page)

    # Si entras a catálogo, refresca listado si el stub tiene hook
    if page_object_name == "pageProCatalogo":
        try: refresh_pro_catalogo(root)
        except Exception: pass

    _sync_pro_buttons(root)


def init_product_page(root: QWidget):
    """Se llama una sola vez cuando entras por primera vez a pageProductos."""
    # Conectar botones
    btnCat  = root.findChild(QPushButton, "btnProCatalogo")
    btnNew  = root.findChild(QPushButton, "btnProNuevo")
    btnEdit = root.findChild(QPushButton, "btnProModificar")
    btnDel  = root.findChild(QPushButton, "btnProEliminar")

    if btnCat:  btnCat.clicked.connect( lambda: show_pro_page(root, "pageProCatalogo") )
    if btnNew:  btnNew.clicked.connect( lambda: show_pro_page(root, "pageProNuevo") )
    if btnEdit: btnEdit.clicked.connect( lambda: show_pro_page(root, "pageProModificar") )
    if btnDel:  btnDel.clicked.connect( lambda: show_pro_page(root, "pageProEliminar") )

    # Sincroniza estado cuando cambie el stack interno
    try:
        _get_pro_stack(root).currentChanged.connect(lambda _i: _sync_pro_buttons(root))
    except Exception:
        pass


# Entry point para el router de Productos (lo llamas desde main_window)
from PySide6.QtWidgets import QWidget as _QW

def enter_productos(root: QWidget):
    """
    Al entrar a pageProductos:
      - Primera vez: init_product_page(...) y abrir Catálogo
      - Siguientes: si estás en Catálogo, refrescar listado
    """
    page = root.findChild(_QW, "pageProductos")
    if page is None:
        return

    if not getattr(page, "_pro_inited", False):
        init_product_page(root)
        setattr(page, "_pro_inited", True)
        show_pro_page(root, "pageProNuevo")

