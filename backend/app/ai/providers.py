from __future__ import annotations

import os


class ProviderUnavailable(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ProviderUnavailable(f"{name} is not configured; using manual/demo fallback.")
    return value


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def google_cloud_configured() -> bool:
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
