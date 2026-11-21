import httpx

from backend.app.core.config import get_settings


class ApiFootballError(Exception):
    """Error controlado al consultar API-Football."""


class ApiFootballClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        if not self.settings.api_football_key:
            raise ApiFootballError(
                "Falta configurar API_FOOTBALL_KEY en el archivo .env."
            )

        url = f"{self.settings.api_football_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"x-apisports-key": self.settings.api_football_key}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ApiFootballError(
                f"API-Football respondió con HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise ApiFootballError("No se pudo conectar con API-Football.") from exc
        except ValueError as exc:
            raise ApiFootballError("La API devolvió una respuesta no válida.") from exc

        if payload.get("errors"):
            raise ApiFootballError(f"API-Football informó errores: {payload['errors']}")

        return payload
