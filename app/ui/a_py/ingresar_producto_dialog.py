# app/ui/compras/ingresar_producto_dialog.py

from __future__ import annotations
import os, uuid
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtWidgets import QDialog, QWidget, QLineEdit, QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QMessageBox
from PySide6.QtUiTools import QUiLoader

from app.core.db_local import SessionLocal
from app.core.repositories import get_producto_por_codigo


# NOTA: el .ui vive en app/ui/a_ui/ingresar_prodructo_dialog.ui (con 'prodructo')
_UI_RELATIVE_CANDIDATES = [
    "ingresar_prodructo_dialog.ui",        # mismo directorio (por si lo mueves acá)
    "../a_ui/ingresar_prodructo_dialog.ui",# ruta real en tu proyecto
    "../a_ui/ingresar_producto_dialog.ui", # fallback si alguna vez corriges la ortografía
]

def _load_dialog_ui(parent: QWidget) -> QDialog:
    base_dir = os.path.dirname(__file__)
    loader = QUiLoader()
    tried = []
    last_err = None

    for rel in _UI_RELATIVE_CANDIDATES:
        ui_path = os.path.normpath(os.path.join(base_dir, rel))
        tried.append(ui_path)
        if not os.path.exists(ui_path):
            continue
        f = QFile(ui_path)
        if not f.open(QIODevice.ReadOnly):
            last_err = f"No se pudo abrir: {ui_path}"
            continue
        try:
            dlg = loader.load(f, parent)
            f.close()
            if isinstance(dlg, QDialog):
                return dlg
            # si el root del .ui no es QDialog, lo envolvemos
            wrapper = QDialog(parent)
            dlg.setParent(wrapper)
            return wrapper
        except Exception as e:
            last_err = f"Error al cargar UI {ui_path}: {e}"
        finally:
            try:
                f.close()
            except Exception:
                pass

    # si no encontramos nada, mostramos qué rutas probamos
    details = "\n - " + "\n - ".join(tried) if tried else ""
    raise RuntimeError((last_err or "No se encontró el archivo .ui del diálogo de ingreso.") + details)

def open_ingresar_producto_dialog(parent: QWidget, on_accept=None, modal=True):
    """
    Abre el diálogo para ingresar un producto a la orden de compra.
    on_accept(dlg, data_dict) será llamado al presionar 'Agregar' si los datos son válidos.

    data_dict = {
        "id_detalle_orden": str(uuid),
        "codigo": str,
        "descripcion": str,
        "cantidad": int,
        "precio_costo": int,
    }
    """
    dlg = _load_dialog_ui(parent)

    # Widgets según nombres dados
    codigo_edit: QLineEdit            = dlg.findChild(QLineEdit, "codigoVenIngEdit")
    desc_label: QLabel                = dlg.findChild(QLabel, "descripcionVenIngLabel")
    precio_spin: QDoubleSpinBox       = dlg.findChild(QDoubleSpinBox, "precioVenIngSpin")
    exist_spin: QSpinBox              = dlg.findChild(QSpinBox, "existenciasVenIngSpin")
    btn_agregar: QPushButton          = dlg.findChild(QPushButton, "agregarVenIngBnt")

    # Defaults
    if exist_spin:
        exist_spin.setMinimum(1)
        if exist_spin.value() <= 0:
            exist_spin.setValue(1)
    if precio_spin:
        # trabajas en pesos enteros; dejamos 0 decimales por si acaso
        try:
            precio_spin.setDecimals(0)
        except Exception:
            pass
        if precio_spin.value() < 0:
            precio_spin.setValue(0)

    def _lookup_and_fill():
        """Busca el producto por código; si existe, llena descripción y precio costo por defecto."""
        code = (codigo_edit.text().strip() if codigo_edit else "")
        if not code:
            if desc_label: desc_label.setText("")
            return
        with SessionLocal() as s:
            p = get_producto_por_codigo(s, code)
        if not p:
            if desc_label: desc_label.setText("No encontrado")
            # no tocamos el precio si no existe
            return
        if desc_label:
            desc_label.setText(p.descripcion or "")
        if precio_spin:
            try:
                precio_spin.setValue(int(p.precio_costo or 0))
            except Exception:
                precio_spin.setValue(0)

    def _accept():
        code = (codigo_edit.text().strip() if codigo_edit else "")
        if not code:
            QMessageBox.warning(dlg, "Falta código", "Ingresa un código de producto.")
            if codigo_edit: codigo_edit.setFocus()
            return

        # confirmar que exista en BD
        with SessionLocal() as s:
            p = get_producto_por_codigo(s, code)
        if not p:
            QMessageBox.warning(dlg, "No encontrado", f"Código “{code}” no existe.")
            if codigo_edit:
                codigo_edit.setFocus()
                codigo_edit.selectAll()
            return

        qty = int(exist_spin.value()) if exist_spin else 1
        if qty <= 0:
            QMessageBox.warning(dlg, "Cantidad inválida", "La cantidad debe ser mayor que 0.")
            if exist_spin: exist_spin.setFocus()
            return

        pc = int(precio_spin.value()) if precio_spin else int(p.precio_costo or 0)
        if pc < 0:
            QMessageBox.warning(dlg, "Precio inválido", "El precio de costo no puede ser negativo.")
            if precio_spin: precio_spin.setFocus()
            return

        data = {
            "id_detalle_orden": str(uuid.uuid4()),
            "codigo": code,
            "descripcion": p.descripcion or "",
            "cantidad": qty,
            "precio_costo": pc,
        }
        if callable(on_accept):
            on_accept(dlg, data)
        dlg.accept()

    # Conexiones
    if codigo_edit:
        codigo_edit.editingFinished.connect(_lookup_and_fill)
        codigo_edit.returnPressed.connect(_lookup_and_fill)
    if btn_agregar:
        btn_agregar.clicked.connect(_accept)

    # Mostrar
    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
