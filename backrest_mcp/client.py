"""
Backrest HTTP client — connect-rpc-over-HTTP (plain POST + JSON body).

All endpoints follow the pattern:
  POST {base_url}/v1.Backrest/{MethodName}

Optional Basic Auth via BACKREST_USERNAME / BACKREST_PASSWORD env vars.
4xx/5xx responses raise httpx.HTTPStatusError.
"""

from __future__ import annotations

import os
from functools import lru_cache

import httpx
import structlog

log = structlog.get_logger(__name__)


class BackrestClient:
    """Async HTTP client for the Backrest connect-rpc API."""

    def __init__(self, base_url: str, username: str = "", password: str = "") -> None:
        self._base = base_url.rstrip("/")
        self._auth = (username, password) if username and password else None

    async def post(self, method: str, body: dict) -> dict:
        url = f"{self._base}/v1.Backrest/{method}"
        log.debug("backrest_request", method=method)
        async with httpx.AsyncClient(auth=self._auth, timeout=120.0) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            return r.json()


@lru_cache(maxsize=1)
def get_client() -> BackrestClient:
    return BackrestClient(
        base_url=os.environ.get("BACKREST_URL", "http://localhost:9898"),
        username=os.environ.get("BACKREST_USERNAME", ""),
        password=os.environ.get("BACKREST_PASSWORD", ""),
    )
