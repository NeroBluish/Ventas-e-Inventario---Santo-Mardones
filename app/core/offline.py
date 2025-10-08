from .net import api_healthcheck

def is_online() -> bool:
    return api_healthcheck()
