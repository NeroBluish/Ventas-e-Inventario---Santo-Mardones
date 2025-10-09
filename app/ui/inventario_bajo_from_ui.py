# app/ui/inventario_bajo_from_ui.py
from app.ui.ui_runtime import load_ui  # QUiLoader helper
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from app.ui.ventas_controller import init_ventas_page
from PySide6.QtWidgets import QTableView, QPushButton, QStackedWidget, QWidget, QToolButton   # <-- NUEVO
from PySide6.QtCore import Qt, QSortFilterProxyModel
from app.ui.add_producto_dialog import open_add_producto_dialog  

# --- DB imports ---
from app.core.db_local import SessionLocal
from app.core.repositories import get_productos_bajo_inventario
# ------------------

# ------------------- helpers para STACK (NUEVO) -------------------
def _get_stack(root):
    stk = root.findChild(QStackedWidget, "stack")
    if stk is None:
        raise RuntimeError("Falta QStackedWidget con objectName='stack' en el .ui")
    return stk

def _show_page(root, page_object_name: str):
    """Cambia a la página indicada por objectName (pageVentas, pageInventario, etc.)."""
    stk = _get_stack(root)
    page = root.findChild(QWidget, page_object_name)
    if page is None:
        raise RuntimeError(f"No existe la página '{page_object_name}' en el .ui")
    
    # init one-shot cuando entras a Ventas por primera vez
    if page_object_name == "pageVentas" and not getattr(page, "_ventas_inited", False):
        init_ventas_page(root)
        setattr(page, "_ventas_inited", True)
        
    stk.setCurrentWidget(page)
    _sync_nav_state(root)
    # Si entras a Inventario, refrescamos la tabla automáticamente
    if page_object_name == "pageInventario":
        try:
            load_table_from_db(root)
        except Exception:
            pass
# ------------------------------------------------------------------

def _sync_nav_state(root):
    """Marca/desmarca y habilita/deshabilita los botones según la página actual."""
    try:
        stk = _get_stack(root)
        current = stk.currentWidget().objectName()
    except Exception:
        return

    # Busca tus botones por objectName (y también soporta QToolButton)
    def _find(name):
        return (root.findChild(QPushButton, name)
                or root.findChild(QToolButton, name))

    btnVentas = _find("btnVentas")
    btnInvent = _find("btnInventario")

    buttons = {"pageVentas": btnVentas, "pageInventario": btnInvent}

    # Reset: todos habilitados y sin check
    for b in buttons.values():
        if b:
            b.setCheckable(True)
            b.setChecked(False)
            b.setEnabled(True)

    # Activo: marcar y (opcional) deshabilitar para que se vea "inactivo"
    active = buttons.get(current)
    if active:
        active.setCheckable(True)
        active.setChecked(True)
        active.setEnabled(False)   # ← quita esta línea si NO quieres que se deshabilite


# --- helpers de modelo -------------------------------------------------------
def _build_model(parent=None):
    m = QStandardItemModel(0, 5, parent)
    m.setHorizontalHeaderLabels([
        "Código", "Descripción del producto",
        "Precio venta", "Existencias", "Inv. mínimo"
    ])
    return m

def _add_row(model: QStandardItemModel, row_tuple):
    c, d, precio, ex, minimo = row_tuple
    items = [
        QStandardItem(str(c)),
        QStandardItem(str(d)),
        QStandardItem(str(precio)),
        QStandardItem(str(ex)),
        QStandardItem(str(minimo)),
    ]
    for i in (2, 3, 4):
        items[i].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    model.appendRow(items)
# -----------------------------------------------------------------------------


def create_main_window(username="admin"):
    """Carga el .ui, prepara la QTableView y devuelve la ventana lista (vacía hasta cargar)."""
    w = load_ui("app/ui/InventarioBajo_window.ui")
    w.setWindowTitle(f"Ventas e Inventario - Santo Mardones — {username}")

    # 1) Tabla de la página Inventario
    tabla = w.findChild(QTableView, "tablaInventario")
    if tabla is None:
        raise RuntimeError("No encontré QTableView 'tablaInventario' en el .ui")

    # 2) Modelo + proxy
    model = _build_model(w)
    proxy = QSortFilterProxyModel(w)
    proxy.setSourceModel(model)
    proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
    proxy.setFilterKeyColumn(-1)  # todas las columnas
    tabla.setModel(proxy)

    # 3) Ajustes visuales
    tabla.setAlternatingRowColors(True)
    tabla.setSortingEnabled(True)
    tabla.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    tabla.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    tabla.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    h = tabla.horizontalHeader()
    h.setStretchLastSection(True)
    h.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    if model.columnCount() >= 5:
        tabla.setColumnWidth(0, 110)
        tabla.setColumnWidth(1, 360)

    # 4) Acciones de la toolbar
    actSalir = w.findChild(QAction, "actionSalir")
    if actSalir:
        actSalir.triggered.connect(w.close)

    actRefrescar = w.findChild(QAction, "actionRefrescar")
    if actRefrescar:
        actRefrescar.triggered.connect(lambda: _on_refresh(w))
    else:
        print("⚠️ No encontré 'actionRefrescar' en el .ui")

    # Agregar producto
    actAgregar = w.findChild(QAction, "actionAgregar")
    btnAgregar = w.findChild(QPushButton, "btnAgregar")
    def _on_saved():
        load_table_from_db(w)
        try:
            w.statusBar().showMessage("Producto agregado", 2000)
        except Exception:
            pass
    if actAgregar:
        actAgregar.triggered.connect(lambda: open_add_producto_dialog(w, on_saved=_on_saved, modal=False))
    if btnAgregar:
        btnAgregar.clicked.connect(lambda: open_add_producto_dialog(w, on_saved=_on_saved, modal=False))

    # 5) NAVEGACIÓN entre páginas (NUEVO)
    actVentas = w.findChild(QAction, "actionVentas")
    btnVentas = w.findChild(QPushButton, "btnVentas")
    if actVentas:
        actVentas.triggered.connect(lambda: _show_page(w, "pageVentas"))
    if btnVentas:
        btnVentas.clicked.connect(lambda: _show_page(w, "pageVentas"))

    actInventario = w.findChild(QAction, "actionInventario")
    btnInventario = w.findChild(QPushButton, "btnInventario")
    if actInventario:
        actInventario.triggered.connect(lambda: _show_page(w, "pageInventario"))
    if btnInventario:
        btnInventario.clicked.connect(lambda: _show_page(w, "pageInventario"))

    # 6) Referencias y página inicial
    w.tablaInventario = tabla
    w.modeloInventario = model
    w.proxyInventario = proxy

    # Página inicial: Inventario
    try:
        _show_page(w, "pageInventario")
    except Exception as e:
        print(e)
    finally:
        _sync_nav_state(w)   # ← para que arranque con el botón correcto marcado/inactivo

        # justo al final de create_main_window(...)

    try:
        _get_stack(w).currentChanged.connect(lambda _i: _sync_nav_state(w))
    except Exception:
        pass


    return w


def _on_refresh(window):
    load_table_from_db(window)
    try:
        window.statusBar().showMessage("Tabla actualizada", 2000)
    except Exception:
        pass


def replace_table_data(window, rows):
    m = getattr(window, "modeloInventario", None)
    if m is None:
        return
    m.removeRows(0, m.rowCount())
    for r in rows:
        _add_row(m, r)


def load_table_from_db(window):
    with SessionLocal() as s:
        rows = get_productos_bajo_inventario(s)
    replace_table_data(window, rows)
