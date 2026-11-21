from fastapi import FastAPI, HTTPException, Query

from backend.app.core.config import get_settings
from backend.app.services.api_football import ApiFootballClient, ApiFootballError

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="API inicial para consultar y analizar estadísticas de fútbol.",
    version="0.1.0",
)


@app.get("/", tags=["Inicio"])
async def home() -> dict:
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "message": "Backend inicial listo.",
    }


@app.get("/health", tags=["Sistema"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/teams/search", tags=["Equipos"])
async def search_teams(
    name: str = Query(min_length=3, description="Nombre del equipo"),
) -> dict:
    client = ApiFootballClient()
    try:
        return await client.get("teams", {"search": name})
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
