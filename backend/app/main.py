from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.services.api_football import ApiFootballClient, ApiFootballError
from backend.app.services.analytics import build_team_analysis

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title=settings.app_name,
    description="Laboratorio de análisis estadístico de fútbol con datos verificables.",
    version="0.3.0",
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["Sistema"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/provider/status", tags=["Sistema"])
async def provider_status() -> dict:
    client = ApiFootballClient()
    try:
        payload = await client.get("status")
        account = (payload.get("response") or [{}])[0]
        return {"connected": True, "account": account, "provider": "API-Football"}
    except ApiFootballError as exc:
        return {"connected": False, "error": str(exc), "provider": "API-Football"}


@app.get("/api/teams/search", tags=["Equipos"])
async def search_teams(name: str = Query(min_length=3, description="Nombre del equipo")) -> dict:
    client = ApiFootballClient()
    try:
        return await client.get("teams", {"search": name})
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/teams/{team_id}/leagues", tags=["Equipos"])
async def team_leagues(team_id: int) -> dict:
    client = ApiFootballClient()
    try:
        payload = await client.get("leagues", {"team": team_id, "current": "true"})
        if not payload.get("response"):
            payload = await client.get("leagues", {"team": team_id})
        return payload
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/teams/{team_id}/analysis", tags=["Análisis"])
async def team_analysis(
    team_id: int,
    league_id: int = Query(gt=0),
    season: int = Query(ge=2000, le=2100),
    last: int = Query(default=10, ge=5, le=20),
) -> dict:
    client = ApiFootballClient()
    try:
        season_stats, fixtures = await __import__("asyncio").gather(
            client.get("teams/statistics", {"team": team_id, "league": league_id, "season": season}),
            client.get("fixtures", {
                "team": team_id, "league": league_id, "season": season,
                "last": last, "timezone": "America/Lima"
            }),
        )
        return build_team_analysis(team_id, league_id, season, season_stats.get("response") or {}, fixtures, last)
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/teams/{team_id}/players", tags=["Jugadores"])
async def team_players(
    team_id: int,
    league_id: int = Query(gt=0),
    season: int = Query(ge=2000, le=2100),
    search: str | None = Query(default=None, min_length=3),
    page: int = Query(default=1, ge=1, le=50),
) -> dict:
    client = ApiFootballClient()
    params = {"team": team_id, "league": league_id, "season": season, "page": page}
    if search:
        params["search"] = search
    try:
        return await client.get("players", params)
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
