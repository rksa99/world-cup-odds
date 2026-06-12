# Claude Code Playbook — Migrating to Live Data

Paste these into Claude Code **one at a time**, in order. Wait for each to
finish and review its diff before moving on. Steps 0–1 you do yourself
(keys/secrets); the rest you hand to Claude Code.

---

## Step 0 — You do this (don't delegate secrets)
```bash
cd ~/your-wc2026-project
unzip ~/Downloads/wc2026_live_data_clients.zip -d .
cp .env.example .env && $EDITOR .env      # paste your 3 real keys
echo ".env" >> .gitignore
pip install requests
```
Register the free accounts first if you haven't:
- football-data.org/client/register  → FOOTBALL_DATA_TOKEN
- dashboard.api-football.com          → API_FOOTBALL_KEY
- the-odds-api.com                     → ODDS_API_KEY

---

## Step 1 — Verify the pipes (paste to Claude Code)
> Run `python smoke_test.py`. If any of the three clients fail, diagnose the
> error (auth, sport-key name, endpoint shape) and fix the client in `clients/`
> until all three return live data. Do not touch `.env` — if a key is missing,
> tell me. Confirm the World Cup sport keys printed by the odds client match
> what the code expects, and update the constants if they differ.

## Step 2 — Map the existing agents
> Read SPEC_LIVE_DATA.md and CLAUDE.md. Then list each of the six agents, and
> for each one tell me exactly where it currently gets its data (file + line),
> and which `clients/` call should replace it. Don't change anything yet — just
> give me the migration table.

## Step 3 — Rip out mock data, agent by agent
> Starting with the odds agent, replace its data source with the matching
> `clients/` call per the migration table. Show me the diff before applying.
> Then do the same for stats, form/fitness, news, and head-to-head — one agent
> per diff, pausing after each so I can review. After all five, run
> `grep -rin "mock\|dummy\|sample\|hardcoded" .` and show me anything left in
> agent code.

## Step 4 — Wire the freshness gate + provenance
> In the orchestrator, integrate `clients/freshness.py` so no per-match
> prediction is emitted unless odds, stats, and fitness inputs pass their TTLs.
> When the gate fails, follow the degradation ladder in SPEC_LIVE_DATA.md §7.
> Add the provenance ledger: every emitted prediction writes its input
> snapshots to `data/snapshots/` via `save_snapshot`. Show me the diff.

## Step 5 — Lock the two pre-tournament predictions
> Snapshot today's locked winner and top-scorer predictions into the provenance
> ledger with today's date, and make them immutable in code. Add a daily
> "confidence tracker" that compares them against live outright odds from the
> odds client, clearly labeled as tracking, not a revised pick.

## Step 6 — Hebrew UI honesty
> Update the Hebrew UI so it reads only from the local store (never calls the
> APIs directly). Every displayed prediction must show: עודכן לאחרונה
> (last updated, in Asia/Jerusalem time), מקורות (source count), and a
> נתונים מיושנים badge when any input missed its TTL. Show me the diff.

## Step 7 — Dry run on the opener
> Run the full pipeline for tomorrow's two fixtures (Mexico vs South Africa,
> South Korea vs Czechia): fetch odds, stats, and fitness; pass them through
> the freshness gate; produce a per-match prediction with a confidence score;
> and write the provenance snapshot. Print the prediction and the snapshot path.
> If the gate blocks it, show me which input failed and why.

---

## Guardrails to repeat if Claude Code drifts
- "Don't fabricate data — if it's missing, return data_unavailable."
- "Show me the diff before applying."
- "Cache H2H and squads permanently; don't re-spend api-football quota."
- "Store UTC; convert to Israel time only in the UI."
