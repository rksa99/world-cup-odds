"""Shared HTTP base for all data clients.

Design rules (from SPEC_LIVE_DATA.md):
- Every response is wrapped with `fetched_at` (UTC ISO) and `source`.
- Rate-limit guard: per-client min interval between calls + 429 backoff.
- Quota headers are logged on every call so you can see budget burn.
- On failure after retries, raise DataUnavailable — callers must surface
  `data_unavailable`, never invent data.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


class DataUnavailable(Exception):
    """Raised when live data cannot be fetched. Never swallow this silently."""

    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"[{source}] data_unavailable: {reason}")


def load_env(path: str = ".env") -> None:
    """Tiny .env loader (no python-dotenv dependency)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BaseClient:
    source_name: str
    base_url: str
    min_interval_s: float = 1.0          # rate-limit guard between calls
    max_retries: int = 3
    timeout_s: float = 15.0
    quota_headers: tuple = ()            # header names to log (quota tracking)
    _last_call_ts: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        self.log = logging.getLogger(self.source_name)
        self.session = requests.Session()

    # -- override in subclasses -------------------------------------------
    def auth_headers(self) -> dict:
        return {}

    # -- core --------------------------------------------------------------
    def get(self, path: str, params: Optional[dict] = None) -> dict:
        """GET with rate-limit guard, retries, quota logging.

        Returns: {"source", "fetched_at", "data": <parsed json>}
        Raises: DataUnavailable on persistent failure.
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        last_err = "unknown"

        for attempt in range(1, self.max_retries + 1):
            self._respect_rate_limit()
            try:
                resp = self.session.get(
                    url, params=params, headers=self.auth_headers(), timeout=self.timeout_s
                )
            except requests.RequestException as e:
                last_err = f"network error: {e}"
                self.log.warning("attempt %d/%d %s", attempt, self.max_retries, last_err)
                time.sleep(2 ** attempt)
                continue

            self._log_quota(resp)

            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2 ** attempt * 5))
                last_err = f"rate limited (429), waited {wait}s"
                self.log.warning("429 on %s — backing off %.0fs", path, wait)
                time.sleep(wait)
                continue

            if resp.status_code in (401, 403):
                raise DataUnavailable(self.source_name, f"auth failed ({resp.status_code}) — check API key in .env")

            if resp.status_code >= 500:
                last_err = f"server error {resp.status_code}"
                time.sleep(2 ** attempt)
                continue

            if resp.status_code != 200:
                raise DataUnavailable(self.source_name, f"HTTP {resp.status_code}: {resp.text[:200]}")

            try:
                data = resp.json()
            except json.JSONDecodeError:
                raise DataUnavailable(self.source_name, "response was not valid JSON")

            return {"source": self.source_name, "fetched_at": utc_now_iso(), "data": data}

        raise DataUnavailable(self.source_name, f"failed after {self.max_retries} attempts: {last_err}")

    # -- helpers -------------------------------------------------------------
    def _respect_rate_limit(self):
        elapsed = time.monotonic() - self._last_call_ts
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call_ts = time.monotonic()

    def _log_quota(self, resp: requests.Response):
        for h in self.quota_headers:
            if h in resp.headers:
                self.log.info("quota %s = %s", h, resp.headers[h])


def save_snapshot(payload: dict, kind: str, key: str, root: str = "data/snapshots") -> Path:
    """Provenance ledger: persist the exact raw input behind a prediction."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = Path(root) / kind
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{key}_{ts}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path
