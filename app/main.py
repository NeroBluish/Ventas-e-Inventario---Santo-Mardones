#app/main.py
import sys
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

# Importa los recursos compilados (activa rutas :/…)
import assets.imagenes  # registra QResource para :/png/...

from app.core.db_local import init_db
from app.ui.main_window import create_main_window
from app.ui.a_py.login_runtime import create_login_dialog

def main():
    init_db()
    app = QApplication(sys.argv)

    # 1) Mostrar login
    login = create_login_dialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    # 2) Abrir MainWindow
    username = login.findChild(QLineEdit, "usernameEdit").text().strip() if login else "admin"
    w = create_main_window(username="admin")
    w.show()
    app.exec()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
