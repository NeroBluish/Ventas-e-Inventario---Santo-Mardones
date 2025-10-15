# app/ui/compras/modificar_producto_dialog.py
from __future__ import annotations
import os
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtWidgets import (
    QDialog, QWidget, QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QMessageBox
)
from PySide6.QtUiTools import QUiLoader

from app.core.db_local import SessionLocal
from app.core.repositories import get_producto_por_codigo

_UI_RELATIVE_CANDIDATES = [
    "modificar_producto_dialog.ui",          # por si luego lo mueves acá
    "../a_ui/modificar_producto_dialog.ui",  # ubicación real del .ui
]

def _load_dialog_ui(parent: QWidget) -> QDialog:
    base_dir = os.path.dirname(__file__)
    loader = QUiLoader()
    last_err = None
    for rel in _UI_RELATIVE_CANDIDATES:
        path = os.path.normpath(os.path.join(base_dir, rel))
        if not os.path.exists(path):
            continue
        f = QFile(path)
        if not f.open(QIODevice.ReadOnly):
            last_err = f"No se pudo abrir: {path}"
            continue
        try:
            dlg = loader.load(f, parent)
            f.close()
            if isinstance(dlg, QDialog):
                return dlg
            d = QDialog(parent)
            dlg.setParent(d)
            return d
        except Exception as e:
            last_err = f"Error al cargar UI {path}: {e}"
        finally:
            try: f.close()
            except Exception: pass
    raise RuntimeError(last_err or "No se encontró el .ui de Modificar.")

def open_modificar_producto_dialog(
    parent: QWidget,
    item: dict,
    on_accept=None,
    modal=True,
):
    """
    item esperado:
      {"id_detalle_orden", "codigo", "descripcion", "cantidad", "precio_costo"}
    """
    dlg = _load_dialog_ui(parent)

    # Widgets por nombre
    lbl_cod:  QLabel          = dlg.findChild(QLabel, "codigoVenModLabel")
    lbl_desc: QLabel          = dlg.findChild(QLabel, "descripcionVenModLabel")
    sp_prec:  QDoubleSpinBox  = dlg.findChild(QDoubleSpinBox, "precioVenModSpin")
    sp_qty:   QSpinBox        = dlg.findChild(QSpinBox, "existenciasVenIModSpin") \
                             or dlg.findChild(QSpinBox, "existenciasVenModSpin")
    btn_ok:   QPushButton     = dlg.findChild(QPushButton, "agregarVenModBnt")

    # Prefill
    codigo = item.get("codigo", "")
    if lbl_cod:  lbl_cod.setText(str(codigo))
    desc = item.get("descripcion") or ""
    if not desc:
        # lookup por si el cache no tenía desc
        try:
            with SessionLocal() as s:
                p = get_producto_por_codigo(s, codigo)
            if p and p.descripcion:
                desc = p.descripcion
        except Exception:
            pass
    if lbl_desc: lbl_desc.setText(desc)

    if sp_qty:
        sp_qty.setMinimum(1)
        sp_qty.setValue(int(item.get("cantidad", 1)))
    if sp_prec:
        try: sp_prec.setDecimals(0)  # trabajamos en enteros
        except Exception: pass
        sp_prec.setMinimum(0)
        sp_prec.setValue(int(item.get("precio_costo", 0)))

    def _accept():
        qty = int(sp_qty.value()) if sp_qty else 1
        pc  = int(sp_prec.value()) if sp_prec else 0
        if qty <= 0:
            QMessageBox.warning(dlg, "Cantidad inválida", "Debe ser mayor que 0.")
            return
        if pc < 0:
            QMessageBox.warning(dlg, "Precio inválido", "No puede ser negativo.")
            return
        data = {
            "id_detalle_orden": item.get("id_detalle_orden"),
            "codigo": codigo,
            "descripcion": desc,
            "cantidad": qty,
            "precio_costo": pc,
        }
        if callable(on_accept):
            on_accept(dlg, data)
        dlg.accept()

    if btn_ok:
        btn_ok.clicked.connect(_accept)

    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
