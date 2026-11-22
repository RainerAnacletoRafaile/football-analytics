import httpx
from backend.app.core.config import get_settings

class FootballDataError(Exception):
    pass

class FootballDataClient:
    def __init__(self):
        self.settings = get_settings()

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        if not self.settings.football_data_token:
            raise FootballDataError("Falta configurar FOOTBALL_DATA_TOKEN en Render.")
        url = self.settings.football_data_base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.get(url, headers={"X-Auth-Token": self.settings.football_data_token}, params=params)
                if response.status_code == 429:
                    reset=response.headers.get("X-RequestCounter-Reset")
                    wait=(" El contador se restablece en aproximadamente "+reset+" segundos." if reset and reset.isdigit() else " Espera a que se restablezca la ventana de un minuto.")
                    raise FootballDataError("Límite de football-data.org alcanzado (10 peticiones/minuto)."+wait)
                if response.status_code == 403:
                    raise FootballDataError("Este recurso o competición no está incluido en tu plan gratuito.")
                if response.status_code == 401:
                    raise FootballDataError("Token no válido. Revisa FOOTBALL_DATA_TOKEN en Render.")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise FootballDataError("Football-data.org respondió HTTP " + str(exc.response.status_code)) from exc
        except httpx.HTTPError as exc:
            raise FootballDataError("No se pudo conectar con football-data.org.") from exc
