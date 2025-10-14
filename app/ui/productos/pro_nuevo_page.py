# app/ui/productos/pro_nuevo_page.py

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QMessageBox
from PySide6.QtCore import QObject
from sqlalchemy import text
from app.core.db_local import SessionLocal
from app.core import repositories  # para insert_producto
from app.ui.a_py.precios import calcular_precio_venta, calc_ganancia_pct_desde_pv
from app.ui.a_py.ui_helpers import signals_blocked

IVA_DEFAULT = 19.0  # IVA Chile

def enter_pro_nuevo(root: QWidget):
    pagePro = root.findChild(QWidget, "pageProductos")
    page    = pagePro.findChild(QWidget, "pageProNuevo") if pagePro else None
    if not page:
        return
    if getattr(page, "_pro_nuevo_setup_done", False):
        return

    # --- Widgets ---
    codigo: QLineEdit            = page.findChild(QLineEdit, "codigoProNewEdit")
    descripcion: QLineEdit       = page.findChild(QLineEdit, "descripcionProNewEdit")
    costo: QDoubleSpinBox        = page.findChild(QDoubleSpinBox, "costoProNewSpin")
    ganancia: QDoubleSpinBox     = page.findChild(QDoubleSpinBox, "gananciaProNewSpin")      
    impuesto: QDoubleSpinBox     = page.findChild(QDoubleSpinBox, "impuestoProNewSpin")        
    precio_venta: QDoubleSpinBox = page.findChild(QDoubleSpinBox, "precioProNewSpin")
    albergado: QComboBox         = page.findChild(QComboBox, "albergadoProNewCombo")
    hay: QSpinBox                = page.findChild(QSpinBox, "hayProNewSpin")
    min_ini: QSpinBox            = page.findChild(QSpinBox, "minIniProNewSpin")
    max_ini: QSpinBox            = page.findChild(QSpinBox, "maxIniProNewSpin") 
    btn_guardar: QPushButton     = page.findChild(QPushButton, "guardarProNewBtn")
    btn_cancelar: QPushButton    = page.findChild(QPushButton, "cancelarProNewBtn")

    # --- Estado ---
    state = {"last": "gan"}   # quién manda (gan|pv) según el último edit
    reent = {"on": False}

    def set_silent(w: QObject, setter: str, val):
        with signals_blocked(w):
            getattr(w, setter)(val)

    # --- Cálculo bidireccional ---
    def recalc_from_gan():
        pc, ge, imp = float(costo.value()), float(ganancia.value()), float(impuesto.value())
        pv = calcular_precio_venta(pc, ge, imp)
        set_silent(precio_venta, "setValue", float(pv))

    def recalc_from_pv():
        pc, pv, imp = float(costo.value()), float(precio_venta.value()), float(impuesto.value())
        if pc <= 0:
            set_silent(ganancia, "setValue", 0.0)
            return
        g = calc_ganancia_pct_desde_pv(pc, imp, pv)
        set_silent(ganancia, "setValue", float(g))

    def update_by_last():
        (recalc_from_pv if state["last"] == "pv" else recalc_from_gan)()

    # --- Handlers de edición ---
    def on_gan_changed(_):
        if reent["on"]: return
        reent["on"] = True
        try:
            state["last"] = "gan"
            recalc_from_gan()
        finally:
            reent["on"] = False

    def on_pv_changed(_):
        if reent["on"]: return
        reent["on"] = True
        try:
            state["last"] = "pv"
            recalc_from_pv()
        finally:
            reent["on"] = False

    def on_costo_imp_changed(_):
        if reent["on"]: return
        reent["on"] = True
        try:
            update_by_last()
        finally:
            reent["on"] = False

    # --- Combo albergado ---
    if albergado:
        with signals_blocked(albergado):
            albergado.clear()
            albergado.setEditable(False)
            albergado.addItems(["solo catalogado", "catalogado y albergado"])
            albergado.setCurrentIndex(1)

      # ---- IVA por defecto ----
    if impuesto and float(impuesto.value()) <= 0.0:
        set_silent(impuesto, "setValue", IVA_DEFAULT)

    # --- Snapshot inicial (para Cancelar) ---
    initial = {
        "codigo": codigo.text() if codigo else "",
        "descripcion": descripcion.text() if descripcion else "",
        "costo": float(costo.value()) if costo else 0.0,
        "ganancia": float(ganancia.value()) if ganancia else 0.0,
        "impuesto": float(impuesto.value()) if impuesto else IVA_DEFAULT,
        "precio_venta": float(precio_venta.value()) if precio_venta else 0.0,
        "albergado_index": albergado.currentIndex() if albergado else 1,
        "hay": int(hay.value()) if hay else 0,
        "min_ini": int(min_ini.value()) if min_ini else 0,
        "max_ini": int(max_ini.value()) if max_ini else 0,
    }

    def reset_form():
        if codigo:        set_silent(codigo, "setText", initial["codigo"])
        if descripcion:   set_silent(descripcion, "setText", initial["descripcion"])
        if costo:         set_silent(costo, "setValue", initial["costo"])
        if ganancia:      set_silent(ganancia, "setValue", initial["ganancia"])
        if impuesto:      set_silent(impuesto, "setValue", initial["impuesto"])
        if precio_venta:  set_silent(precio_venta, "setValue", initial["precio_venta"])
        if albergado:     set_silent(albergado, "setCurrentIndex", initial["albergado_index"])
        if hay:           set_silent(hay, "setValue", initial["hay"])
        if min_ini:       set_silent(min_ini, "setValue", initial["min_ini"])
        if max_ini:       set_silent(max_ini, "setValue", initial["max_ini"])
        state["last"] = "gan"
        if codigo:
            codigo.setFocus()
            codigo.selectAll()

    # --- Guardar en DB ---
    def on_guardar():
        cod = (codigo.text() if codigo else "").strip()
        desc = (descripcion.text() if descripcion else "").strip()
        pc   = float(costo.value())
        impv = float(impuesto.value())
        ge = float(precio_venta.value())

        alb_idx = albergado.currentIndex() if albergado else 1
        alb_val = "catalogado y albergado" if alb_idx == 1 else "solo catalogado"   # 1 = "catalogado y albergado"

        exi = int(hay.value())
        inv_min = int(min_ini.value())
        inv_max = int(max_ini.value())

        # Validaciones mínimas
        if not cod:
            QMessageBox.warning(page, "Falta dato", "Código no puede estar vacío.")
            if codigo: codigo.setFocus()
            return
        if not desc:
            QMessageBox.warning(page, "Falta dato", "Descripción no puede estar vacía.")
            if descripcion: descripcion.setFocus()
            return

        try:
            with SessionLocal() as s, s.begin():

                # 0) Verificar duplicado (case-insensitive) en productos
                row = s.execute(
                    text("SELECT 1 FROM productos WHERE LOWER(codigo)=LOWER(:cod) LIMIT 1"),
                    {"cod": cod},
                ).first()
                if row:
                    QMessageBox.warning(page, "Código duplicado",
                        f"Ya existe un producto con código “{cod}”.")
                    if codigo: codigo.setFocus(); codigo.selectAll()
                    return
                
                # 1) Insertar producto (usa tu repo; soporta firmas distintas)
                try:
                    # Firma extensa (si tu repo la tiene)
                    repositories.insert_producto(s, cod, desc, pc, exi,inv_min,inv_max, ge, impv, alb_val)
                except TypeError:
                    QMessageBox.critical(page, "Error al guardar", f"No se pudo guardar el producto:\n")
                    pass

            # Éxito
            QMessageBox.information(page, "Producto", "Producto guardado correctamente.")
            # deja coherente los spinboxes
            with signals_blocked(ganancia): ganancia.setValue(ge)
            with signals_blocked(precio_venta): precio_venta.setValue()

        except TypeError:
           QMessageBox.critical(page, "Error al guardar", f"No se pudo guardar el producto:\n")
           pass 

    # --- Conexiones ---
    if ganancia:     ganancia.valueChanged.connect(on_gan_changed)
    if precio_venta: precio_venta.valueChanged.connect(on_pv_changed)
    if costo:        costo.valueChanged.connect(on_costo_imp_changed)
    if impuesto:     impuesto.valueChanged.connect(on_costo_imp_changed)
    if btn_cancelar: btn_cancelar.clicked.connect(reset_form)
    if btn_guardar:  btn_guardar.clicked.connect(on_guardar)

    # Inicial coherente
    recalc_from_gan()
    if codigo:
        codigo.setFocus()
        codigo.selectAll()

    page._pro_nuevo_setup_done = True
