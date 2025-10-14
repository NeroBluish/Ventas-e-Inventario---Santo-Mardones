# app/ui/productos/pro_catalogo_page.py
from PySide6.QtWidgets import QWidget, QComboBox, QTableView, QPushButton
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from sqlalchemy import select
from app.core.db_local import SessionLocal
from app.core.models import Producto
from app.ui.a_py.precios import calcular_precio_venta


COLS = [
    "Código", "Descripción",
    "Precio costo", "Precio venta", "% Impuesto",
    "Existencias", "Inv. mín.", "Inv. máx.",
    "Albergado"
]


# ---------------- helpers de búsqueda "tolerante" ----------------
def _find_any(parent: QWidget, klass, name_candidates=(), text_candidates=()):
    # por objectName (preferido)
    for n in name_candidates:
        w = parent.findChild(klass, n)
        if w:
            return w
    # si solo hay uno de ese tipo dentro del contenedor, úsalo
    lst = parent.findChildren(klass)
    return lst[0] if len(lst) == 1 else None
# -----------------------------------------------------------------


def _new_model(parent=None):
    m = QStandardItemModel(0, len(COLS), parent)
    m.setHorizontalHeaderLabels(COLS)
    return m


def _append_row(model: QStandardItemModel, p: Producto):
    vals = [
        p.codigo,
        p.descripcion or "",
        int(p.precio_costo or 0),
        int(p.precio_venta or 0),
        int(p.porcentaje_impuesto or 0),
        int(p.existencias or 0),
        int(p.inv_minimo or 0),
        int(p.inv_maximo or 0),
        str(p.albergado or "")
    ]
    items = [QStandardItem(str(v)) for v in vals]
    # Alinear números a la derecha
    for idx in (2, 3, 4, 5, 6, 7, 8):
        items[idx].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    model.appendRow(items)


def _load_rows_into(model: QStandardItemModel, filtro: str | None):
    """filtro: None = todos, 'catalogado', 'albergado y catalogado' (case-insensitive)."""
    model.removeRows(0, model.rowCount())
    with SessionLocal() as s:
        prods = s.execute(
            select(Producto).where(Producto.deleted_at.is_(None)).order_by(Producto.codigo.asc())
        ).scalars().all()

    fl = (filtro or "").strip().lower()
    for p in prods:
        alb = (p.albergado or "").strip().lower()
        if not fl or fl == "todos":
            pass  # sin filtro
        elif fl == "solo catalogados" or fl == "catalogados":
            if alb != "catalogado":
                continue
        elif fl == "albergados y catalogados":
            if alb != "albergado y catalogado":
                continue
        # (otros valores del campo albergado quedarán fuera por ahora)
        _append_row(model, p)


def enter_pro_catalogo(root: QWidget):
    """
    Inicializa la página 'pageProCatalogo' (una sola vez) y deja conectados:
      - Combo de filtro: 'Todos' | 'Solo catalogados' | 'Albergados y catalogados'
      - Botón Refrescar: recarga desde DB
    """
    pagePro = root.findChild(QWidget, "pageProductos")
    page    = pagePro.findChild(QWidget, "pageProCatalogo") if pagePro else None
    if not page:
        return

    if getattr(page, "_catalogo_inited", False):
        # ya inicializado → solo refresca
        _refresh(page)
        return

    # Widgets (si no tienen objectName, tomamos el único de su tipo en el contenedor)
    combo = _find_any(page, QComboBox, name_candidates=("comboFiltro", "cbFiltro", "comboBox"))
    table = _find_any(page, QTableView, name_candidates=("tablaCatalogo", "tableCatalogo", "tableView"))
    btn   = _find_any(page, QPushButton, name_candidates=("btnRefrescarCatalogo", "btnRefrescar", "btnActualizar"))

    if table is None:
        raise RuntimeError("No encontré el QTableView del catálogo (asigna objectName o deja uno solo en la página).")

    # Modelo
    model = _new_model(page)
    table.setModel(model)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)

    # Opciones del combo
    if combo:
        if combo.count() == 0:
            combo.addItems(["Todos", "Solo catalogados", "Albergados y catalogados"])
        combo.currentIndexChanged.connect(lambda _i: _refresh(page))

    # Botón refrescar
    if btn:
        btn.clicked.connect(lambda: _refresh(page))

    # guardar referencias en la página para futuros refresh
    page._catalogo_model = model
    page._catalogo_combo = combo

    # primera carga
    _refresh(page)
    setattr(page, "_catalogo_inited", True)


def _refresh(page: QWidget):
    """Recarga la tabla según el estado actual del combo."""
    model = getattr(page, "_catalogo_model", None)
    combo = getattr(page, "_catalogo_combo", None)
    if not model:
        return
    filtro = combo.currentText() if combo else "Todos"
    _load_rows_into(model, filtro=filtro)


# Para que el sub-router de Productos pueda pedir un refresh explícito:
def refresh_pro_catalogo(root: QWidget):
    pagePro = root.findChild(QWidget, "pageProductos")
    page    = pagePro.findChild(QWidget, "pageProCatalogo") if pagePro else None
    if not page:
        return
    if not getattr(page, "_catalogo_inited", False):
        enter_pro_catalogo(root)
    else:
        _refresh(page)
