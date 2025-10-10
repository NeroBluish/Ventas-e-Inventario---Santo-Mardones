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

def update_producto(session, codigo_original: str, *, codigo: str | None = None,
                    descripcion: str | None = None, precio_venta: int | None = None,
                    existencias: int | None = None, inv_minimo: int | None = None) -> Producto:
    """Actualiza un producto por su código actual. Devuelve el producto actualizado.
    Levanta ValueError si no existe.
    """
    prod = session.execute(
        select(Producto).where(
            Producto.deleted_at.is_(None),
            Producto.codigo == codigo_original
        )
    ).scalar_one_or_none()
    if not prod:
        raise ValueError(f"Producto con código '{codigo_original}' no existe")

    if codigo is not None:
        prod.codigo = codigo
    if descripcion is not None:
        prod.descripcion = descripcion
    if precio_venta is not None:
        prod.precio_venta = int(precio_venta)
    if existencias is not None:
        prod.existencias = int(existencias)
    if inv_minimo is not None:
        prod.inv_minimo = int(inv_minimo)

    prod.updated_at = datetime.utcnow()
    if getattr(prod, "version", None) is not None:
        prod.version = int(prod.version) + 1
    return prod

def soft_delete_producto(session, codigo: str):
    prod = session.execute(
        select(Producto).where(
            Producto.deleted_at.is_(None),
            Producto.codigo == codigo
        )
    ).scalar_one_or_none()
    if not prod:
        raise ValueError(f"Producto con código '{codigo}' no existe")
    now = datetime.utcnow()
    prod.deleted_at = now
    prod.updated_at = now
    if getattr(prod, "version", None) is not None:
        prod.version = int(prod.version) + 1
    return prod

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
    # Validar stock y acumular total antes de crear la boleta
    total = 0
    productos_cache = {}
    for it in items:
        cant = int(it["cantidad"])
        if cant <= 0:
            raise ValueError("Cantidad debe ser mayor a 0")
        precio = int(it["precio_unit"])
        total += precio * cant

        # Buscar producto por codigo para validar stock
        p = session.execute(
            select(Producto).where(
                Producto.deleted_at.is_(None),
                Producto.codigo == it["codigo"],
            )
        ).scalar_one_or_none()
        if not p:
            raise ValueError(f"Producto '{it['codigo']}' no existe")
        if p.existencias is None:
            p.existencias = 0
        if p.existencias < cant:
            raise ValueError(
                f"Stock insuficiente para '{p.codigo}': hay {p.existencias}, se requieren {cant}"
            )
        productos_cache[it["codigo"]] = p
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
        # Descontar stock y actualizar metadata
        p = productos_cache.get(it["codigo"])  # ya validado arriba
        if p:
            p.existencias = int(p.existencias) - int(it["cantidad"])
            p.updated_at = datetime.utcnow()
            # Opcional: versionado simple
            if getattr(p, "version", None) is not None:
                p.version = int(p.version) + 1
    return boleta
