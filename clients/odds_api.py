"""The Odds API client — odds source (replaces the scraping agent).

Covers: match 1X2 (h2h market) + outright tournament winner.
Free tier: ~500 credits/month. Each call costs (markets × regions) credits,
so one region + one market = 1 credit per call. Budget per spec:
  - match odds: 3 snapshots per match (T-24h / T-6h / T-1h)
  - outrights: once daily
Sport keys: soccer_fifa_world_cup (matches), soccer_fifa_world_cup_winner (outright).
NOTE: verify both sport keys against GET /v4/sports once your key is live —
key names occasionally change between tournaments.
Env: ODDS_API_KEY
"""

from __future__ import annotations

import os

from .base import BaseClient, DataUnavailable

SPORT_MATCHES = "soccer_fifa_world_cup"
SPORT_OUTRIGHT = "soccer_fifa_world_cup_winner"


class OddsApiClient(BaseClient):
    def __init__(self):
        super().__init__(
            source_name="the-odds-api",
            base_url="https://api.the-odds-api.com/v4",
            min_interval_s=1.5,
            quota_headers=("x-requests-remaining", "x-requests-used"),
        )
        self.key = os.environ.get("ODDS_API_KEY", "")
        if not self.key:
            raise DataUnavailable(self.source_name, "ODDS_API_KEY missing from .env")

    def get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["apiKey"] = self.key
        return super().get(path, params)

    # -- endpoints ---------------------------------------------------------
    def list_sports(self) -> dict:
        """Free call (0 credits). Use to verify the World Cup sport keys."""
        return self.get("sports")

    def match_odds(self) -> dict:
        """1X2 odds for upcoming WC matches, EU bookmakers. 1 credit."""
        return self.get(
            f"sports/{SPORT_MATCHES}/odds",
            {"regions": "eu", "markets": "h2h", "oddsFormat": "decimal"},
        )

    def outright_winner(self) -> dict:
        """Tournament winner market — daily snapshot. 1 credit."""
        return self.get(
            f"sports/{SPORT_OUTRIGHT}/odds",
            {"regions": "eu", "markets": "outrights", "oddsFormat": "decimal"},
        )


# -- math helpers (pure functions, no quota) -----------------------------------

def implied_probabilities(decimal_odds: list[float]) -> list[float]:
    """De-vigged implied probabilities from decimal odds (1X2 or outright).

    Standard normalization: p_i = (1/o_i) / Σ(1/o_j).
    """
    if any(o <= 1.0 for o in decimal_odds):
        raise ValueError("decimal odds must be > 1.0")
    raw = [1.0 / o for o in decimal_odds]
    total = sum(raw)
    return [r / total for r in raw]


def consensus_h2h(event: dict) -> dict:
    """Average de-vigged 1X2 probabilities across all bookmakers for one event.

    `event` is one element of the match_odds() data list.
    Returns {"home": p, "draw": p, "away": p, "bookmakers": n}.
    """
    home, away = event["home_team"], event["away_team"]
    acc = {"home": 0.0, "draw": 0.0, "away": 0.0}
    n = 0
    for bm in event.get("bookmakers", []):
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            prices = {o["name"]: o["price"] for o in market.get("outcomes", [])}
            if home not in prices or away not in prices or "Draw" not in prices:
                continue
            ph, pd, pa = implied_probabilities([prices[home], prices["Draw"], prices[away]])
            acc["home"] += ph
            acc["draw"] += pd
            acc["away"] += pa
            n += 1
    if n == 0:
        return {"home": None, "draw": None, "away": None, "bookmakers": 0}
    return {k: round(v / n, 4) for k, v in acc.items()} | {"bookmakers": n}
