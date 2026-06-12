"""World Cup 2026 match data — 48 teams, 12 groups.
Source: Wikipedia / FIFA official schedule (fetched June 2026).
Times are local venue time.
"""

FLAGS = {
    "Mexico":                  "🇲🇽",
    "South Africa":            "🇿🇦",
    "South Korea":             "🇰🇷",
    "Czech Republic":          "🇨🇿",
    "Canada":                  "🇨🇦",
    "Bosnia and Herzegovina":  "🇧🇦",
    "Qatar":                   "🇶🇦",
    "Switzerland":             "🇨🇭",
    "Brazil":                  "🇧🇷",
    "Morocco":                 "🇲🇦",
    "Haiti":                   "🇭🇹",
    "Scotland":                "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "United States":           "🇺🇸",
    "Paraguay":                "🇵🇾",
    "Australia":               "🇦🇺",
    "Turkey":                  "🇹🇷",
    "Germany":                 "🇩🇪",
    "Curaçao":                 "🇨🇼",
    "Ivory Coast":             "🇨🇮",
    "Ecuador":                 "🇪🇨",
    "Netherlands":             "🇳🇱",
    "Japan":                   "🇯🇵",
    "Sweden":                  "🇸🇪",
    "Tunisia":                 "🇹🇳",
    "Belgium":                 "🇧🇪",
    "Egypt":                   "🇪🇬",
    "Iran":                    "🇮🇷",
    "New Zealand":             "🇳🇿",
    "Spain":                   "🇪🇸",
    "Cape Verde":              "🇨🇻",
    "Saudi Arabia":            "🇸🇦",
    "Uruguay":                 "🇺🇾",
    "France":                  "🇫🇷",
    "Senegal":                 "🇸🇳",
    "Iraq":                    "🇮🇶",
    "Norway":                  "🇳🇴",
    "Argentina":               "🇦🇷",
    "Algeria":                 "🇩🇿",
    "Austria":                 "🇦🇹",
    "Jordan":                  "🇯🇴",
    "Portugal":                "🇵🇹",
    "DR Congo":                "🇨🇩",
    "Uzbekistan":              "🇺🇿",
    "Colombia":                "🇨🇴",
    "England":                 "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Croatia":                 "🇭🇷",
    "Ghana":                   "🇬🇭",
    "Panama":                  "🇵🇦",
    "TBD":                     "🏳",
}


def _m(id, stage, home, away, date, time, venue, city):
    return {
        "id": id, "stage": stage,
        "home": home, "away": away,
        "home_flag": FLAGS.get(home, "🏳"),
        "away_flag": FLAGS.get(away, "🏳"),
        "date": date, "time": time,
        "venue": f"{venue}, {city}",
        "status": "upcoming",
    }


def _tbd(id, stage, date, time, venue, city):
    return _m(id, stage, "TBD", "TBD", date, time, venue, city)


MATCHES = [
    # ── GROUP A ──────────────────────────────────────────────────────────────
    _m("A1",  "Group A", "Mexico",         "South Africa",          "2026-06-11", "13:00", "Estadio Azteca",          "Mexico City"),
    _m("A2",  "Group A", "South Korea",    "Czech Republic",        "2026-06-11", "20:00", "Estadio Akron",           "Zapopan"),
    _m("A3",  "Group A", "Czech Republic", "South Africa",          "2026-06-18", "12:00", "Mercedes-Benz Stadium",   "Atlanta"),
    _m("A4",  "Group A", "Mexico",         "South Korea",           "2026-06-18", "19:00", "Estadio Akron",           "Zapopan"),
    _m("A5",  "Group A", "Czech Republic", "Mexico",                "2026-06-24", "19:00", "Estadio Azteca",          "Mexico City"),
    _m("A6",  "Group A", "South Africa",   "South Korea",           "2026-06-24", "19:00", "Estadio BBVA",            "Guadalupe"),

    # ── GROUP B ──────────────────────────────────────────────────────────────
    _m("B1",  "Group B", "Canada",         "Bosnia and Herzegovina","2026-06-12", "15:00", "BMO Field",               "Toronto"),
    _m("B2",  "Group B", "Qatar",          "Switzerland",           "2026-06-13", "12:00", "Levi's Stadium",          "Santa Clara"),
    _m("B3",  "Group B", "Switzerland",    "Bosnia and Herzegovina","2026-06-18", "12:00", "SoFi Stadium",            "Inglewood"),
    _m("B4",  "Group B", "Canada",         "Qatar",                 "2026-06-18", "15:00", "BC Place",                "Vancouver"),
    _m("B5",  "Group B", "Switzerland",    "Canada",                "2026-06-24", "12:00", "BC Place",                "Vancouver"),
    _m("B6",  "Group B", "Bosnia and Herzegovina", "Qatar",         "2026-06-24", "12:00", "Lumen Field",             "Seattle"),

    # ── GROUP C ──────────────────────────────────────────────────────────────
    _m("C1",  "Group C", "Brazil",         "Morocco",               "2026-06-13", "18:00", "MetLife Stadium",         "East Rutherford"),
    _m("C2",  "Group C", "Haiti",          "Scotland",              "2026-06-13", "21:00", "Gillette Stadium",        "Foxborough"),
    _m("C3",  "Group C", "Scotland",       "Morocco",               "2026-06-19", "18:00", "Gillette Stadium",        "Foxborough"),
    _m("C4",  "Group C", "Brazil",         "Haiti",                 "2026-06-19", "20:30", "Lincoln Financial Field", "Philadelphia"),
    _m("C5",  "Group C", "Scotland",       "Brazil",                "2026-06-24", "18:00", "Hard Rock Stadium",       "Miami Gardens"),
    _m("C6",  "Group C", "Morocco",        "Haiti",                 "2026-06-24", "18:00", "Mercedes-Benz Stadium",   "Atlanta"),

    # ── GROUP D ──────────────────────────────────────────────────────────────
    _m("D1",  "Group D", "United States",  "Paraguay",              "2026-06-12", "18:00", "SoFi Stadium",            "Inglewood"),
    _m("D2",  "Group D", "Australia",      "Turkey",                "2026-06-13", "21:00", "BC Place",                "Vancouver"),
    _m("D3",  "Group D", "United States",  "Australia",             "2026-06-19", "12:00", "Lumen Field",             "Seattle"),
    _m("D4",  "Group D", "Turkey",         "Paraguay",              "2026-06-19", "20:00", "Levi's Stadium",          "Santa Clara"),
    _m("D5",  "Group D", "Turkey",         "United States",         "2026-06-25", "19:00", "SoFi Stadium",            "Inglewood"),
    _m("D6",  "Group D", "Paraguay",       "Australia",             "2026-06-25", "19:00", "Levi's Stadium",          "Santa Clara"),

    # ── GROUP E ──────────────────────────────────────────────────────────────
    _m("E1",  "Group E", "Germany",        "Curaçao",               "2026-06-14", "12:00", "NRG Stadium",             "Houston"),
    _m("E2",  "Group E", "Ivory Coast",    "Ecuador",               "2026-06-14", "19:00", "Lincoln Financial Field", "Philadelphia"),
    _m("E3",  "Group E", "Germany",        "Ivory Coast",           "2026-06-20", "16:00", "BMO Field",               "Toronto"),
    _m("E4",  "Group E", "Ecuador",        "Curaçao",               "2026-06-20", "19:00", "Arrowhead Stadium",       "Kansas City"),
    _m("E5",  "Group E", "Curaçao",        "Ivory Coast",           "2026-06-25", "16:00", "Lincoln Financial Field", "Philadelphia"),
    _m("E6",  "Group E", "Ecuador",        "Germany",               "2026-06-25", "16:00", "MetLife Stadium",         "East Rutherford"),

    # ── GROUP F ──────────────────────────────────────────────────────────────
    _m("F1",  "Group F", "Netherlands",    "Japan",                 "2026-06-14", "15:00", "AT&T Stadium",            "Arlington"),
    _m("F2",  "Group F", "Sweden",         "Tunisia",               "2026-06-14", "20:00", "Estadio BBVA",            "Guadalupe"),
    _m("F3",  "Group F", "Netherlands",    "Sweden",                "2026-06-20", "12:00", "NRG Stadium",             "Houston"),
    _m("F4",  "Group F", "Tunisia",        "Japan",                 "2026-06-20", "22:00", "Estadio BBVA",            "Guadalupe"),
    _m("F5",  "Group F", "Japan",          "Sweden",                "2026-06-25", "18:00", "AT&T Stadium",            "Arlington"),
    _m("F6",  "Group F", "Tunisia",        "Netherlands",           "2026-06-25", "18:00", "Arrowhead Stadium",       "Kansas City"),

    # ── GROUP G ──────────────────────────────────────────────────────────────
    _m("G1",  "Group G", "Belgium",        "Egypt",                 "2026-06-15", "12:00", "Lumen Field",             "Seattle"),
    _m("G2",  "Group G", "Iran",           "New Zealand",           "2026-06-15", "18:00", "SoFi Stadium",            "Inglewood"),
    _m("G3",  "Group G", "Belgium",        "Iran",                  "2026-06-21", "12:00", "SoFi Stadium",            "Inglewood"),
    _m("G4",  "Group G", "New Zealand",    "Egypt",                 "2026-06-21", "18:00", "BC Place",                "Vancouver"),
    _m("G5",  "Group G", "Egypt",          "Iran",                  "2026-06-26", "20:00", "Lumen Field",             "Seattle"),
    _m("G6",  "Group G", "New Zealand",    "Belgium",               "2026-06-26", "20:00", "BC Place",                "Vancouver"),

    # ── GROUP H ──────────────────────────────────────────────────────────────
    _m("H1",  "Group H", "Spain",          "Cape Verde",            "2026-06-15", "12:00", "Mercedes-Benz Stadium",   "Atlanta"),
    _m("H2",  "Group H", "Saudi Arabia",   "Uruguay",               "2026-06-15", "18:00", "Hard Rock Stadium",       "Miami Gardens"),
    _m("H3",  "Group H", "Spain",          "Saudi Arabia",          "2026-06-21", "12:00", "Mercedes-Benz Stadium",   "Atlanta"),
    _m("H4",  "Group H", "Uruguay",        "Cape Verde",            "2026-06-21", "18:00", "Hard Rock Stadium",       "Miami Gardens"),
    _m("H5",  "Group H", "Cape Verde",     "Saudi Arabia",          "2026-06-26", "19:00", "NRG Stadium",             "Houston"),
    _m("H6",  "Group H", "Uruguay",        "Spain",                 "2026-06-26", "18:00", "Estadio Akron",           "Zapopan"),

    # ── GROUP I ──────────────────────────────────────────────────────────────
    _m("I1",  "Group I", "France",         "Senegal",               "2026-06-16", "15:00", "MetLife Stadium",         "East Rutherford"),
    _m("I2",  "Group I", "Iraq",           "Norway",                "2026-06-16", "18:00", "Gillette Stadium",        "Foxborough"),
    _m("I3",  "Group I", "France",         "Iraq",                  "2026-06-22", "17:00", "Lincoln Financial Field", "Philadelphia"),
    _m("I4",  "Group I", "Norway",         "Senegal",               "2026-06-22", "20:00", "MetLife Stadium",         "East Rutherford"),
    _m("I5",  "Group I", "Norway",         "France",                "2026-06-26", "15:00", "Gillette Stadium",        "Foxborough"),
    _m("I6",  "Group I", "Senegal",        "Iraq",                  "2026-06-26", "15:00", "BMO Field",               "Toronto"),

    # ── GROUP J ──────────────────────────────────────────────────────────────
    _m("J1",  "Group J", "Argentina",      "Algeria",               "2026-06-16", "20:00", "Arrowhead Stadium",       "Kansas City"),
    _m("J2",  "Group J", "Austria",        "Jordan",                "2026-06-16", "21:00", "Levi's Stadium",          "Santa Clara"),
    _m("J3",  "Group J", "Argentina",      "Austria",               "2026-06-22", "12:00", "AT&T Stadium",            "Arlington"),
    _m("J4",  "Group J", "Jordan",         "Algeria",               "2026-06-22", "20:00", "Levi's Stadium",          "Santa Clara"),
    _m("J5",  "Group J", "Algeria",        "Austria",               "2026-06-27", "21:00", "Arrowhead Stadium",       "Kansas City"),
    _m("J6",  "Group J", "Jordan",         "Argentina",             "2026-06-27", "21:00", "AT&T Stadium",            "Arlington"),

    # ── GROUP K ──────────────────────────────────────────────────────────────
    _m("K1",  "Group K", "Portugal",       "DR Congo",              "2026-06-17", "12:00", "NRG Stadium",             "Houston"),
    _m("K2",  "Group K", "Uzbekistan",     "Colombia",              "2026-06-17", "20:00", "Estadio Azteca",          "Mexico City"),
    _m("K3",  "Group K", "Portugal",       "Uzbekistan",            "2026-06-23", "12:00", "NRG Stadium",             "Houston"),
    _m("K4",  "Group K", "Colombia",       "DR Congo",              "2026-06-23", "20:00", "Estadio Akron",           "Zapopan"),
    _m("K5",  "Group K", "Colombia",       "Portugal",              "2026-06-27", "19:30", "Hard Rock Stadium",       "Miami Gardens"),
    _m("K6",  "Group K", "DR Congo",       "Uzbekistan",            "2026-06-27", "19:30", "Mercedes-Benz Stadium",   "Atlanta"),

    # ── GROUP L ──────────────────────────────────────────────────────────────
    _m("L1",  "Group L", "England",        "Croatia",               "2026-06-17", "15:00", "AT&T Stadium",            "Arlington"),
    _m("L2",  "Group L", "Ghana",          "Panama",                "2026-06-17", "19:00", "BMO Field",               "Toronto"),
    _m("L3",  "Group L", "England",        "Ghana",                 "2026-06-23", "16:00", "Gillette Stadium",        "Foxborough"),
    _m("L4",  "Group L", "Panama",         "Croatia",               "2026-06-23", "19:00", "BMO Field",               "Toronto"),
    _m("L5",  "Group L", "Panama",         "England",               "2026-06-27", "17:00", "MetLife Stadium",         "East Rutherford"),
    _m("L6",  "Group L", "Croatia",        "Ghana",                 "2026-06-27", "17:00", "Lincoln Financial Field", "Philadelphia"),

    # ── ROUND OF 32 ──────────────────────────────────────────────────────────
    _tbd("R32-1",  "Round of 32", "2026-06-28", "12:00", "SoFi Stadium",            "Inglewood"),
    _tbd("R32-2",  "Round of 32", "2026-06-29", "16:30", "Gillette Stadium",        "Foxborough"),
    _tbd("R32-3",  "Round of 32", "2026-06-29", "19:00", "Estadio BBVA",            "Guadalupe"),
    _tbd("R32-4",  "Round of 32", "2026-06-29", "12:00", "NRG Stadium",             "Houston"),
    _tbd("R32-5",  "Round of 32", "2026-06-30", "17:00", "MetLife Stadium",         "East Rutherford"),
    _tbd("R32-6",  "Round of 32", "2026-06-30", "12:00", "AT&T Stadium",            "Arlington"),
    _tbd("R32-7",  "Round of 32", "2026-06-30", "19:00", "Estadio Azteca",          "Mexico City"),
    _tbd("R32-8",  "Round of 32", "2026-07-01", "12:00", "Mercedes-Benz Stadium",   "Atlanta"),
    _tbd("R32-9",  "Round of 32", "2026-07-01", "17:00", "Levi's Stadium",          "Santa Clara"),
    _tbd("R32-10", "Round of 32", "2026-07-01", "13:00", "Lumen Field",             "Seattle"),
    _tbd("R32-11", "Round of 32", "2026-07-02", "19:00", "BMO Field",               "Toronto"),
    _tbd("R32-12", "Round of 32", "2026-07-02", "12:00", "SoFi Stadium",            "Inglewood"),
    _tbd("R32-13", "Round of 32", "2026-07-02", "20:00", "BC Place",                "Vancouver"),
    _tbd("R32-14", "Round of 32", "2026-07-03", "18:00", "Hard Rock Stadium",       "Miami Gardens"),
    _tbd("R32-15", "Round of 32", "2026-07-03", "20:30", "Arrowhead Stadium",       "Kansas City"),
    _tbd("R32-16", "Round of 32", "2026-07-03", "13:00", "AT&T Stadium",            "Arlington"),

    # ── ROUND OF 16 ──────────────────────────────────────────────────────────
    _tbd("R16-1",  "Round of 16", "2026-07-04", "17:00", "Lincoln Financial Field", "Philadelphia"),
    _tbd("R16-2",  "Round of 16", "2026-07-04", "12:00", "NRG Stadium",             "Houston"),
    _tbd("R16-3",  "Round of 16", "2026-07-05", "16:00", "MetLife Stadium",         "East Rutherford"),
    _tbd("R16-4",  "Round of 16", "2026-07-05", "18:00", "Estadio Azteca",          "Mexico City"),
    _tbd("R16-5",  "Round of 16", "2026-07-06", "14:00", "AT&T Stadium",            "Arlington"),
    _tbd("R16-6",  "Round of 16", "2026-07-06", "17:00", "Lumen Field",             "Seattle"),
    _tbd("R16-7",  "Round of 16", "2026-07-07", "12:00", "Mercedes-Benz Stadium",   "Atlanta"),
    _tbd("R16-8",  "Round of 16", "2026-07-07", "13:00", "BC Place",                "Vancouver"),

    # ── QUARTER-FINALS ───────────────────────────────────────────────────────
    _tbd("QF-1",   "Quarterfinal", "2026-07-09", "16:00", "Gillette Stadium",       "Foxborough"),
    _tbd("QF-2",   "Quarterfinal", "2026-07-10", "12:00", "SoFi Stadium",           "Inglewood"),
    _tbd("QF-3",   "Quarterfinal", "2026-07-11", "17:00", "Hard Rock Stadium",      "Miami Gardens"),
    _tbd("QF-4",   "Quarterfinal", "2026-07-11", "20:00", "Arrowhead Stadium",      "Kansas City"),

    # ── SEMI-FINALS ──────────────────────────────────────────────────────────
    _tbd("SF-1",   "Semifinal",    "2026-07-14", "14:00", "AT&T Stadium",           "Arlington"),
    _tbd("SF-2",   "Semifinal",    "2026-07-15", "15:00", "Mercedes-Benz Stadium",  "Atlanta"),

    # ── THIRD PLACE ──────────────────────────────────────────────────────────
    _tbd("3P",     "Third Place",  "2026-07-18", "17:00", "Hard Rock Stadium",      "Miami Gardens"),

    # ── FINAL ────────────────────────────────────────────────────────────────
    _tbd("Final",  "Final",        "2026-07-19", "15:00", "MetLife Stadium",        "East Rutherford"),
]


TEAM_STATS = {
    "France": {
        "fifa_rank": 2, "elo": 2027, "form": ["W", "W", "D", "W", "W"],
        "goals_scored_10": 23, "goals_conceded_10": 8, "xg_per90": 2.1, "xga_per90": 0.9,
        "clean_sheets": 4, "wc_titles": 2, "key_players": ["Mbappé", "Griezmann", "Camavinga"],
        "fitness_score": 88,
    },
    "Germany": {
        "fifa_rank": 12, "elo": 1953, "form": ["W", "L", "W", "W", "D"],
        "goals_scored_10": 18, "goals_conceded_10": 11, "xg_per90": 1.8, "xga_per90": 1.1,
        "clean_sheets": 3, "wc_titles": 4, "key_players": ["Müller", "Gnabry", "Neuer"],
        "fitness_score": 82,
    },
    "Brazil": {
        "fifa_rank": 4, "elo": 2012, "form": ["W", "W", "W", "D", "W"],
        "goals_scored_10": 25, "goals_conceded_10": 7, "xg_per90": 2.3, "xga_per90": 0.8,
        "clean_sheets": 5, "wc_titles": 5, "key_players": ["Vinicius Jr", "Rodrygo", "Alisson"],
        "fitness_score": 91,
    },
    "Argentina": {
        "fifa_rank": 1, "elo": 2058, "form": ["W", "W", "W", "W", "D"],
        "goals_scored_10": 22, "goals_conceded_10": 6, "xg_per90": 2.0, "xga_per90": 0.7,
        "clean_sheets": 6, "wc_titles": 3, "key_players": ["Messi", "Di María", "Martinez"],
        "fitness_score": 86,
    },
    "England": {
        "fifa_rank": 5, "elo": 1990, "form": ["W", "W", "D", "W", "W"],
        "goals_scored_10": 20, "goals_conceded_10": 9, "xg_per90": 1.9, "xga_per90": 1.0,
        "clean_sheets": 4, "wc_titles": 1, "key_players": ["Bellingham", "Saka", "Pickford"],
        "fitness_score": 85,
    },
    "Spain": {
        "fifa_rank": 7, "elo": 1973, "form": ["W", "W", "W", "D", "W"],
        "goals_scored_10": 19, "goals_conceded_10": 8, "xg_per90": 1.8, "xga_per90": 0.9,
        "clean_sheets": 5, "wc_titles": 1, "key_players": ["Yamal", "Pedri", "Morata"],
        "fitness_score": 89,
    },
    "Portugal": {
        "fifa_rank": 6, "elo": 1975, "form": ["W", "W", "D", "W", "L"],
        "goals_scored_10": 21, "goals_conceded_10": 10, "xg_per90": 2.0, "xga_per90": 1.1,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Ronaldo", "Félix", "Rúben Dias"],
        "fitness_score": 80,
    },
    "Netherlands": {
        "fifa_rank": 8, "elo": 1966, "form": ["W", "W", "D", "L", "W"],
        "goals_scored_10": 18, "goals_conceded_10": 10, "xg_per90": 1.7, "xga_per90": 1.0,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Van Dijk", "Dumfries", "Flekken"],
        "fitness_score": 83,
    },
    "Belgium": {
        "fifa_rank": 3, "elo": 1998, "form": ["W", "D", "W", "W", "D"],
        "goals_scored_10": 20, "goals_conceded_10": 9, "xg_per90": 1.9, "xga_per90": 0.9,
        "clean_sheets": 4, "wc_titles": 0, "key_players": ["De Bruyne", "Lukaku", "Courtois"],
        "fitness_score": 84,
    },
    "Mexico": {
        "fifa_rank": 15, "elo": 1901, "form": ["W", "D", "W", "L", "W"],
        "goals_scored_10": 14, "goals_conceded_10": 12, "xg_per90": 1.4, "xga_per90": 1.2,
        "clean_sheets": 2, "wc_titles": 0, "key_players": ["Jiménez", "Corona", "Ochoa"],
        "fitness_score": 78,
    },
    "United States": {
        "fifa_rank": 13, "elo": 1892, "form": ["W", "D", "W", "W", "L"],
        "goals_scored_10": 16, "goals_conceded_10": 13, "xg_per90": 1.5, "xga_per90": 1.3,
        "clean_sheets": 2, "wc_titles": 0, "key_players": ["Pulisic", "McKennie", "Turner"],
        "fitness_score": 83,
    },
    "Canada": {
        "fifa_rank": 40, "elo": 1820, "form": ["W", "D", "L", "W", "W"],
        "goals_scored_10": 13, "goals_conceded_10": 12, "xg_per90": 1.3, "xga_per90": 1.2,
        "clean_sheets": 2, "wc_titles": 0, "key_players": ["Davies", "David", "Borjan"],
        "fitness_score": 80,
    },
    "Morocco": {
        "fifa_rank": 14, "elo": 1910, "form": ["W", "W", "D", "W", "L"],
        "goals_scored_10": 15, "goals_conceded_10": 8, "xg_per90": 1.4, "xga_per90": 0.9,
        "clean_sheets": 4, "wc_titles": 0, "key_players": ["Hakimi", "En-Nesyri", "Bounou"],
        "fitness_score": 85,
    },
    "Japan": {
        "fifa_rank": 18, "elo": 1877, "form": ["W", "W", "D", "W", "D"],
        "goals_scored_10": 17, "goals_conceded_10": 10, "xg_per90": 1.6, "xga_per90": 1.0,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Mitoma", "Kubo", "Maignan"],
        "fitness_score": 87,
    },
    "Colombia": {
        "fifa_rank": 9, "elo": 1940, "form": ["W", "W", "W", "D", "W"],
        "goals_scored_10": 19, "goals_conceded_10": 9, "xg_per90": 1.8, "xga_per90": 0.9,
        "clean_sheets": 4, "wc_titles": 0, "key_players": ["Díaz", "James", "Ospina"],
        "fitness_score": 86,
    },
    "Uruguay": {
        "fifa_rank": 11, "elo": 1938, "form": ["W", "D", "W", "L", "W"],
        "goals_scored_10": 16, "goals_conceded_10": 10, "xg_per90": 1.6, "xga_per90": 1.0,
        "clean_sheets": 3, "wc_titles": 2, "key_players": ["Núñez", "Valverde", "Rochet"],
        "fitness_score": 82,
    },
    "Norway": {
        "fifa_rank": 24, "elo": 1855, "form": ["W", "W", "W", "D", "W"],
        "goals_scored_10": 22, "goals_conceded_10": 10, "xg_per90": 2.0, "xga_per90": 1.0,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Haaland", "Ødegaard", "Nyland"],
        "fitness_score": 88,
    },
    "Senegal": {
        "fifa_rank": 20, "elo": 1862, "form": ["W", "D", "W", "W", "L"],
        "goals_scored_10": 15, "goals_conceded_10": 11, "xg_per90": 1.4, "xga_per90": 1.1,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Mané", "Gueye", "Mendy"],
        "fitness_score": 81,
    },
    "Sweden": {
        "fifa_rank": 25, "elo": 1848, "form": ["W", "D", "W", "D", "W"],
        "goals_scored_10": 14, "goals_conceded_10": 10, "xg_per90": 1.4, "xga_per90": 1.0,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Isak", "Forsberg", "Olsen"],
        "fitness_score": 80,
    },
    "Ecuador": {
        "fifa_rank": 30, "elo": 1825, "form": ["W", "D", "L", "W", "W"],
        "goals_scored_10": 14, "goals_conceded_10": 11, "xg_per90": 1.3, "xga_per90": 1.1,
        "clean_sheets": 3, "wc_titles": 0, "key_players": ["Valencia", "Caicedo", "Galíndez"],
        "fitness_score": 79,
    },
    "Australia": {
        "fifa_rank": 23, "elo": 1845, "form": ["W", "D", "W", "L", "W"],
        "goals_scored_10": 13, "goals_conceded_10": 12, "xg_per90": 1.3, "xga_per90": 1.2,
        "clean_sheets": 2, "wc_titles": 0, "key_players": ["Irvine", "Leckie", "Ryan"],
        "fitness_score": 78,
    },
}

H2H_RECORDS = {
    ("France",  "Germany"):        {"france_wins": 9,  "draws": 7,  "germany_wins": 16, "last5": ["W", "D", "L", "W", "D"]},
    ("Brazil",  "Argentina"):      {"home_wins": 40,   "draws": 25, "away_wins": 37,    "last5": ["D", "L", "W", "L", "W"]},
    ("England", "France"):         {"home_wins": 17,   "draws": 7,  "away_wins": 8,     "last5": ["L", "D", "L", "W", "L"]},
    ("Spain",   "Germany"):        {"home_wins": 10,   "draws": 5,  "away_wins": 6,     "last5": ["W", "D", "W", "L", "W"]},
    ("Mexico",  "United States"):  {"home_wins": 16,   "draws": 14, "away_wins": 9,     "last5": ["W", "L", "D", "W", "D"]},
    ("Argentina","Brazil"):        {"home_wins": 37,   "draws": 25, "away_wins": 40,    "last5": ["W", "D", "L", "W", "D"]},
    ("Brazil",  "Morocco"):        {"home_wins": 3,    "draws": 1,  "away_wins": 0,     "last5": ["W", "W", "D", "W", "W"]},
    ("Netherlands","Japan"):       {"home_wins": 2,    "draws": 1,  "away_wins": 1,     "last5": ["W", "D", "W", "L", "W"]},
    ("Germany", "Netherlands"):    {"home_wins": 14,   "draws": 9,  "away_wins": 13,    "last5": ["D", "L", "W", "D", "W"]},
    ("England", "Croatia"):        {"home_wins": 8,    "draws": 4,  "away_wins": 5,     "last5": ["W", "L", "W", "L", "W"]},
    ("Norway",  "France"):         {"home_wins": 5,    "draws": 3,  "away_wins": 11,    "last5": ["L", "D", "L", "L", "D"]},
    ("Portugal","Colombia"):       {"home_wins": 4,    "draws": 2,  "away_wins": 2,     "last5": ["W", "D", "W", "W", "D"]},
    ("Spain",   "Uruguay"):        {"home_wins": 6,    "draws": 4,  "away_wins": 5,     "last5": ["W", "D", "L", "W", "D"]},
}

PRETOURNAMENT_PREDICTIONS = {
    "winner": [
        {"nation": "Brazil",    "flag": "🇧🇷", "probability": 18, "reasoning": "Strongest squad depth, Vinicius Jr in peak form"},
        {"nation": "France",    "flag": "🇫🇷", "probability": 15, "reasoning": "Defending finalist, Mbappé & Giroud partnership deadly"},
        {"nation": "England",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "probability": 12, "reasoning": "Golden generation peaking, Bellingham driving creativity"},
    ],
    "golden_boot": [
        {"player": "Erling Haaland",  "flag": "🇳🇴", "nation": "Norway",    "expected_goals": 7.1, "reasoning": "1.3 xG/90 in qualifying, Norway in favourable group"},
        {"player": "Kylian Mbappé",   "flag": "🇫🇷", "nation": "France",    "expected_goals": 6.4, "reasoning": "France favourites to go deep, Mbappé peaks in tournaments"},
        {"player": "Vinicius Jr",     "flag": "🇧🇷", "nation": "Brazil",    "expected_goals": 5.9, "reasoning": "Brazil's attacking focal point, World-class finishing"},
    ],
}
