# app/ui/Ventas/_Ventas_page.py
from PySide6.QtCore import Qt
import re
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QTableView, QLabel, QMessageBox

from app.ui.Ventas.varios_dialog import open_varios_dialog
from app.ui.Ventas.buscar_producto_dialog import open_buscar_producto_dialog

from app.core.db_local import SessionLocal
from app.core.repositories import get_producto_por_codigo, crear_boleta_con_detalles

IVA_RATE = 0.19                 
PRECIO_UNIT_INCLUYE_IVA = True   # True = P.Unit ya viene con IVA




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
    
    def remove(self, codigo: str, qty: int | None = None):
        """Elimina qty unidades del código; si qty es None o alcanza 0, borra toda la fila."""
        it = self.items.get(codigo)
        if not it:
            return
        if qty is None or qty >= it["cant"]:
            self.items.pop(codigo, None)
        else:
            it["cant"] -= qty
    
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
    lbl_iva  = page.findChild(QLabel, "lblIVA")
    lbl_neto = page.findChild(QLabel, "lblNeto")


    btn_del_row = page.findChild(QPushButton, "btnEliminarFila") \
              or page.findChild(QPushButton, "btnBorrarArt")   \
              or None  # (en tu UI el texto dice "Borrar Art.")

    # Botón para ELIMINAR TODO el ticket (el que está abajo a la derecha):
    btn_clear_all = page.findChild(QPushButton, "btnEliminarTicket") \
              or page.findChild(QPushButton, "btnEliminarTodo")  \
              or None  # si puedes, renómbralo a 'btnEliminarTicket'
    
    # buscar por nombre o por texto
    btn_buscar = page.findChild(QPushButton, "btnBuscar") \
            or page.findChild(QPushButton, "btnBuscarProducto") \
            or None
    
    # localizar el botón (por nombre o por texto)
    btn_varios = page.findChild(QPushButton, "btnINSVarios") \
           or page.findChild(QPushButton, "btnVarios")   \
           or None  # también lo encuentra por texto si quieres

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

    def _recalc():
        bruto = state.total()  # suma de (P.Unit * Cant) del carrito
        if PRECIO_UNIT_INCLUYE_IVA:
            neto = round(bruto / (1 + IVA_RATE))
            iva  = bruto - neto
            total = bruto
        else:
            neto = bruto
            iva  = round(neto * IVA_RATE)
            total = neto + iva
        
        # pinta labels
        if lbl_total:
            lbl_total.setText(_fmt_money(total))
        if lbl_iva:
            lbl_iva.setText(f"IVA: {_fmt_money(iva)}")
        if lbl_neto:
            lbl_neto.setText(f"Neto: {_fmt_money(neto)}")

    def _repaint():
        m = page._ventas_model
        m.removeRows(0, m.rowCount())
        for (codigo, desc, cant, punit) in state.as_rows():
            _add_row(m, codigo, desc, cant, punit)
        _recalc()

    def _remove_selected():
        sel = table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(page, "Eliminar", "Selecciona una fila del ticket.")
            return
        row = sel[0].row()
        code = model.item(row, 0).text()  # columna Código
        state.remove(code)                # borra toda la línea (puedes pasar qty=1 si quieres restar 1)
        _repaint()

    def _clear_all():
        if not state.items:
            return
        resp = QMessageBox.question(
            page, "Vaciar ticket", "¿Deseas eliminar TODOS los productos del ticket?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            state.clear()
            _repaint()

    def _open_buscar():
        open_buscar_producto_dialog(root, modal=True)  # modal y con parent; la X sólo cierra el diálogo

    def _open_varios():
        def _take(_dlg, data):
            code = data["codigo"]
            qty  = data["cantidad"]
            if not code:
                return
            # buscar el producto por código
            with SessionLocal() as s:
                p = get_producto_por_codigo(s, code)
            if not p:
                QMessageBox.information(page, "No encontrado", f"Código '{code}' no existe.")
                return
            # agregar al carrito y refrescar
            state.add(p.codigo, p.descripcion, int(p.precio_venta), cant=qty)
            _repaint()
        open_varios_dialog(root, on_accept=_take, modal=True)


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

    # Override: soporta cantidad en codigo (ABC*3, ABC x3)
    def _add_by_code():
        raw = (code_edit.text().strip() if code_edit else "")
        if not raw:
            return
        m = re.match(r"^\s*([^\s\*xX]+)\s*(?:[xX\*]\s*(\d+))?\s*$", raw)
        if not m:
            QMessageBox.information(page, "Formato no valido", "Usa: CODIGO o CODIGO*x (p.ej. ABC*3)")
            return
        code = m.group(1)
        try:
            qty = int(m.group(2) or 1)
        except ValueError:
            qty = 1
        if qty <= 0:
            QMessageBox.information(page, "Cantidad invalida", "La cantidad debe ser mayor que 0.")
            return
        with SessionLocal() as s:
            p = get_producto_por_codigo(s, code)
        if not p:
            QMessageBox.information(page, "No encontrado", f"Codigo '{code}' no existe.")
            return
        state.add(p.codigo, p.descripcion, int(p.precio_venta), cant=qty)
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
                total_val = int(boleta.total)
        except Exception as e:
            QMessageBox.critical(page, "Error al cobrar", str(e))
            return
        state.clear()
        _repaint()
        QMessageBox.information(page, "Venta registrada", f"Boleta {folio} guardada.\nTotal: {_fmt_money(total_val)}")

    # Enlaces
    if code_edit:
        code_edit.returnPressed.connect(_add_by_code)
    if btn_add:
        btn_add.clicked.connect(_add_by_code)
    if btn_cobrar:
        btn_cobrar.clicked.connect(_cobrar)
    if btn_del_row:
        btn_del_row.clicked.connect(_remove_selected)
    if btn_clear_all:
        btn_clear_all.clicked.connect(_clear_all)
    if btn_buscar:
        btn_buscar.clicked.connect(_open_buscar)
    if btn_varios:
        btn_varios.clicked.connect(_open_varios)

    # expone repaint para re-entrada desde el router
    page._ventas_repaint = _repaint
    # arranque
    _repaint()


# ---------- wrapper mínimo para el router ----------
from PySide6.QtWidgets import QWidget as _QW

def enter_ventas(root: QWidget):
    """
    Llamar al entrar a pageVentas:
      - Primera vez: init_ventas_page(...)
      - Siguientes:  repinta para reflejar el estado actual del carrito
    """
    page = root.findChild(_QW, "pageVentas")
    if page is None:
        return
    if not getattr(page, "_ventas_inited", False):
        init_ventas_page(root)
        setattr(page, "_ventas_inited", True)
    else:
        rep = getattr(page, "_ventas_repaint", None)
        if callable(rep):
            rep()

