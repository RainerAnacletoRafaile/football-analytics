# Football Analytics

Sistema personal de análisis estadístico de fútbol. El objetivo es transformar datos recientes de equipos y jugadores en indicadores descriptivos y estimaciones de probabilidad explicables.

> Herramienta informativa y experimental. No garantiza resultados deportivos ni beneficios económicos. Las estimaciones deben mostrar su metodología, limitaciones e incertidumbre.

## Stack
- Python 3.11+
- FastAPI
- HTTPX
- Pydantic Settings
- API-Football (API v3)
- HTML, CSS y JavaScript

## Estructura
```
backend/
  app/
    main.py
    core/config.py
    services/api_football.py
frontend/
  index.html
  css/styles.css
  js/app.js
.env.example
.gitignore
requirements.txt
```

## Puesta en marcha
1. Crear y activar un entorno virtual.
2. Instalar dependencias: `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env` y añadir la clave de API-Football en `API_FOOTBALL_KEY`.
4. Ejecutar desde la raíz: `uvicorn backend.app.main:app --reload`
5. Abrir `http://127.0.0.1:8000` para ver el dashboard o `http://127.0.0.1:8000/docs` para la documentación de la API.

La clave es privada: no la compartas ni la subas al repositorio.

## Estado actual
- Dashboard web adaptable a móvil y escritorio.
- Comprobación básica del estado del backend.
- Búsqueda de equipos conectada al endpoint `/api/teams/search`.
- Los módulos de jugadores, partidos y estimaciones están pendientes.

## Fuente de datos
API-Football: https://www.api-football.com/documentation-v3

La disponibilidad de estadísticas de jugadores, remates y tarjetas depende de la competición, temporada y cobertura del proveedor. La aplicación debe indicar cuando un dato no esté disponible, en vez de inventarlo.
