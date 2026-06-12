"""Flask server for World Cup 2026 Betting Intelligence System — v3.0"""

from flask import Flask, render_template, jsonify, request
from data import MATCHES, PRETOURNAMENT_PREDICTIONS
from agents import run_prediction_pipeline, PROVIDERS, DEFAULT_MODELS, DEFAULT_AGENT_CONFIGS

app = Flask(__name__)
_predictions_cache = {}
_last_result = {}


@app.route("/")
def index():
    return render_template("index.html", matches=MATCHES)


@app.route("/api/providers")
def providers():
    return jsonify(PROVIDERS)


@app.route("/api/agents")
def agents_config():
    return jsonify(DEFAULT_AGENT_CONFIGS)


@app.route("/api/predict/<match_id>", methods=["POST"])
def predict(match_id):
    body = request.get_json(silent=True) or {}
    provider         = body.get("provider", "anthropic")
    api_key          = body.get("api_key", "").strip()
    model            = body.get("model") or DEFAULT_MODELS.get(provider, "")
    odds_api_key     = body.get("odds_api_key", "").strip()
    api_football_key = body.get("api_football_key", "").strip()
    newsapi_key      = body.get("newsapi_key", "").strip()
    agent_overrides  = body.get("agent_overrides")

    if not api_key:
        return jsonify({"error": "נדרש מפתח API — פתח את ההגדרות ⚙️ והכנס מפתח"}), 400
    if provider not in PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400

    # Cache key excludes data-API keys so fresh live data is always fetched
    cache_key = f"{match_id}:{provider}:{model}" if not agent_overrides else None
    if cache_key and cache_key in _predictions_cache:
        return jsonify(_predictions_cache[cache_key])

    match = next((m for m in MATCHES if m["id"] == match_id), None)
    if not match:
        return jsonify({"error": "Match not found"}), 404
    if match["home"] == "TBD" or match["away"] == "TBD":
        return jsonify({"error": "Teams not yet determined"}), 400

    try:
        result = run_prediction_pipeline(
            match["home"], match["away"],
            provider, api_key, model,
            agent_overrides,
            odds_api_key=odds_api_key,
            api_football_key=api_football_key,
            newsapi_key=newsapi_key,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    result["match_id"] = match_id
    result["provider"] = provider
    result["model"]    = model
    if cache_key:
        _predictions_cache[cache_key] = result
    _last_result.clear()
    _last_result.update(result)
    return jsonify(result)


@app.route("/api/pretournament")
def pretournament():
    return jsonify(PRETOURNAMENT_PREDICTIONS)


@app.route("/api/pretournament/live")
def pretournament_live():
    from fetchers import fetch_outright_odds
    from data import FLAGS
    odds_api_key = request.args.get("odds_api_key", "").strip()

    if not odds_api_key:
        return jsonify({"source": "static", "data": PRETOURNAMENT_PREDICTIONS})

    def _flag(nation):
        for name, flag in FLAGS.items():
            if nation.lower() in name.lower() or name.lower() in nation.lower():
                return flag
        return "🏳️"

    try:
        live = fetch_outright_odds(odds_api_key)
        winner_list = live.get("winner", [])
        scorer_list = live.get("scorer", [])

        # Augment with flags and live marker
        for w in winner_list:
            w["flag"] = _flag(w["nation"])
            w["live"] = True
            w["reasoning"] = "Live market odds"
        for s in scorer_list:
            s["flag"] = "⚽"
            s["live"] = True

        winner_out = winner_list or PRETOURNAMENT_PREDICTIONS["winner"]
        scorer_out = scorer_list or PRETOURNAMENT_PREDICTIONS["golden_boot"]

        return jsonify({
            "source": "live" if (winner_list or scorer_list) else "static",
            "winner_live": bool(winner_list),
            "scorer_live": bool(scorer_list),
            "data": {"winner": winner_out, "golden_boot": scorer_out},
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"source": "static", "data": PRETOURNAMENT_PREDICTIONS,
                        "warning": str(e)})


@app.route("/api/debug/odds-sports")
def debug_odds_sports():
    """List all sports available on this Odds API key — helps diagnose missing markets."""
    import requests as _req
    odds_api_key = request.args.get("odds_api_key", "").strip()
    if not odds_api_key:
        return jsonify({"error": "odds_api_key param required"}), 400
    try:
        r = _req.get("https://api.the-odds-api.com/v4/sports/",
                     params={"apiKey": odds_api_key}, timeout=10)
        r.raise_for_status()
        sports = r.json()
        soccer = [s for s in sports if "soccer" in s.get("key","").lower() or "football" in s.get("title","").lower()]
        return jsonify({"total": len(sports), "soccer": soccer, "all_keys": [s["key"] for s in sports]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug/odds-markets")
def debug_odds_markets():
    """Show what markets are available on a given sport key."""
    import requests as _req
    odds_api_key = request.args.get("odds_api_key", "").strip()
    sport = request.args.get("sport", "soccer_fifa_world_cup_winner").strip()
    if not odds_api_key:
        return jsonify({"error": "odds_api_key param required"}), 400
    try:
        r = _req.get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                     params={"apiKey": odds_api_key, "regions": "eu,uk,us",
                             "markets": "outrights,top_goalscorer,player_first_goalscorer",
                             "oddsFormat": "decimal"}, timeout=10)
        r.raise_for_status()
        events = r.json()
        markets_found = set()
        for ev in events:
            for bk in ev.get("bookmakers", []):
                for mkt in bk.get("markets", []):
                    markets_found.add(mkt["key"])
        return jsonify({"sport": sport, "event_count": len(events), "markets_found": sorted(markets_found)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    """Test connectivity + quota for a single API key. Body: {service, key, provider?, model?}."""
    import requests as _req
    body = request.get_json(silent=True) or {}
    service = body.get("service", "")
    key = (body.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "msg": "מפתח ריק"})

    try:
        if service == "odds":
            r = _req.get("https://api.the-odds-api.com/v4/sports/",
                         params={"apiKey": key}, timeout=10)
            if r.status_code == 401:
                return jsonify({"ok": False, "msg": "מפתח לא תקין (401)"})
            r.raise_for_status()
            remaining = r.headers.get("x-requests-remaining", "?")
            used = r.headers.get("x-requests-used", "?")
            wc = any("fifa_world_cup" in s.get("key", "") for s in r.json())
            return jsonify({"ok": True,
                            "msg": f"מחובר · נותרו {remaining} בקשות" + ("  · מונדיאל זמין ✓" if wc else "")})

        if service == "api_football":
            r = _req.get("https://v3.football.api-sports.io/status",
                         headers={"x-apisports-key": key}, timeout=10)
            r.raise_for_status()
            data = r.json()
            errs = data.get("errors")
            if errs:
                return jsonify({"ok": False, "msg": f"שגיאה: {errs}"})
            resp = data.get("response", {})
            req = resp.get("requests", {})
            return jsonify({"ok": True,
                            "msg": f"מחובר · {req.get('current','?')}/{req.get('limit_day','?')} בקשות היום"})

        if service == "newsapi":
            r = _req.get("https://newsapi.org/v2/top-headlines",
                         params={"category": "sports", "pageSize": 1, "apiKey": key}, timeout=10)
            data = r.json()
            if data.get("status") == "ok":
                return jsonify({"ok": True, "msg": f"מחובר · {data.get('totalResults',0)} כותרות זמינות"})
            return jsonify({"ok": False, "msg": data.get("message", "מפתח לא תקין")})

        if service == "ai":
            provider = body.get("provider", "anthropic")
            model = body.get("model") or DEFAULT_MODELS.get(provider, "")
            from agents import test_ai_connection
            ok, msg = test_ai_connection(provider, key, model)
            return jsonify({"ok": ok, "msg": msg})

        return jsonify({"ok": False, "msg": f"שירות לא ידוע: {service}"})
    except _req.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        return jsonify({"ok": False, "msg": f"שגיאת HTTP {code}"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"שגיאת חיבור: {e}"})


@app.route("/api/matches")
def matches():
    return jsonify(MATCHES)


@app.route("/api/debug/last")
def debug_last():
    if not _last_result:
        return jsonify({"error": "no predictions yet"})
    return jsonify({
        "match": f"{_last_result.get('home')} vs {_last_result.get('away')}",
        "predicted_score": _last_result.get("predicted_score"),
        "home_xg": _last_result.get("home_xg"),
        "away_xg": _last_result.get("away_xg"),
        "model_probs": _last_result.get("model_probs"),
        "market_implied": _last_result.get("market_implied"),
        "best_bet": _last_result.get("best_bet"),
        "all_markets_ev": _last_result.get("all_markets_ev"),
        "data_sources": _last_result.get("data_sources"),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5050)
