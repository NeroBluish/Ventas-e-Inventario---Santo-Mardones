# app/ui/inventario_bajo_from_ui.py
from app.ui.ui_runtime import load_ui  # QUiLoader helper
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QTableView
from PySide6.QtCore import Qt, QSortFilterProxyModel

# --- DB imports ---
from app.core.db_local import SessionLocal
from app.core.repositories import get_productos_bajo_inventario
# ------------------

# --- helpers de modelo -------------------------------------------------------
def _build_model(parent=None):
    m = QStandardItemModel(0, 5, parent)
    m.setHorizontalHeaderLabels([
        "Código", "Descripción del producto",
        "Precio venta", "Existencias", "Inv. mínimo"
    ])
    return m

def _add_row(model: QStandardItemModel, row_tuple):
    # row_tuple = (codigo, descripcion, precio_venta, existencias, inv_minimo)
    c, d, precio, ex, minimo = row_tuple
    items = [
        QStandardItem(str(c)),
        QStandardItem(str(d)),
        QStandardItem(str(precio)),   # si quieres formato miles, te doy abajo
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

    # 1) Encontrar la tabla por objectName
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

    # 4) Acciones de la toolbar (opcional)
    actSalir = w.findChild(QAction, "actionSalir")
    if actSalir:
        actSalir.triggered.connect(w.close)

    # 5) Referencias para recargar luego
    w.tablaInventario = tabla
    w.modeloInventario = model
    w.proxyInventario = proxy

    return w


def replace_table_data(window, rows):
    """rows: iterable de tuplas (codigo, descripcion, precio_venta, existencias, inv_minimo)."""
    m = getattr(window, "modeloInventario", None)
    if m is None:
        return
    m.removeRows(0, m.rowCount())
    for r in rows:
        _add_row(m, r)


def load_table_from_db(window):
    """Carga datos reales (existencias < inv_minimo). Si no hay, la tabla queda vacía."""
    with SessionLocal() as s:
        rows = get_productos_bajo_inventario(s)
    replace_table_data(window, rows)
