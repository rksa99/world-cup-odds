"""
Layer 2 — Probability Engine
Pure Python math. No LLM. No market odds as input.
Produces independent model probabilities from real stats data.
"""

import math
from itertools import product

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_GOALS   = 7      # compute score matrix up to 7 goals per side
POISSON_ELO_BLEND = (0.60, 0.40)   # Poisson weight, Elo weight

# Tournament base xG rates (goals per game in major tournaments)
BASE_XG_HOME = 1.35
BASE_XG_AWAY = 1.10

# Kelly fraction (quarter-Kelly for variance reduction)
KELLY_FRACTION = 0.25

# Minimum EV to flag as a value bet
VALUE_THRESHOLD = 0.05   # 5% EV


# ---------------------------------------------------------------------------
# Dixon-Coles bivariate Poisson model
# ---------------------------------------------------------------------------

def _dc_tau(home_goals, away_goals, lambda_h, lambda_a, rho=-0.1):
    """Dixon-Coles low-score correction factor."""
    if home_goals == 0 and away_goals == 0:
        return 1 - lambda_h * lambda_a * rho
    elif home_goals == 0 and away_goals == 1:
        return 1 + lambda_h * rho
    elif home_goals == 1 and away_goals == 0:
        return 1 + lambda_a * rho
    elif home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def poisson_model(home_xg: float, away_xg: float) -> dict:
    """
    Dixon-Coles corrected bivariate Poisson.
    Returns score matrix and derived probabilities.
    """
    home_xg = max(0.3, home_xg)
    away_xg = max(0.3, away_xg)

    score_matrix = {}
    for h, a in product(range(MAX_GOALS), range(MAX_GOALS)):
        p = _poisson_pmf(h, home_xg) * _poisson_pmf(a, away_xg) * _dc_tau(h, a, home_xg, away_xg)
        score_matrix[(h, a)] = p

    # Normalise (DC correction shifts total slightly)
    total = sum(score_matrix.values())
    score_matrix = {k: v/total for k, v in score_matrix.items()}

    home_win = sum(p for (h, a), p in score_matrix.items() if h > a)
    draw     = sum(p for (h, a), p in score_matrix.items() if h == a)
    away_win = sum(p for (h, a), p in score_matrix.items() if h < a)
    over25   = sum(p for (h, a), p in score_matrix.items() if h + a > 2.5)
    under25  = 1.0 - over25
    btts     = sum(p for (h, a), p in score_matrix.items() if h > 0 and a > 0)

    sorted_scores = sorted(score_matrix.items(), key=lambda x: -x[1])
    most_likely = f"{sorted_scores[0][0][0]}-{sorted_scores[0][0][1]}"
    top3 = [{"score": f"{h}-{a}", "prob": round(p, 4)} for (h, a), p in sorted_scores[:3]]

    # Most likely score for each outcome — lets the UI show a scoreline that is
    # consistent with the predicted winner (Poisson's single modal score is often
    # a draw even when a win is the likeliest outcome).
    def _top_for(cond):
        for (h, a), p in sorted_scores:
            if cond(h, a):
                return f"{h}-{a}"
        return most_likely
    score_by_outcome = {
        "home_win": _top_for(lambda h, a: h > a),
        "draw":     _top_for(lambda h, a: h == a),
        "away_win": _top_for(lambda h, a: h < a),
    }

    # Asian handicap probabilities: P(home wins by more than line)
    ah_probs = {}
    for line in [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]:
        ah_home = sum(p for (h, a), p in score_matrix.items() if (h - a) > line)
        ah_away = sum(p for (h, a), p in score_matrix.items() if (h - a) < line)
        ah_probs[line] = {"home": round(ah_home, 4), "away": round(ah_away, 4)}

    return {
        "home_win_prob": round(home_win, 4),
        "draw_prob":     round(draw, 4),
        "away_win_prob": round(away_win, 4),
        "over25_prob":   round(over25, 4),
        "under25_prob":  round(under25, 4),
        "btts_prob":     round(btts, 4),
        "home_xg":       round(home_xg, 2),
        "away_xg":       round(away_xg, 2),
        "most_likely_score": most_likely,
        "score_by_outcome": score_by_outcome,
        "top3_scores":   top3,
        "ah_probs":      ah_probs,
        "model":         "poisson_dixon_coles",
    }


# ---------------------------------------------------------------------------
# Expected xG computation from real stats
# ---------------------------------------------------------------------------

def compute_expected_xg(home_stats: dict, away_stats: dict,
                         fallback_home: float = None,
                         fallback_away: float = None) -> tuple[float, float]:
    """
    Compute expected xG for both teams from real stats data.
    Uses actual xG/game if available, otherwise goals/game.
    """
    def xg_per_game(team_stats):
        form = team_stats.get("form", {})
        xg  = form.get("xg_per_game")
        xga = form.get("xga_per_game")
        gf  = form.get("goals_for_per_game")
        ga  = form.get("goals_against_per_game")
        return (xg or gf or BASE_XG_HOME), (xga or ga or BASE_XG_AWAY)

    h_att, h_def = xg_per_game(home_stats)   # home attack xG, home defense conceded xG
    a_att, a_def = xg_per_game(away_stats)

    # Attack strength relative to average; defense weakness relative to average
    avg_att = (BASE_XG_HOME + BASE_XG_AWAY) / 2
    h_attack_strength  = h_att / avg_att
    a_attack_strength  = a_att / avg_att
    h_defense_weakness = h_def / avg_att
    a_defense_weakness = a_def / avg_att

    home_xg = h_attack_strength * a_defense_weakness * BASE_XG_HOME
    away_xg = a_attack_strength * h_defense_weakness * BASE_XG_AWAY

    if fallback_home: home_xg = fallback_home
    if fallback_away: away_xg = fallback_away

    return round(max(0.3, home_xg), 2), round(max(0.3, away_xg), 2)


# ---------------------------------------------------------------------------
# Elo model
# ---------------------------------------------------------------------------

# Base Elo estimates for WC 2026 teams (if API doesn't provide)
ELO_DEFAULTS = {
    "Brazil": 2070, "France": 2040, "England": 2010, "Spain": 2020,
    "Germany": 1990, "Argentina": 2060, "Portugal": 1980, "Netherlands": 1960,
    "Belgium": 1940, "Italy": 1950, "Uruguay": 1920, "Croatia": 1910,
    "Mexico": 1870, "United States": 1850, "Colombia": 1890, "Ecuador": 1830,
    "Morocco": 1880, "Senegal": 1850, "Nigeria": 1820, "Ivory Coast": 1800,
    "Japan": 1860, "South Korea": 1830, "Australia": 1780, "Iran": 1790,
    "Switzerland": 1900, "Denmark": 1910, "Sweden": 1870, "Austria": 1850,
    "Turkey": 1840, "Poland": 1820, "Hungary": 1800, "Scotland": 1810,
    "Canada": 1810, "Costa Rica": 1780, "Panama": 1760, "Jamaica": 1750,
    "Qatar": 1740, "Saudi Arabia": 1780, "South Africa": 1740,
}


# Host nations play at home in WC 2026 — a real, measurable advantage (~+65 Elo).
HOST_NATIONS = {"Mexico", "United States", "USA", "Canada"}
HOST_ELO_BONUS = 65


def elo_model(home_name: str, away_name: str,
              home_elo: float = None, away_elo: float = None,
              home_advantage: float = 0.0) -> dict:
    """
    Standard Elo 3-way probability.
    Venues are neutral at the World Cup EXCEPT for host nations (USA/Mexico/Canada),
    who genuinely play at home — pass home_advantage for those games.
    """
    he = (home_elo or ELO_DEFAULTS.get(home_name, 1800)) + home_advantage
    ae = away_elo or ELO_DEFAULTS.get(away_name, 1800)

    # 2-way Elo expected score
    expected_home = 1 / (1 + 10 ** ((ae - he) / 400))

    # Convert to 3-way using draw probability that shrinks with Elo gap
    elo_diff = abs(he - ae)
    draw_prob = max(0.15, min(0.35, 0.30 - elo_diff * 0.0002))

    # Distribute the 2-way prob into win/draw/loss
    # The home 2-way expected value splits between win and a portion of draw
    home_win = expected_home - draw_prob * expected_home
    away_win = (1 - expected_home) - draw_prob * (1 - expected_home)

    # Re-normalise to ensure sum = 1
    total = home_win + draw_prob + away_win
    return {
        "home_win_prob": round(home_win / total, 4),
        "draw_prob":     round(draw_prob / total, 4),
        "away_win_prob": round(away_win / total, 4),
        "home_elo": he, "away_elo": ae, "elo_diff": elo_diff,
        "model": "elo",
    }


# ---------------------------------------------------------------------------
# Blend Poisson + Elo
# ---------------------------------------------------------------------------

def blend_probabilities(poisson: dict, elo: dict,
                         weights: tuple = POISSON_ELO_BLEND) -> dict:
    """Weighted blend of Poisson and Elo 1X2 probabilities."""
    pw, ew = weights
    blended = {
        "home_win_prob": round(poisson["home_win_prob"] * pw + elo["home_win_prob"] * ew, 4),
        "draw_prob":     round(poisson["draw_prob"]     * pw + elo["draw_prob"]     * ew, 4),
        "away_win_prob": round(poisson["away_win_prob"] * pw + elo["away_win_prob"] * ew, 4),
    }
    # Carry Poisson-only fields unchanged
    for k in ("over25_prob", "under25_prob", "btts_prob", "home_xg", "away_xg",
              "most_likely_score", "score_by_outcome", "top3_scores", "ah_probs"):
        blended[k] = poisson[k]
    blended["poisson_weight"] = pw
    blended["elo_weight"] = ew
    return blended


# ---------------------------------------------------------------------------
# Market implied probability (margin removal)
# ---------------------------------------------------------------------------

def market_implied(h2h_odds: dict) -> dict:
    """
    Strip bookmaker margin using Pinnacle as reference (lowest margin).
    Falls back to average odds if Pinnacle unavailable.
    """
    ph = h2h_odds.get("pinnacle_home") or h2h_odds.get("avg_home")
    pd = h2h_odds.get("pinnacle_draw") or h2h_odds.get("avg_draw")
    pa = h2h_odds.get("pinnacle_away") or h2h_odds.get("avg_away")

    if not (ph and pd and pa):
        return None

    raw_h, raw_d, raw_a = 1/ph, 1/pd, 1/pa
    total = raw_h + raw_d + raw_a
    return {
        "home": round(raw_h / total, 4),
        "draw": round(raw_d / total, 4),
        "away": round(raw_a / total, 4),
        "overround": round(total - 1, 4),
        "reference": "Pinnacle" if h2h_odds.get("pinnacle_home") else "market_average",
        "over25": round(1 / (h2h_odds.get("avg_over") or 1.9), 4) if h2h_odds.get("avg_over") else None,
        "under25": round(1 / (h2h_odds.get("avg_under") or 1.9), 4) if h2h_odds.get("avg_under") else None,
        "btts_yes": round(1 / (h2h_odds.get("avg_yes") or 1.85), 4) if h2h_odds.get("avg_yes") else None,
    }


# ---------------------------------------------------------------------------
# Value Calculator — EV + Kelly for all markets
# ---------------------------------------------------------------------------

def _kelly(model_prob: float, decimal_odds: float, fraction: float = KELLY_FRACTION) -> float:
    b = decimal_odds - 1
    if b <= 0 or model_prob <= 0:
        return 0.0
    q = 1 - model_prob
    full = (b * model_prob - q) / b
    return max(0.0, round(full * fraction, 4))


def _ev(model_prob: float, decimal_odds: float) -> float:
    return round(model_prob * decimal_odds - 1, 4)


def _best_book(bk_rows: list, outcome_key: str) -> tuple[str, float]:
    """Find bookmaker with best odds for a given outcome."""
    best_odds = 0.0
    best_book = ""
    for b in bk_rows:
        o = b.get(outcome_key, 0) or 0
        if o > best_odds:
            best_odds = o
            best_book = b.get("bookmaker", "")
    return best_book, best_odds


def compute_value(market_label: str, model_prob: float,
                  market_implied_prob: float | None,
                  best_odds: float, best_book: str) -> dict:
    """
    Value = the BEST available price beating the sharp de-vigged consensus.
    Fair probability is anchored on the market consensus (the sharpest estimate),
    nudged at most ±3pp by our model. This prevents a miscalibrated model from
    manufacturing fantasy EVs (e.g. a 7-goal Poisson saying 25% on a 10% longshot).
    """
    consensus = market_implied_prob if market_implied_prob is not None else (1 / best_odds)
    # Bounded model tilt: our model can move fair value a little, not a lot.
    tilt = max(-0.03, min(0.03, model_prob - consensus))
    fair_prob = max(0.001, min(0.999, consensus + tilt))

    ev    = _ev(fair_prob, best_odds)
    edge  = round(fair_prob - (1 / best_odds), 4)         # price edge vs the offered odds
    model_edge = round(model_prob - consensus, 4)          # does our model agree with market?
    kelly = _kelly(fair_prob, best_odds)
    return {
        "market": market_label,
        "model_prob": round(model_prob, 4),
        "market_implied_prob": round(consensus, 4),
        "fair_prob": round(fair_prob, 4),
        "best_odds": best_odds,
        "best_book": best_book,
        "ev": ev,
        "edge": edge,
        "model_edge": model_edge,
        "kelly": kelly,
        "is_value": ev > VALUE_THRESHOLD and kelly > 0,
    }


def compute_all_markets(model_probs: dict, odds_data: dict,
                        implied: dict | None,
                        home: str, away: str) -> dict:
    """
    Compute EV + Kelly for every available market.
    Returns dict keyed by market label.
    """
    results = {}
    h2h = odds_data.get("h2h", {}) if odds_data else {}
    totals = odds_data.get("totals", {}) if odds_data else {}
    btts   = odds_data.get("btts", {}) if odds_data else {}
    bk_rows = h2h.get("bookmakers", [])

    # 1X2
    if h2h:
        for outcome, prob_key, best_key, label in [
            ("home", "home_win_prob", "best_home", f"{home} Win"),
            ("draw", "draw_prob",     "best_draw", "Draw"),
            ("away", "away_win_prob", "best_away", f"{away} Win"),
        ]:
            best_o = h2h.get(best_key, 0)
            if best_o:
                best_b = h2h.get(f"{best_key}_book", "")
                imp = implied.get(outcome) if implied else None
                results[f"1x2_{outcome}"] = compute_value(
                    label, model_probs[prob_key], imp, best_o, best_b
                )

    # Over/Under 2.5
    if totals:
        best_ov = totals.get("best_over", 0)
        best_un = totals.get("best_under", 0)
        if best_ov:
            imp_ov = implied.get("over25") if implied else None
            results["over25"] = compute_value(
                "Over 2.5 Goals", model_probs.get("over25_prob", 0),
                imp_ov, best_ov, ""
            )
        if best_un:
            imp_un = implied.get("under25") if implied else None
            results["under25"] = compute_value(
                "Under 2.5 Goals", model_probs.get("under25_prob", 0),
                imp_un, best_un, ""
            )

    # BTTS
    if btts:
        best_yes = btts.get("best_yes", 0)
        if best_yes:
            imp_btts = implied.get("btts_yes") if implied else None
            results["btts_yes"] = compute_value(
                "Both Teams to Score", model_probs.get("btts_prob", 0),
                imp_btts, best_yes, ""
            )

    return results


def find_best_bet(all_markets: dict) -> dict | None:
    """
    Return the best value bet, ranked by quarter-Kelly stake (risk-adjusted growth),
    not raw EV — this avoids always recommending high-variance longshots that have a
    huge EV but a near-zero optimal stake.
    """
    candidates = [v for v in all_markets.values() if v.get("is_value")]
    if not candidates:
        return None
    return max(candidates, key=lambda x: (x["kelly"], x["ev"]))


# ---------------------------------------------------------------------------
# Apply LLM adjustments to model probabilities
# ---------------------------------------------------------------------------

def apply_adjustments(model_probs: dict,
                       news_adj_home: float = 0.0,
                       news_adj_away: float = 0.0,
                       form_adj_home: float = 0.0,
                       form_adj_away: float = 0.0,
                       h2h_adj_home:  float = 0.0) -> dict:
    """
    Apply qualitative modifiers from LLM agents to model probabilities.
    Adjustments are additive deltas; result is re-normalised to sum 1.
    """
    adj = dict(model_probs)
    adj["home_win_prob"] = max(0.01, adj["home_win_prob"] + news_adj_home + form_adj_home + h2h_adj_home)
    adj["away_win_prob"] = max(0.01, adj["away_win_prob"] + news_adj_away - form_adj_home)
    # Draw absorbs the remainder
    total = adj["home_win_prob"] + adj["draw_prob"] + adj["away_win_prob"]
    adj["home_win_prob"] = round(adj["home_win_prob"] / total, 4)
    adj["draw_prob"]     = round(adj["draw_prob"]     / total, 4)
    adj["away_win_prob"] = round(adj["away_win_prob"] / total, 4)
    return adj
