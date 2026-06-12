# World Cup 2026 Prediction System — Live Data Spec (v2)

**Status:** Replaces all mock/static/hardcoded data. Effective immediately — tournament kicks off June 11, 2026.
**Hard rule:** No agent may return a prediction derived from fabricated, cached-beyond-TTL, or LLM-imagined data. If live data is unavailable, the agent must return `data_unavailable` with a reason, and the orchestrator must degrade gracefully (see §7).

---

## 1. Data Sources (the real-data backbone)

| Source | Role | Tier | Limits |
|---|---|---|---|
| **football-data.org** | Primary: fixtures, live scores, standings, lineups | Free | 10 calls/min |
| **API-Football** (api-sports.io), `league=1&season=2026` | Secondary: player stats, events, H2H, injuries | Free | 100 req/day |
| **The Odds API** (the-odds-api.com) | Odds: match 1X2 + outright winner markets | Free | ~500 credits/mo |
| **RSS feeds** (BBC Sport, ESPN FC, FIFA.com news) | News/injury monitoring | Free | Poll-friendly |
| **openfootball/worldcup.json** (GitHub raw) | Fallback: schedule + results, no key needed | Free | Unlimited (static JSON) |

API keys live in `.env` only: `FOOTBALL_DATA_TOKEN`, `API_FOOTBALL_KEY`, `ODDS_API_KEY`. Never committed. Every client must send the key via header, log remaining-quota headers, and back off on 429.

---

## 2. Agent-by-Agent Rewiring

### 2.1 Odds Agent (סוכן יחסי הימורים)
- **Replace:** any scraped/hardcoded odds table.
- **Source:** The Odds API — `GET /v4/sports/soccer_fifa_world_cup/odds?regions=eu&markets=h2h` for match odds; `soccer_fifa_world_cup_winner` for outrights.
- **Cadence:** Match odds — once at T-24h, T-6h, T-1h before kickoff (3 calls/match, fits free credits). Outrights — once daily.
- **Output:** implied probabilities (de-vigged), bookmaker count, timestamp.
- **Fail mode:** if quota exhausted → use last snapshot if < 12h old, else `data_unavailable`.

### 2.2 Stats Model Agent (סוכן מודל סטטיסטי)
- **Replace:** any pretrained-on-stale-data assumptions about squads.
- **Source:** API-Football — `/fixtures?league=1&season=2026` (results), `/fixtures/statistics` (shots, possession, xG where present), `/standings`.
- **Final squads only:** squads were locked June 1; pull `/players/squads` once and cache for the whole tournament. No provisional-list players.
- **Cadence:** Once per day pre-match window + once after each completed match (results ingestion). Budget: ≤ 30 req/day.
- **Model inputs must carry a `fetched_at` timestamp**; reject inputs older than 24h for per-match predictions.

### 2.3 Form & Fitness Agent (סוכן כושר ופציעות)
- **Replace:** LLM "general knowledge" about injuries — this is the most dangerous mock-data point in the system.
- **Sources:** API-Football `/injuries?league=1&season=2026` + News Agent feed (§2.4) cross-check. A player is flagged "doubtful" only if at least one structured source or two independent news items say so.
- **Cadence:** Twice daily + T-2h before each match (lineups confirm via football-data.org match endpoint — starting XI is published ~1h before kickoff).
- **Output:** per-team availability delta vs. baseline squad strength.

### 2.4 News Agent (סוכן חדשות)
- **Replace:** unstructured web search calls with no provenance.
- **Source:** RSS polling (BBC Sport football, ESPN FC, FIFA media). Each item stored with URL, source, published timestamp.
- **Cadence:** Every 30 min during tournament days.
- **Job:** entity-extract (team, player, event type: injury/suspension/lineup/turmoil), emit structured events to Form & Fitness and Orchestrator. Hebrew summaries generated at the UI layer only — raw store stays in source language.

### 2.5 Head-to-Head Agent (סוכן היסטוריה)
- **Source:** API-Football `/fixtures/headtohead?h2h={team1}-{team2}`. Historical — fetch once per matchup and cache permanently (history doesn't change).
- **Weight cap:** H2H older than 8 years contributes ≤ 10% to the orchestrator's blend. (Mexico–South Africa 2010 is trivia, not signal.)

### 2.6 Orchestrator (המנצח)
- **New responsibilities:**
  1. **Freshness gate** — refuses to emit a per-match prediction unless odds, stats, and fitness inputs all carry `fetched_at` within their TTLs (odds 12h, stats 24h, fitness 6h, lineup 2h-to-live).
  2. **Provenance ledger** — every prediction is stored with the exact input snapshots that produced it (JSON, one file per prediction under `data/snapshots/`). This makes post-tournament evaluation honest.
  3. **Locked predictions stay locked** — winner + top scorer picks are immutable; orchestrator may publish a daily "confidence tracker" comparing them against live outright odds, clearly labeled as tracking, not revision.

---

## 3. Polling Schedule (daily budget)

| Window | Action | Calls |
|---|---|---|
| 06:00 | Standings, yesterday's results, outright odds | ~10 |
| Per match, T-24h / T-6h / T-1h | Match odds snapshot | 3 |
| Per match, T-2h | Injuries + news sweep | ~5 |
| Per match, T-1h | Confirmed lineups | 1–2 |
| Live (optional) | Score poll every 60s via football-data.org | within 10/min |
| Post-match | Result + statistics ingestion | 2–3 |

With up to 4–6 matches/day in the group stage, this stays inside free tiers. If it doesn't, drop live polling first — predictions are pre-match anyway.

## 4. Caching & Storage
- SQLite (or JSON files) with tables: `fixtures`, `odds_snapshots`, `injuries`, `news_events`, `h2h`, `predictions`, `snapshots`.
- Every row: `source`, `fetched_at`, `raw_payload`.
- TTLs enforced at read time, not write time.

## 5. Time Handling
- Store everything in UTC. Convert to Israel time (Asia/Jerusalem, UTC+3 in June) only in the Hebrew UI. Mexico City kickoffs are UTC-6 — a 13:00 local opener is 22:00 in Israel. Off-by-timezone bugs will silently break the freshness gate.

## 6. Hebrew UI Contract
- UI reads only from the local store, never calls external APIs directly.
- Every displayed prediction shows: עודכן לאחרונה (last updated), מקורות (sources count), and a stale-data badge (נתונים מיושנים) if any input missed its TTL.

## 7. Graceful Degradation Ladder
1. All inputs fresh → full prediction with confidence score.
2. Odds missing → model + fitness only, confidence capped, badge shown.
3. Stats stale → publish odds-implied probabilities only, labeled as such.
4. Everything stale → no prediction. Show last valid one with timestamp. Never invent.

## 8. Migration Checklist (do in this order)
- [ ] Add `.env` with three API keys; register free accounts today (before kickoff traffic).
- [ ] Build thin clients: `clients/football_data.py`, `clients/api_football.py`, `clients/odds_api.py` — each with rate-limit guard + quota logging.
- [ ] Smoke test: pull tomorrow's two fixtures (Mexico–South Africa, South Korea–Czechia) end to end.
- [ ] Delete every mock fixture/odds file from the repo; grep for `mock`, `dummy`, `sample`, `hardcoded`.
- [ ] Wire freshness gate into orchestrator; run one dry prediction for the opener.
- [ ] Snapshot the locked winner/top-scorer predictions with today's date into the provenance ledger.
