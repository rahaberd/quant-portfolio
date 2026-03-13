const gridEl = document.getElementById("articlesGrid");
const filterEl = document.getElementById("sourceFilter");
const emptyStateEl = document.getElementById("emptyState");
const wsStatusEl = document.getElementById("wsStatus");

let articles = [];
let activeSource = "";
let reconnectDelayMs = 1000;

filterEl.addEventListener("change", async (event) => {
  activeSource = event.target.value;
  await loadInitialNews();
});

async function loadInitialNews() {
  const query = activeSource ? `?source=${encodeURIComponent(activeSource)}` : "";

  try {
    const response = await fetch(`/api/news${query}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch news: ${response.status}`);
    }

    const payload = await response.json();
    articles = payload;
    refreshFilterOptions(payload);
    renderArticles();
  } catch (error) {
    console.error(error);
  }
}

function refreshFilterOptions(payload) {
  const knownSources = new Set(Array.from(filterEl.options).map((opt) => opt.value).filter(Boolean));
  const incomingSources = new Set(payload.map((item) => item.source).filter(Boolean));

  for (const source of incomingSources) {
    if (knownSources.has(source)) {
      continue;
    }
    const option = document.createElement("option");
    option.value = source;
    option.textContent = source;
    filterEl.appendChild(option);
  }
}

function renderArticles() {
  gridEl.innerHTML = "";

  for (const article of articles) {
    const card = buildArticleCard(article);
    gridEl.appendChild(card);
  }

  emptyStateEl.classList.toggle("hidden", articles.length > 0);
}

function buildArticleCard(article) {
  const wrapper = document.createElement("article");
  wrapper.className =
    "card-enter overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-0.5 hover:shadow-lg";

  const imageMarkup = article.image_url
    ? `<img src="${escapeHtml(article.image_url)}" alt="" class="h-48 w-full object-cover" loading="lazy" referrerpolicy="no-referrer" />`
    : `<div class="flex h-48 w-full items-center justify-center bg-gradient-to-br from-emerald-100 to-sky-100 text-sm font-medium text-slate-500">No image available</div>`;

  wrapper.innerHTML = `
    ${imageMarkup}
    <div class="space-y-3 p-5">
      <div class="flex items-center justify-between gap-3">
        <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">${escapeHtml(article.source)}</span>
        <span class="text-xs text-slate-500">${timeAgo(article.published_at)}</span>
      </div>
      <h2 class="headline-font text-lg font-semibold leading-snug text-slate-900">${escapeHtml(article.title)}</h2>
      <p class="summary-clamp text-sm text-slate-600">${escapeHtml(article.summary || "No summary available.")}</p>
      <a
        href="${escapeHtml(article.url)}"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center text-sm font-semibold text-amber-600 hover:text-amber-700"
      >
        Read full article
      </a>
    </div>
  `;

  return wrapper;
}

function upsertIncomingArticle(article) {
  const duplicateIndex = articles.findIndex((item) => item.url === article.url);
  if (duplicateIndex >= 0) {
    articles.splice(duplicateIndex, 1);
  }

  if (activeSource && article.source !== activeSource) {
    return;
  }

  articles.unshift(article);
  articles = articles.slice(0, 50);
  renderArticles();
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/news`);

  socket.addEventListener("open", () => {
    wsStatusEl.textContent = "Live";
    wsStatusEl.className = "rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800";
    reconnectDelayMs = 1000;
  });

  socket.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      refreshFilterOptions([data]);
      upsertIncomingArticle(data);
    } catch (error) {
      console.error("Failed to parse WebSocket payload", error);
    }
  });

  socket.addEventListener("close", () => {
    wsStatusEl.textContent = "Reconnecting...";
    wsStatusEl.className = "rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800";

    setTimeout(connectWebSocket, reconnectDelayMs);
    reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
  });

  socket.addEventListener("error", (error) => {
    console.error("WebSocket error", error);
    socket.close();
  });
}

function timeAgo(isoDate) {
  const then = new Date(isoDate).getTime();
  if (!Number.isFinite(then)) {
    return "just now";
  }

  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

(async function bootstrap() {
  await loadInitialNews();
  connectWebSocket();
})();
