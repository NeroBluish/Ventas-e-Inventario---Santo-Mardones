# app/core/repositories.py
from __future__ import annotations

from datetime import datetime, date
from typing import Iterable

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.models import (
    Producto, Transito,
    Boleta, BoletaDetalle,
    OrdenCompra, DetalleOrden
)


# =========================
# Helpers internos
# =========================
def _bump_version(obj):
    if getattr(obj, "version", None) is not None:
        obj.version = int(obj.version or 0) + 1


def _ensure_transito(session: Session, producto: Producto) -> Transito:
    """
    Devuelve el snapshot Transito 1:1 del producto, creándolo si no existe.
    """
    tr = session.execute(
        select(Transito).where(Transito.producto_codigo == producto.codigo)
    ).scalar_one_or_none()
    if tr is None:
        tr = Transito(
            producto_codigo=producto.codigo,
            mas_existencias=0,
            new_precio_costo=int(producto.precio_costo or 0),
            estado_transito="desactivado",
            updated_at=datetime.utcnow(),
        )
        session.add(tr)
        _bump_version(tr)
    return tr


def _parse_date_maybe(d: str | date | None) -> date | None:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    # Espera formato 'YYYY-MM-DD'
    return datetime.strptime(str(d), "%Y-%m-%d").date()


# =========================
# Productos (existente + fixes)
# =========================
def insert_producto(session: Session, codigo, descripcion,
                    precio_costo, existencias, inv_minimo, inv_maximo,
                    precio_venta=0, porcentaje_impuesto=19,
                    albergado="catalogado y albergado",):
    p = Producto(
        codigo=codigo,
        descripcion=descripcion,
        precio_costo=int(precio_costo or 0),
        precio_venta=int(precio_venta or 0),
        porcentaje_impuesto=int(porcentaje_impuesto or 0),
        existencias=int(existencias or 0),
        inv_minimo=int(inv_minimo or 0),
        inv_maximo=int(inv_maximo or 0),
        albergado=albergado or "catalogado y albergado",
    )
    session.add(p)
    return p


def update_producto(session: Session, codigo_original: str, *,
                    codigo: str | None = None,
                    descripcion: str | None = None,
                    precio_costo: int | None = None,
                    precio_venta: int | None = None,
                    porcentaje_impuesto: int | None = None,
                    existencias: int | None = None,
                    inv_minimo: int | None = None,
                    inv_maximo: int | None = None,
                    albergado: str | None = None) -> Producto:
    prod = session.execute(
        select(Producto).where(
            Producto.deleted_at.is_(None),
            Producto.codigo == codigo_original
        )
    ).scalar_one_or_none()
    if not prod:
        raise ValueError(f"Producto con código '{codigo_original}' no existe")

    if codigo is not None:                prod.codigo = codigo
    if descripcion is not None:           prod.descripcion = descripcion
    if precio_costo is not None:          prod.precio_costo = int(precio_costo)
    if precio_venta is not None:          prod.precio_venta = int(precio_venta)
    if porcentaje_impuesto is not None:   prod.porcentaje_impuesto = int(porcentaje_impuesto)
    if existencias is not None:           prod.existencias = int(existencias)
    if inv_minimo is not None:            prod.inv_minimo = int(inv_minimo)
    if inv_maximo is not None:            prod.inv_maximo = int(inv_maximo)
    if albergado is not None:             prod.albergado = albergado

    prod.updated_at = datetime.utcnow()
    _bump_version(prod)
    return prod


def soft_delete_producto(session: Session, codigo: str):
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
    _bump_version(prod)
    return prod


def get_productos_bajo_inventario(session: Session):
    """
    Devuelve [(codigo, descripcion, precio_venta, existencias, inv_minimo)] de productos bajo mínimo.
    (Antes había un unpack que no cuadraba; se corrige para devolver sólo lo necesario.)
    """
    rows = session.execute(
        select(
            Producto.codigo,
            Producto.descripcion,
            Producto.precio_venta,
            Producto.existencias,
            Producto.inv_minimo
        ).where(
            Producto.deleted_at.is_(None),
            Producto.existencias < Producto.inv_minimo
        ).order_by(Producto.codigo.asc())
    ).all()
    return [tuple(r) for r in rows]


def get_producto_por_codigo(session: Session, codigo: str) -> Producto | None:
    return session.execute(
        select(Producto).where(
            Producto.deleted_at.is_(None),
            Producto.codigo == codigo
        )
    ).scalar_one_or_none()


def get_productos_sobre_inventario(session: Session):
    """
    Devuelve [(codigo, descripcion, precio_venta, existencias, inv_maximo)] de productos sobre máximo.
    """
    rows = session.execute(
        select(
            Producto.codigo,
            Producto.descripcion,
            Producto.precio_venta,
            Producto.existencias,
            Producto.inv_maximo
        ).where(
            Producto.deleted_at.is_(None),
            Producto.inv_maximo.isnot(None),
            Producto.inv_maximo > 0,
            Producto.existencias > Producto.inv_maximo
        ).order_by(Producto.codigo.asc())
    ).all()
    return [tuple(r) for r in rows]


# =========================
# Ventas / Boletas (como tenías)
# =========================
def _next_folio(session: Session) -> str:
    # Folio simple por día: BLT-YYYYMMDD-000001
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"BLT-{today}-"
    count_today = session.execute(
        select(func.count(Boleta.id)).where(Boleta.folio.like(f"{prefix}%"))
    ).scalar_one()
    return f"{prefix}{count_today+1:06d}"


def crear_boleta_con_detalles(session: Session, items: Iterable[dict]):
    """
    items = iterable de dicts:
      {"codigo": str, "descripcion": str, "precio_unit": int, "cantidad": int}
    """
    total = 0
    productos_cache: dict[str, Producto] = {}

    for it in items:
        cant = int(it["cantidad"])
        if cant <= 0:
            raise ValueError("Cantidad debe ser mayor a 0")
        precio = int(it["precio_unit"])
        total += precio * cant

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
            precio_unitario=int(it["precio_unit"]),
            cantidad=int(it["cantidad"]),
            subtotal=int(it["precio_unit"]) * int(it["cantidad"]),
        )
        session.add(det)

        p = productos_cache.get(it["codigo"])
        if p:
            p.existencias = int(p.existencias) - int(it["cantidad"])
            p.updated_at = datetime.utcnow()
            _bump_version(p)

    return boleta


# =========================
# Órdenes de compra + snapshot Transito (1:1)
# =========================
def crear_orden_compra_con_detalles(
    session: Session,
    *,
    folio_orden: str,
    fecha_llegada_orden: str | date | None,
    estado_orden: str = "pendiente",
    detalle_items: Iterable[dict],
):
    """
    detalle_items: iterable de dicts
      {
        "codigo_producto": str,
        "cantidad": int,
        "precio_unitario": int,
        "descripcion": str | None
      }
    Crea la OC (header + líneas) y ACTUALIZA el snapshot Transito por producto:
      mas_existencias += cantidad
      new_precio_costo = precio_unitario (si >0)
      estado_transito = "pendiente" (o "en_camino")
    """
    oc = OrdenCompra(
        folio_orden=folio_orden,
        fecha_llegada_orden=_parse_date_maybe(fecha_llegada_orden),
        estado_orden=estado_orden or "pendiente",
        detalle_orden=None,
        updated_at=datetime.utcnow(),
    )
    session.add(oc)
    session.flush()  # asegura id

    for it in detalle_items:
        codigo = it["codigo_producto"]
        cantidad = int(it.get("cantidad", 0))
        precio_u = int(it.get("precio_unitario", 0))
        desc     = it.get("descripcion")

        if cantidad <= 0:
            raise ValueError(f"Cantidad inválida para '{codigo}'")

        prod = session.execute(
            select(Producto).where(
                Producto.deleted_at.is_(None),
                Producto.codigo == codigo
            )
        ).scalar_one_or_none()
        if not prod:
            raise ValueError(f"Producto '{codigo}' no existe")

        det = DetalleOrden(
            orden_id=oc.id_ordenes_com,
            codigo_producto=codigo,
            cant_enorden=cantidad,
            precio_unitario_orden=precio_u,
            descripcion_enorden=desc
        )
        session.add(det)

        # Actualiza snapshot Transito
        tr = _ensure_transito(session, prod)
        tr.mas_existencias = int(tr.mas_existencias or 0) + cantidad
        if precio_u > 0:
            tr.new_precio_costo = precio_u
        tr.estado_transito = "pendiente" if oc.estado_orden == "pendiente" else "en_camino"
        tr.updated_at = datetime.utcnow()
        _bump_version(tr)

    return oc


def cancelar_orden_compra(session: Session, id_orden: str) -> OrdenCompra:
    """
    Marca la OC como 'cancelada' y revierte el snapshot de tránsito
    (resta las cantidades comprometidas de esa OC).
    """
    oc = session.get(OrdenCompra, id_orden)
    if not oc:
        raise ValueError("Orden de compra no existe")

    # Revertir snapshot por cada línea
    for det in oc.detalles:
        prod = session.execute(
            select(Producto).where(
                Producto.deleted_at.is_(None),
                Producto.codigo == det.codigo_producto
            )
        ).scalar_one_or_none()
        if not prod:
            # si el producto ya no existe, ignora el ajuste de snapshot
            continue
        tr = _ensure_transito(session, prod)
        tr.mas_existencias = max(0, int(tr.mas_existencias or 0) - int(det.cant_enorden or 0))
        tr.estado_transito = "desactivado" if tr.mas_existencias == 0 else tr.estado_transito
        tr.updated_at = datetime.utcnow()
        _bump_version(tr)

    oc.estado_orden = "cancelada"
    oc.updated_at = datetime.utcnow()
    _bump_version(oc)
    return oc


def recepcionar_orden_total(session: Session, id_orden: str) -> OrdenCompra:
    """
    Recepciona COMPLETAMENTE la OC (todas sus líneas):
      - Sube existencias de cada producto
      - Ajusta snapshot Transito (resta mas_existencias)
      - Actualiza precio_costo con el precio de la OC (estrategia: último costo)
      - Marca la OC como 'cerrada'
    *Nota*: si más adelante quieres recepciones parciales,
            convendrá introducir tablas de eventos (Embarque/Recepcion).
    """
    oc = session.get(OrdenCompra, id_orden)
    if not oc:
        raise ValueError("Orden de compra no existe")

    for det in oc.detalles:
        prod = session.execute(
            select(Producto).where(
                Producto.deleted_at.is_(None),
                Producto.codigo == det.codigo_producto
            )
        ).scalar_one_or_none()
        if not prod:
            raise ValueError(f"Producto '{det.codigo_producto}' no existe (no se puede recepcionar)")

        # subir stock
        prod.existencias = int(prod.existencias or 0) + int(det.cant_enorden or 0)
        prod.precio_costo = int(det.precio_unitario_orden or prod.precio_costo or 0)  # estrategia: último
        prod.updated_at = datetime.utcnow()
        _bump_version(prod)

        # ajustar snapshot
        tr = _ensure_transito(session, prod)
        tr.mas_existencias = max(0, int(tr.mas_existencias or 0) - int(det.cant_enorden or 0))
        tr.estado_transito = "desactivado" if tr.mas_existencias == 0 else tr.estado_transito
        tr.updated_at = datetime.utcnow()
        _bump_version(tr)

    oc.estado_orden = "cerrada"
    oc.updated_at = datetime.utcnow()
    _bump_version(oc)
    return oc
