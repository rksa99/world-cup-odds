"""football-data.org client — PRIMARY source.

Covers: fixtures, live scores, standings, confirmed lineups.
Free tier: 10 calls/min  →  min_interval_s = 6.5 keeps us safely under.
Competition code for the FIFA World Cup: "WC".
Docs: https://www.football-data.org/documentation/quickstart
Env:  FOOTBALL_DATA_TOKEN
"""

from __future__ import annotations

import os

from .base import BaseClient, DataUnavailable


class FootballDataClient(BaseClient):
    def __init__(self):
        super().__init__(
            source_name="football-data.org",
            base_url="https://api.football-data.org/v4",
            min_interval_s=6.5,  # 10/min free tier
            quota_headers=("X-Requests-Available-Minute",),
        )
        self.token = os.environ.get("FOOTBALL_DATA_TOKEN", "")
        if not self.token:
            raise DataUnavailable(self.source_name, "FOOTBALL_DATA_TOKEN missing from .env")

    def auth_headers(self) -> dict:
        return {"X-Auth-Token": self.token}

    # -- endpoints ----------------------------------------------------------
    def fixtures(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        """All World Cup matches, optionally windowed (YYYY-MM-DD)."""
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return self.get("competitions/WC/matches", params or None)

    def live_and_today(self) -> dict:
        """Today's matches incl. live status (poll ≤ 1/min during matches)."""
        return self.get("competitions/WC/matches", {"status": "LIVE"})

    def match(self, match_id: int) -> dict:
        """Single match detail — includes confirmed lineups ~1h pre-kickoff."""
        return self.get(f"matches/{match_id}")

    def standings(self) -> dict:
        """All 12 group tables with tiebreakers applied."""
        return self.get("competitions/WC/standings")
