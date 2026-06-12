"""API-Football (api-sports.io) client — SECONDARY source.

Covers: match statistics, injuries, head-to-head, locked squads.
Free tier: 100 requests/DAY — every call counts. Cache aggressively:
  - squads: fetch ONCE per team, cache for entire tournament (locked June 1)
  - h2h: fetch ONCE per pairing, cache forever (history doesn't change)
World Cup identifiers: league=1, season=2026.
Env: API_FOOTBALL_KEY
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .base import BaseClient, DataUnavailable

LEAGUE = 1
SEASON = 2026
CACHE_DIR = Path("data/cache/api_football")


class ApiFootballClient(BaseClient):
    def __init__(self):
        super().__init__(
            source_name="api-football",
            base_url="https://v3.football.api-sports.io",
            min_interval_s=2.0,
            quota_headers=("x-ratelimit-requests-remaining", "X-RateLimit-Remaining"),
        )
        self.key = os.environ.get("API_FOOTBALL_KEY", "")
        if not self.key:
            raise DataUnavailable(self.source_name, "API_FOOTBALL_KEY missing from .env")

    def auth_headers(self) -> dict:
        return {"x-apisports-key": self.key}

    # -- daily-budget endpoints ----------------------------------------------
    def fixtures(self, date: str | None = None) -> dict:
        params = {"league": LEAGUE, "season": SEASON}
        if date:
            params["date"] = date  # YYYY-MM-DD
        return self.get("fixtures", params)

    def fixture_statistics(self, fixture_id: int) -> dict:
        """Post-match: shots, possession, xG where provided."""
        return self.get("fixtures/statistics", {"fixture": fixture_id})

    def injuries(self) -> dict:
        """Tournament-wide injury list — poll twice daily, not per match."""
        return self.get("injuries", {"league": LEAGUE, "season": SEASON})

    def standings(self) -> dict:
        return self.get("standings", {"league": LEAGUE, "season": SEASON})

    # -- cache-forever endpoints ----------------------------------------------
    def head_to_head(self, team1_id: int, team2_id: int) -> dict:
        """H2H history. Cached permanently — burns zero quota on repeat calls."""
        key = f"h2h_{min(team1_id, team2_id)}_{max(team1_id, team2_id)}"
        cached = self._read_cache(key)
        if cached:
            return cached
        result = self.get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}"})
        self._write_cache(key, result)
        return result

    def squad(self, team_id: int) -> dict:
        """Locked 26-man squad. Cached for the whole tournament."""
        key = f"squad_{team_id}"
        cached = self._read_cache(key)
        if cached:
            return cached
        result = self.get("players/squads", {"team": team_id})
        self._write_cache(key, result)
        return result

    # -- tiny permanent cache ---------------------------------------------------
    @staticmethod
    def _read_cache(key: str) -> dict | None:
        p = CACHE_DIR / f"{key}.json"
        if p.exists():
            return json.loads(p.read_text())
        return None

    @staticmethod
    def _write_cache(key: str, payload: dict) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(payload, ensure_ascii=False))
