from datetime import datetime
from sqlalchemy import select
from .db_local import SessionLocal
from .models import Producto, Outbox, SyncState
from .net import api_pull, api_push
import ast

def _get_sync_state(session, table: str) -> SyncState:
    st = session.get(SyncState, table)
    if not st:
        st = SyncState(table_name=table, last_sync=None, last_version=None)
        session.add(st)
    return st

def pull_productos():
    with SessionLocal() as s, s.begin():
        st = _get_sync_state(s, "productos")
        since = st.last_sync.isoformat() if st.last_sync else None
        try:
            data = api_pull("productos", since_iso=since)
        except Exception as e:
            return False, f"Pull error: {e}"

        for row in data:
            local = s.get(Producto, row["id"])
            incoming_updated = datetime.fromisoformat(row["updated_at"])
            if not local:
                local = Producto(**row)
                local.updated_at = incoming_updated
                if row.get("deleted_at"):
                    local.deleted_at = datetime.fromisoformat(row["deleted_at"])
                s.add(local)
            else:
                if incoming_updated >= local.updated_at:  # LWW
                    for k, v in row.items():
                        if k in {"updated_at", "deleted_at"} and isinstance(v, str) and v:
                            v = datetime.fromisoformat(v)
                        setattr(local, k, v)

        st.last_sync = datetime.utcnow()
        return True, f"Pull OK ({len(data)} cambios)"

def push_outbox():
    with SessionLocal() as s, s.begin():
        items = s.execute(select(Outbox).where(Outbox.sent.is_(False))).scalars().all()
        if not items:
            return True, "No hay cambios locales"
        by_table = {}
        for it in items:
            by_table.setdefault(it.table, []).append(it)

        for table, rows in by_table.items():
            batch = []
            for it in rows:
                try:
                    payload = ast.literal_eval(it.payload)
                except Exception:
                    payload = {"raw": it.payload}
                batch.append({"op": it.op, "data": payload})

            try:
                api_push(table, batch)
            except Exception as e:
                return False, f"Push error en {table}: {e}"

            for it in rows:
                it.sent = True

        return True, "Push OK"
