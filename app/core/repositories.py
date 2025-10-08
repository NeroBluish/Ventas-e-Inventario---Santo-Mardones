from sqlalchemy import select
from app.core.models import Producto

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
