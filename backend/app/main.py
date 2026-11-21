from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.services.api_football import ApiFootballClient, ApiFootballError

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"

app = FastAPI(
    title=settings.app_name,
    description="Aplicación de análisis estadístico de fútbol.",
    version="0.2.0",
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(FRONTEND_DIR / "index.html")


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
