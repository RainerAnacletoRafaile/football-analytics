from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from time import monotonic
import asyncio
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
_cache_locks={}
async def cached(key,endpoint,params=None,ttl=900):
    now=monotonic()
    hit=_cache.get(key)
    if hit and now-hit[0]<ttl:
        return hit[1]
    lock=_cache_locks.setdefault(key,asyncio.Lock())
    async with lock:
        now=monotonic()
        hit=_cache.get(key)
        if hit and now-hit[0]<ttl:
            return hit[1]
        value=await FootballDataClient().get(endpoint,params)
        _cache[key]=(monotonic(),value)
        if len(_cache)>512:
            expired=sorted(_cache.items(),key=lambda item:item[1][0])[:len(_cache)-512]
            for old_key,_ in expired:
                _cache.pop(old_key,None)
                _cache_locks.pop(old_key,None)
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
    end=datetime.now(ZoneInfo("America/Lima")).date()
    start=end-timedelta(days=365)
    params={"dateFrom":start.isoformat(),"dateTo":end.isoformat(),"competitions":code,"limit":500}
    try:
        d=await cached("team-matches:"+str(team_id)+":"+code,"teams/"+str(team_id)+"/matches",params,ttl=600)
        raw=d.get("matches")
        if not isinstance(raw,list):
            raise HTTPException(status_code=502,detail="Respuesta inválida del proveedor: falta la lista de partidos.")
        matches=[]
        for m in raw:
            if not isinstance(m,dict) or m.get("status")!="FINISHED":
                continue
            score=(m.get("score") or {}).get("fullTime") or {}
            home_score,away_score=score.get("home"),score.get("away")
            home=m.get("homeTeam") or {};away=m.get("awayTeam") or {}
            if not isinstance(home_score,int) or not isinstance(away_score,int):
                continue
            if home.get("id")!=team_id and away.get("id")!=team_id:
                continue
            matches.append(m)
        matches.sort(key=lambda m:m.get("utcDate") or "",reverse=True)
        rows=[]
        for m in matches[:last]:
            home=m.get("homeTeam") or {};away=m.get("awayTeam") or {}
            score=m.get("score",{}).get("fullTime",{})
            is_home=home.get("id")==team_id
            gf=score["home"] if is_home else score["away"]
            ga=score["away"] if is_home else score["home"]
            opponent=away if is_home else home
            result="W" if gf>ga else "D" if gf==ga else "L"
            rows.append({"id":m.get("id"),"date":m.get("utcDate"),"opponent":opponent.get("name") or "Rival no identificado","opponent_id":opponent.get("id"),"venue":"Local" if is_home else "Visitante","score":str(score["home"])+"-"+str(score["away"]),"goals_for":gf,"goals_against":ga,"total_goals":gf+ga,"result":result,"matchday":m.get("matchday"),"stage":m.get("stage")})
        n=len(rows)
        wins=sum(x["result"]=="W" for x in rows);draws=sum(x["result"]=="D" for x in rows);losses=sum(x["result"]=="L" for x in rows)
        gf=sum(x["goals_for"] for x in rows);ga=sum(x["goals_against"] for x in rows)
        both=sum(x["goals_for"]>0 and x["goals_against"]>0 for x in rows)
        over05=sum(x["total_goals"]>=1 for x in rows);over15=sum(x["total_goals"]>=2 for x in rows);over25=sum(x["total_goals"]>=3 for x in rows);over35=sum(x["total_goals"]>=4 for x in rows)
        scored=sum(x["goals_for"]>0 for x in rows);conceded=sum(x["goals_against"]>0 for x in rows);clean=sum(x["goals_against"]==0 for x in rows)
        pct=lambda value,total=n:round(value/total*100,1) if total else None
        def split(group):
            count=len(group)
            return {"matches":count,"wins":sum(x["result"]=="W" for x in group),"draws":sum(x["result"]=="D" for x in group),"losses":sum(x["result"]=="L" for x in group),"goals_for":sum(x["goals_for"] for x in group),"goals_against":sum(x["goals_against"] for x in group),"avg_goals_for":round(sum(x["goals_for"] for x in group)/count,2) if count else None,"avg_goals_against":round(sum(x["goals_against"] for x in group)/count,2) if count else None}
        points=wins*3+draws
        streak=None
        if rows:
            result=rows[0]["result"];count=0
            for row in rows:
                if row["result"]!=result:break
                count+=1
            streak={"result":result,"count":count}
        buckets={"0 goles":sum(x["total_goals"]==0 for x in rows),"1-2 goles":sum(1<=x["total_goals"]<=2 for x in rows),"3-4 goles":sum(3<=x["total_goals"]<=4 for x in rows),"5+ goles":sum(x["total_goals"]>=5 for x in rows)}
        trends=[]
        for label,successes,why in [
            ("Total goles +0.5",over05,"Al menos un gol en el partido."),
            ("Total goles +1.5",over15,"Al menos dos goles en el partido."),
            ("Total goles +2.5",over25,"Al menos tres goles en el partido."),
            ("Total goles +3.5",over35,"Al menos cuatro goles en el partido."),
            ("Ambos marcan",both,"Los dos equipos anotaron."),
            ("Equipo marca",scored,"El equipo anotó al menos un gol."),
            ("Portería a cero",clean,"El equipo no recibió goles.")]:
            trends.append({"label":label,"successes":successes,"total":n,"rate":pct(successes),"why":why+" "+str(successes)+" de "+str(n)+" partidos."})
        league_context=None
        try:
            table_data=await cached("standings:"+code,"competitions/"+code+"/standings",ttl=1800)
            total_table=next((x.get("table",[]) for x in table_data.get("standings",[]) if x.get("type")=="TOTAL"),[])
            team_row=next((x for x in total_table if (x.get("team") or {}).get("id")==team_id),None)
            valid_rows=[x for x in total_table if isinstance(x.get("playedGames"),int) and x.get("playedGames",0)>0]
            if team_row:
                league_context={"position":team_row.get("position"),"played":team_row.get("playedGames"),"points":team_row.get("points"),"league_teams":len(total_table),"league_avg_goals_for":round(sum(x.get("goalsFor",0) for x in valid_rows)/len(valid_rows),2) if valid_rows else None,"league_avg_goals_against":round(sum(x.get("goalsAgainst",0) for x in valid_rows)/len(valid_rows),2) if valid_rows else None,"team_goals_for":team_row.get("goalsFor"),"team_goals_against":team_row.get("goalsAgainst"),"team_goal_difference":team_row.get("goalDifference")}
        except (FootballDataError,AttributeError,TypeError,ValueError):
            league_context=None
        return {"team_id":team_id,"competition":code,"source":"football-data.org","generated_at":datetime.now(ZoneInfo("America/Lima")).isoformat(),"period":{"from":start.isoformat(),"to":end.isoformat()},"sample_size":n,"requested_sample":last,"data_quality":{"valid_finished_matches":n,"discarded_or_unfinished_matches":len(raw)-len(matches),"sample_label":"Muestra reducida" if n<5 else "Muestra moderada" if n<10 else "Muestra amplia" if n>=15 else "Muestra estándar","warning":"La muestra es pequeña; evita sacar conclusiones fuertes." if n<5 else ("Los porcentajes describen estos partidos, no garantizan el siguiente resultado." if n<15 else "La muestra es descriptiva y no constituye una predicción.")},"league_context":league_context,"recent":{"matches":rows,"record":{"wins":wins,"draws":draws,"losses":losses,"points":points,"points_per_game":round(points/n,2) if n else None,"win_rate":pct(wins),"draw_rate":pct(draws),"loss_rate":pct(losses)},"goals_for":gf,"goals_against":ga,"goal_difference":gf-ga,"avg_total_goals":round((gf+ga)/n,2) if n else None,"avg_goals_for":round(gf/n,2) if n else None,"avg_goals_against":round(ga/n,2) if n else None,"btts_rate":pct(both),"scored_rate":pct(scored),"conceded_rate":pct(conceded),"clean_sheet_rate":pct(clean),"home":split([x for x in rows if x["venue"]=="Local"]),"away":split([x for x in rows if x["venue"]=="Visitante"]),"goal_buckets":buckets,"current_streak":streak,"goals_by_match":[{"opponent":x["opponent"],"date":x["date"],"for":x["goals_for"],"against":x["goals_against"],"total":x["total_goals"],"result":x["result"]} for x in reversed(rows)]},"trends":trends,"methodology":{"sample":"Últimos "+str(last)+" partidos finalizados en los últimos 365 días; se excluyen partidos sin marcador final válido.","frequency":"Frecuencia observada = aciertos / partidos válidos × 100.","uncertainty":"No es una probabilidad predictiva ni una recomendación de apuesta.","limitations":["Se utilizan únicamente campos que entrega football-data.org en el plan contratado.","No se generan remates, tiros a puerta, córners, posesión o tarjetas si el proveedor no los entrega en esta cobertura.","Los marcadores y calendarios pueden tener retraso según el plan.","La tabla de liga puede no estar disponible para algunas competiciones o fases.","No se ajusta por lesiones, alineaciones, descanso ni fuerza del rival."]}}
    except FootballDataError as e:
        fail(e)

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
