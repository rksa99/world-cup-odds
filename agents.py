"""
Multi-agent pipeline for World Cup 2026 — v3.0
Layer 3: LLM analysis agents that read real fetched data.
No fabrication. No simulated probabilities.
"""

import json
import time
import concurrent.futures
import requests as _requests

from probability import (
    poisson_model, elo_model, blend_probabilities,
    compute_expected_xg, market_implied,
    compute_all_markets, find_best_bet, apply_adjustments,
    ELO_DEFAULTS, POISSON_ELO_BLEND, VALUE_THRESHOLD,
)
from fetchers import (
    fetch_match_odds, fetch_match_stats, fetch_match_news,
    fetch_match_stats_fallback, fetch_outright_odds,
)
from data import TEAM_STATS, H2H_RECORDS

# ---------------------------------------------------------------------------
# Provider / model catalogue
# ---------------------------------------------------------------------------

PROVIDERS = {
    "anthropic": {
        "label": "Anthropic",
        "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-4o", "gpt-4.1", "gpt-4o-mini", "o3", "o4-mini"],
    },
    "google": {
        "label": "Google Gemini",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
                   "gemini-2.5-flash-lite"],
    },
    "openrouter": {
        "label": "OpenRouter",
        "models": [
            "meta-llama/llama-3.3-70b-instruct",
            "mistralai/mistral-large",
            "deepseek/deepseek-r1",
            "google/gemini-2.5-pro",
        ],
    },
}

DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-7",
    "openai":    "gpt-4o",
    "google":    "gemini-2.0-flash",
    "openrouter":"meta-llama/llama-3.3-70b-instruct",
}

PRICING = {
    "claude-opus-4-7":   {"in": 5.00,  "out": 25.00},
    "claude-sonnet-4-6": {"in": 3.00,  "out": 15.00},
    "claude-haiku-4-5":  {"in": 1.00,  "out":  5.00},
    "gpt-4o":            {"in": 2.50,  "out": 10.00},
    "gpt-4.1":           {"in": 2.00,  "out":  8.00},
    "gpt-4o-mini":       {"in": 0.15,  "out":  0.60},
    "o3":                {"in": 10.00, "out": 40.00},
    "o4-mini":           {"in": 1.10,  "out":  4.40},
    "gemini-2.5-pro":    {"in": 1.25,  "out": 10.00},
    "gemini-2.0-flash":  {"in": 0.075, "out":  0.30},
    "gemini-2.5-flash":  {"in": 0.075, "out":  0.30},
    "meta-llama/llama-3.3-70b-instruct": {"in": 0.08, "out": 0.30},
    "mistralai/mistral-large":           {"in": 2.00, "out": 6.00},
    "deepseek/deepseek-r1":              {"in": 0.55, "out": 2.19},
    "google/gemini-2.5-pro":             {"in": 1.25, "out": 10.00},
}

# ---------------------------------------------------------------------------
# Default agent configs (shown in agents modal; system prompts are editable)
# ---------------------------------------------------------------------------

DEFAULT_AGENT_CONFIGS = {
    "news": {
        "name": "News Analysis",
        "name_he": "ניתוח חדשות",
        "description": "Reads real NewsAPI articles and extracts injury/lineup impact",
        "weight": 0.20,
        "data_sources": "NewsAPI — real articles from BBC Sport, ESPN, Sky Sports, Marca, L'Equipe, The Athletic",
        "note": "This agent reads REAL news articles fetched live from NewsAPI. It only reports facts found in the articles — it does not invent. Requires NEWSAPI_KEY.",
        "system": (
            "You are a football intelligence analyst reading real pre-match news articles. "
            "Extract only facts stated in the provided articles. "
            "Identify confirmed injuries, suspensions, lineup changes, and tactical signals. "
            "For each finding, estimate its directional impact on match probabilities. "
            "If no relevant articles are provided or they contain nothing material, say so explicitly. "
            "Return valid JSON only."
        ),
    },
    "form": {
        "name": "Form Analysis",
        "name_he": "ניתוח כושר",
        "description": "Interprets real recent fixture data from API-Football",
        "weight": 0.15,
        "data_sources": "API-Football — last 10 fixtures with xG, shots, possession, results",
        "note": "This agent interprets REAL fixture data fetched from API-Football. xG trends, fatigue patterns, and defensive form are derived from actual match statistics. Requires API_FOOTBALL_KEY.",
        "system": (
            "You are a football form analyst interpreting real match statistics. "
            "Analyse xG trends, results patterns, fatigue indicators, and defensive form. "
            "Identify if a team is over- or under-performing their underlying xG. "
            "Assess fatigue risk based on match density and travel. "
            "Output qualitative form modifiers (small positive/negative floats, e.g. +0.03), "
            "not raw probabilities. Return valid JSON only."
        ),
    },
    "h2h": {
        "name": "H2H Analysis",
        "name_he": "עימותים ישירים",
        "description": "Interprets real head-to-head records from API-Football",
        "weight": 0.05,
        "data_sources": "API-Football — all historical H2H fixtures, scores, competitions",
        "note": "This agent interprets REAL H2H records fetched from API-Football. It analyses patterns from actual match results, not from memory. Requires API_FOOTBALL_KEY.",
        "system": (
            "You are a football historian analysing real head-to-head records. "
            "Weight competitive matches over friendlies. "
            "Identify genuine psychological patterns from the actual data provided. "
            "If fewer than 5 meetings exist, reduce confidence accordingly. "
            "Output a small probability modifier (-0.05 to +0.05) not a raw prediction. "
            "Return valid JSON only."
        ),
    },
    "value": {
        "name": "Value Bet Analyst",
        "name_he": "מציאת ערך",
        "description": "Selects the best value bet from the pre-computed EV table",
        "weight": None,
        "data_sources": "Pre-computed EV table (Poisson+Elo model vs live bookmaker odds)",
        "note": "This agent does NOT compute probabilities — it receives the pre-computed expected value table and selects the single best bet. It considers line movement and qualitative signals to confirm or override the top EV pick.",
        "system": (
            "You are a professional value bettor. You receive a pre-computed expected value table "
            "showing EV%, edge%, Kelly stake, and line movement for every available market. "
            "Select the single best bet. Consider: "
            "(1) highest EV markets, "
            "(2) whether line movement (steam) confirms the model edge, "
            "(3) whether confirmed news/injuries materially affect the pick. "
            "If no market has EV > 5%, return a NO BET recommendation. "
            "Do not recompute probabilities. Use only the data provided. "
            "Return valid JSON only."
        ),
    },
    "orchestrator": {
        "name": "Orchestrator",
        "name_he": "מתזמר",
        "description": "Assembles the final prediction card from all agent outputs",
        "weight": None,
        "data_sources": "All agent outputs + Poisson/Elo model probabilities",
        "note": "The orchestrator synthesizes all layer outputs into the final prediction card. It does not call external APIs.",
        "system": (
            "You are the chief analyst producing the final match prediction report. "
            "You receive model probabilities (Poisson+Elo, adjusted for news/form/h2h), "
            "live bookmaker odds, and a best bet recommendation. "
            "Write a concise confidence explanation and 3-5 key drivers. "
            "Make drivers specific to this match — reference actual data points. "
            "Return valid JSON only."
        ),
    },
}


def _merge_configs(overrides: dict | None) -> dict:
    if not overrides:
        return {k: dict(v) for k, v in DEFAULT_AGENT_CONFIGS.items()}
    merged = {k: dict(v) for k, v in DEFAULT_AGENT_CONFIGS.items()}
    for key, patch in overrides.items():
        if key in merged:
            merged[key].update(patch)
    return merged


# ---------------------------------------------------------------------------
# Generic LLM call → (text, usage_dict)
# ---------------------------------------------------------------------------

def _post_with_retry(url, **kwargs):
    for attempt in range(4):
        resp = _requests.post(url, **kwargs)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
            wait = float(retry_after) if retry_after else (attempt + 1) * 20
            import sys; print(f"[RATE LIMIT] 429 attempt {attempt+1}, waiting {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def _call_anthropic(system, prompt, api_key, model):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    kwargs = dict(model=model, max_tokens=2048, system=system,
                  messages=[{"role": "user", "content": prompt}])
    if model.startswith("claude-opus-4") or model.startswith("claude-sonnet-4"):
        kwargs["thinking"] = {"type": "adaptive"}
    msg = client.messages.create(**kwargs)
    text = next(b.text for b in msg.content if b.type == "text")
    return text, {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens}


def _call_openai_compat(url, system, prompt, api_key, model):
    resp = _post_with_retry(url, json={
        "model": model, "temperature": 0.3,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    u = data.get("usage", {})
    return text, {"input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0)}


def _call_google(system, prompt, api_key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    resp = _post_with_retry(url, json={
        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
    }, timeout=60)
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    um = data.get("usageMetadata", {})
    return text, {"input": um.get("promptTokenCount", 0), "output": um.get("candidatesTokenCount", 0)}


def call_llm(system: str, prompt: str, provider: str, api_key: str, model: str):
    if provider == "anthropic":
        return _call_anthropic(system, prompt, api_key, model)
    elif provider == "openai":
        return _call_openai_compat("https://api.openai.com/v1/chat/completions", system, prompt, api_key, model)
    elif provider == "google":
        return _call_google(system, prompt, api_key, model)
    elif provider == "openrouter":
        return _call_openai_compat("https://openrouter.ai/api/v1/chat/completions", system, prompt, api_key, model)
    raise ValueError(f"Unknown provider: {provider}")


def test_ai_connection(provider: str, api_key: str, model: str):
    """Lightweight ping to verify an AI provider key + model. Returns (ok, msg)."""
    if provider not in PROVIDERS:
        return False, f"ספק לא ידוע: {provider}"
    try:
        text, usage = call_llm("Reply with the single word OK.", "ping",
                               provider, api_key, model)
        return True, f"מחובר · {model} ✓"
    except Exception as e:
        s = str(e)
        if "401" in s or "authentication" in s.lower() or "api key" in s.lower() or "invalid" in s.lower():
            return False, "מפתח לא תקין"
        if "404" in s or "not found" in s.lower() or "does not exist" in s.lower():
            return False, f"מודל לא נמצא: {model}"
        if "429" in s or "rate" in s.lower() or "quota" in s.lower():
            return False, "חריגה ממכסה (429)"
        return False, f"שגיאה: {s[:120]}"


def _parse_json(text: str) -> dict:
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in response: {text[:200]!r}")
    return json.loads(text[start:end + 1])


def _zero_usage():
    return {"input": 0, "output": 0}


def _score_matches_outcome(score: str, outcome: str) -> bool:
    """True if a 'H-A' scoreline is consistent with home_win/draw/away_win."""
    if not score or "-" not in str(score):
        return False
    try:
        h, a = (int(x) for x in str(score).split("-")[:2])
    except (ValueError, TypeError):
        return False
    if outcome == "home_win":
        return h > a
    if outcome == "away_win":
        return a > h
    if outcome == "draw":
        return h == a
    return True


# ---------------------------------------------------------------------------
# Layer 3 — LLM Analysis Agents
# All receive REAL fetched data. They output modifiers, not raw probabilities.
# ---------------------------------------------------------------------------

def news_analysis_agent(home: str, away: str, news_data: dict | None,
                         provider, api_key, model, cfg) -> tuple[dict, dict]:
    if not news_data or not news_data.get("articles"):
        return {
            "alerts": [], "overall_impact": "NEUTRAL",
            "news_adjustment_home": 0.0, "news_adjustment_away": 0.0,
            "articles_read": 0, "key_finding": "No news data available",
            "data_source": "none",
        }, _zero_usage()

    articles = news_data["articles"][:10]
    article_text = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['description'] or ''}\n{a['content_snippet'] or ''}"
        for a in articles
    )

    prompt = f"""You are reading {len(articles)} REAL news articles about {home} vs {away} in the 2026 FIFA World Cup.

ARTICLES:
{article_text}

Extract only facts stated in these articles. Return JSON:
{{
    "alerts": [
        {{
            "headline": "<exact headline from article>",
            "source": "<news source>",
            "impact_direction": "HOME_POSITIVE|AWAY_POSITIVE|NEUTRAL",
            "prob_delta": <float, e.g. -0.07 means reduces home win prob by 7%>,
            "confidence": "HIGH|MEDIUM|LOW",
            "fact_basis": "<what exactly in the article supports this>"
        }}
    ],
    "overall_impact": "HOME_POSITIVE|AWAY_POSITIVE|NEUTRAL",
    "news_adjustment_home": <net float adjustment to home win probability, e.g. -0.05>,
    "news_adjustment_away": <net float adjustment to away win probability>,
    "key_finding": "<single most important fact from the articles, or 'No material findings'>",
    "articles_read": {len(articles)}
}}
If no articles contain material pre-match information, return empty alerts and 0.0 adjustments."""

    try:
        text, usage = call_llm(cfg["system"], prompt, provider, api_key, model)
        result = _parse_json(text)
        result["data_source"] = "NewsAPI (live)"
        return result, usage
    except Exception as e:
        import sys; print(f"[news_analysis_agent] {e}", file=sys.stderr)
        return {
            "alerts": [], "overall_impact": "NEUTRAL",
            "news_adjustment_home": 0.0, "news_adjustment_away": 0.0,
            "articles_read": len(articles), "key_finding": "Parse error",
            "data_source": "NewsAPI (live)",
        }, _zero_usage()


def form_analysis_agent(home: str, away: str, stats_data: dict | None,
                         provider, api_key, model, cfg) -> tuple[dict, dict]:
    if not stats_data:
        return {
            "home_form_trend": "UNKNOWN", "away_form_trend": "UNKNOWN",
            "home_fatigue_risk": "UNKNOWN", "away_fatigue_risk": "UNKNOWN",
            "form_modifier_home": 0.0, "form_modifier_away": 0.0,
            "key_observations": ["No live stats data available — using fallback model"],
            "data_source": "none",
        }, _zero_usage()

    hf = stats_data["home"]["form"]
    af = stats_data["away"]["form"]
    h_inj = stats_data["home"].get("injuries", [])
    a_inj = stats_data["away"].get("injuries", [])

    prompt = f"""Analyse REAL recent form data for {home} vs {away} in the 2026 FIFA World Cup.

{home} — Last {hf.get('games_played', '?')} games:
  Results: {hf.get('results', [])}
  Goals scored/game: {hf.get('goals_for_per_game', '?')}
  Goals conceded/game: {hf.get('goals_against_per_game', '?')}
  xG/game: {hf.get('xg_per_game', 'N/A')}
  xGA/game: {hf.get('xga_per_game', 'N/A')}
  Clean sheets: {hf.get('clean_sheets', '?')}
  Injured players: {json.dumps(h_inj[:5])}

{away} — Last {af.get('games_played', '?')} games:
  Results: {af.get('results', [])}
  Goals scored/game: {af.get('goals_for_per_game', '?')}
  Goals conceded/game: {af.get('goals_against_per_game', '?')}
  xG/game: {af.get('xg_per_game', 'N/A')}
  xGA/game: {af.get('xga_per_game', 'N/A')}
  Clean sheets: {af.get('clean_sheets', '?')}
  Injured players: {json.dumps(a_inj[:5])}

Return JSON:
{{
    "home_form_trend": "IMPROVING|STABLE|DECLINING",
    "away_form_trend": "IMPROVING|STABLE|DECLINING",
    "home_fatigue_risk": "LOW|MEDIUM|HIGH",
    "away_fatigue_risk": "LOW|MEDIUM|HIGH",
    "form_modifier_home": <float -0.06 to +0.06>,
    "form_modifier_away": <float -0.06 to +0.06>,
    "key_observations": ["<fact-based observation>", ...],
    "summary": "<2 sentence summary citing actual numbers>"
}}"""

    try:
        text, usage = call_llm(cfg["system"], prompt, provider, api_key, model)
        result = _parse_json(text)
        result["data_source"] = "API-Football (live)"
        return result, usage
    except Exception as e:
        import sys; print(f"[form_analysis_agent] {e}", file=sys.stderr)
        return {
            "home_form_trend": "UNKNOWN", "away_form_trend": "UNKNOWN",
            "home_fatigue_risk": "LOW", "away_fatigue_risk": "LOW",
            "form_modifier_home": 0.0, "form_modifier_away": 0.0,
            "key_observations": ["Form data parse error"],
            "data_source": "API-Football (live)",
        }, _zero_usage()


def h2h_analysis_agent(home: str, away: str, stats_data: dict | None,
                        provider, api_key, model, cfg) -> tuple[dict, dict]:
    # Fall back to local H2H_RECORDS if no live data
    h2h = None
    source = "none"
    if stats_data:
        h2h = stats_data.get("h2h")
        source = "API-Football (live)"
    if not h2h or h2h.get("meetings", 0) == 0:
        h2h_local = H2H_RECORDS.get((home, away)) or H2H_RECORDS.get((away, home))
        if h2h_local:
            h2h = h2h_local
            source = "local database"

    if not h2h or h2h.get("meetings", 0) == 0:
        return {
            "h2h_home_win_rate": 0.40, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.35,
            "psychological_edge": "EVEN", "h2h_modifier_home": 0.0,
            "meetings": 0, "summary": "No H2H data available",
            "data_source": source,
        }, _zero_usage()

    prompt = f"""Analyse REAL head-to-head data for {home} vs {away} in the 2026 FIFA World Cup.

H2H Record:
{json.dumps(h2h, indent=2)}

Return JSON:
{{
    "h2h_home_win_rate": <float from actual data>,
    "h2h_draw_rate": <float from actual data>,
    "h2h_away_win_rate": <float from actual data>,
    "psychological_edge": "{home}|{away}|EVEN",
    "h2h_modifier_home": <float -0.05 to +0.05, based on H2H pattern>,
    "meetings": <int>,
    "competitive_weighted": <bool, true if you weighted competitive matches more>,
    "summary": "<2 sentences citing actual records>"
}}"""

    try:
        text, usage = call_llm(cfg["system"], prompt, provider, api_key, model)
        result = _parse_json(text)
        result["data_source"] = source
        return result, usage
    except Exception as e:
        import sys; print(f"[h2h_analysis_agent] {e}", file=sys.stderr)
        win_rate = h2h.get("home_win_rate", 0.40)
        return {
            "h2h_home_win_rate": win_rate,
            "h2h_draw_rate": h2h.get("draw_rate", 0.25),
            "h2h_away_win_rate": h2h.get("away_win_rate", 0.35),
            "psychological_edge": "EVEN", "h2h_modifier_home": 0.0,
            "meetings": h2h.get("meetings", 0), "summary": "H2H data parse error",
            "data_source": source,
        }, _zero_usage()


def _bet_from_market(m: dict) -> dict:
    """Build a best_bet card from a computed market row (pure math, no LLM)."""
    return {
        "market": m["market"],
        "selection": m["market"],
        "bookmaker": m.get("best_book", ""),
        "odds": m["best_odds"],
        "model_probability_pct": round(m["model_prob"] * 100, 1),
        "market_implied_pct": round((m.get("market_implied_prob") or 0) * 100, 1),
        "edge_pct": round(m["edge"] * 100, 1),
        "expected_value_pct": round(m["ev"] * 100, 1),
        "kelly_stake_pct": round(m["kelly"] * 100, 1),
        "recommended_stake_pct": round(m["kelly"] * 100, 1),
        "confidence": "HIGH" if m["kelly"] >= 0.03 else "MEDIUM" if m["kelly"] >= 0.012 else "LOW",
        "reasoning": (f"ערך חיובי {m['ev']*100:.1f}% על {m['market']} — "
                      f"מחיר {m['best_odds']:.2f} אצל {m.get('best_book') or 'הספר הטוב ביותר'} "
                      f"מול הוגן {(1/(m['best_odds']) + m['edge'])*100:.1f}%. Kelly {m['kelly']*100:.1f}%."),
    }


def build_value_result(all_markets_ev: dict, odds_data: dict | None) -> tuple[dict, dict]:
    """
    Deterministic value-bet selection (no LLM). Picks the best bet by risk-adjusted
    Kelly via find_best_bet, plus a runner-up. Returns the same shape the UI expects.
    """
    if not all_markets_ev:
        return {
            "best_bet": None, "runner_up": None,
            "no_bet_reason": "No live odds available — cannot compute value",
            "overall_confidence": "LOW", "line_movement_signal": "UNKNOWN",
        }, _zero_usage()

    lm = odds_data.get("line_movement", {}) if odds_data else {}
    lm_signal = "CONFIRMS_MODEL" if lm.get("steam_detected") else ("UNKNOWN" if not lm else "NEUTRAL")

    best = find_best_bet(all_markets_ev)
    if not best:
        return {
            "best_bet": None,
            "no_bet_reason": f"לא נמצא הימור עם ערך חיובי מעל {int(VALUE_THRESHOLD*100)}% EV",
            "overall_confidence": "LOW", "line_movement_signal": lm_signal,
        }, _zero_usage()

    # Runner-up: next best value market that isn't the chosen one
    others = [v for v in all_markets_ev.values()
              if v.get("is_value") and v["market"] != best["market"]]
    runner = max(others, key=lambda x: (x["kelly"], x["ev"])) if others else None

    return {
        "best_bet": _bet_from_market(best),
        "runner_up": _bet_from_market(runner) if runner else None,
        "line_movement_signal": lm_signal,
        "overall_confidence": _bet_from_market(best)["confidence"],
    }, _zero_usage()


def value_bet_agent(home: str, away: str,
                    adjusted_probs: dict, market_implied_probs: dict | None,
                    all_markets_ev: dict, odds_data: dict | None,
                    news_result: dict, form_result: dict,
                    provider, api_key, model, cfg) -> tuple[dict, dict]:

    if not all_markets_ev:
        return {
            "best_bet": None,
            "runner_up": None,
            "no_bet_reason": "No live odds available — cannot compute value",
            "overall_confidence": "LOW",
            "line_movement_signal": "UNKNOWN",
        }, _zero_usage()

    # Build line movement summary
    lm = odds_data.get("line_movement", {}) if odds_data else {}
    lm_text = ""
    if lm.get("steam_detected"):
        lm_text = f"STEAM MOVE detected: {lm.get('movement', 'unknown direction')} ({lm.get('delta_pct', '?')}%)"
    elif lm:
        lm_text = f"Stable market. Open: {lm.get('open', '?')} → Current: {lm.get('current', '?')}"
    else:
        lm_text = "No line movement data available"

    ev_table = json.dumps({k: {
        "market": v["market"], "ev_pct": f"{v['ev']*100:.1f}%",
        "edge_pct": f"{v['edge']*100:.1f}%",
        "kelly_stake_pct": f"{v['kelly']*100:.1f}%",
        "best_odds": v["best_odds"], "best_book": v.get("best_book", ""),
        "model_prob": f"{v['model_prob']*100:.1f}%",
        "market_implied_prob": f"{(v.get('market_implied_prob') or 0)*100:.1f}%",
        "is_value": v["is_value"],
    } for k, v in all_markets_ev.items()}, indent=2)

    prompt = f"""You are a professional value bettor analysing {home} vs {away} in the 2026 FIFA World Cup.

PRE-COMPUTED EXPECTED VALUE TABLE (from Poisson+Elo model vs live bookmaker odds):
{ev_table}

LINE MOVEMENT: {lm_text}

NEWS KEY FINDING: {news_result.get('key_finding', 'N/A')}
NEWS OVERALL IMPACT: {news_result.get('overall_impact', 'NEUTRAL')}

FORM:
  {home}: {form_result.get('home_form_trend', 'UNKNOWN')}, fatigue: {form_result.get('home_fatigue_risk', 'UNKNOWN')}
  {away}: {form_result.get('away_form_trend', 'UNKNOWN')}, fatigue: {form_result.get('away_fatigue_risk', 'UNKNOWN')}

Select the BEST single bet. Rules:
- Only recommend if EV > 5%
- If steam move confirms model edge, increase confidence
- If news is critical and changes the picture, factor it in
- Do not recompute probabilities — use the table

Return JSON:
{{
    "best_bet": {{
        "market_key": "<key from EV table, e.g. '1x2_home'>",
        "market": "<human label>",
        "selection": "<e.g. '{home} Win'>",
        "bookmaker": "<best book>",
        "odds": <float>,
        "model_probability_pct": <float, e.g. 62.0>,
        "market_implied_pct": <float>,
        "edge_pct": <float>,
        "expected_value_pct": <float>,
        "kelly_stake_pct": <float>,
        "recommended_stake_pct": <float, quarter Kelly>,
        "confidence": "HIGH|MEDIUM|LOW",
        "reasoning": "<2-3 sentences referencing actual EV numbers, line movement, and news>"
    }},
    "runner_up": {{ same structure or null }},
    "no_bet_markets": ["<market label>", ...],
    "line_movement_signal": "CONFIRMS_MODEL|CONTRADICTS_MODEL|NEUTRAL|UNKNOWN",
    "overall_confidence": "HIGH|MEDIUM|LOW"
}}
If no market has EV > 5%, set best_bet to null and explain in reasoning field at top level:
{{ "best_bet": null, "no_bet_reason": "<explanation>", "overall_confidence": "LOW" }}"""

    try:
        text, usage = call_llm(cfg["system"], prompt, provider, api_key, model)
        return _parse_json(text), usage
    except Exception as e:
        import sys; print(f"[value_bet_agent] {e}", file=sys.stderr)
        best = find_best_bet(all_markets_ev)
        if best:
            return {
                "best_bet": {
                    "market": best["market"],
                    "selection": best["market"],
                    "bookmaker": best.get("best_book", ""),
                    "odds": best["best_odds"],
                    "model_probability_pct": round(best["model_prob"] * 100, 1),
                    "market_implied_pct": round((best.get("market_implied_prob") or 0) * 100, 1),
                    "edge_pct": round(best["edge"] * 100, 1),
                    "expected_value_pct": round(best["ev"] * 100, 1),
                    "kelly_stake_pct": round(best["kelly"] * 100, 1),
                    "recommended_stake_pct": round(best["kelly"] * 100, 1),
                    "confidence": "MEDIUM",
                    "reasoning": f"EV {best['ev']*100:.1f}% on {best['market']} (parse fallback)",
                },
                "runner_up": None,
                "line_movement_signal": "UNKNOWN",
                "overall_confidence": "MEDIUM",
            }, _zero_usage()
        return {
            "best_bet": None,
            "no_bet_reason": "No value bet found above 5% EV threshold",
            "overall_confidence": "LOW",
        }, _zero_usage()


def orchestrator_agent(home: str, away: str,
                        adjusted_probs: dict, market_implied_probs: dict | None,
                        best_bet_result: dict, news_result: dict,
                        form_result: dict, h2h_result: dict,
                        odds_data: dict | None, stats_data: dict | None,
                        provider, api_key, model, cfg) -> tuple[dict, dict]:

    best_bet = best_bet_result.get("best_bet")
    market_str = json.dumps(market_implied_probs, indent=2) if market_implied_probs else "Not available"

    prompt = f"""Produce the final match prediction for {home} vs {away} at the 2026 FIFA World Cup.

MODEL PROBABILITIES (Poisson+Elo, adjusted):
  {home} Win: {adjusted_probs['home_win_prob']*100:.1f}%
  Draw: {adjusted_probs['draw_prob']*100:.1f}%
  {away} Win: {adjusted_probs['away_win_prob']*100:.1f}%
  Home xG: {adjusted_probs.get('home_xg', '?')}
  Away xG: {adjusted_probs.get('away_xg', '?')}
  Most likely score: {adjusted_probs.get('most_likely_score', '?')}

MARKET IMPLIED PROBABILITIES:
{market_str}

BEST BET: {json.dumps(best_bet, indent=2) if best_bet else "NO VALUE BET FOUND"}

NEWS: {news_result.get('key_finding', 'N/A')} (impact: {news_result.get('overall_impact', 'NEUTRAL')})
FORM: {home} {form_result.get('home_form_trend', '?')}, {away} {form_result.get('away_form_trend', '?')}
H2H: {h2h_result.get('summary', 'N/A')}

Return JSON:
{{
    "result_prediction": "home_win|draw|away_win",
    "home_win_prob": <int percentage>,
    "draw_prob": <int percentage>,
    "away_win_prob": <int percentage>,
    "predicted_score": "<string>",
    "home_xg": <float>,
    "away_xg": <float>,
    "confidence": "HIGH|MEDIUM|LOW",
    "confidence_explanation": "<one sentence>",
    "key_drivers": [
        {{"icon": "✓|~|⚠", "text": "<specific, data-backed driver>", "agent": "<source>", "severity": "CRITICAL|SIGNIFICANT|MINOR"}}
    ]
}}"""

    # Coherent outcome + scoreline (used for fallback and to sanitise LLM output)
    probs = {
        "home_win": adjusted_probs["home_win_prob"],
        "draw":     adjusted_probs["draw_prob"],
        "away_win": adjusted_probs["away_win_prob"],
    }
    pred = max(probs, key=probs.get)
    sbo = adjusted_probs.get("score_by_outcome") or {}
    coherent_score = sbo.get(pred) or adjusted_probs.get("most_likely_score", "1-1")
    outcome_label = {"home_win": home, "draw": "תיקו", "away_win": away}[pred]

    try:
        text, usage = call_llm(cfg["system"], prompt, provider, api_key, model)
        result = _parse_json(text)
        # Ensure the scoreline matches the predicted outcome (avoid "home win" + 1-1 draw)
        if not _score_matches_outcome(result.get("predicted_score"), result.get("result_prediction", pred)):
            result["predicted_score"] = coherent_score
        result.setdefault("outcome_label", outcome_label)
        return result, usage
    except Exception as e:
        import sys; print(f"[orchestrator_agent] {e}", file=sys.stderr)
        return {
            "result_prediction": pred,
            "outcome_label": outcome_label,
            "home_win_prob": round(adjusted_probs["home_win_prob"] * 100),
            "draw_prob":     round(adjusted_probs["draw_prob"] * 100),
            "away_win_prob": round(adjusted_probs["away_win_prob"] * 100),
            "predicted_score": coherent_score,
            "home_xg": adjusted_probs.get("home_xg", 1.2),
            "away_xg": adjusted_probs.get("away_xg", 1.0),
            "confidence": "MEDIUM",
            "confidence_explanation": "Model-based prediction (orchestrator fallback)",
            "key_drivers": [],
        }, _zero_usage()


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_prediction_pipeline(home: str, away: str,
                              provider: str, api_key: str, model: str,
                              agent_overrides: dict | None = None,
                              odds_api_key: str = "",
                              api_football_key: str = "",
                              newsapi_key: str = "") -> dict:

    if home == "TBD" or away == "TBD":
        return {"error": "Fixture not yet determined"}

    cfgs = _merge_configs(agent_overrides)

    # ── Layer 1: Parallel data fetch ─────────────────────────────────────────
    import sys
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        odds_fut  = ex.submit(fetch_match_odds,  home, away, odds_api_key)
        stats_fut = ex.submit(fetch_match_stats, home, away, api_football_key)
        news_fut  = ex.submit(fetch_match_news,  home, away, newsapi_key)

    odds_data  = None
    stats_data = None
    news_data  = None
    try: odds_data  = odds_fut.result()
    except Exception as e: print(f"[pipeline] odds fetch: {e}", file=sys.stderr)
    try: stats_data = stats_fut.result()
    except Exception as e: print(f"[pipeline] stats fetch: {e}", file=sys.stderr)
    try: news_data  = news_fut.result()
    except Exception as e: print(f"[pipeline] news fetch: {e}", file=sys.stderr)

    # Fallback stats from local TEAM_STATS if API-Football unavailable
    local_home = TEAM_STATS.get(home, {})
    local_away = TEAM_STATS.get(away, {})

    # ── Layer 2: Probability engine (pure Python, no LLM) ─────────────────────
    # Compute expected xG
    if stats_data:
        h_xg, a_xg = compute_expected_xg(stats_data["home"], stats_data["away"])
    else:
        # Fall back to TEAM_STATS local data
        h_xg = local_home.get("xg_per90", 1.35)
        a_xg = local_away.get("xg_per90", 1.10)

    # Host-nation home advantage (USA/Mexico/Canada play in their own country)
    from probability import HOST_NATIONS, HOST_ELO_BONUS
    is_host_home = home in HOST_NATIONS
    if is_host_home:
        h_xg = round(h_xg * 1.15, 2)   # hosts score ~15% more at home
        a_xg = round(a_xg * 0.90, 2)   # and concede less

    poisson_probs = poisson_model(h_xg, a_xg)

    # Elo model
    home_elo = local_home.get("elo") or ELO_DEFAULTS.get(home, 1800)
    away_elo = local_away.get("elo") or ELO_DEFAULTS.get(away, 1800)
    elo_probs = elo_model(home, away, home_elo, away_elo,
                          home_advantage=HOST_ELO_BONUS if is_host_home else 0.0)

    # Blend
    model_probs = blend_probabilities(poisson_probs, elo_probs)

    # Market implied (uses Pinnacle odds as reference)
    implied = None
    if odds_data and odds_data.get("h2h"):
        implied = market_implied(odds_data["h2h"])
        # Add totals + btts implied
        if odds_data.get("totals"):
            t = odds_data["totals"]
            if implied and t.get("avg_over"):
                implied["over25"]  = round(1 / t["avg_over"],  4)
                implied["under25"] = round(1 / t["avg_under"], 4)
        if odds_data.get("btts"):
            b = odds_data["btts"]
            if implied and b.get("avg_yes"):
                implied["btts_yes"] = round(1 / b["avg_yes"], 4)

    # First-pass value calculation (before LLM adjustments)
    first_pass_ev = compute_all_markets(model_probs, odds_data, implied, home, away)

    # ── Layer 3: LLM analysis agents (run in parallel) ────────────────────────
    # All providers run concurrently. The retry/backoff in _post_with_retry handles
    # rate limits; if an agent still fails it only forfeits its small modifier (the
    # core probabilities come from the math layer), so parallelism is accuracy-safe.
    def run_agents():
        agent_fns = {
            "news": lambda: news_analysis_agent(home, away, news_data,  provider, api_key, model, cfgs["news"]),
            "form": lambda: form_analysis_agent(home, away, stats_data, provider, api_key, model, cfgs["form"]),
            "h2h":  lambda: h2h_analysis_agent( home, away, stats_data, provider, api_key, model, cfgs["h2h"]),
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futures = {k: ex.submit(fn) for k, fn in agent_fns.items()}
            return {k: v.result() for k, v in futures.items()}

    raw = run_agents()
    news_result, news_usage = raw["news"]
    form_result, form_usage = raw["form"]
    h2h_result,  h2h_usage  = raw["h2h"]

    # Apply qualitative adjustments to model probabilities
    adjusted_probs = apply_adjustments(
        model_probs,
        news_adj_home = news_result.get("news_adjustment_home", 0.0),
        news_adj_away = news_result.get("news_adjustment_away", 0.0),
        form_adj_home = form_result.get("form_modifier_home", 0.0),
        form_adj_away = form_result.get("form_modifier_away", 0.0),
        h2h_adj_home  = h2h_result.get("h2h_modifier_home", 0.0),
    )

    # Recompute EV after adjustments
    final_ev = compute_all_markets(adjusted_probs, odds_data, implied, home, away)

    # ── Value Bet (pure math — no LLM round-trip) ─────────────────────────────
    # The best bet is selected deterministically by find_best_bet (the source of
    # truth). Skipping the LLM narration here removes a full sequential round-trip
    # with zero impact on which bet is chosen or its EV/Kelly numbers.
    value_result, value_usage = build_value_result(final_ev, odds_data)

    # ── Orchestrator ──────────────────────────────────────────────────────────
    orch_result, orch_usage = orchestrator_agent(
        home, away, adjusted_probs, implied,
        value_result, news_result, form_result, h2h_result,
        odds_data, stats_data,
        provider, api_key, model, cfgs["orchestrator"]
    )

    # ── Token stats ───────────────────────────────────────────────────────────
    price = PRICING.get(model, {"in": 0, "out": 0})
    usages = {"news": news_usage, "form": form_usage, "h2h": h2h_usage,
              "value": value_usage, "orchestrator": orch_usage}
    total_in = total_out = 0
    agent_rows = []
    for key_name, u in usages.items():
        ti, to = u["input"], u["output"]
        total_in += ti; total_out += to
        cost = (ti * price["in"] + to * price["out"]) / 1_000_000
        agent_rows.append({"agent": cfgs.get(key_name, {}).get("name", key_name),
                            "input_tokens": ti, "output_tokens": to,
                            "cost_usd": round(cost, 6)})
    total_cost = (total_in * price["in"] + total_out * price["out"]) / 1_000_000

    # ── Assemble final output ─────────────────────────────────────────────────
    return {
        # Prediction card fields (for match card display)
        "home": home, "away": away,
        "result_prediction": orch_result.get("result_prediction", "draw"),
        "outcome_label":  orch_result.get("outcome_label"),
        "home_win_prob":  orch_result.get("home_win_prob"),
        "draw_prob":      orch_result.get("draw_prob"),
        "away_win_prob":  orch_result.get("away_win_prob"),
        "predicted_score":orch_result.get("predicted_score"),
        "top3_scores":    adjusted_probs.get("top3_scores"),
        "home_xg":        orch_result.get("home_xg"),
        "away_xg":        orch_result.get("away_xg"),
        "confidence":     orch_result.get("confidence", "MEDIUM"),
        "confidence_explanation": orch_result.get("confidence_explanation", ""),
        "key_drivers":    orch_result.get("key_drivers", []),

        # Value bet (the main new output)
        "best_bet":       value_result.get("best_bet"),
        "runner_up_bet":  value_result.get("runner_up"),
        "no_bet_reason":  value_result.get("no_bet_reason"),
        "line_movement_signal": value_result.get("line_movement_signal", "UNKNOWN"),
        "all_markets_ev": final_ev,

        # Model transparency
        "model_probs": {
            "home_win": adjusted_probs["home_win_prob"],
            "draw":     adjusted_probs["draw_prob"],
            "away_win": adjusted_probs["away_win_prob"],
            "home_xg":  adjusted_probs.get("home_xg"),
            "away_xg":  adjusted_probs.get("away_xg"),
            "over25_prob":  adjusted_probs.get("over25_prob"),
            "under25_prob": adjusted_probs.get("under25_prob"),
            "expected_goals_total": round((adjusted_probs.get("home_xg") or 0) + (adjusted_probs.get("away_xg") or 0), 2),
            "most_likely_score": adjusted_probs.get("most_likely_score"),
            "top3_scores": adjusted_probs.get("top3_scores"),
            "method": f"Poisson({poisson_probs['home_xg']}xG/{poisson_probs['away_xg']}xG) × {POISSON_ELO_BLEND[0]} + Elo × {POISSON_ELO_BLEND[1]}",
        },
        "market_implied": implied,

        # Line movement
        "line_movement": odds_data.get("line_movement") if odds_data else None,

        # Sub-agent outputs (for debug + agents panel)
        "sub_agents": {
            "news": news_result, "form": form_result, "h2h": h2h_result,
        },

        # Data sources
        "data_sources": {
            "odds":  f"The Odds API — live, {odds_data['h2h']['bookmaker_count']} bookmakers" if odds_data and odds_data.get("h2h") else "Not available",
            "stats": f"API-Football — live" if stats_data else "Not available (using local fallback)",
            "news":  f"NewsAPI — {news_data['total']} articles" if news_data else "Not available",
        },

        # Token stats
        "token_stats": {
            "per_agent": agent_rows,
            "total_input":  total_in, "total_output": total_out,
            "total_cost_usd": round(total_cost, 6),
            "model": model, "provider": provider, "price_per_m": price,
        },
    }
