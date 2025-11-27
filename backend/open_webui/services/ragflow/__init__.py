"""RagFlow service adapters (dataset/file/chunk management).

All clients are thin wrappers around RagFlow HTTP APIs and are designed
to be dependency-light. They read configuration from request.app.state.config
when available, falling back to sane defaults for local development.
"""

__all__ = [
    "get_base_url",
    "get_api_key",
    "get_timeout",
]

DEFAULT_RAGFLOW_BASE_URL = "http://192.168.2.168:9222"
DEFAULT_RAGFLOW_API_KEY = "ragflow-fV9iHE6hm-FUIKiUn_mvpvUWhYrYNZ_URvf7TDQmbQU"
DEFAULT_RAGFLOW_TIMEOUT = 30.0


def get_base_url(request=None) -> str:
    try:
        cfg = getattr(getattr(request, "app", None), "state", None)
        if cfg and getattr(cfg, "config", None):
            val = getattr(cfg.config, "RAGFLOW_BASE_URL", None)
            if isinstance(val, str) and val.strip():
                return val.rstrip("/")
    except Exception:
        pass
    return DEFAULT_RAGFLOW_BASE_URL


def get_api_key(request=None) -> str:
    try:
        cfg = getattr(getattr(request, "app", None), "state", None)
        if cfg and getattr(cfg, "config", None):
            val = getattr(cfg.config, "RAGFLOW_API_KEY", None)
            if isinstance(val, str) and val.strip():
                return val
    except Exception:
        pass
    return DEFAULT_RAGFLOW_API_KEY


def get_timeout(request=None) -> float:
    try:
        cfg = getattr(getattr(request, "app", None), "state", None)
        if cfg and getattr(cfg, "config", None):
            val = getattr(cfg.config, "RAGFLOW_TIMEOUT", None)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    return DEFAULT_RAGFLOW_TIMEOUT


