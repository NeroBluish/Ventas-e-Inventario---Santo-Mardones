# app/ui/Inventario/inv_ajustes_page.py
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QMessageBox
)

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
    descEdit: QWidget          # QLineEdit | QTextEdit | QPlainTextEdit
    precioFld: QWidget         # QDoubleSpinBox | QSpinBox | QLineEdit
    existFld: QWidget          # QSpinBox | QLineEdit
    btnMod: QPushButton
    btnOtro: QPushButton
    codigo_actual: str | None = None


# --------- localizar widgets y construir vista ----------
def _build_view(root: QWidget) -> _View:
    page_inv = root.findChild(QWidget, "pageInventario")
    if not page_inv:
        raise RuntimeError("Falta 'pageInventario'")
    page = page_inv.findChild(QWidget, "pageInvAjustes")
    if not page:
        raise RuntimeError("Falta 'pageInvAjustes'")

    codigoEdit   = find_any(page, QLineEdit,  ["codigoInvEdit", "codigoEdit"])
    btnBuscar    = find_any(page, QPushButton,["btnBuscarProducto", "btnBuscar"], ["buscar producto", "buscar"])
    frameDetalle = find_any(page, QWidget,    ["frameDetalleInv", "frameDetalle"])

    # Campos de detalle (soporta variantes)
    descEdit  = (find_any(page, QLineEdit, ["descInvEdit","descripcionEdit"])
                 or find_any(page, QTextEdit, ["descInvEdit","descripcionEdit"])
                 or find_any(page, QPlainTextEdit, ["descInvEdit","descripcionEdit"]))
    precioFld = (find_any(page, QDoubleSpinBox, ["precioInvSpin","precioSpin"])
                 or find_any(page, QSpinBox, ["precioInvSpin","precioSpin"])
                 or find_any(page, QLineEdit, ["precioInvEdit","precioEdit"]))
    existFld  = (find_any(page, QSpinBox, ["existInvSpin","existenciasSpin"])
                 or find_any(page, QLineEdit, ["existInvEdit","existenciasEdit"]))

    btnMod  = find_any(page, QPushButton, ["btnModificar"], ["modificar"])
    btnOtro = find_any(page, QPushButton, ["btnOtro"], ["otro","nuevo","cancelar"])

    missing = []
    if not codigoEdit:   missing.append("QLineEdit código (codigoInvEdit)")
    if not btnBuscar:    missing.append("QPushButton buscar (btnBuscarProducto)")
    if not frameDetalle: missing.append("Contenedor detalle (frameDetalleInv)")
    if not descEdit:     missing.append("Descripción")
    if not precioFld:    missing.append("Precio")
    if not existFld:     missing.append("Existencias")
    if not btnMod:       missing.append("Modificar")
    if not btnOtro:      missing.append("Otro/Nuevo/Cancelar")
    if missing:
        raise RuntimeError("Faltan widgets en Ajustes: " + ", ".join(missing))

    return _View(
        page=page,
        codigoEdit=codigoEdit,
        btnBuscar=btnBuscar,
        frameDetalle=frameDetalle,
        descEdit=descEdit,
        precioFld=precioFld,
        existFld=existFld,
        btnMod=btnMod,
        btnOtro=btnOtro,
    )


# --------- lógica de la página ----------
def _show_detail(v: _View, show: bool):
    v.frameDetalle.setVisible(show)
    v.btnBuscar.setVisible(not show)
    v.codigoEdit.setReadOnly(show)
    if not show:
        v.codigoEdit.clear()
        v.codigoEdit.setFocus()

def _do_buscar(v: _View):
    code = text_get(v.codigoEdit)
    if not code:
        return
    with SessionLocal() as s:
        p = get_producto_por_codigo(s, code)
    if not p:
        QMessageBox.information(v.page, "No encontrado", f"Código '{code}' no existe.")
        return
    v.codigo_actual = p.codigo
    text_set(v.descEdit,  p.descripcion or "")
    num_set(v.precioFld,  int(p.precio_venta or 0))
    num_set(v.existFld,   int(p.existencias or 0))
    _show_detail(v, True)
    # deja la descripción seleccionada
    text_set(v.descEdit,  text_get(v.descEdit))

def _do_otro(v: _View):
    v.codigo_actual = None
    _show_detail(v, False)

def _do_modificar(v: _View):
    code = v.codigo_actual
    if not code:
        QMessageBox.warning(v.page, "Sin producto", "Primero busca un código válido.")
        return
    desc   = text_get(v.descEdit)
    precio = num_get(v.precioFld)
    exist  = num_get(v.existFld)
    try:
        with SessionLocal() as s, s.begin():
            p = update_producto(s, code, descripcion=desc, precio_venta=precio, existencias=exist)
            if not p:
                QMessageBox.warning(v.page, "No encontrado", f"Código '{code}' no existe.")
                return
    except Exception as e:
        QMessageBox.critical(v.page, "Error", f"No se pudo actualizar: {e}")
        return

    # Opcional: refresca la tabla de 'Bajo inventario' si esa subpágina está en uso.
    try:
        from app.ui.Inventario.inv_alertaStock_page import refresh_inv_alerta_stock
        refresh_inv_alerta_stock(v.page.window())  # root
    except Exception:
        pass

    QMessageBox.information(v.page, "Listo", "Producto actualizado.")
    _do_otro(v)


# --------- API pública de la página ----------
def init_inv_ajustes_page(root: QWidget):
    """Se llama una sola vez (lazy-init) desde el sub-router."""
    v = _build_view(root)

    # signals
    v.btnBuscar.clicked.connect(lambda: _do_buscar(v))
    v.codigoEdit.returnPressed.connect(lambda: _do_buscar(v))
    v.btnOtro.clicked.connect(lambda: _do_otro(v))
    v.btnMod.clicked.connect(lambda: _do_modificar(v))

    # estado inicial
    _show_detail(v, False)

    # guarda la vista para reuso (evita GC y rewire)
    v.page._aj_view = v


# ---------- wrapper de entrada para el sub-router ----------
from PySide6.QtWidgets import QWidget as _QW

def enter_inv_ajustes(root):
    """
    Llamar al entrar a pageInvAjustes:
      - Primera vez: init_inv_ajustes_page(root)
      - Reingresos: no requiere refresh (espera interacción del usuario)
    """
    page_inv = root.findChild(_QW, "pageInventario")
    if page_inv is None:
        return
    page = page_inv.findChild(_QW, "pageInvAjustes")
    if page is None:
        return
    if not getattr(page, "_inv_aj_inited", False):
        init_inv_ajustes_page(root)
        setattr(page, "_inv_aj_inited", True)
