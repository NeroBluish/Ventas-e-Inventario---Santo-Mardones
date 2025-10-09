# app/ui/ventas_controller.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QTableView, QLabel, QMessageBox

from app.core.db_local import SessionLocal
from app.core.repositories import get_producto_por_codigo, crear_boleta_con_detalles

COLS = ["Código", "Descripción", "Cant.", "P.Unit", "Importe"]

def _fmt_money(x: int) -> str:
    return f"$ {x:,}".replace(",", ".")

def _new_model(parent=None):
    m = QStandardItemModel(0, len(COLS), parent)
    m.setHorizontalHeaderLabels(COLS)
    return m

def _add_row(model: QStandardItemModel, codigo, desc, cant, punit):
    imp = cant * punit
    cells = [
        QStandardItem(str(codigo)),
        QStandardItem(str(desc)),
        QStandardItem(str(cant)),
        QStandardItem(str(punit)),
        QStandardItem(str(imp)),
    ]
    for i in (2,3,4):
        cells[i].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    model.appendRow(cells)

class VentasState:
    """Carrito en memoria: {codigo: {"desc", "precio_unit", "cant"}}"""
    def __init__(self):
        self.items = {}  # dict

    def add(self, codigo, desc, precio_unit, cant=1):
        it = self.items.get(codigo)
        if it:
            it["cant"] += cant
        else:
            self.items[codigo] = {"desc": desc, "precio_unit": precio_unit, "cant": cant}

    def clear(self):
        self.items.clear()

    def total(self):
        return sum(v["precio_unit"]*v["cant"] for v in self.items.values())

    def as_rows(self):
        # devuelve lista para la tabla
        out = []
        for cod, v in self.items.items():
            out.append((cod, v["desc"], v["cant"], v["precio_unit"]))
        return out
    
def _find_any(parent, cls, names):
    """Busca por nombre dentro de parent; si no, toma el ÚNICO del tipo cls en toda la subjerarquía."""
    for n in names:
        w = parent.findChild(cls, n)
        if w:
            return w
    lst = parent.findChildren(cls)  # recursivo
    return lst[0] if len(lst) == 1 else None

def init_ventas_page(root: QWidget):
    """
    Prepara la pageVentas dentro del MainWindow (cargado desde .ui).
    Requiere en el .ui (pageVentas):
      - codigoEdit (QLineEdit)
      - btnAgregarTicket (QPushButton)
      - tablaTicket (QTableView)
      - lblTotal (QLabel)
      - btnCobrar (QPushButton)
    """
    page = root.findChild(QWidget, "pageVentas")
    if page is None:
        raise RuntimeError("No existe pageVentas en el stack")

    # Widgets dentro de pageVentas (tolera TabWidget/frames)
    code_edit  = _find_any(page, QLineEdit,  ["codigoEdit"])
    btn_add    = _find_any(page, QPushButton,["btnAgregarTicket","btnAgregar"])
    table      = _find_any(page, QTableView, ["tablaTicket","tablaVentas","tableView"])
    lbl_total  = _find_any(page, QLabel,     ["lblTotal","total"])
    btn_cobrar = _find_any(page, QPushButton,["btnCobrar","cobrar"])

    missing = []
    if table is None:      missing.append("QTableView (ej. 'tablaTicket')")
    if code_edit is None:  missing.append("QLineEdit código (ej. 'codigoEdit')")
    if btn_add is None:    missing.append("QPushButton agregar (ej. 'btnAgregarTicket')")
    if btn_cobrar is None: missing.append("QPushButton cobrar (ej. 'btnCobrar')")
    if missing:
        raise RuntimeError("Faltan widgets en pageVentas: " + ", ".join(missing))

    # Estado (carrito) + modelo tabla
    state = VentasState()
    model = _new_model(page)
    table.setModel(model)
    table.horizontalHeader().setStretchLastSection(True)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(False)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    page._ventas_state = state
    page._ventas_model = model

    def _repaint():
        # repinta tabla desde el carrito
        m = page._ventas_model
        m.removeRows(0, m.rowCount())
        for (codigo, desc, cant, punit) in state.as_rows():
            _add_row(m, codigo, desc, cant, punit)
        if lbl_total:
            lbl_total.setText(_fmt_money(state.total()))

    def _add_by_code():
        code = (code_edit.text().strip() if code_edit else "")
        if not code:
            return
        with SessionLocal() as s:
            p = get_producto_por_codigo(s, code)
        if not p:
            QMessageBox.information(page, "No encontrado", f"Código '{code}' no existe.")
            return
        state.add(p.codigo, p.descripcion, int(p.precio_venta), cant=1)
        _repaint()
        if code_edit:
            code_edit.clear()
            code_edit.setFocus()

    def _cobrar():
        if not state.items:
            QMessageBox.information(page, "Carrito vacío", "Agrega productos antes de cobrar.")
            return
        items = [
            {
                "codigo": cod,
                "descripcion": v["desc"],
                "precio_unit": v["precio_unit"],
                "cantidad": v["cant"],
            }
            for cod, v in state.items.items()
        ]
        try:
            with SessionLocal() as s, s.begin():
                boleta = crear_boleta_con_detalles(s, items)
                folio = boleta.folio
        except Exception as e:
            QMessageBox.critical(page, "Error al cobrar", str(e))
            return
        state.clear()
        _repaint()
        QMessageBox.information(page, "Venta registrada", f"Boleta {folio} guardada.\nTotal: {_fmt_money(boleta.total)}")

    # Enlaces
    if code_edit:
        code_edit.returnPressed.connect(_add_by_code)
    if btn_add:
        btn_add.clicked.connect(_add_by_code)
    if btn_cobrar:
        btn_cobrar.clicked.connect(_cobrar)

    # arranque
    _repaint()
