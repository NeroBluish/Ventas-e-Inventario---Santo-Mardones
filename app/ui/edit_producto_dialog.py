from app.ui.ui_runtime import load_ui
from PySide6.QtWidgets import (
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.db_local import SessionLocal
from app.core.repositories import update_producto, get_producto_por_codigo


def open_edit_producto_dialog(parent=None, codigo: str | None = None, on_saved=None, modal=False):
    """
    Abre el formulario de producto para editar un producto existente (buscado por código).
    Cambia el texto del botón a "Guardar" y precarga los campos.
    """
    w = load_ui("app/ui/Agregar_Producto.ui")

    try:
        w.setWindowTitle("Editar producto")
    except Exception:
        pass

    codigoEdit      = w.findChild(QLineEdit, "codigoEdit")
    descripcionEdit = w.findChild(QTextEdit, "descripcionEdit") or w.findChild(QPlainTextEdit, "descripcionEdit")
    precioSpin      = w.findChild(QDoubleSpinBox, "precioSpin") or w.findChild(QSpinBox, "precioSpin")
    existenciasSpin = w.findChild(QSpinBox, "existenciasSpin")
    minimoSpin      = w.findChild(QSpinBox, "minimoSpin")
    btnAgregar      = w.findChild(QPushButton, "btnAgregar")
    if btnAgregar:
        btnAgregar.setText("Guardar")

    # Cargar datos actuales
    prod = None
    if codigo:
        with SessionLocal() as s:
            prod = get_producto_por_codigo(s, codigo)
    if not prod:
        QMessageBox.critical(parent or w, "Error", f"No se encontró el producto '{codigo}'.")
        w.close()
        return w

    # Precargar
    if codigoEdit:
        codigoEdit.setText(prod.codigo)
    if isinstance(descripcionEdit, (QTextEdit, QPlainTextEdit)):
        descripcionEdit.setPlainText(prod.descripcion)
    elif descripcionEdit:
        try:
            descripcionEdit.setText(prod.descripcion)
        except Exception:
            pass
    if precioSpin:
        try:
            precioSpin.setValue(float(prod.precio_venta))
        except Exception:
            precioSpin.setValue(int(prod.precio_venta or 0))
    if existenciasSpin:
        existenciasSpin.setValue(int(prod.existencias or 0))
    if minimoSpin:
        minimoSpin.setValue(int(prod.inv_minimo or 0))

    def _text(ed):
        if isinstance(ed, (QTextEdit, QPlainTextEdit)):
            return ed.toPlainText().strip()
        return ed.text().strip() if ed else ""

    def _num(sp):
        return int(sp.value()) if sp else 0

    def _guardar():
        new_codigo = _text(codigoEdit)
        descripcion = _text(descripcionEdit)
        precio = _num(precioSpin)
        exist  = _num(existenciasSpin)
        minimo = _num(minimoSpin)

        if not new_codigo or not descripcion:
            QMessageBox.warning(w, "Faltan datos", "Código y descripción son obligatorios.")
            return
        try:
            with SessionLocal() as s, s.begin():
                update_producto(
                    s,
                    prod.codigo,
                    codigo=new_codigo,
                    descripcion=descripcion,
                    precio_venta=precio,
                    existencias=exist,
                    inv_minimo=minimo,
                )
        except Exception as e:
            QMessageBox.critical(w, "Error", f"No se pudo guardar: {e}")
            return

        if callable(on_saved):
            on_saved()
        w.close()

    if btnAgregar:
        btnAgregar.clicked.connect(_guardar)

    if modal:
        w.setWindowModality(Qt.ApplicationModal)
    else:
        w.setWindowFlag(Qt.Window, True)
        w.setWindowModality(Qt.NonModal)
        w.setAttribute(Qt.WA_QuitOnClose, False)
        w.setAttribute(Qt.WA_DeleteOnClose, True)

        if parent is not None:
            w.setParent(parent)
            if not hasattr(parent, "_child_windows"):
                parent._child_windows = []
            parent._child_windows.append(w)
            def _cleanup(_obj=None):
                try:
                    parent._child_windows.remove(w)
                except ValueError:
                    pass
            w.destroyed.connect(_cleanup)

    w.show()
    return w

