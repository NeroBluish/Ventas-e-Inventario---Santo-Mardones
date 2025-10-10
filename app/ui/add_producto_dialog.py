# app/ui/add_producto_dialog.py
from app.ui.ui_runtime import load_ui
from PySide6.QtWidgets import (
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.db_local import SessionLocal
from app.core.repositories import insert_producto, update_producto, get_producto_por_codigo

def open_add_producto_dialog(parent=None, on_saved=None, modal=False):
    """
    Abre Agregar_Producto.ui.
    - modal=False -> ventana independiente (no bloquea y NO cierra la app al cerrarse).
    - modal=True  -> modal encima de la principal.
    """
    w = load_ui("app/ui/Agregar_Producto.ui")

    if modal:
        # Modal sobre la principal
        if parent is not None:
            w.setParent(parent)
        w.setWindowModality(Qt.ApplicationModal)
    else:
        # Ventana TOP-LEVEL independiente, pero asociada a la principal
        if parent is not None:
            w.setParent(parent)                     # mantenemos relación padre/hijo
        w.setWindowFlag(Qt.Window, True)            # que sea una ventana real
        w.setWindowModality(Qt.NonModal)            # no bloquear la principal
        w.setAttribute(Qt.WA_QuitOnClose, False)    # ¡cerrarla NO termina la app!
        w.setAttribute(Qt.WA_DeleteOnClose, True)   # liberar al cerrar

        # Mantener referencia para que el GC no la destruya antes de tiempo
        if parent is not None:
            if not hasattr(parent, "_child_windows"):
                parent._child_windows = []
            parent._child_windows.append(w)
            def _cleanup(_obj=None):
                try:
                    parent._child_windows.remove(w)
                except ValueError:
                    pass
            w.destroyed.connect(_cleanup)

    # ----- localizar widgets -----
    codigoEdit      = w.findChild(QLineEdit, "codigoEdit")
    descripcionEdit = w.findChild(QTextEdit, "descripcionEdit") or w.findChild(QPlainTextEdit, "descripcionEdit")
    precioSpin      = w.findChild(QDoubleSpinBox, "precioSpin") or w.findChild(QSpinBox, "precioSpin")
    existenciasSpin = w.findChild(QSpinBox, "existenciasSpin")
    minimoSpin      = w.findChild(QSpinBox, "minimoSpin")
    btnAgregar      = w.findChild(QPushButton, "btnAgregar")

    def _text(ed):
        if isinstance(ed, (QTextEdit, QPlainTextEdit)):
            return ed.toPlainText().strip()
        return ed.text().strip() if ed else ""

    def _num(sp):
        return int(sp.value()) if sp else 0

    def _guardar():
        codigo = _text(codigoEdit)
        descripcion = _text(descripcionEdit)
        precio = _num(precioSpin)
        exist  = _num(existenciasSpin)
        minimo = _num(minimoSpin)

        if not codigo or not descripcion:
            QMessageBox.warning(w, "Faltan datos", "Código y descripción son obligatorios.")
            return
        try:
            with SessionLocal() as s, s.begin():
                insert_producto(s, codigo, descripcion, precio, exist, minimo)
        except Exception as e:
            QMessageBox.critical(w, "Error", f"No se pudo guardar: {e}")
            return

        if callable(on_saved):
            on_saved()
        w.close()  # solo se cierra ESTA ventana

    if btnAgregar:
        btnAgregar.clicked.connect(_guardar)

    w.show()    # ¡NO usar exec()!
    return w
