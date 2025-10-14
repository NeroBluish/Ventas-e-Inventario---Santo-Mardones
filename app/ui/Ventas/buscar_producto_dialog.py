# app/ui/Ventas/buscar_producto_dialog.py
from app.ui.a_py.ui_runtime import load_ui
from app.core.db_local import SessionLocal
from app.core.models import Producto
from sqlalchemy import select

from PySide6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QDialog, QLineEdit, QTableView, QPushButton

COLUMNS = ["Código", "Descripción", "Precio", "Existencias"]

def _build_model(parent=None):
    m = QStandardItemModel(0, len(COLUMNS), parent)
    m.setHorizontalHeaderLabels(COLUMNS)
    return m

def _row(items):
    for i in (2, 3):  # números a la derecha
        items[i].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return items

def _load_products(model: QStandardItemModel):
    model.removeRows(0, model.rowCount())
    with SessionLocal() as s:
        rows = s.execute(
            select(Producto.codigo, Producto.descripcion, Producto.precio_venta, Producto.existencias)
            .where(Producto.deleted_at.is_(None))
            .order_by(Producto.descripcion.asc())
        ).all()
    for cod, desc, precio, ex in rows:
        model.appendRow(_row([
            QStandardItem(str(cod or "")),
            QStandardItem(str(desc or "")),
            QStandardItem(str(int(precio or 0))),
            QStandardItem(str(int(ex or 0))),
        ]))

def open_buscar_producto_dialog(parent, on_accept=None, modal=True):
    dlg = load_ui("app/ui/a_ui/buscar_producto_dialog.ui")  # <-- QDialog en el .ui
    if isinstance(dlg, QDialog) and modal:
        dlg.setWindowModality(Qt.ApplicationModal)

    # Widgets del diálogo (usa estos objectName en el .ui)
    search: QLineEdit  = dlg.findChild(QLineEdit,  "searchEdit")    or dlg.findChildren(QLineEdit)[0]
    table:  QTableView = dlg.findChild(QTableView, "resultadosView") or dlg.findChildren(QTableView)[0]
    btn_ok: QPushButton = dlg.findChild(QPushButton, "btnAceptar")

    # Estilos de selección más legibles
    table.setStyleSheet("""
    QTableView::item:selected            { background: #2d6cdf; color: white; }   /* activa */
    QTableView::item:selected:!active    { background: #cfe0ff; color: #111; }    /* ventana sin foco */
    QHeaderView::section                 { background: #f3f3f3; font-weight: 600; }
    QTableView                           { gridline-color: #ddd; }
    """)


    # Modelo + proxy (filtro por prefijo en la columna Descripción = 1)
    model = _build_model(dlg)
    _load_products(model)

    proxy = QSortFilterProxyModel(dlg)
    proxy.setSourceModel(model)
    proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
    proxy.setFilterKeyColumn(1)  # Descripción
    table.setModel(proxy)

    # Tabla más cómoda
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSortingEnabled(True)
    table.sortByColumn(1, Qt.AscendingOrder)

    # Filtro en vivo por PREFIJO de la descripción
    def _apply_filter(text: str):
        # ^texto  => empieza con 'texto'
        rx = QRegularExpression("^" + QRegularExpression.escape(text))
        proxy.setFilterRegularExpression(rx)
        # opcional: seleccionar la primera fila visible
        if proxy.rowCount() > 0:
            table.selectRow(0)

    search.textChanged.connect(_apply_filter)
    search.setFocus()

    # Aceptar (opcionalmente devuelve el producto seleccionado)
    def _accept_selected():
        if on_accept:
            idx = table.currentIndex()
            if idx.isValid():
                src_row = proxy.mapToSource(idx).row()
                data = {
                    "codigo": model.item(src_row, 0).text(),
                    "descripcion": model.item(src_row, 1).text(),
                    "precio": int(model.item(src_row, 2).text()),
                    "existencias": int(model.item(src_row, 3).text()),
                }
                on_accept(dlg, data)
        if isinstance(dlg, QDialog):
            dlg.accept()
        else:
            dlg.close()

    if btn_ok:
        btn_ok.clicked.connect(_accept_selected)

    # Doble click en la tabla también acepta
    table.doubleClicked.connect(lambda _idx: _accept_selected())

    # Mostrar
    return dlg.exec() if modal else dlg.show()
