const form = document.querySelector("#team-search-form");
const input = document.querySelector("#team-name");
const button = document.querySelector("#search-button");
const feedback = document.querySelector("#search-feedback");
const results = document.querySelector("#team-results");
const apiStatusText = document.querySelector("#api-status-text");
const statusDot = document.querySelector(".status-dot");

async function checkBackend() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Backend no disponible");
    apiStatusText.textContent = "Backend conectado";
    statusDot.style.background = "#b8f36b";
    statusDot.style.boxShadow = "0 0 12px #b8f36b66";
  } catch {
    apiStatusText.textContent = "Sin conexión con backend";
    statusDot.style.background = "#ff8585";
    statusDot.style.boxShadow = "0 0 12px #ff858566";
  }
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

  try {
    const response = await fetch(`/api/teams/search?name=${encodeURIComponent(name)}`);
    const payload = await response.json();
    if (!response.ok) {
      const detail = typeof payload.detail === "string" ? payload.detail : "No se pudo completar la consulta.";
      throw new Error(detail);
    }

    const teams = Array.isArray(payload.response) ? payload.response : [];
    if (!teams.length) {
      feedback.textContent = "No encontramos equipos con ese nombre. Prueba con otra búsqueda.";
      return;
    }

    feedback.textContent = `Encontramos ${teams.length} resultado(s). La información mostrada depende de la cobertura del proveedor.`;
    for (const item of teams) {
      const team = item.team || {};
      const country = item.team?.country || "País no disponible";
      const card = document.createElement("article");
      card.className = "team-card";
      if (team.logo) {
        const logo = document.createElement("img");
        logo.src = team.logo;
        logo.alt = "";
        logo.loading = "lazy";
        card.append(logo);
      }
      const details = document.createElement("div");
      const title = document.createElement("b");
      title.textContent = team.name || "Equipo sin nombre";
      const subtitle = document.createElement("small");
      subtitle.textContent = `${country}${team.id ? ` · ID ${team.id}` : ""}`;
      details.append(title, subtitle);
      card.append(details);
      results.append(card);
    }
  } catch (error) {
    feedback.className = "feedback error";
    feedback.textContent = error.message || "Ha ocurrido un error al consultar los datos.";
  } finally {
    button.disabled = false;
    button.innerHTML = 'Buscar equipo <span>↗</span>';
  }
});

checkBackend();