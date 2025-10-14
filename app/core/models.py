# app/core/models.py
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, String, Integer, DateTime, Date, Text, Boolean, Index, ForeignKey, UniqueConstraint
)
from datetime import datetime
import uuid

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())


# =========================
# PRODUCTO 1 ─── 0..1 TRANSITO (snapshot por producto)
# =========================
class Producto(Base):
    __tablename__ = "productos"

    codigo = Column(String, primary_key=True)  # p.ej. "A-001"

    descripcion         = Column(String,  nullable=False)
    existencias         = Column(Integer, nullable=False, default=0)
    inv_minimo          = Column(Integer, nullable=False, default=0)
    inv_maximo          = Column(Integer, nullable=False, default=0)
    precio_costo        = Column(Integer, nullable=False, default=0)
    precio_venta        = Column(Integer, nullable=False, default=0)
    porcentaje_impuesto = Column(Integer, nullable=False, default=19)
    albergado           = Column(String,  nullable=False, default="Albergado y catalogado")

    # 1:1 → Transito (snapshot agregado por producto)
    transito = relationship(
        "Transito",
        back_populates="producto",
        uselist=False,
        cascade="all, delete-orphan"
    )

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version    = Column(Integer, nullable=False, default=1)


class Transito(Base):
    __tablename__ = "transito"

    id_transito = Column(String, primary_key=True, default=gen_uuid)

    # Estado agregado "en camino" para ESTE producto
    mas_existencias   = Column(Integer, nullable=False, default=0)
    new_precio_costo  = Column(Integer, nullable=False, default=0)
    estado_transito   = Column(String,  nullable=False, default="desactivado")

    # FK ÚNICA → forza 1:1 con Producto
    producto_codigo = Column(
        String,
        ForeignKey("productos.codigo", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    producto = relationship("Producto", back_populates="transito")

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version    = Column(Integer, nullable=False, default=1)


# Índice útil para sincronización/offline
Index("idx_productos_updated", Producto.updated_at)



class Boleta(Base):
    __tablename__ = "boletas"
    id = Column(String, primary_key=True, default=gen_uuid)
    folio = Column(String, unique=True, nullable=False)         # ej: BLT-20251009-000001
    total = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    detalles = relationship("BoletaDetalle", back_populates="boleta", cascade="all, delete-orphan")


class BoletaDetalle(Base):
    __tablename__ = "boleta_detalles"
    id = Column(String, primary_key=True, default=gen_uuid)
    boleta_id = Column(String, ForeignKey("boletas.id", ondelete="CASCADE"), nullable=False, index=True)

    # snapshot de producto en el momento de la venta
    codigo_producto     = Column(String, nullable=False)
    descripcion         = Column(String, nullable=False)
    precio_unitario     = Column(Integer, nullable=False, default=0)
    cantidad            = Column(Integer, nullable=False, default=0)
    subtotal            = Column(Integer, nullable=False, default=0)

    boleta = relationship("Boleta", back_populates="detalles")


# =========================
# ORDEN DE COMPRA 1 ─── N DETALLE ORDEN  N ─── 1 PRODUCTO
# (tabla puente que materializa OC↔Producto)
# =========================
class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id_ordenes_com = Column(String, primary_key=True, default=gen_uuid)

    folio_orden         = Column(String, nullable=False)   # puedes marcar unique=True si quieres
    fecha_llegada_orden = Column(Date,   nullable=True)    # mejor Date/DateTime que String
    estado_orden        = Column(String, nullable=False, default="pendiente")

    # 1:N → DetalleOrden
    detalles = relationship(
        "DetalleOrden",
        back_populates="orden",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("folio_orden", name="uq_ordenes_compra_folio"),
    )

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version    = Column(Integer, nullable=False, default=1)


class DetalleOrden(Base):
    __tablename__ = "detalles_orden"

    id_detalle_orden = Column(String, primary_key=True, default=gen_uuid)

    # FK al header de la OC (padre)
    orden_id = Column(
        String,
        ForeignKey("ordenes_compra.id_ordenes_com", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # FK al producto (N:1)
    codigo_producto = Column(
        String,
        ForeignKey("productos.codigo"),
        nullable=False,
        index=True
    )

    # Cantidad y precio negociado en la OC
    cant_enorden          = Column(Integer, nullable=False, default=0)
    precio_unitario_orden = Column(Integer, nullable=False, default=0)

    # (Opcional) snapshot de descripción a la fecha de la OC
    descripcion_enorden   = Column(String, nullable=True)

    # Relaciones ORM
    orden    = relationship("OrdenCompra", back_populates="detalles")
    producto = relationship("Producto")

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version    = Column(Integer, nullable=False, default=1)


# =========================
# Infra de sincronización (como ya la tenías)
# =========================
class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True, default=gen_uuid)
    table = Column(String, nullable=False)
    op = Column(String, nullable=False)      # "insert" | "update" | "delete"
    payload = Column(Text, nullable=False)   # dict serializado (str)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent = Column(Boolean, nullable=False, default=False)


class SyncState(Base):
    __tablename__ = "sync_state"
    table_name = Column(String, primary_key=True)
    last_sync = Column(DateTime, nullable=True)
    last_version = Column(Integer, nullable=True)
