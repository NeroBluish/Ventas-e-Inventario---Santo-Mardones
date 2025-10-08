from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Index
from datetime import datetime
import uuid

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class Producto(Base):
    __tablename__ = "productos"
    id = Column(String, primary_key=True, default=gen_uuid)

    # --- NUEVOS CAMPOS para GUI/Inventario ---
    codigo = Column(String, unique=True, nullable=False)          # p.ej. "A-001"
    descripcion = Column(String, nullable=False)                   # nombre/desc del producto
    precio_venta = Column(Integer, nullable=False, default=0)      # en centavos o entero
    existencias = Column(Integer, nullable=False, default=0)
    inv_minimo = Column(Integer, nullable=False, default=0)
    # -----------------------------------------

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=False, default=1)

Index("idx_productos_codigo", Producto.codigo, unique=True)
Index("idx_productos_updated", Producto.updated_at)

class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True, default=gen_uuid)
    table = Column(String, nullable=False)   # p.ej. "productos"
    op = Column(String, nullable=False)      # "insert" | "update" | "delete"
    payload = Column(Text, nullable=False)   # dict serializado (str)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent = Column(Boolean, nullable=False, default=False)

class SyncState(Base):
    __tablename__ = "sync_state"
    table_name = Column(String, primary_key=True)
    last_sync = Column(DateTime, nullable=True)
    last_version = Column(Integer, nullable=True)
