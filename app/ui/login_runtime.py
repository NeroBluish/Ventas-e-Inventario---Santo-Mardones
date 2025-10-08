# app/ui/login_runtime.py
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QCheckBox
from app.ui.ui_runtime import load_ui

def create_login_dialog():
    # Asegúrate de que el formulario raíz en Designer sea un QDialog
    dlg = load_ui("app/ui/login.ui")  # devuelve un QDialog si el .ui es un Dialog

    # Busca los widgets por objectName (puestos en Designer)
    user_edit = dlg.findChild(QLineEdit, "usernameEdit")
    pass_edit = dlg.findChild(QLineEdit, "passwordEdit")
    status_lbl = dlg.findChild(QLabel, "statusLabel")
    btn_login  = dlg.findChild(QPushButton, "loginBtn")


    # Lógica de validación
    def try_login():
        u = (user_edit.text() if user_edit else "").strip()
        p =  pass_edit.text() if pass_edit else ""
        if u == "admin" and p == "1212":
            dlg.accept()
        else:
            if status_lbl:
                status_lbl.setText("Usuario o contraseña incorrectos")

    # Conexiones
    if btn_login:
        btn_login.clicked.connect(try_login)
    if user_edit:
        user_edit.returnPressed.connect(try_login)   # Enter para aceptar
    if pass_edit:
        pass_edit.returnPressed.connect(try_login)
 

    return dlg
