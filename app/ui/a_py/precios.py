# app/ui/a_py/precios.py

def calcular_precio_venta(precio_costo: float | None, ganancia_esperada: float | None, porcentaje_impuesto: float | None) -> float:
    """
    calcula precio venta, toamdo precio costo, porcentaje ganacia e impuestos
    """

    pc  = float(precio_costo or 0)
    ge  = pc*(ganancia_esperada/100)
    imp = float(porcentaje_impuesto or 0)
    base = pc + ge
    return float(round(base * (1 + imp/100)))


def calc_ganancia_pct_desde_pv(costo: float, imp: float, precio_venta: float) -> float:
    """
    calcula porcentaje ganacia a partir de precio venta
    """
    neto = (100*precio_venta)/(100 + imp)
    ganenter = neto - costo
    return float(round(ganenter/(costo/100)))