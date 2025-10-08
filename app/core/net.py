import httpx
from .config import BASE_URL, API_TOKEN, HTTP_TIMEOUT

def _headers():
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = API_TOKEN
    return h

def api_healthcheck():
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as c:
            r = c.get(f"{BASE_URL}/health", headers=_headers())
            r.raise_for_status()
            return True
    except Exception:
        return False

def api_pull(resource: str, since_iso: str | None):
    params = {"since": since_iso} if since_iso else {}
    with httpx.Client(timeout=HTTP_TIMEOUT) as c:
        r = c.get(f"{BASE_URL}/sync/pull/{resource}", params=params, headers=_headers())
        r.raise_for_status()
        return r.json()

def api_push(resource: str, batch: list[dict]):
    with httpx.Client(timeout=HTTP_TIMEOUT) as c:
        r = c.post(f"{BASE_URL}/sync/push/{resource}", json=batch, headers=_headers())
        r.raise_for_status()
        return r.json()
