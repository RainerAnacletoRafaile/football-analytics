from __future__ import annotations

from collections import Counter
from math import sqrt
from typing import Any


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(part: int, total: int) -> float | None:
    return round(part / total * 100, 1) if total else None


def _wilson(successes: int, total: int, z: float = 1.645) -> dict[str, float] | None:
    """90% Wilson interval for a historical proportion, not a forecast guarantee."""
    if total == 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * sqrt((p * (1 - p) / total) + (z * z / (4 * total * total))) / denominator
    return {"lower": round(max(0, center - margin) * 100, 1),
            "upper": round(min(1, center + margin) * 100, 1)}


def build_team_analysis(team_id: int, league_id: int, season: int,
                        season_stats: dict, fixtures_payload: dict, last: int) -> dict:
    fixtures = fixtures_payload.get("response") or []
    finished = []
    for item in fixtures:
        fixture = item.get("fixture") or {}
        status = (fixture.get("status") or {}).get("short")
        goals = item.get("goals") or {}
        home = item.get("teams", {}).get("home") or {}
        away = item.get("teams", {}).get("away") or {}
        gh, ga = goals.get("home"), goals.get("away")
        if status not in {"FT", "AET", "PEN"} or gh is None or ga is None:
            continue
        is_home = home.get("id") == team_id
        if not is_home and away.get("id") != team_id:
            continue
        gf, gc = (gh, ga) if is_home else (ga, gh)
        result = "W" if gf > gc else "D" if gf == gc else "L"
        finished.append({
            "fixture_id": fixture.get("id"),
            "date": fixture.get("date"),
            "venue": "Local" if is_home else "Visitante",
            "opponent": away.get("name") if is_home else home.get("name"),
            "opponent_logo": away.get("logo") if is_home else home.get("logo"),
            "score": f"{gh}-{ga}",
            "goals_for": gf,
            "goals_against": gc,
            "result": result,
            "league": (item.get("league") or {}).get("name"),
        })

    finished.sort(key=lambda x: x.get("date") or "", reverse=True)
    sample = finished[:last]
    n = len(sample)
    wins = sum(x["result"] == "W" for x in sample)
    draws = sum(x["result"] == "D" for x in sample)
    losses = sum(x["result"] == "L" for x in sample)
    scored = sum(x["goals_for"] > 0 for x in sample)
    conceded = sum(x["goals_against"] > 0 for x in sample)
    btts = sum(x["goals_for"] > 0 and x["goals_against"] > 0 for x in sample)
    over15 = sum(x["goals_for"] + x["goals_against"] >= 2 for x in sample)
    over25 = sum(x["goals_for"] + x["goals_against"] >= 3 for x in sample)
    over35 = sum(x["goals_for"] + x["goals_against"] >= 4 for x in sample)
    clean = sum(x["goals_against"] == 0 for x in sample)
    failed = sum(x["goals_for"] == 0 for x in sample)
    total_gf = sum(x["goals_for"] for x in sample)
    total_ga = sum(x["goals_against"] for x in sample)
    home_games = [x for x in sample if x["venue"] == "Local"]
    away_games = [x for x in sample if x["venue"] == "Visitante"]

    def split_stats(rows: list[dict]) -> dict:
        count = len(rows)
        return {
            "matches": count,
            "wins": sum(x["result"] == "W" for x in rows),
            "draws": sum(x["result"] == "D" for x in rows),
            "losses": sum(x["result"] == "L" for x in rows),
            "goals_for": sum(x["goals_for"] for x in rows),
            "goals_against": sum(x["goals_against"] for x in rows),
            "avg_goals_for": round(sum(x["goals_for"] for x in rows) / count, 2) if count else None,
            "avg_goals_against": round(sum(x["goals_against"] for x in rows) / count, 2) if count else None,
        }

    trends = [
        {"key": "victory", "label": "Victoria", "successes": wins, "total": n,
         "rate": _pct(wins, n), "why": f"Ganó {wins} de {n} partidos recientes."},
        {"key": "team_over_0_5", "label": "Equipo marca +0.5 goles", "successes": scored, "total": n,
         "rate": _pct(scored, n), "why": f"Marcó al menos un gol en {scored} de {n} partidos."},
        {"key": "team_over_1_5", "label": "Equipo marca +1.5 goles", "successes": sum(x["goals_for"] >= 2 for x in sample), "total": n,
         "rate": _pct(sum(x["goals_for"] >= 2 for x in sample), n),
         "why": f"Marcó dos o más goles en {sum(x['goals_for'] >= 2 for x in sample)} de {n} partidos."},
        {"key": "over_1_5", "label": "Total goles +1.5", "successes": over15, "total": n,
         "rate": _pct(over15, n), "why": f"Hubo al menos 2 goles totales en {over15} de {n} partidos."},
        {"key": "over_2_5", "label": "Total goles +2.5", "successes": over25, "total": n,
         "rate": _pct(over25, n), "why": f"Hubo al menos 3 goles totales en {over25} de {n} partidos."},
        {"key": "over_3_5", "label": "Total goles +3.5", "successes": over35, "total": n,
         "rate": _pct(over35, n), "why": f"Hubo al menos 4 goles totales en {over35} de {n} partidos."},
        {"key": "btts", "label": "Ambos equipos marcan", "successes": btts, "total": n,
         "rate": _pct(btts, n), "why": f"Ambos marcaron en {btts} de {n} partidos."},
        {"key": "clean_sheet", "label": "Portería a cero", "successes": clean, "total": n,
         "rate": _pct(clean, n), "why": f"No recibió goles en {clean} de {n} partidos."},
    ]
    for trend in trends:
        trend["historical_interval_90"] = _wilson(trend["successes"], trend["total"])
        trend["interpretation"] = (
            "Muestra pequeña: interpretar con mucha cautela." if n < 5 else
            "Frecuencia histórica descriptiva; no equivale a una probabilidad futura calibrada."
        )

    stats = season_stats or {}
    fixtures_stats = stats.get("fixtures") or {}
    goals_stats = stats.get("goals") or {}
    cards_stats = stats.get("cards") or {}
    goals_for_stats = goals_stats.get("for") or {}
    goals_against_stats = goals_stats.get("against") or {}
    goals_for_total = (goals_for_stats.get("total") or {}).get("total")
    goals_against_total = (goals_against_stats.get("total") or {}).get("total")

    season_summary = {
        "played": (fixtures_stats.get("played") or {}).get("total"),
        "wins": (fixtures_stats.get("wins") or {}).get("total"),
        "draws": (fixtures_stats.get("draws") or {}).get("total"),
        "losses": (fixtures_stats.get("loses") or {}).get("total"),
        "goals_for": goals_for_total,
        "goals_against": goals_against_total,
        "avg_goals_for": _number(goals_for_stats.get("average", {}).get("total")),
        "avg_goals_against": _number(goals_against_stats.get("average", {}).get("total")),
        "clean_sheets": (stats.get("clean_sheet") or {}).get("total"),
        "failed_to_score": (stats.get("failed_to_score") or {}).get("total"),
        "yellow_cards": (cards_stats.get("yellow") or {}).get("total"),
        "red_cards": (cards_stats.get("red") or {}).get("total"),
        "form": stats.get("form"),
    }

    return {
        "team_id": team_id,
        "league_id": league_id,
        "season": season,
        "sample_size": n,
        "requested_sample": last,
        "recent": {
            "matches": sample,
            "record": {"wins": wins, "draws": draws, "losses": losses},
            "goals_for": total_gf,
            "goals_against": total_ga,
            "avg_goals_for": round(total_gf / n, 2) if n else None,
            "avg_goals_against": round(total_ga / n, 2) if n else None,
            "scored_rate": _pct(scored, n),
            "conceded_rate": _pct(conceded, n),
            "btts_rate": _pct(btts, n),
            "clean_sheet_rate": _pct(clean, n),
            "failed_to_score_rate": _pct(failed, n),
        },
        "home_away": {"home": split_stats(home_games), "away": split_stats(away_games)},
        "trends": trends,
        "season": season_summary,
        "source": "API-Football API v3",
        "methodology": {
            "sample": f"Últimos {last} partidos finalizados disponibles para el equipo en la competición y temporada seleccionadas.",
            "frequency": "Aciertos observados / partidos válidos de la muestra × 100.",
            "uncertainty": "Intervalo Wilson del 90% para una proporción histórica. No es una predicción calibrada.",
            "limitations": ["La cobertura depende de la competición y temporada.",
                            "Los partidos aplazados o sin resultado final se excluyen.",
                            "Una muestra corta puede cambiar mucho con un solo partido.",
                            "No se ajusta por fuerza del rival, alineaciones, lesiones ni contexto del próximo partido."],
        },
        "available_matches": len(finished),
    }
