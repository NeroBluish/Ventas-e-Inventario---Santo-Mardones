from sqlalchemy import select, func
from app.core.models import Producto, Boleta, BoletaDetalle
from datetime import datetime

def insert_producto(session, codigo, descripcion, precio_venta, existencias, inv_minimo):
    p = Producto(
        codigo=codigo, descripcion=descripcion, precio_venta=precio_venta,
        existencias=existencias, inv_minimo=inv_minimo
    )
    session.add(p)
    return p

def get_productos_bajo_inventario(session):
    rows = session.execute(
        select(
            Producto.codigo, Producto.descripcion, Producto.precio_venta,
            Producto.existencias, Producto.inv_minimo
        ).where(
            Producto.deleted_at.is_(None),
            Producto.existencias < Producto.inv_minimo
        ).order_by(Producto.codigo.asc())
    ).all()
    return [tuple(r) for r in rows]

def get_producto_por_codigo(session, codigo: str):
    return session.execute(
        select(Producto).where(
            Producto.deleted_at.is_(None),
            Producto.codigo == codigo
        )
    ).scalar_one_or_none()

def _next_folio(session) -> str:
    # Folio simple por día: BLT-YYYYMMDD-000001
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"BLT-{today}-"
    # cuenta cuántas boletas de hoy para numerar
    count_today = session.execute(
        select(func.count(Boleta.id)).where(Boleta.folio.like(f"{prefix}%"))
    ).scalar_one()
    return f"{prefix}{count_today+1:06d}"

def crear_boleta_con_detalles(session, items):
    """
    items = iterable de dicts:
      {"codigo": str, "descripcion": str, "precio_unit": int, "cantidad": int}
    """
    total = sum(it["precio_unit"] * it["cantidad"] for it in items)
    boleta = Boleta(folio=_next_folio(session), total=total, created_at=datetime.utcnow())
    session.add(boleta)
    session.flush()  # asegura boleta.id

    for it in items:
        det = BoletaDetalle(
            boleta_id=boleta.id,
            codigo_producto=it["codigo"],
            descripcion=it["descripcion"],
            precio_unitario=it["precio_unit"],
            cantidad=it["cantidad"],
            subtotal=it["precio_unit"] * it["cantidad"],
        )
        session.add(det)
    return boleta