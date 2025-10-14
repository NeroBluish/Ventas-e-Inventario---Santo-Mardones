# app/ui/Ventas/varios_dialog.py
from app.ui.a_py.ui_runtime import load_ui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QSpinBox, QPushButton

def open_varios_dialog(parent, on_accept=None, modal=True):
    dlg = load_ui("app/ui/a_ui/varios_dialog.ui")   # QDialog
    dlg.setAttribute(Qt.WA_DeleteOnClose, True)
    if isinstance(dlg, QDialog) and modal:
        dlg.setWindowModality(Qt.ApplicationModal)

    # widgets (tolerante a nombres si olvidaste alguno)
    code = dlg.findChild(QLineEdit, "codigoEditVarios") or dlg.findChildren(QLineEdit)[0]
    qty  = dlg.findChild(QSpinBox,  "cantidadSpin")     or dlg.findChildren(QSpinBox)[0]
    ok   = dlg.findChild(QPushButton, "btnAceptar")     or None
    cancel = dlg.findChild(QPushButton, "btnCancelar")  or None

    # Aceptar: devuelve {'codigo': str, 'cantidad': int}
    def _accept():
        data = {"codigo": (code.text().strip() if code else ""), "cantidad": int(qty.value()) if qty else 1}
        if on_accept:
            on_accept(dlg, data)
        if isinstance(dlg, QDialog):
            dlg.accept()
        else:
            dlg.close()

    # Cancelar/X: solo cierra el diálogo, la app sigue
    def _cancel():
        if isinstance(dlg, QDialog):
            dlg.reject()
        else:
            dlg.close()

    if ok:     ok.clicked.connect(_accept)
    if cancel: cancel.clicked.connect(_cancel)

    # Enter = aceptar, Esc = cancelar
    dlg.accepted.connect(lambda: None)
    dlg.rejected.connect(lambda: None)

    return dlg.exec() if modal else dlg.show()
