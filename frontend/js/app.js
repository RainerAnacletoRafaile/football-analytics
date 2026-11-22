const form = document.querySelector("#team-search-form");
const input = document.querySelector("#team-name");
const button = document.querySelector("#search-button");
const feedback = document.querySelector("#search-feedback");
const results = document.querySelector("#team-results");
const apiStatusText = document.querySelector("#api-status-text");
const statusDot = document.querySelector(".status-dot");
const analysisPanel = document.querySelector("#team-analysis");
const analysisFeedback = document.querySelector("#analysis-feedback");
const analysisContent = document.querySelector("#analysis-content");
let selectedTeam = null;

const number = (value, suffix = "") => value === null || value === undefined || value === "" ? "—" : `${value}${suffix}`;
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const date = (value) => value ? new Date(value).toLocaleDateString("es-PE",{day:"2-digit",month:"short",year:"numeric",timeZone:"America/Lima"}) : "Fecha no disponible";

async function api(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "No se pudo completar la consulta.");
  return payload;
}

async function checkBackend() {
  try {
    await api("/health");
    apiStatusText.textContent = "Backend conectado";
    statusDot.style.background = "#b8f36b";
    statusDot.style.boxShadow = "0 0 12px #b8f36b66";
  } catch {
    apiStatusText.textContent = "Sin conexión con backend";
    statusDot.style.background = "#ff8585";
    statusDot.style.boxShadow = "0 0 12px #ff858566";
  }
}

function makeTeamCard(item) {
  const team = item.team || {};
  const card = document.createElement("article");
  card.className = "team-card";
  const logo = document.createElement("img");
  logo.src = team.logo || "";
  logo.alt = "";
  logo.loading = "lazy";
  logo.onerror = () => logo.remove();
  const details = document.createElement("div");
  details.className = "team-card-details";
  const title = document.createElement("b");
  title.textContent = team.name || "Equipo sin nombre";
  const subtitle = document.createElement("small");
  subtitle.textContent = `${team.country || "País no disponible"} · ID ${team.id || "—"}`;
  const choose = document.createElement("button");
  choose.type = "button";
  choose.className = "team-select-button";
  choose.textContent = "Analizar equipo";
  choose.addEventListener("click", () => openTeam(item));
  details.append(title, subtitle, choose);
  card.append(logo, details);
  return card;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = input.value.trim();
  if (name.length < 3) return;
  button.disabled = true;
  button.textContent = "Buscando...";
  feedback.className = "feedback";
  feedback.textContent = "Consultando API-Football...";
  results.replaceChildren();
  analysisPanel.hidden = true;
  try {
    const payload = await api(`/api/teams/search?name=${encodeURIComponent(name)}`);
    const teams = Array.isArray(payload.response) ? payload.response : [];
    feedback.textContent = teams.length
      ? `Encontramos ${teams.length} resultado(s). Selecciona el club exacto para abrir su informe.`
      : "No encontramos equipos con ese nombre. Prueba con otra búsqueda.";
    teams.forEach(item => results.append(makeTeamCard(item)));
  } catch (error) {
    feedback.className = "feedback error";
    feedback.textContent = error.message;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Buscar equipo <span>↗</span>';
  }
});

async function openTeam(item) {
  selectedTeam = item.team || {};
  analysisPanel.hidden = false;
  analysisPanel.scrollIntoView({behavior:"smooth",block:"start"});
  document.querySelector("#analysis-team-name").textContent = selectedTeam.name || "Análisis del equipo";
  document.querySelector("#analysis-subtitle").textContent = `${selectedTeam.country || "País no disponible"} · ID ${selectedTeam.id}`;
  analysisFeedback.textContent = "Buscando competiciones y temporadas disponibles...";
  analysisContent.replaceChildren();
  try {
    const payload = await api(`/api/teams/${selectedTeam.id}/leagues`);
    const leagues = payload.response || [];
    const leagueSelect = document.querySelector("#league-select");
    const seasonSelect = document.querySelector("#season-select");
    leagueSelect.replaceChildren();
    seasonSelect.replaceChildren();
    if (!leagues.length) throw new Error("El proveedor no devolvió competiciones para este equipo.");
    leagues.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = entry.league.id;
      option.textContent = `${entry.league.name} · ${entry.country?.name || "Competición"}`;
      option.dataset.seasons = JSON.stringify(entry.seasons || []);
      leagueSelect.append(option);
      if (index === 0) option.selected = true;
    });
    populateSeasons();
    analysisFeedback.textContent = `Se encontraron ${leagues.length} competición(es). Elige la competición y genera el informe.`;
  } catch (error) {
    analysisFeedback.className = "feedback error";
    analysisFeedback.textContent = error.message;
  }
}

function populateSeasons() {
  const leagueSelect = document.querySelector("#league-select");
  const seasonSelect = document.querySelector("#season-select");
  const chosen = leagueSelect.selectedOptions[0];
  const seasons = chosen ? JSON.parse(chosen.dataset.seasons || "[]") : [];
  seasonSelect.replaceChildren();
  seasons.slice().sort((a,b)=>b.year-a.year).forEach(season => {
    const option = document.createElement("option");
    option.value = season.year;
    option.textContent = `${season.year}${season.current ? " · actual" : ""}`;
    seasonSelect.append(option);
    if (season.current) option.selected = true;
  });
  if (!seasonSelect.value && seasonSelect.options.length) seasonSelect.selectedIndex = 0;
}
document.querySelector("#league-select").addEventListener("change", populateSeasons);
document.querySelector("#close-analysis").addEventListener("click",()=>analysisPanel.hidden=true);
document.querySelector("#run-analysis").addEventListener("click", runAnalysis);

function statCard(label,value,detail="") {
  return `<article class="stat-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(detail)}</small></article>`;
}
function trendCard(trend) {
  const interval = trend.historical_interval_90;
  const range = interval ? `Intervalo Wilson 90%: ${interval.lower}%–${interval.upper}%` : "Sin muestra suficiente";
  return `<article class="trend-card">
    <div class="trend-top"><b>${esc(trend.label)}</b><strong>${number(trend.rate,"%")}</strong></div>
    <div class="trend-bar"><span style="width:${Math.max(0,Math.min(100,trend.rate || 0))}%"></span></div>
    <p>${esc(trend.why)}</p><small>${esc(range)} · ${trend.total} partidos</small>
    <em>${esc(trend.interpretation)}</em>
  </article>`;
}
function renderMatches(matches) {
  if (!matches.length) return '<p class="empty-note">No hay partidos finalizados disponibles para esta muestra.</p>';
  return `<div class="match-list">${matches.map(match=>`<div class="match-row">
    <div><b>${esc(match.opponent)}</b><small>${esc(date(match.date))} · ${esc(match.venue)}</small></div>
    <strong class="result-${match.result.toLowerCase()}">${esc(match.score)}</strong>
    <span class="result-pill result-${match.result.toLowerCase()}">${match.result==="W"?"Victoria":match.result==="D"?"Empate":"Derrota"}</span>
  </div>`).join("")}</div>`;
}
function renderAnalysis(data) {
  const r=data.recent, s=data.season, h=data.home_away;
  const record = `${r.record.wins}V · ${r.record.draws}E · ${r.record.losses}D`;
  const seasonStats = [
    ["Partidos jugados",s.played],["Victorias",s.wins],["Empates",s.draws],["Derrotas",s.losses],
    ["Goles a favor",s.goals_for],["Goles en contra",s.goals_against],
    ["Media goles a favor",s.avg_goals_for],["Media goles en contra",s.avg_goals_against],
    ["Porterías a cero",s.clean_sheets],["Partidos sin marcar",s.failed_to_score],
    ["Tarjetas amarillas",s.yellow_cards],["Tarjetas rojas",s.red_cards]
  ];
  analysisContent.innerHTML = `
    <div class="analysis-section-head"><div><span class="section-kicker">01 / ÚLTIMA MUESTRA</span><h3>Forma reciente</h3></div><span class="sample-chip">${data.sample_size} de ${data.requested_sample} partidos disponibles</span></div>
    <div class="stats-grid">
      ${statCard("Balance",record,"Resultados de la muestra")}
      ${statCard("Goles marcados",number(r.goals_for),`Media ${number(r.avg_goals_for)} por partido`)}
      ${statCard("Goles recibidos",number(r.goals_against),`Media ${number(r.avg_goals_against)} por partido`)}
      ${statCard("Ambos marcan",number(r.btts_rate,"%"),"Frecuencia observada")}
      ${statCard("Marcó al menos uno",number(r.scored_rate,"%"),"Frecuencia observada")}
      ${statCard("Portería a cero",number(r.clean_sheet_rate,"%"),"Frecuencia observada")}
    </div>
    <div class="analysis-section-head"><div><span class="section-kicker">02 / TENDENCIAS</span><h3>Mercados estadísticos históricos</h3><p>Frecuencias de la muestra, no predicciones garantizadas.</p></div></div>
    <div class="trend-grid">${data.trends.map(trendCard).join("")}</div>
    <div class="analysis-section-head"><div><span class="section-kicker">03 / CONTEXTO</span><h3>Rendimiento local y visitante</h3></div></div>
    <div class="split-grid">
      ${["home","away"].map(key=>{const x=h[key];return `<article class="split-card"><h4>${key==="home"?"En casa":"Fuera de casa"}</h4><b>${x.matches} partidos</b><p>${x.wins} victorias · ${x.draws} empates · ${x.losses} derrotas</p><p>Goles: ${x.goals_for} a favor / ${x.goals_against} en contra</p><small>Promedios: ${number(x.avg_goals_for)} marcados · ${number(x.avg_goals_against)} recibidos</small></article>`}).join("")}
    </div>
    <div class="analysis-section-head"><div><span class="section-kicker">04 / TEMPORADA</span><h3>Estadísticas acumuladas oficiales</h3></div></div>
    <div class="stats-grid season-grid">${seasonStats.map(([label,value])=>statCard(label,number(value))).join("")}</div>
    <div class="analysis-section-head"><div><span class="section-kicker">05 / PARTIDO A PARTIDO</span><h3>Resultados que respaldan el análisis</h3></div></div>
    ${renderMatches(r.matches)}
    <details class="methodology" open><summary>Metodología, fuentes y límites</summary>
      <p><b>Fuente:</b> API-Football API v3. Competición ID ${data.league_id}, temporada ${data.season}. Consulta realizada: ${new Date().toLocaleString("es-PE")}.</p>
      <p><b>Cálculo:</b> ${esc(data.methodology.frequency)} ${esc(data.methodology.sample)}</p>
      <p><b>Incertidumbre:</b> ${esc(data.methodology.uncertainty)}</p>
      <ul>${data.methodology.limitations.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>
      <p>Los valores ausentes se muestran como «—». La cobertura puede variar según la liga y temporada.</p>
    </details>`;
}
async function runAnalysis() {
  if (!selectedTeam?.id) return;
  const league = document.querySelector("#league-select").value;
  const season = document.querySelector("#season-select").value;
  const last = document.querySelector("#sample-select").value;
  if (!league || !season) {
    analysisFeedback.textContent = "No hay una competición/temporada seleccionada.";
    return;
  }
  const runButton = document.querySelector("#run-analysis");
  runButton.disabled = true;
  runButton.textContent = "Calculando...";
  analysisFeedback.className = "feedback";
  analysisFeedback.textContent = "Consultando estadísticas de temporada y partidos recientes...";
  analysisContent.replaceChildren();
  try {
    const data = await api(`/api/teams/${selectedTeam.id}/analysis?league_id=${league}&season=${season}&last=${last}`);
    renderAnalysis(data);
    analysisFeedback.textContent = `Informe generado. ${data.sample_size} partidos válidos analizados.`;
  } catch (error) {
    analysisFeedback.className = "feedback error";
    analysisFeedback.textContent = error.message;
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Generar análisis ↗";
  }
}

checkBackend();


let playerRows = [];
let playerPage = 1;
let playerTotalPages = 1;
async function loadPlayers(page = 1) {
  if (!selectedTeam?.id) return;
  const league = document.querySelector("#league-select").value;
  const season = document.querySelector("#season-select").value;
  const feedback = document.querySelector("#players-feedback");
  const wrap = document.querySelector("#players-table-wrap");
  const filter = document.querySelector("#player-filter").value.trim();
  feedback.className = "feedback";
  feedback.textContent = "Consultando estadísticas individuales...";
  wrap.replaceChildren();
  document.querySelector("#player-report").hidden = false;
  try {
    const query = new URLSearchParams({league_id:league,season,page:String(page)});
    if (filter.length >= 3) query.set("search",filter);
    const payload = await api(`/api/teams/${selectedTeam.id}/players?${query}`);
    playerRows = payload.response || [];
    playerPage = payload.paging?.current || page;
    playerTotalPages = payload.paging?.total || 1;
    renderPlayers();
    feedback.textContent = playerRows.length
      ? `Página ${playerPage} de ${playerTotalPages}. Datos proporcionados por API-Football.`
      : "No hay estadísticas individuales disponibles para esta combinación de equipo, competición y temporada.";
  } catch (error) {
    feedback.className = "feedback error";
    feedback.textContent = error.message;
  }
}
function renderPlayers() {
  const filter = document.querySelector("#player-filter").value.trim().toLowerCase();
  const rows = playerRows.filter(row => (row.player?.name || "").toLowerCase().includes(filter));
  document.querySelector("#player-count").textContent = `${rows.length} jugador(es) en esta página`;
  const wrap = document.querySelector("#players-table-wrap");
  if (!rows.length) {
    wrap.innerHTML = '<p class="empty-note">No hay jugadores que coincidan con el filtro.</p>';
    return;
  }
  wrap.innerHTML = `<div class="table-scroll"><table class="players-table">
    <thead><tr><th>Jugador</th><th>Pos.</th><th>Part.</th><th>Min.</th><th>Goles</th><th>Asist.</th><th>Remates</th><th>A puerta</th><th>Pases %</th><th>Rating</th><th>Amar.</th><th>Rojas</th></tr></thead>
    <tbody>${rows.map(row=>{
      const p=row.player||{}, s=row.statistics?.[0]||{}, g=s.games||{}, sh=s.shots||{}, goals=s.goals||{}, passes=s.passes||{}, cards=s.cards||{};
      return `<tr><td><div class="player-name"><img src="${esc(p.photo||"")}" alt="" loading="lazy" onerror="this.style.display='none'"><span><b>${esc(p.name||"Sin nombre")}</b><small>#${esc(p.number??"—")}</small></span></div></td>
      <td>${esc(g.position||"—")}</td><td>${number(g.appearences)}</td><td>${number(g.minutes)}</td><td>${number(goals.total)}</td><td>${number(goals.assists)}</td><td>${number(sh.total)}</td><td>${number(sh.on)}</td><td>${number(passes.accuracy,"%")}</td><td>${number(g.rating)}</td><td>${number(cards.yellow)}</td><td>${number(cards.red)}</td></tr>`;
    }).join("")}</tbody></table></div>
    <div class="pagination"><button type="button" id="players-prev" ${playerPage<=1?"disabled":""}>Anterior</button><span>Página ${playerPage} / ${playerTotalPages}</span><button type="button" id="players-next" ${playerPage>=playerTotalPages?"disabled":""}>Siguiente</button></div>`;
  document.querySelector("#players-prev")?.addEventListener("click",()=>loadPlayers(playerPage-1));
  document.querySelector("#players-next")?.addEventListener("click",()=>loadPlayers(playerPage+1));
}
document.querySelector("#load-players").addEventListener("click",()=>loadPlayers(1));
document.querySelector("#player-filter").addEventListener("input",renderPlayers);
