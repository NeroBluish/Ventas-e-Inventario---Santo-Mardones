# app/ui/compras/com_ingresar_page.py

import uuid

from datetime import date
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QDateEdit, QPushButton, QTableView, QMessageBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from sqlalchemy import text

from app.core.db_local import SessionLocal
from app.core import repositories  # intentaremos usar crear_orden_compra_con_detalles si existe

from app.ui.a_py.ingresar_producto_dialog import open_ingresar_producto_dialog
from app.ui.a_py.modificar_producto_dialog import open_modificar_producto_dialog


COLS = ["Código", "Descripción", "Cant.", "P.Costo", "Subtotal"]

def _fmt_money(x: int | float) -> str:
    try:
        x = int(round(x))
    except Exception:
        pass
    return f"$ {x:,}".replace(",", ".")

def _new_model(parent=None):
    m = QStandardItemModel(0, len(COLS), parent)
    m.setHorizontalHeaderLabels(COLS)
    return m

class OrdenCache:
    """Cache de detalle en memoria."""
    def __init__(self):
        self.rows: list[dict] = []  # cada dict: {"codigo","descripcion","cantidad","precio_costo"}

    def clear(self):
        self.rows.clear()

    def total(self):
        return sum(int(r.get("cantidad", 0)) * int(r.get("precio_costo", 0)) for r in self.rows)

    def as_rows(self):
        for r in self.rows:
            yield (
                r.get("codigo", ""),
                r.get("descripcion", ""),
                int(r.get("cantidad", 0)),
                int(r.get("precio_costo", 0)),
            )

def enter_com_ingresar(root: QWidget):
    pagePro = root.findChild(QWidget, "pageCompras")
    page    = pagePro.findChild(QWidget, "pageComIng") if pagePro else None
    if not page:
        return
    if getattr(page, "_com_ing_inited", False):
        # Si ya está preparado, sólo repinta la tabla por si el cache cambió
        repaint = getattr(page, "_com_ing_repaint", None)
        if callable(repaint):
            repaint()
        return

    # -------- Widgets ----------
    folio_edit: QLineEdit      = page.findChild(QLineEdit,  "folioComNewEdit")
    fecha_edit: QDateEdit      = page.findChild(QDateEdit,  "fechaComNewDate")
    btn_ingresar: QPushButton  = page.findChild(QPushButton,"ingresarNewProComBtn")
    btn_modificar: QPushButton = page.findChild(QPushButton,"modificarNewProComBtn")
    btn_quitar: QPushButton    = page.findChild(QPushButton,"quitarNewProComBtn")
    table: QTableView          = page.findChild(QTableView, "productosNewtable")
    btn_guardar: QPushButton   = page.findChild(QPushButton,"guardarComNewBtn")
    btn_cancelar: QPushButton  = page.findChild(QPushButton,"cancelarComNewBtn")

    # -------- Estado & modelo ----------
    cache = OrdenCache()
    model = _new_model(page)
    if table:
        table.setModel(model)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    page._com_ing_cache = cache
    page._com_ing_model = model

    # -------- Helpers de UI ----------
    def repaint_table():
        m = page._com_ing_model
        m.removeRows(0, m.rowCount())
        for codigo, desc, cant, pcosto in cache.as_rows():
            subtotal = cant * pcosto
            cells = [
                QStandardItem(str(codigo)),
                QStandardItem(str(desc)),
                QStandardItem(str(cant)),
                QStandardItem(str(pcosto)),
                QStandardItem(str(subtotal)),
            ]
            for i in (2, 3, 4):
                cells[i].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            m.appendRow(cells)

    def reset_form():
        cache.clear()
        repaint_table()
        if folio_edit:
            folio_edit.clear()
            folio_edit.setFocus()
        if fecha_edit:
            # deja la fecha al día de hoy
            from PySide6.QtCore import QDate
            today = QDate.currentDate()
            fecha_edit.setDate(today)

    page._com_ing_repaint = repaint_table

        # -------- Ingresar / Modificar / Quitar ----------
    def _ingresar():
        def _take(_dlg, data):
            # data: id_detalle_orden, codigo, descripcion, cantidad, precio_costo
            cache.rows.append({
                "id_detalle_orden": data["id_detalle_orden"],  # ya viene generado en el diálogo
                "codigo": data["codigo"],
                "descripcion": data["descripcion"],
                "cantidad": int(data["cantidad"]),
                "precio_costo": int(data["precio_costo"]),
            })
            repaint_table()

        open_ingresar_producto_dialog(page, on_accept=_take, modal=True)

    # --- Utils selección ---
    def _selected_row_index():
        if not table:
            return None
        sel = table.selectionModel().selectedRows()
        if not sel:
            return None
        return sel[0].row()

    # --- Quitar fila seleccionada ---
    def _quitar():
        idx = _selected_row_index()
        if idx is None:
            QMessageBox.information(page, "Quitar", "Selecciona una fila del detalle.")
            return
        try:
            cache.rows.pop(idx)
        except Exception:
            return
        repaint_table()
        # re-selecciona fila anterior si existe
        if table and cache.rows:
            new_idx = max(0, idx-1)
            table.selectRow(new_idx)

    # --- Modificar fila seleccionada ---
    def _modificar():
        idx = _selected_row_index()
        if idx is None:
            QMessageBox.information(page, "Modificar", "Selecciona una fila del detalle.")
            return
        row = cache.rows[idx]
        def _take(_dlg, data):
            # conserva id_detalle_orden y codigo; actualiza cantidad, precio y descripción
            row["cantidad"] = int(data["cantidad"])
            row["precio_costo"] = int(data["precio_costo"])
            row["descripcion"] = data.get("descripcion", row.get("descripcion", ""))
            repaint_table()
            if table:
                table.selectRow(idx)  # deja seleccionada la misma fila
        open_modificar_producto_dialog(page, row, on_accept=_take, modal=True)

    # --- Conexiones ---
    if btn_ingresar:  btn_ingresar.clicked.connect(_ingresar)   # (ya lo tenías)
    if btn_modificar: btn_modificar.clicked.connect(_modificar)
    if btn_quitar:    btn_quitar.clicked.connect(_quitar)



    # -------- Guardar orden (cabecera + detalles) ----------
    def _guardar():
        folio = (folio_edit.text().strip() if folio_edit else "")
        if not folio:
            QMessageBox.warning(page, "Falta folio", "Ingresa el folio de la orden.")
            if folio_edit: folio_edit.setFocus()
            return

        if not cache.rows:
            QMessageBox.information(page, "Sin detalles", "Agrega productos al detalle antes de guardar.")
            return

        # Fecha (YYYY-MM-DD)
        if fecha_edit:
            qd = fecha_edit.date()
            fecha_llegada_str = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        else:
            from datetime import date
            fecha_llegada_str = str(date.today())

        try:
            with SessionLocal() as s, s.begin():
                # 0) Folio duplicado
                dup = s.execute(
                    text("SELECT 1 FROM ordenes_compra WHERE folio_orden = :f LIMIT 1"),
                    {"f": folio},
                ).first()
                if dup:
                    QMessageBox.warning(page, "Folio duplicado", f"Ya existe la orden {folio}.")
                    if folio_edit: folio_edit.setFocus(); folio_edit.selectAll()
                    return

                # 1) Intentar via repositorio
                created_via_repo = False
                oc_id = None
                try:
                    crear_fn = getattr(repositories, "crear_orden_compra_con_detalles", None)
                    if callable(crear_fn):
                        items = [
                            {
                                "codigo_producto": r.get("codigo"),
                                "cantidad":        int(r.get("cantidad", 0)),
                                "precio_unitario": int(r.get("precio_costo", 0)),
                                "descripcion":     r.get("descripcion", ""),
                            }
                            for r in cache.rows
                        ]
                        oc = crear_fn(
                            s,
                            folio_orden=folio,
                            fecha_llegada_orden=fecha_llegada_str,
                            detalle_items=items
                        )
                        created_via_repo = True
                        # si el repo devuelve la entidad, intenta leer su id (opcional)
                        try:
                            oc_id = getattr(oc, "id_ordenes_com", None)
                        except Exception:
                            oc_id = None
                except Exception as e:
                    QMessageBox.critical(page, "Error al guardar (repo)", str(e))
                    return

                # 2) Fallback SQL plano
                if not created_via_repo:
                    s.execute(
                        text("""
                            INSERT INTO ordenes_compra (folio_orden, fecha_llegada_orden, estado_orden)
                            VALUES (:folio, :fecha, 'pendiente')
                        """),
                        {"folio": folio, "fecha": fecha_llegada_str},
                    )
                    # id recién insertado en SQLite
                    oc_id = s.execute(text("SELECT last_insert_rowid()")).scalar_one()

                    for r in cache.rows:
                        s.execute(
                            text("""
                                INSERT INTO detalles_orden
                                (id_detalle_orden, orden_id, codigo_producto, cant_enorden, precio_unitario_orden, descripcion_enorden)
                                VALUES
                                (:id_det, :oc_id, :cod, :cant, :precio, :desc)
                            """),
                            {
                                "id_det": r.get("id_detalle_orden") or str(uuid.uuid4()),
                                "oc_id":  oc_id,
                                "cod":    r.get("codigo"),
                                "cant":   int(r.get("cantidad", 0)),
                                "precio": int(r.get("precio_costo", 0)),
                                "desc":   r.get("descripcion", ""),
                             },
                        )

            # Éxito
            msg = f"Orden {folio} registrada correctamente."
            if oc_id is not None:
                msg += f"\nID interno: {oc_id}"
            QMessageBox.information(page, "Orden guardada", msg)
            reset_form()

        except Exception as e:
            QMessageBox.critical(page, "Error al guardar", f"No se pudo guardar la orden:\n{e}")


    # -------- Cancelar (volver a estado inicial) ----------
    def _cancelar():
        reset_form()

    if btn_guardar:  btn_guardar.clicked.connect(_guardar)
    if btn_cancelar: btn_cancelar.clicked.connect(_cancelar)

    # Estado inicial
    reset_form()
    page._com_ing_inited = True
