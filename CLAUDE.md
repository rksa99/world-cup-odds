# CLAUDE.md — World Cup 2026 Prediction System

This file is read on every Claude Code session. Follow it strictly.

## What this project is
A FIFA World Cup 2026 prediction system with a Hebrew UI and six agents
(odds, news, statistical model, form/fitness, head-to-head, orchestrator).
Two locked pre-tournament predictions (winner, top scorer) plus per-match
predictions. The full data contract lives in `SPEC_LIVE_DATA.md` — read it
before changing any agent.

## Non-negotiable rules
1. **Real data only.** Every fixture, score, odd, injury, and stat comes from
   `clients/` (football_data, api_football, odds_api). Never fabricate,
   hardcode, or LLM-imagine sports data.
2. **Fail honestly.** If live data is missing or stale, return `data_unavailable`
   with a reason and degrade per `SPEC_LIVE_DATA.md` §7. Never invent a value
   to fill a gap.
3. **Respect free-tier budgets.**
   - api-football: 100 requests/DAY. Cache H2H and squads permanently.
   - the-odds-api: ~500 credits/month. 3 odds snapshots per match max.
   - football-data.org: 10 calls/min (clients already pace this).
4. **Freshness gate.** No per-match prediction may be emitted unless odds,
   stats, and fitness inputs pass their TTLs (`clients/freshness.py`).
5. **Provenance.** Every prediction is stored with the exact input snapshots
   that produced it, under `data/snapshots/`.
6. **Locked predictions stay locked.** Winner and top-scorer picks are
   immutable. You may publish a confidence tracker against live odds, clearly
   labeled as tracking — never as a revised pick.
7. **Time.** Store everything in UTC. Convert to Asia/Jerusalem (UTC+3 in June)
   only at the Hebrew UI layer. Mexico City kickoffs are UTC-6.
8. **Secrets.** API keys live only in `.env`, never committed, never printed,
   never passed to a model. If a key is missing, say so — don't work around it.

## Working style I expect
- Show a diff before applying multi-file edits, especially across the six agents.
- Make one logical change per step; don't refactor everything in a single pass.
- After editing a client or agent, run the relevant smoke/unit check.
- Prefer editing existing files over creating parallel new ones.

## Key files
- `SPEC_LIVE_DATA.md` — the data contract. Source of truth.
- `clients/base.py` — shared HTTP: retries, backoff, quota logging, `fetched_at`.
- `clients/{football_data,api_football,odds_api}.py` — the three sources.
- `clients/freshness.py` — TTL gate for the orchestrator.
- `smoke_test.py` — end-to-end check against the next day's fixtures.

## Definition of done for the migration
- `python smoke_test.py` passes (all three sources return live data).
- `grep -rin "mock\|dummy\|sample\|hardcoded" .` returns nothing in agent code.
- Orchestrator refuses stale predictions and writes provenance snapshots.
- Hebrew UI shows last-updated time, source count, and a stale badge
  (נתונים מיושנים) when any input misses its TTL.
