"""
Layer 1 — Data Fetcher Layer
Pure HTTP fetchers. No LLM. Returns structured dicts for the probability engine and analysis agents.
"""

import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

def _get(url, params=None, headers=None, timeout=10):
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# OddsFetcher — The Odds API
# ---------------------------------------------------------------------------

_ODDS_BASE = "https://api.the-odds-api.com/v4"
_ODDS_SPORTS = ["soccer_fifa_world_cup"]
_ODDS_MARKETS = "h2h,totals"   # btts/asian_handicap not on bulk endpoint for this sport


# Canonical aliases — maps the many spellings sources use to one form.
# Both sides of a comparison are normalized through this before matching.
_TEAM_ALIASES = {
    "usa": "united states",
    "united states of america": "united states",
    "us": "united states",
    "korea republic": "south korea",
    "korea, republic of": "south korea",
    "czechia": "czech republic",
    "cote d'ivoire": "ivory coast",
    "côte d'ivoire": "ivory coast",
    "turkiye": "turkey",
    "türkiye": "turkey",
    "cabo verde": "cape verde",
    "dr congo": "dr congo",
    "democratic republic of congo": "dr congo",
    "congo dr": "dr congo",
}


def _normalize_team(name: str) -> str:
    n = (name or "").lower().strip()
    n = n.replace("&", "and").replace(".", "")
    n = " ".join(n.split())          # collapse whitespace
    return _TEAM_ALIASES.get(n, n)


def _team_match(api_name: str, our_name: str) -> bool:
    a, b = _normalize_team(api_name), _normalize_team(our_name)
    if not a or not b:
        return False
    if a == b:
        return True
    # Substring fallback, but only for longer tokens to avoid false positives
    # like a 2-3 letter code matching inside an unrelated name.
    return (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a)


def _strip_margin(h, d, a):
    rh, rd, ra = 1/h, 1/d, 1/a
    total = rh + rd + ra
    return {"home": rh/total, "draw": rd/total, "away": ra/total, "overround": round(total - 1, 4)}


def _parse_h2h(bookmakers, home, away):
    """Aggregate H2H odds across bookmakers."""
    home_list, draw_list, away_list = [], [], []
    bk_rows = []
    for bk in bookmakers:
        for mkt in bk.get("markets", []):
            if mkt["key"] != "h2h":
                continue
            oc = {o["name"].lower(): o["price"] for o in mkt["outcomes"]}
            h = next((v for k, v in oc.items() if _team_match(k, home)), None)
            d = oc.get("draw")
            a = next((v for k, v in oc.items() if _team_match(k, away) and k != "draw"), None)
            if h and d and a:
                home_list.append(h); draw_list.append(d); away_list.append(a)
                bk_rows.append({"bookmaker": bk["title"], "home": h, "draw": d, "away": a})
    if not home_list:
        return None
    avg_h = sum(home_list)/len(home_list)
    avg_d = sum(draw_list)/len(draw_list)
    avg_a = sum(away_list)/len(away_list)
    return {
        "bookmakers": bk_rows,
        "bookmaker_count": len(bk_rows),
        "best_home": max(home_list), "best_draw": max(draw_list), "best_away": max(away_list),
        "best_home_book": bk_rows[home_list.index(max(home_list))]["bookmaker"],
        "best_draw_book": bk_rows[draw_list.index(max(draw_list))]["bookmaker"],
        "best_away_book": bk_rows[away_list.index(max(away_list))]["bookmaker"],
        "avg_home": round(avg_h, 3), "avg_draw": round(avg_d, 3), "avg_away": round(avg_a, 3),
        "pinnacle_home": next((b["home"] for b in bk_rows if "pinnacle" in b["bookmaker"].lower()), avg_h),
        "pinnacle_draw": next((b["draw"] for b in bk_rows if "pinnacle" in b["bookmaker"].lower()), avg_d),
        "pinnacle_away": next((b["away"] for b in bk_rows if "pinnacle" in b["bookmaker"].lower()), avg_a),
    }


def _parse_totals(bookmakers):
    over_list, under_list = [], []
    for bk in bookmakers:
        for mkt in bk.get("markets", []):
            if mkt["key"] != "totals":
                continue
            oc = {o["name"].lower(): o["price"] for o in mkt["outcomes"]}
            ov = oc.get("over"); un = oc.get("under")
            if ov and un:
                over_list.append(ov); under_list.append(un)
    if not over_list:
        return None
    return {
        "line": 2.5,
        "best_over": max(over_list), "best_under": max(under_list),
        "avg_over": round(sum(over_list)/len(over_list), 3),
        "avg_under": round(sum(under_list)/len(under_list), 3),
    }


def _parse_btts(bookmakers):
    yes_list, no_list = [], []
    for bk in bookmakers:
        for mkt in bk.get("markets", []):
            if mkt["key"] != "btts":
                continue
            oc = {o["name"].lower(): o["price"] for o in mkt["outcomes"]}
            y = oc.get("yes"); n = oc.get("no")
            if y and n:
                yes_list.append(y); no_list.append(n)
    if not yes_list:
        return None
    return {
        "best_yes": max(yes_list), "best_no": max(no_list),
        "avg_yes": round(sum(yes_list)/len(yes_list), 3),
        "avg_no": round(sum(no_list)/len(no_list), 3),
    }


def fetch_match_odds(home: str, away: str, odds_api_key: str) -> dict | None:
    """
    Fetch live H2H + Totals + BTTS odds for a match.
    Returns None if match not found or no key provided.
    """
    if not odds_api_key:
        return None
    for sport in _ODDS_SPORTS:
        try:
            events = _get(f"{_ODDS_BASE}/sports/{sport}/odds/", params={
                "apiKey": odds_api_key, "regions": "eu,uk,us",
                "markets": _ODDS_MARKETS, "oddsFormat": "decimal",
            })
            for ev in events:
                hn, an = ev.get("home_team", ""), ev.get("away_team", "")
                swapped = False
                if _team_match(hn, away) and _team_match(an, home):
                    hn, an = an, hn
                    swapped = True
                if not (_team_match(hn, home) and _team_match(an, away)):
                    continue

                bks = ev.get("bookmakers", [])
                h2h = _parse_h2h(bks, home if not swapped else away, away if not swapped else home)
                if not h2h:
                    continue

                if swapped:
                    h2h["best_home"], h2h["best_away"] = h2h["best_away"], h2h["best_home"]
                    h2h["best_home_book"], h2h["best_away_book"] = h2h["best_away_book"], h2h["best_home_book"]
                    h2h["avg_home"], h2h["avg_away"] = h2h["avg_away"], h2h["avg_home"]
                    h2h["pinnacle_home"], h2h["pinnacle_away"] = h2h["pinnacle_away"], h2h["pinnacle_home"]
                    for b in h2h["bookmakers"]:
                        b["home"], b["away"] = b["away"], b["home"]

                totals = _parse_totals(bks)
                btts   = _parse_btts(bks)

                return {
                    "event_id": ev.get("id"),
                    "commence_time": ev.get("commence_time"),
                    "h2h": h2h,
                    "totals": totals,
                    "btts": btts,
                    "sport": sport,
                    "source": "live",
                }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Odds API key")
            if e.response.status_code == 422:
                continue
            print(f"[OddsFetcher] {sport}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[OddsFetcher] {sport}: {e}", file=sys.stderr)
    return None


def fetch_outright_odds(odds_api_key: str) -> dict:
    """Fetch tournament winner + top scorer outright odds. Returns {winner: [], scorer: []}."""
    if not odds_api_key:
        return {"winner": [], "scorer": []}

    winner_probs = {}
    scorer_probs = {}

    # Winner outrights live on their own sport key (has_outrights: true)
    _WINNER_SPORT = "soccer_fifa_world_cup_winner"
    SCORER_MARKETS = ["top_goalscorer", "player_first_goalscorer", "top_scorer"]

    try:
        events = _get(f"{_ODDS_BASE}/sports/{_WINNER_SPORT}/odds/", params={
            "apiKey": odds_api_key, "regions": "eu,uk,us",
            "markets": "outrights", "oddsFormat": "decimal",
        })
        for ev in events:
            for bk in ev.get("bookmakers", []):
                for mkt in bk.get("markets", []):
                    for oc in mkt.get("outcomes", []):
                        n = oc["name"]
                        winner_probs.setdefault(n, []).append(round(1/oc["price"], 4))
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Odds API key")
        print(f"[OddsFetcher] winner outrights: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[OddsFetcher] winner outrights: {e}", file=sys.stderr)

    # Top scorer outrights are not available on The Odds API for this tournament.
    # scorer_probs stays empty → caller falls back to static data.

    def top3(probs_dict, key):
        entries = [(n, sum(v)/len(v)) for n, v in probs_dict.items()]
        return sorted(entries, key=lambda x: -x[1])[:3]

    return {
        "winner": [{"nation": n, "probability": round(p*100, 1)} for n, p in top3(winner_probs, "nation")],
        "scorer": [{"player": n, "probability": round(p*100, 1)} for n, p in top3(scorer_probs, "player")],
    }


# ---------------------------------------------------------------------------
# StatsFetcher — API-Football (RapidAPI)
# ---------------------------------------------------------------------------

_APIF_BASE = "https://v3.football.api-sports.io"
_WC_LEAGUE  = 1          # FIFA World Cup 2026 league ID in API-Football
_WC_SEASON  = 2026


def _apif_get(path, params, key):
    return _get(f"{_APIF_BASE}{path}", params=params,
                headers={"x-apisports-key": key}, timeout=15)


def _resolve_team_id(name: str, key: str) -> int | None:
    try:
        data = _apif_get("/teams", {"name": name}, key)
        teams = data.get("response", [])
        if teams:
            return teams[0]["team"]["id"]
        # Try partial match
        data2 = _apif_get("/teams", {"search": name[:5]}, key)
        for t in data2.get("response", []):
            if _team_match(t["team"]["name"], name):
                return t["team"]["id"]
    except Exception as e:
        print(f"[StatsFetcher] resolve_team_id({name}): {e}", file=sys.stderr)
    return None


def _fetch_recent_fixtures(team_id: int, key: str, count: int = 10) -> list:
    try:
        data = _apif_get("/fixtures", {
            "team": team_id, "last": count,
            "league": _WC_LEAGUE, "season": _WC_SEASON,
        }, key)
        fixtures = data.get("response", [])
        # If no WC fixtures yet, fall back to all competitions
        if not fixtures:
            data = _apif_get("/fixtures", {"team": team_id, "last": count}, key)
            fixtures = data.get("response", [])
        return fixtures
    except Exception as e:
        print(f"[StatsFetcher] recent_fixtures({team_id}): {e}", file=sys.stderr)
        return []


def _fixture_xg(fixture_id: int, key: str) -> tuple[float, float]:
    """Returns (home_xg, away_xg) for a fixture, or (None, None) if unavailable."""
    try:
        data = _apif_get("/fixtures/statistics", {"fixture": fixture_id}, key)
        stats = data.get("response", [])
        home_xg = away_xg = None
        for team_stats in stats:
            for s in team_stats.get("statistics", []):
                if s["type"].lower() in ("expected goals", "xg"):
                    val = s.get("value")
                    if val is not None:
                        try:
                            v = float(str(val).replace("–", "0").replace("-", "0") or 0)
                        except (ValueError, TypeError):
                            v = 0.0
                        if team_stats.get("team", {}).get("id") == stats[0]["team"]["id"]:
                            home_xg = v
                        else:
                            away_xg = v
        return home_xg, away_xg
    except Exception:
        return None, None


def _parse_fixtures(fixtures: list, team_id: int, key: str) -> dict:
    # NOTE: per-fixture xG (statistics endpoint) is intentionally NOT fetched
    # here. It cost ~1 HTTP call per fixture (~20 sequential round-trips) and
    # burned the 100/day API-Football quota. compute_expected_xg() already
    # falls back to goals-per-game when xg is None, so dropping it is
    # accuracy-neutral while making stats fetch dramatically faster.
    results, gf, ga = [], 0, 0
    for fix in fixtures[:10]:
        teams = fix.get("teams", {})
        goals = fix.get("goals", {})
        is_home = teams.get("home", {}).get("id") == team_id
        team_goals = goals.get("home" if is_home else "away") or 0
        opp_goals  = goals.get("away" if is_home else "home") or 0
        gf += team_goals; ga += opp_goals
        if team_goals > opp_goals:   results.append("W")
        elif team_goals == opp_goals: results.append("D")
        else:                         results.append("L")

    n = max(len(results), 1)
    return {
        "results": results,
        "goals_for":     gf,
        "goals_against": ga,
        "goals_for_per_game":     round(gf / n, 2),
        "goals_against_per_game": round(ga / n, 2),
        "xg_for":  None,
        "xga":     None,
        "xg_per_game":  None,
        "xga_per_game": None,
        "clean_sheets": sum(1 for f in fixtures[:n] if
                            (f.get("goals", {}).get("away" if f.get("teams", {}).get("home", {}).get("id") == team_id else "home") or 0) == 0),
        "games_played": n,
    }


def _fetch_injuries(team_id: int, key: str) -> list:
    try:
        data = _apif_get("/injuries", {
            "team": team_id, "league": _WC_LEAGUE, "season": _WC_SEASON,
        }, key)
        injuries = []
        for item in data.get("response", []):
            p = item.get("player", {})
            injuries.append({
                "name": p.get("name"), "reason": p.get("reason", "injury"),
                "type": item.get("injury", {}).get("type", ""),
            })
        return injuries
    except Exception:
        return []


def _fetch_h2h(id1: int, id2: int, key: str) -> dict:
    try:
        data = _apif_get("/fixtures/headtohead", {
            "h2h": f"{id1}-{id2}", "last": 10
        }, key)
        fixtures = data.get("response", [])
        if not fixtures:
            return {"meetings": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "last5": []}
        home_wins = draws = away_wins = 0
        last5 = []
        for fix in fixtures:
            teams = fix.get("teams", {})
            goals = fix.get("goals", {})
            gh = goals.get("home") or 0
            ga = goals.get("away") or 0
            is_home_team1 = teams.get("home", {}).get("id") == id1
            if gh > ga:
                if is_home_team1: home_wins += 1
                else:             away_wins += 1
            elif gh == ga:
                draws += 1
            else:
                if is_home_team1: away_wins += 1
                else:             home_wins += 1
            last5.append({
                "date": fix.get("fixture", {}).get("date", "")[:10],
                "home_team": teams.get("home", {}).get("name"),
                "away_team": teams.get("away", {}).get("name"),
                "home_goals": gh, "away_goals": ga,
                "competition": fix.get("league", {}).get("name", ""),
            })
        total = len(fixtures)
        return {
            "meetings": total,
            "home_wins": home_wins, "draws": draws, "away_wins": away_wins,
            "home_win_rate": round(home_wins / total, 3),
            "draw_rate":     round(draws / total, 3),
            "away_win_rate": round(away_wins / total, 3),
            "avg_goals": round((sum(f["home_goals"]+f["away_goals"] for f in last5)) / max(len(last5), 1), 2),
            "last5": last5[:5],
        }
    except Exception as e:
        print(f"[StatsFetcher] h2h({id1},{id2}): {e}", file=sys.stderr)
        return {"meetings": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "last5": []}


def fetch_match_stats(home: str, away: str, api_football_key: str) -> dict | None:
    """
    Fetch live team stats, form, injuries, and H2H from API-Football.
    Returns None if no key provided.
    """
    if not api_football_key:
        return None
    try:
        # Resolve team IDs in parallel (independent lookups).
        with ThreadPoolExecutor(max_workers=2) as ex:
            home_id_f = ex.submit(_resolve_team_id, home, api_football_key)
            away_id_f = ex.submit(_resolve_team_id, away, api_football_key)
            home_id = home_id_f.result()
            away_id = away_id_f.result()
        if not home_id or not away_id:
            print(f"[StatsFetcher] Could not resolve team IDs: {home}={home_id}, {away}={away_id}", file=sys.stderr)
            return None

        # Fan out all independent stats calls concurrently. These no longer
        # make per-fixture xG calls, so the whole block is 5 parallel HTTP
        # round-trips instead of ~25 sequential ones.
        with ThreadPoolExecutor(max_workers=5) as ex:
            home_fixes_f = ex.submit(_fetch_recent_fixtures, home_id, api_football_key)
            away_fixes_f = ex.submit(_fetch_recent_fixtures, away_id, api_football_key)
            home_inj_f   = ex.submit(_fetch_injuries, home_id, api_football_key)
            away_inj_f   = ex.submit(_fetch_injuries, away_id, api_football_key)
            h2h_f        = ex.submit(_fetch_h2h, home_id, away_id, api_football_key)
            home_fixes = home_fixes_f.result()
            away_fixes = away_fixes_f.result()
            home_inj   = home_inj_f.result()
            away_inj   = away_inj_f.result()
            h2h        = h2h_f.result()

        home_form = _parse_fixtures(home_fixes, home_id, api_football_key)
        away_form = _parse_fixtures(away_fixes, away_id, api_football_key)

        return {
            "home": {
                "name": home, "team_id": home_id,
                "form": home_form, "injuries": home_inj,
            },
            "away": {
                "name": away, "team_id": away_id,
                "form": away_form, "injuries": away_inj,
            },
            "h2h": h2h,
            "source": "live",
        }
    except Exception as e:
        print(f"[StatsFetcher] fetch_match_stats error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# NewsFetcher — NewsAPI
# ---------------------------------------------------------------------------

_NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def fetch_match_news(home: str, away: str, newsapi_key: str, days_back: int = 7) -> dict | None:
    """Fetch real news articles about both teams. Returns None if no key."""
    if not newsapi_key:
        return None
    from datetime import datetime, timedelta
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = f'("{home}" OR "{away}") (football OR soccer OR FIFA OR "World Cup")'
    try:
        data = _get(_NEWSAPI_BASE, params={
            "apiKey": newsapi_key,
            "q": query,
            "from": since,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 15,
        })
        articles = []
        for a in data.get("articles", []):
            articles.append({
                "source": a.get("source", {}).get("name", ""),
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "url": a.get("url", ""),
                "published": a.get("publishedAt", ""),
                "content_snippet": (a.get("content") or "")[:400],
            })
        return {"articles": articles, "total": data.get("totalResults", 0), "source": "live"}
    except Exception as e:
        print(f"[NewsFetcher] {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# FallbackFetcher — football-data.org (free, rate-limited)
# ---------------------------------------------------------------------------

_FD_BASE = "https://api.football-data.org/v4"


def fetch_match_stats_fallback(home: str, away: str, fd_key: str) -> dict | None:
    """Basic stats from football-data.org — used when API-Football quota exhausted."""
    if not fd_key:
        return None
    try:
        headers = {"X-Auth-Token": fd_key}
        # Get WC matches
        data = _get(f"{_FD_BASE}/competitions/WC/matches",
                    params={"status": "SCHEDULED,FINISHED"}, headers=headers)
        matches = data.get("matches", [])
        h2h_matches = [m for m in matches if
                       (_team_match(m.get("homeTeam", {}).get("name", ""), home) and
                        _team_match(m.get("awayTeam", {}).get("name", ""), away)) or
                       (_team_match(m.get("homeTeam", {}).get("name", ""), away) and
                        _team_match(m.get("awayTeam", {}).get("name", ""), home))]
        return {
            "home": {"name": home, "team_id": None, "form": {}, "injuries": []},
            "away": {"name": away, "team_id": None, "form": {}, "injuries": []},
            "h2h": {"meetings": len(h2h_matches), "last5": [], "source": "fallback"},
            "source": "fallback",
        }
    except Exception as e:
        print(f"[FallbackFetcher] {e}", file=sys.stderr)
        return None
