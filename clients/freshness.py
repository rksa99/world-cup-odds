"""Freshness gate — the orchestrator's first line of defense.

TTLs from SPEC_LIVE_DATA.md §2.6:
  odds 12h · stats 24h · fitness 6h · lineup 2h · news 1h
A prediction may only be emitted when every required input passes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

TTL_HOURS = {
    "odds": 12,
    "stats": 24,
    "fitness": 6,
    "lineup": 2,
    "news": 1,
    "h2h": 24 * 365 * 10,  # effectively permanent
}


def is_fresh(fetched_at_iso: str, kind: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    fetched = datetime.fromisoformat(fetched_at_iso)
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return now - fetched <= timedelta(hours=TTL_HOURS[kind])


def gate(inputs: dict[str, dict], required: tuple = ("odds", "stats", "fitness")) -> dict:
    """Check a bundle of agent inputs before prediction.

    `inputs` maps kind -> wrapped payload ({"fetched_at": ..., "data": ...}).
    Returns {"ok": bool, "stale": [...], "missing": [...]}.
    """
    stale, missing = [], []
    for kind in required:
        payload = inputs.get(kind)
        if payload is None or "fetched_at" not in payload:
            missing.append(kind)
        elif not is_fresh(payload["fetched_at"], kind):
            stale.append(kind)
    return {"ok": not stale and not missing, "stale": stale, "missing": missing}
