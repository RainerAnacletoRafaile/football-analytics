from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from time import monotonic
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import get_settings
from backend.app.services.football_data import FootballDataClient, FootballDataError

settings=get_settings()
FRONTEND_DIR=Path(__file__).resolve().parents[2]/"frontend"
app=FastAPI(title=settings.app_name,description="Football Analytics con datos de football-data.org.",version="1.0.0")
app.mount("/static",StaticFiles(directory=FRONTEND_DIR),name="static")
_cache={}
async def cached(key,endpoint,params=None,ttl=900):
    now=monotonic()
    hit=_cache.get(key)
    if hit and now-hit[0]<ttl:return hit[1]
    value=await FootballDataClient().get(endpoint,params)
    _cache[key]=(now,value)
    return value
def fail(exc):
    raise HTTPException(status_code=503,detail=str(exc)) from exc

@app.get("/",include_in_schema=False)
async def home():return FileResponse(FRONTEND_DIR/"index.html")

@app.get("/health")
async def health():return {"status":"ok","provider":"football-data.org"}

@app.get("/api/provider/status")
async def provider_status():
    try:
        d=await cached("competitions","competitions",ttl=3600)
        return {"connected":True,"provider":"football-data.org","competition_count":len(d.get("competitions",[])),"plan":"Free"}
    except FootballDataError as e:return {"connected":False,"provider":"football-data.org","error":str(e)}

@app.get("/api/competitions")
async def competitions():
    try:return await cached("competitions","competitions",ttl=3600)
    except FootballDataError as e:fail(e)

@app.get("/api/competitions/{code}/teams")
async def competition_teams(code:str):
    try:return await cached("teams:"+code,"competitions/"+code.upper()+"/teams",ttl=3600)
    except FootballDataError as e:fail(e)

@app.get("/api/teams/search")
async def search_teams(name:str=Query(min_length=2),competition:str=Query(min_length=2)):
    code=competition.upper()
    try:
        d=await cached("teams:"+code,"competitions/"+code+"/teams",ttl=3600)
        q=name.casefold()
        rows=[t for t in d.get("teams",[]) if q in (t.get("name") or "").casefold() or q in (t.get("shortName") or "").casefold() or q in (t.get("tla") or "").casefold()]
        return {"response":[{"team":t,"competition":d.get("competition",{})} for t in rows],"results":len(rows),"source":"football-data.org"}
    except FootballDataError as e:fail(e)

@app.get("/api/teams/{team_id}/analysis")
async def team_analysis(team_id:int,competition:str=Query(min_length=2),last:int=Query(default=10,ge=5,le=20)):
    code=competition.upper()
    end=datetime.now(ZoneInfo('America/Lima')).date()
    start=end-timedelta(days=240)
    params={"dateFrom":start.isoformat(),"dateTo":end.isoformat(),"competitions":code,"limit":100}
    try:
        d=await cached("team-matches:"+str(team_id)+":"+code,"teams/"+str(team_id)+"/matches",params,ttl=600)
        matches=[m for m in d.get("matches",[]) if m.get("status")=="FINISHED" and m.get("score",{}).get("fullTime",{}).get("home") is not None]
        matches.sort(key=lambda m:m.get("utcDate",""),reverse=True)
        rows=[]
        for m in matches[:last]:
            home=m.get("homeTeam",{});away=m.get("awayTeam",{});score=m.get("score",{}).get("fullTime",{})
            ih=home.get("id")==team_id
            gf=score.get("home") if ih else score.get("away")
            ga=score.get("away") if ih else score.get("home")
            opp=away if ih else home
            result="W" if gf>ga else "D" if gf==ga else "L"
            rows.append({"id":m.get("id"),"date":m.get("utcDate"),"opponent":opp.get("name"),"venue":"Local" if ih else "Visitante","score":str(score.get("home"))+"-"+str(score.get("away")),"goals_for":gf,"goals_against":ga,"result":result})
        n=len(rows);wins=sum(x["result"]=="W" for x in rows);draws=sum(x["result"]=="D" for x in rows);losses=sum(x["result"]=="L" for x in rows)
        gf=sum(x["goals_for"] for x in rows);ga=sum(x["goals_against"] for x in rows)
        both=sum(x["goals_for"]>0 and x["goals_against"]>0 for x in rows)
        o15=sum(x["goals_for"]+x["goals_against"]>=2 for x in rows);o25=sum(x["goals_for"]+x["goals_against"]>=3 for x in rows)
        pct=lambda x:round(x/n*100,1) if n else None
        trends=[{"label":"Total goles +1.5","successes":o15,"total":n,"rate":pct(o15),"why":"Hubo al menos dos goles en "+str(o15)+" de "+str(n)+" partidos."},{"label":"Total goles +2.5","successes":o25,"total":n,"rate":pct(o25),"why":"Hubo al menos tres goles en "+str(o25)+" de "+str(n)+" partidos."},{"label":"Ambos marcan","successes":both,"total":n,"rate":pct(both),"why":"Ambos equipos marcaron en "+str(both)+" de "+str(n)+" partidos."}]
        return {"team_id":team_id,"competition":code,"source":"football-data.org","sample_size":n,"requested_sample":last,"recent":{"matches":rows,"record":{"wins":wins,"draws":draws,"losses":losses},"goals_for":gf,"goals_against":ga,"avg_goals_for":round(gf/n,2) if n else None,"avg_goals_against":round(ga/n,2) if n else None,"btts_rate":pct(both),"scored_rate":pct(sum(x["goals_for"]>0 for x in rows)),"clean_sheet_rate":pct(sum(x["goals_against"]==0 for x in rows))},"trends":trends,"methodology":{"sample":"Últimos "+str(last)+" partidos finalizados dentro de los últimos 240 días.","frequency":"Aciertos observados / partidos válidos × 100.","uncertainty":"Frecuencia descriptiva, no probabilidad predictiva calibrada.","limitations":["Cobertura limitada a las competiciones del plan gratuito.","Este proveedor no ofrece remates, córners ni tarjetas en el plan gratuito.","Los marcadores pueden tener retraso.","No se ajusta por lesiones, alineaciones ni fuerza del rival."]}}
    except FootballDataError as e:fail(e)

@app.get("/api/competitions/{code}/standings")
async def standings(code:str):
    try:return await cached("standings:"+code,"competitions/"+code.upper()+"/standings",ttl=1800)
    except FootballDataError as e:fail(e)

@app.get("/api/competitions/{code}/scorers")
async def scorers(code:str,limit:int=Query(default=10,ge=1,le=20)):
    try:return await cached("scorers:"+code,"competitions/"+code.upper()+"/scorers",{"limit":limit},ttl=1800)
    except FootballDataError as e:fail(e)

@app.get("/api/matches")
async def matches(date_from:date|None=None,date_to:date|None=None):
    start=date_from or datetime.now(ZoneInfo('America/Lima')).date();end=date_to or start
    try:return await cached("matches:"+str(start)+":"+str(end),"matches",{"dateFrom":start.isoformat(),"dateTo":end.isoformat()},ttl=300)
    except FootballDataError as e:fail(e)
