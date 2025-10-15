# app/ui/compras/com_lis_page.py
from __future__ import annotations
from datetime import date, timedelta
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PySide6.QtWidgets import QWidget, QComboBox, QDateEdit, QTableView, QPushButton, QMessageBox
from sqlalchemy import text

from app.core.db_local import SessionLocal

COLS = ["Estado", "Folio", "Fecha llegada", "Detalles", "Total"]

def _fmt_money(x: int | float) -> str:
    try:
        x = int(round(x))
    except Exception:
        pass
    return f"{x:,}".replace(",", ".")

def _estado_color(estado: str) -> QBrush | None:
    est = (estado or "").strip().lower()
    if "pend" in est:
        return QBrush(QColor("#d9ecff"))  # azul pastel
    if "cerr" in est:
        return QBrush(QColor("#eeeeee"))  # gris claro
    return None

def _new_model(parent=None):
    m = QStandardItemModel(0, len(COLS), parent)
    m.setHorizontalHeaderLabels(COLS)
    return m

def enter_com_listar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageCompras")
    page    = pagePro.findChild(QWidget, "pageComLis") if pagePro else None
    if not page:
        return

    # Re-entrada: si ya está inicializado, solo refresca
    if getattr(page, "_com_lis_inited", False):
        rep = getattr(page, "_com_lis_reload", None)
        if callable(rep):
            rep()
        return

    # ---- Widgets ----
    combo_estado: QComboBox   = page.findChild(QComboBox,  "filtroestadoComLisCombo")
    date_desde:   QDateEdit   = page.findChild(QDateEdit,  "fechadesdeComLisDate")
    date_hasta:   QDateEdit   = page.findChild(QDateEdit,  "fechahastaComLisDate")
    table:        QTableView  = page.findChild(QTableView, "ordenesComLisTable")
    btn_refresh:  QPushButton = page.findChild(QPushButton,"refrescarComLisBtn")

    # ---- Modelo / tabla ----
    model = _new_model(page)
    if table:
        table.setModel(model)
        table.setWordWrap(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    page._com_lis_model = model

    # ---- Filtros por defecto (hoy ± 14 días) ----
    today = QDate.currentDate()
    if date_desde:
        date_desde.setDate(today.addDays(-14))
    if date_hasta:
        date_hasta.setDate(today.addDays(+14))

    # ---- Helpers ----
    def _estado_filtro() -> str:
        """Devuelve 'pendiente' | 'cerrado' | 'todos' según el texto del combo."""
        if not combo_estado:
            return "todos"
        t = (combo_estado.currentText() or "").lower()
        if "pend" in t:
            return "pendiente"
        if "cerr" in t:
            return "cerrado"
        return "todos"

    def _dates_range():
        """Devuelve (YYYY-MM-DD, YYYY-MM-DD)."""
        if date_desde:
            d1 = date_desde.date()
            desde = f"{d1.year():04d}-{d1.month():02d}-{d1.day():02d}"
        else:
            desde = str(date.today() - timedelta(days=14))
        if date_hasta:
            d2 = date_hasta.date()
            hasta = f"{d2.year():04d}-{d2.month():02d}-{d2.day():02d}"
        else:
            hasta = str(date.today() + timedelta(days=14))
        return desde, hasta

    def _fetch_and_fill():
        m = page._com_lis_model
        m.removeRows(0, m.rowCount())
        filtro = _estado_filtro()
        desde, hasta = _dates_range()

        try:
            with SessionLocal() as s:
                # 1) Traer cabeceras dentro del rango
                params = {"desde": desde, "hasta": hasta}
                sql = """
                    SELECT id_ordenes_com, folio_orden, fecha_llegada_orden, estado_orden
                    FROM ordenes_compra
                    WHERE fecha_llegada_orden >= :desde AND fecha_llegada_orden <= :hasta
                """
                if filtro != "todos":
                    sql += " AND estado_orden = :estado"
                    params["estado"] = filtro
                sql += " ORDER BY fecha_llegada_orden DESC, folio_orden ASC"
                cabeceras = s.execute(text(sql), params).fetchall()

                # 2) Por cada orden, traer sus detalles y armar filas
                for (oc_id, folio, fecha_lleg, estado) in cabeceras:
                    dets = s.execute(
                        text("""
                            SELECT id_detalle_orden, codigo_producto, cant_enorden, precio_unitario_orden, descripcion_enorden
                            FROM detalles_orden
                            WHERE orden_id = :oid
                            ORDER BY rowid ASC
                        """),
                        {"oid": oc_id},
                    ).fetchall()

                    # Construir texto de detalles y total
                    total = 0
                    lines = []
                    for (_id, cod, cant, precio, desc) in dets:
                        subtotal = int(cant) * int(precio)
                        total += subtotal
                        line = f"{cod} | {desc or ''} | Cant: {cant} | Cost/Cdu: {_fmt_money(precio)} | SubTotal:{_fmt_money(subtotal)}"
                        lines.append(line)
                    detalles_txt = "\n".join(lines) if lines else "(sin detalles)"

                    # Celdas
                    it_estado = QStandardItem(str(estado or ""))
                    col = _estado_color(estado)
                    if col:
                        it_estado.setBackground(col)
                    it_estado.setTextAlignment(Qt.AlignCenter)

                    it_folio  = QStandardItem(str(folio))
                    it_fecha  = QStandardItem(str(fecha_lleg))
                    it_det    = QStandardItem(detalles_txt)
                    it_total  = QStandardItem(_fmt_money(total))
                    it_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                    m.appendRow([it_estado, it_folio, it_fecha, it_det, it_total])

            # ajustar tamaños para mostrar multilinea
            if table:
                table.resizeColumnsToContents()
                table.resizeRowsToContents()

        except Exception as e:
            QMessageBox.critical(page, "Error", f"No se pudo listar órdenes:\n{e}")

    # Exponer para re-entradas
    page._com_lis_reload = _fetch_and_fill

    # ---- Conexiones (refrescan al mover filtros) ----
    if combo_estado:
        combo_estado.currentIndexChanged.connect(_fetch_and_fill)
    if date_desde:
        date_desde.dateChanged.connect(_fetch_and_fill)
    if date_hasta:
        date_hasta.dateChanged.connect(_fetch_and_fill)
    if btn_refresh:
        btn_refresh.clicked.connect(_fetch_and_fill)

    # ---- Carga inicial ----
    _fetch_and_fill()
    page._com_lis_inited = True
