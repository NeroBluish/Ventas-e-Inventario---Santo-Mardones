# app/ui/Inventario/inv_agregar_page.py
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget, QLineEdit, QLabel, QPushButton, QSpinBox, QMessageBox

from app.core.db_local import SessionLocal
from app.core.repositories import get_producto_por_codigo, update_producto

from app.ui.a_py.ui_helpers import (
    find_any, text_get, text_set, num_get, num_set
)

@dataclass
class _View:
    page: QWidget
    codigoEdit: QLineEdit
    btnBuscar: QPushButton
    frameDetalle: QWidget
    lblDesc: QLabel
    lblHay: QLabel
    spinAgregar: QSpinBox
    btnAgregar: QPushButton
    btnOtro: QPushButton
    codigo_actual: str | None = None


# ---------- localizar widgets ----------
def _build_view(root: QWidget) -> _View:
    page_inv = root.findChild(QWidget, "pageInventario")
    if not page_inv:
        raise RuntimeError("Falta 'pageInventario'")
    page = page_inv.findChild(QWidget, "pageInvAgregar")
    if not page:
        raise RuntimeError("Falta 'pageInvAgregar'")

    codigoEdit   = find_any(page, QLineEdit,  ["codigoInvAgEdit", "codigoEdit"])
    btnBuscar    = find_any(page, QPushButton,["btnBuscarInvAg", "btnBuscar"], ["buscar producto", "buscar"])
    frameDetalle = find_any(page, QWidget,    ["frameDetalleInvAg", "frameDetalle"])

    lblDesc      = find_any(page, QLabel,     ["lblDescInvAg", "lblDescripcion"])
    lblHay       = find_any(page, QLabel,     ["lblHayInvAg", "lblHay"])
    spinAgregar  = find_any(page, QSpinBox,   ["spinAgregarInvAg", "spinAgregar"])
    btnAgregar   = find_any(page, QPushButton,["btnAgregarInv"], ["agregar a inventario", "agregar"])
    btnOtro      = find_any(page, QPushButton,["btnOtroInvAg"], ["otro", "nuevo", "cancelar"])

    missing = []
    if not codigoEdit:   missing.append("QLineEdit código (codigoInvAgEdit)")
    if not btnBuscar:    missing.append("QPushButton buscar (btnBuscarInvAg)")
    if not frameDetalle: missing.append("Contenedor detalle (frameDetalleInvAg)")
    if not lblDesc:      missing.append("Label descripción (lblDescInvAg)")
    if not lblHay:       missing.append("Label 'hay' (lblHayInvAg)")
    if not spinAgregar:  missing.append("Spin cantidad (spinAgregarInvAg)")
    if not btnAgregar:   missing.append("Botón Agregar (btnAgregarInv)")
    if not btnOtro:      missing.append("Botón Otro (btnOtroInvAg)")
    if missing:
        raise RuntimeError("Faltan widgets en Agregar: " + ", ".join(missing))

    # defaults
    try:
        spinAgregar.setMinimum(1)
        spinAgregar.setValue(1)
    except Exception:
        pass

    return _View(page, codigoEdit, btnBuscar, frameDetalle, lblDesc, lblHay,
                 spinAgregar, btnAgregar, btnOtro)


# ---------- lógica ----------
def _show_detail(v: _View, show: bool):
    v.frameDetalle.setVisible(show)
    v.btnBuscar.setVisible(not show)
    v.codigoEdit.setReadOnly(show)
    if not show:
        v.codigo_actual = None
        v.lblDesc.setText("")
        v.lblHay.setText("")
        try: v.spinAgregar.setValue(1)
        except Exception: pass
        v.codigoEdit.clear()
        v.codigoEdit.setFocus()

def _buscar(v: _View):
    code = text_get(v.codigoEdit)
    if not code:
        return
    with SessionLocal() as s:
        p = get_producto_por_codigo(s, code)
    if not p:
        QMessageBox.information(v.page, "No encontrado", f"Código '{code}' no existe.")
        return
    v.codigo_actual = p.codigo
    v.lblDesc.setText(p.descripcion or "")
    v.lblHay.setText(str(int(p.existencias or 0)))
    _show_detail(v, True)

def _agregar(v: _View):
    if not v.codigo_actual:
        QMessageBox.information(v.page, "Sin producto", "Busca un producto primero.")
        return
    qty = max(0, num_get(v.spinAgregar))
    if qty <= 0:
        QMessageBox.information(v.page, "Cantidad inválida", "Debe ser mayor que 0.")
        return
    # sumar existencias (existentes + qty)
    try:
        with SessionLocal() as s, s.begin():
            p = get_producto_por_codigo(s, v.codigo_actual)
            if not p:
                QMessageBox.warning(v.page, "No encontrado", f"Código '{v.codigo_actual}' ya no existe.")
                return
            nuevo = int(p.existencias or 0) + qty
            update_producto(s, v.codigo_actual, existencias=nuevo)
            # feedback en UI
            v.lblHay.setText(str(nuevo))
            try: v.spinAgregar.setValue(1)
            except Exception: pass
    except Exception as e:
        QMessageBox.critical(v.page, "Error", f"No se pudo agregar: {e}")
        return

    # refrescar tabla de "Alertas de stock" si está en uso
    try:
        from app.ui.Inventario.inv_alertaStock_page import refresh_inv_alerta_stock
        refresh_inv_alerta_stock(v.page.window())
    except Exception:
        pass

    QMessageBox.information(v.page, "Listo", "Existencias actualizadas.")

def _otro(v: _View):
    _show_detail(v, False)


# ---------- API pública ----------
def init_inv_agregar_page(root: QWidget):
    """Se llama una vez (lazy-init)."""
    v = _build_view(root)
    v.btnBuscar.clicked.connect(lambda: _buscar(v))
    v.codigoEdit.returnPressed.connect(lambda: _buscar(v))
    v.btnAgregar.clicked.connect(lambda: _agregar(v))
    v.btnOtro.clicked.connect(lambda: _otro(v))
    _show_detail(v, False)
    v.page._ag_view = v  # guarda vista para reuso


# Wrapper de entrada para el sub-router
from PySide6.QtWidgets import QWidget as _QW

def enter_inv_agregar(root):
    """
    Llamar al entrar a pageInvAgregar:
      - Primera vez: init_inv_agregar_page(root)
      - Reingresos: no requiere refresh (se espera interacción del usuario)
    """
    page_inv = root.findChild(_QW, "pageInventario")
    if page_inv is None:
        return
    page = page_inv.findChild(_QW, "pageInvAgregar")
    if page is None:
        return
    if not getattr(page, "_inv_ag_inited", False):
        init_inv_agregar_page(root)
        setattr(page, "_inv_ag_inited", True)
