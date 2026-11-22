# Football Analytics

Dashboard personal de análisis futbolístico con FastAPI y football-data.org API v4.

## Fuente de datos
- Proveedor principal: https://www.football-data.org/
- Documentación: https://www.football-data.org/documentation/quickstart
- Autenticación: variable de entorno `FOOTBALL_DATA_TOKEN`, enviada mediante `X-Auth-Token`.
- Base URL: `https://api.football-data.org/v4`.

## Funcionalidades
- Listado de competiciones disponibles en el plan gratuito.
- Búsqueda de equipos dentro de una competición seleccionada.
- Forma reciente: últimos 5, 10, 15 o 20 partidos disponibles.
- Frecuencias históricas descriptivas de goles y ambos marcan.
- Clasificaciones y máximos goleadores cuando el proveedor los ofrece.
- Explicación de muestra, cálculos y limitaciones.

## Variables de entorno en Render
Configura:
- `FOOTBALL_DATA_TOKEN`: token privado de tu cuenta football-data.org.

No publiques el token en GitHub ni en el frontend.

## Límites conocidos
El plan gratuito tiene límite de 10 peticiones por minuto y acceso solo a las competiciones indicadas en la página oficial de cobertura. Los datos pueden tener retraso. Esta fuente no ofrece estadísticas avanzadas de remates, córners o tarjetas en el plan gratuito; esos mercados no se estiman ni se inventan.

## Despliegue
Render ejecuta:
```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

La aplicación muestra frecuencias observadas, no probabilidades futuras calibradas ni garantías de resultados.

Datos proporcionados por football-data.org.
