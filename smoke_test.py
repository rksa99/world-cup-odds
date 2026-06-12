#!/usr/bin/env python3
"""Smoke test — run this TONIGHT, before the opener.

Pulls tomorrow's fixtures end to end through all three clients,
computes consensus odds for the opener, runs the freshness gate,
and writes provenance snapshots.

Usage:
    pip install requests
    cp .env.example .env   # then paste your three keys
    python smoke_test.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from clients.base import DataUnavailable, load_env, save_snapshot
from clients.freshness import gate


def main() -> int:
    load_env()
    failures = []

    # ---- 1. football-data.org: tomorrow's fixtures --------------------------
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    fixtures_payload = None
    try:
        from clients.football_data import FootballDataClient
        fd = FootballDataClient()
        fixtures_payload = fd.fixtures(date_from=tomorrow, date_to=tomorrow)
        matches = fixtures_payload["data"].get("matches", [])
        print(f"\n✅ football-data.org — {len(matches)} match(es) on {tomorrow}:")
        for m in matches:
            print(f"   {m['homeTeam']['name']} vs {m['awayTeam']['name']}  (utc: {m['utcDate']})")
        save_snapshot(fixtures_payload, "fixtures", tomorrow)
    except DataUnavailable as e:
        failures.append(str(e))
        print(f"\n❌ {e}")

    # ---- 2. API-Football: standings + injuries (2 quota calls) ---------------
    try:
        from clients.api_football import ApiFootballClient
        af = ApiFootballClient()
        injuries = af.injuries()
        n_inj = len(injuries["data"].get("response", []))
        print(f"\n✅ api-football — injuries endpoint OK ({n_inj} records)")
        save_snapshot(injuries, "injuries", "tournament")
    except DataUnavailable as e:
        failures.append(str(e))
        print(f"\n❌ {e}")

    # ---- 3. The Odds API: verify sport keys, then match odds ------------------
    odds_payload = None
    try:
        from clients.odds_api import OddsApiClient, consensus_h2h
        oc = OddsApiClient()
        sports = oc.list_sports()  # free call
        wc_keys = [s["key"] for s in sports["data"] if "world_cup" in s["key"]]
        print(f"\n✅ the-odds-api — World Cup sport keys live: {wc_keys}")
        odds_payload = oc.match_odds()  # 1 credit
        events = odds_payload["data"]
        print(f"   {len(events)} upcoming events with odds")
        if events:
            first = events[0]
            probs = consensus_h2h(first)
            print(f"   consensus for {first['home_team']} vs {first['away_team']}: {probs}")
        save_snapshot(odds_payload, "odds", "matchday")
    except DataUnavailable as e:
        failures.append(str(e))
        print(f"\n❌ {e}")

    # ---- 4. Freshness gate dry run -----------------------------------------
    inputs = {}
    if odds_payload:
        inputs["odds"] = odds_payload
    if fixtures_payload:
        inputs["stats"] = fixtures_payload   # placeholder until stats agent feeds real model inputs
        inputs["fitness"] = fixtures_payload  # placeholder — wire injuries+news here
    verdict = gate(inputs)
    print(f"\n🚦 freshness gate: {verdict}")

    # ---- summary -------------------------------------------------------------
    if failures:
        print(f"\n⚠️  {len(failures)} client(s) failed — fix before kickoff:")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("\n🏆 All three clients live. System is running on real data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
