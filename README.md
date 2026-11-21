# Football Analytics

Sistema académico de análisis estadístico de fútbol. El objetivo es transformar datos recientes de equipos y jugadores en indicadores descriptivos y estimaciones de probabilidad explicables.

> Este proyecto es una herramienta informativa y experimental. No garantiza resultados deportivos ni beneficios económicos, y no debe tratar sus estimaciones como recomendaciones de apuestas.

## Stack inicial
- Python 3.11+
- FastAPI
- HTTPX
- Pydantic Settings
- API-Football (API v3)
- HTML, CSS y Bootstrap (interfaz en una siguiente iteración)

## Estructura
```
backend/
  app/
    main.py
    core/config.py
    services/api_football.py
.env.example
.gitignore
requirements.txt
```

## Puesta en marcha
1. Crear y activar un entorno virtual.
2. Instalar dependencias: `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env` y añadir la clave de API-Football.
4. Ejecutar desde la raíz: `uvicorn backend.app.main:app --reload`
5. Abrir `http://127.0.0.1:8000/docs` para consultar la API.

La clave se configura como `API_FOOTBALL_KEY` y nunca debe subirse al repositorio.

## Fuente de datos
API-Football: https://www.api-football.com/documentation-v3

La disponibilidad de estadísticas de jugadores, remates y tarjetas depende de la competición, temporada y cobertura de datos del proveedor. La aplicación deberá indicar cuando un dato no esté disponible, en vez de inventarlo.
