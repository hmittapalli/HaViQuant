const API = (location.hostname === "127.0.0.1" || location.hostname === "localhost")
  ? "http://127.0.0.1:8000/api/v1"
  : "https://haviquant-1.onrender.com/api/v1";

const NAV_GROUPS = [
  {label: "Home", items: [
    ["Dashboard", "Market Pulse"],
  ]},
  {label: "Discover", items: [
    ["Trade Scanner", "Trade Scanner"],
    ["News", "News Hub"],
    ["Calendar", "Economic Calendar"],
  ]},
  {label: "Analyze", items: [
    ["Company Intelligence", "HaVi 360"],
    ["Evidence Research", "Evidence"],
    ["Technical", "Technicals"],
    ["Fundamentals", "Fundamentals"],
  ]},
  {label: "Decide", items: [
    ["AI Trade Planner", "AI Trade Planner"],
    ["Decision", "Trade Setup"],
    ["Risk", "Risk Management"],
    ["Backtesting", "Backtesting"],
  ]},
];

const NAV = NAV_GROUPS.flatMap((group) => group.items.map(([page]) => page));

const ICONS = {
  "Dashboard": "grid",
  "Stock Analysis": "trend",
  "Company Intelligence": "building",
  "Fundamentals": "bars",
  "Technical": "pulse",
  "Decision": "bolt",
  "Trade Scanner": "scanner",
  "Evidence Research": "flask",
  "Portfolio": "wallet",
  "Risk": "shield",
  "Backtesting": "backtest",
  "News": "news",
  "Calendar": "calendar",
  "AI Trade Planner": "bolt",
};

const TIMEFRAMES = {
  "1m": ["7d", "1m"],
  "5m": ["60d", "5m"],
  "15m": ["60d", "15m"],
  "30m": ["60d", "30m"],
  "1H": ["60d", "1h"],
  "4H": ["60d", "4h"],
  "1D": ["5y", "1d"],
  "1W": ["5y", "1wk"],
  "1M": ["10y", "1mo"],
};

const CALENDAR_TABS = ["Upcoming", "Macro", "Politics", "Geopolitical", "Earnings", "Economic", "Fed", "All"];
const EVENTS = [];

const state = {
  ticker: "NVDA",
  query: "NVDA",
  page: "Dashboard",
  tf: "5m",
  analysis: null,
  news: [],
  scanner: null,
  scannerLoading: false,
  scannerError: "",
  scannerSector: "All",
  geopolitical: null,
  geopoliticalLoading: false,
  geopoliticalError: "",
  macro: null,
  fallbackMovers: null,
  moversLoading: false,
  planner: null,
  plannerLoading: false,
  plannerError: "",
  plannerForm: {
    capital: 500,
    risk_profile: "balanced",
    strategy: "auto",
    max_loss_amount: 25,
    number_of_positions: 3,
    allow_fractional_shares: true,
    portfolio_aware: false,
  },
  company: null,
  fundamental: null,
  insiders: null,
  chartZoom: 1,
  chartOffset: 0,
  selected: null,
  calendarTab: "Upcoming",
  selectedEvent: "",
  calendarOpen: false,
  moverMode: "Gainers",
  chartTool: "Indicators",
  indicatorMode: "EMA + VWAP + RSI",
  showIndicators: true,
  chartTemplate: "Trade Setup",
  drawPoints: [],
  loading: false,
  error: "",
};

const initialPage = new URLSearchParams(location.search).get("page");
if (initialPage && NAV.includes(initialPage)) state.page = initialPage;

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const first = (...xs) => xs.find((x) => x !== null && x !== undefined && x !== "" && x !== "N/A");
const arr = (x) => Array.isArray(x) ? x : !x ? [] : Array.isArray(x.items) ? x.items : Array.isArray(x.rows) ? x.rows : Array.isArray(x.data) ? x.data : [x];
const num = (x, d = 2) => Number.isFinite(Number(x)) ? Number(x).toFixed(d) : "-";
const pct = (x) => Number.isFinite(Number(x)) ? `${Number(x).toFixed(2)}%` : "-";
const plusPct = (x) => Number.isFinite(Number(x)) ? `+${Number(x).toFixed(2)}%` : "-";
const signedPct = (x) => Number.isFinite(Number(x)) ? `${Number(x) >= 0 ? "+" : ""}${pct(x)}` : "";
const formatDelta = (x) => Number.isFinite(Number(x)) ? `${Number(x) >= 0 ? "+" : ""}${pct(x)}` : "";
const formatMarketValue = (x) => Number.isFinite(Number(x)) ? Number(x).toLocaleString(undefined, {maximumFractionDigits: 2}) : displayValue(x, "");
const compactNumber = (x) => {
  const n = Number(x);
  if (!Number.isFinite(n)) return "Not returned";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(2)}K`;
  return `${sign}${abs.toLocaleString(undefined, {maximumFractionDigits: 2})}`;
};
const TICKER_ALIASES = {
  SPACEX: "SPCX",
  SPACX: "SPCX",
  NVIDIA: "NVDA",
  TESLA: "TSLA",
  MODERNA: "MRNA",
  GOOGLE: "GOOGL",
  ALPHABET: "GOOGL",
  MICROSOFT: "MSFT",
  APPLE: "AAPL",
  AMAZON: "AMZN",
};
const SCAN_UNIVERSE = [
  "SPCX", "NVDA", "AMD", "AVGO", "TSLA", "META", "MSFT", "AAPL", "AMZN", "GOOGL", "NFLX",
  "PLTR", "SMCI", "ARM", "MU", "TSM", "MRNA", "PFE", "LLY", "NVO", "UNH",
  "JPM", "GS", "COIN", "MARA", "RIOT", "HOOD", "SOFI", "RIVN", "LCID", "CCL",
  "NCLH", "BA", "GE", "XOM", "CVX", "OXY", "URA", "CCJ", "AI", "SNOW",
  "CRWD", "PANW", "NET", "DDOG", "SHOP", "UBER", "ABNB", "ROKU", "RBLX", "IONQ",
  "APP", "AFRM", "UPST", "MSTR", "BABA", "PDD", "SE", "MELI", "CELH", "ELF",
  "DKNG", "PINS", "SNAP", "SQ", "PYPL", "INTC", "QCOM", "ORCL", "NOW", "CRM",
  "VRTX", "REGN", "BIIB", "GILD", "BMY", "MRK", "ISRG", "TMO", "DHR", "GEHC",
  "LMT", "RTX", "NOC", "CAT", "DE", "FCX", "NEM", "SLV", "GLD", "TLT",
  "IWM", "XBI", "XLE", "XLK", "XLF", "XLI", "XLY", "XLP", "XLV", "XME",
];
const SECTOR_UNIVERSES = {
  "AI / Semiconductors": ["NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "SMCI", "QCOM", "INTC", "ORCL"],
  "Software / Cloud": ["MSFT", "GOOGL", "META", "SNOW", "CRWD", "PANW", "NET", "DDOG", "NOW", "CRM"],
  "Biotech / Healthcare": ["MRNA", "PFE", "LLY", "NVO", "UNH", "VRTX", "REGN", "BIIB", "GILD", "BMY", "MRK", "ISRG"],
  "Space / Defense": ["SPCX", "RKLB", "BA", "LMT", "RTX", "NOC", "GE", "GEHC"],
  "EV / Mobility": ["TSLA", "RIVN", "LCID", "UBER", "ABNB", "CCL", "NCLH"],
  "Crypto / Fintech": ["COIN", "MARA", "RIOT", "HOOD", "SOFI", "AFRM", "UPST", "PYPL", "MSTR"],
  "Energy / Commodities": ["XOM", "CVX", "OXY", "URA", "CCJ", "FCX", "NEM", "SLV", "GLD", "XLE", "XME"],
  "Consumer / Internet": ["AMZN", "NFLX", "SHOP", "ROKU", "RBLX", "BABA", "PDD", "SE", "MELI", "CELH", "ELF", "DKNG", "PINS", "SNAP"],
  Financials: ["JPM", "GS", "XLF", "SQ", "PYPL", "HOOD", "SOFI"],
  "ETFs / Macro": ["SPY", "QQQ", "IWM", "TLT", "XBI", "XLE", "XLK", "XLF", "XLI", "XLY", "XLP", "XLV"],
};
const money = (x) => {
  const n = Number(x);
  if (!Number.isFinite(n)) return "-";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toLocaleString(undefined, {maximumFractionDigits: 2})}`;
};
const displayValue = (x, fallback = "Not returned") => {
  const v = x ?? "";
  return v === "" || v === "-" || v === "N/A" ? fallback : v;
};
const hasValue = (x) => x !== null && x !== undefined && x !== "" && x !== "-" && x !== "N/A";
const firstNumber = (...xs) => {
  for (const x of xs) {
    const n = Number(x);
    if (Number.isFinite(n)) return n;
  }
  return null;
};
const firstPositiveNumber = (...xs) => {
  for (const x of xs) {
    const n = typeof x === "string" ? Number(x.replace(/[$,%\s,]/g, "")) : Number(x);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
};
const candles = () => arr(first(state.analysis?.candles, state.analysis?.chart, state.analysis?.rows));
const sessionStats = () => {
  const rows = candles().filter((r) => Number.isFinite(Number(r.high)) && Number.isFinite(Number(r.low)));
  if (!rows.length) return {range: "Not returned", volume: "Not returned"};
  const latest = String(first(rows[rows.length - 1]?.time, rows[rows.length - 1]?.date, "")).slice(0, 10);
  const matchedRows = latest ? rows.filter((r) => String(first(r.time, r.date, "")).slice(0, 10) === latest) : [];
  const sessionRows = matchedRows.length ? matchedRows : rows.slice(-78);
  const high = Math.max(...sessionRows.map((r) => Number(r.high)));
  const low = Math.min(...sessionRows.map((r) => Number(r.low)));
  const volume = sessionRows.reduce((sum, r) => sum + (Number(r.volume) || 0), 0);
  return {
    range: Number.isFinite(high) && Number.isFinite(low) ? `${money(low)} - ${money(high)}` : "Not returned",
    volume: volume > 0 ? compactNumber(volume) : "Not returned",
  };
};
const marketCap = () => {
  const p = state.company?.profile || {};
  const cap = firstPositiveNumber(
    p.market_cap,
    p.marketCap,
    state.company?.market_cap,
    state.company?.marketCap,
    state.fundamental?.profile?.market_cap,
    state.fundamental?.profile?.marketCap,
    state.fundamental?.market_cap,
    state.fundamental?.marketCap
  );
  return cap ? money(cap) : "Not returned";
};

async function api(path, options = {}) {
  const token = localStorage.getItem("haviquant_access_token");
  const headers = {"Content-Type": "application/json", ...(options.headers || {}), ...(token ? {Authorization: `Bearer ${token}`} : {})};
  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const r = await fetch(API + path, {...options, headers});
      const raw = await r.text();
      let data = null;
      try { data = raw ? JSON.parse(raw) : null; } catch {}
      if (!r.ok) {
        const message = data?.detail || raw || `${r.status} API request failed`;
        if ([429, 500, 502, 503, 504].includes(r.status) && attempt < 2) {
          lastError = Error(message);
          await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
          continue;
        }
        throw Error(message);
      }
      return data;
    } catch (e) {
      lastError = e;
      if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
    }
  }
  throw lastError || Error("API request failed");
}

async function apiFirst(paths) {
  let lastError = null;
  for (const path of paths) {
    try {
      return await api(path);
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError || Error("API request failed");
}

function icon(name) {
  const common = `viewBox="0 0 24 24" aria-hidden="true"`;
  const paths = {
    grid: `<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>`,
    trend: `<path d="M3 17l5-6 4 3 7-8"/><path d="M17 6h2v2"/>`,
    building: `<path d="M4 21V4h10v17M14 9h6v12M8 8h2M8 12h2M8 16h2M17 13h1M17 17h1"/>`,
    bars: `<path d="M4 19V9M10 19V5M16 19v-8M22 19V3"/>`,
    pulse: `<path d="M3 12h4l2-6 4 12 2-6h6"/>`,
    bolt: `<path d="M13 2 4 14h7l-1 8 10-13h-7z"/>`,
    scanner: `<path d="M4 7V4h3M17 4h3v3M20 17v3h-3M7 20H4v-3"/><path d="M7 12h10"/><path d="M9 9h6M10 15h4"/>`,
    flask: `<path d="M9 3h6M10 3v6l-5 8a3 3 0 0 0 2.6 4.5h8.8A3 3 0 0 0 19 17l-5-8V3"/>`,
    wallet: `<path d="M3 7h18v12H3z"/><path d="M16 12h4"/>`,
    shield: `<path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M9 12l2 2 4-4"/>`,
    backtest: `<path d="M5 6h14M5 12h10M5 18h7"/><path d="M18 15l3 3-3 3"/>`,
    news: `<path d="M4 4h16v16H4zM8 8h8M8 12h8M8 16h5"/>`,
    calendar: `<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>`,
    search: `<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>`,
    moon: `<path d="M21 13a8 8 0 1 1-10-10 6 6 0 0 0 10 10z"/>`,
    bell: `<path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>`,
    draw: `<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>`,
    templates: `<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="18" height="7"/>`,
    camera: `<path d="M4 7h4l2-3h4l2 3h4v13H4z"/><circle cx="12" cy="13" r="4"/>`,
    expand: `<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M21 16v5h-5"/><path d="M3 3l6 6M21 3l-6 6M3 21l6-6M21 21l-6-6"/>`,
    reset: `<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>`,
  };
  return `<svg ${common}>${paths[name] || paths.grid}</svg>`;
}

function card(title, body, cls = "") {
  return `<section class="card ${cls}"><div class="card-title">${esc(title)}</div>${body}</section>`;
}

function metric(label, value, cls = "") {
  return `<div class="metric ${cls}"><span>${esc(label)}</span><strong>${esc(formatCell(value))}</strong></div>`;
}

function rows(obj) {
  return Object.entries(obj || {})
    .filter(([, v]) => hasValue(v) && formatCell(v) !== "Not returned")
    .map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${esc(formatCell(v))}</b></div>`)
    .join("");
}

function formatCell(value) {
  if (!hasValue(value)) return "Not returned";
  if (Array.isArray(value)) return value.length ? value.map(formatCell).join(", ") : "Not returned";
  if (typeof value === "object") return displayValue(first(value.label, value.name, value.title, value.value), "Returned by provider");
  if (typeof value === "number") return Math.abs(value) >= 100000 ? compactNumber(value) : String(value);
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text) && !Number.isNaN(new Date(text).getTime())) {
    return new Date(text).toLocaleString(undefined, {month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit"});
  }
  return displayValue(text);
}

function metricList(items) {
  const visible = items.filter(([, value]) => hasValue(value) && formatCell(value) !== "Not returned");
  return visible.length
    ? visible.map(([label, value, cls]) => metric(label, value, cls || "")).join("")
    : `<div class="empty compact">No provider-backed metrics returned for this section.</div>`;
}

function shell() {
  $("#app").innerHTML = `
    <div class="terminal">
      <aside class="sidebar">
        <div class="brand">
          <div class="brandmark">HQ</div>
          <div><strong>HaViQuant</strong><small>Evidence. Edge. Execution.</small></div>
        </div>
        <nav>${NAV_GROUPS.map((group) => `<section class="nav-group"><h4>${esc(group.label)}</h4>${group.items.map(([page, label]) => `<button class="${state.page === page ? "active" : ""}" data-nav="${esc(page)}">${icon(ICONS[page])}<span>${esc(label)}</span></button>`).join("")}</section>`).join("")}</nav>
        ${sentimentBox("sidebar")}
        <div class="market-status"><b>${state.error ? "Data Issue" : "Market Open"}</b><span>${state.error ? "Provider request needs retry" : "Live API connected"}</span></div>
      </aside>
      <main class="workspace">
        <header class="topbar">
          <div class="searchbox">${icon("search")}<input id="tickerInput" value="${esc(state.query)}" placeholder="Search ticker, company or event..."><button id="analyze">Analyze</button></div>
          ${marketTape()}
          <div class="tools">${icon("bell")}${icon("moon")}</div>
        </header>
        <section class="eventbar">${events()}</section>
        <div id="content" class="content"></div>
        ${["Dashboard", "Stock Analysis", "Trade Scanner"].includes(state.page) ? topMovers() : ""}
      </main>
    </div>
    <div id="stockTooltip" class="stock-tooltip"></div>
    ${state.calendarOpen ? calendarModal() : ""}`;

  $$("[data-nav]").forEach((b) => b.onclick = () => { state.page = b.dataset.nav; shell(); renderContent(); });
  $("#analyze").onclick = () => load($("#tickerInput").value);
  $("#tickerInput").oninput = (e) => state.query = e.target.value.toUpperCase();
  $("#tickerInput").onkeydown = (e) => { if (e.key === "Enter") load(e.target.value); };
  $$("[data-mover]").forEach((b) => b.onclick = () => load(b.dataset.mover));
  $$("[data-mover]").forEach((b) => {
    b.onmouseenter = () => showStockTooltip(b);
    b.onmousemove = () => showStockTooltip(b);
    b.onmouseleave = hideStockTooltip;
  });
  bindGlobalControls();
}

function marketTape() {
  const a = state.analysis || {};
  const change = Number(a.change_pct);
  const indexes = arr(first(
    a.market_indices,
    a.indices,
    a.market?.indices,
    state.macro?.market_indices,
    state.macro?.indices,
    state.macro?.market?.indices
  )).map((item) => [
    first(item.symbol, item.name, item.label),
    first(item.value, item.price, item.last),
    first(item.change_pct, item.changePercent, item.percent_change, item.status, item.state),
  ]);
  const items = [
    ...indexes,
    [state.ticker, a.price, change],
  ].filter(([l, v]) => first(l, "") && Number.isFinite(Number(v)));
  return `<div class="tape">${items.map(([l, v, d]) => `<span><b>${esc(l)}</b><strong>${esc(formatMarketValue(v))}</strong>${Number.isFinite(Number(d)) ? `<em class="${Number(d) < 0 ? "bad" : "good"}">${esc(formatDelta(d))}</em>` : ""}</span>`).join("")}</div>`;
}

function events() {
  const items = calendarEvents().slice(0, 4);
  return `<button class="event-intro" data-open-calendar="1">Impact Calendar<br><small>${esc(todayLabel())}</small></button>${items.length ? items.map((event) => `
    <button class="event-card ${event.level.toLowerCase()} ${state.selectedEvent === event.title ? "selected" : ""}" data-event="${esc(event.title)}"><i></i><div><b>${esc(event.level)}</b><span>${esc(event.title)}</span><em>${esc(event.dateLabel)}</em></div><small><strong>${esc(event.time)}</strong><em>${esc(event.status)}</em></small></button>`).join("") : ""}<button class="calendar-btn" data-open-calendar="1">View Full Calendar</button>`;
}

function topMovers() {
  const moverSource = first(state.macro?.top_movers, state.macro?.movers, state.analysis?.top_movers, state.fallbackMovers, {});
  const data = state.moverMode === "Most Active"
    ? first(moverSource?.most_active, moverSource?.active, moverSource)
    : first(moverSource?.gainers, moverSource?.items, moverSource);
  const items = arr(data).slice(0, 12).map((item) => ({
    symbol: first(item.symbol, item.ticker),
    name: first(item.name, item.company_name, item.company),
    price: first(item.price, item.last),
    change: first(item.change_pct, item.changePercent, item.percent_change),
    sector: first(item.sector, item.industry),
  })).filter((item) => hasValue(item.symbol));
  if (!items.length) return state.moversLoading
    ? `<footer class="movers" data-testid="top-movers"><b>TOP MOVERS</b><span class="mover-status">Loading provider movers...</span></footer>`
    : "";
  return `<footer class="movers" data-testid="top-movers"><b>TOP MOVERS</b><button class="${state.moverMode === "Gainers" ? "active" : ""}" data-mover-mode="Gainers">Gainers</button><button class="${state.moverMode === "Most Active" ? "active" : ""}" data-mover-mode="Most Active">Most Active</button>${items.map((item) => `
    <button data-mover="${esc(item.symbol)}" class="mover" data-tooltip="${esc(moverTooltip(item))}"><i>${esc(String(item.symbol).slice(0, 1))}</i><span>${esc(item.symbol)}</span><em class="${Number(item.change) < 0 ? "bad" : "good"}">${esc(formatDelta(item.change))}</em></button>`).join("")}</footer>`;
}

function hasTopMoverData() {
  const source = first(state.macro?.top_movers, state.macro?.movers, state.analysis?.top_movers, state.fallbackMovers);
  return arr(first(source?.gainers, source?.items, source?.most_active, source?.active, source)).some((item) =>
    hasValue(first(item.symbol, item.ticker))
  );
}

async function loadFallbackMovers() {
  if (state.moversLoading || hasTopMoverData()) return;
  state.moversLoading = true;
  shell();
  const symbols = SCAN_UNIVERSE.slice(0, 32);
  const settled = await Promise.allSettled(symbols.map((symbol) =>
    api(`/market/analysis?ticker=${encodeURIComponent(symbol)}&period=1mo&interval=1d`)
  ));
  const items = settled
    .filter((result) => result.status === "fulfilled")
    .map((result) => {
      const a = result.value || {};
      return {
        symbol: first(a.ticker, a.symbol),
        price: firstNumber(a.price, a.quote?.price),
        change_pct: firstNumber(a.change_pct, a.quote?.change_pct),
        volume: firstNumber(a.volume, a.quote?.volume),
        score: firstNumber(a.setup_quality, a.score),
      };
    })
    .filter((item) => hasValue(item.symbol) && Number.isFinite(Number(item.price)));
  state.fallbackMovers = {
    items: [...items].filter((item) => Number.isFinite(Number(item.change_pct))).sort((a, b) => Number(b.change_pct) - Number(a.change_pct)).slice(0, 12),
    gainers: [...items].filter((item) => Number.isFinite(Number(item.change_pct))).sort((a, b) => Number(b.change_pct) - Number(a.change_pct)).slice(0, 12),
    most_active: [...items].filter((item) => Number.isFinite(Number(item.volume))).sort((a, b) => Number(b.volume) - Number(a.volume)).slice(0, 12),
  };
  state.moversLoading = false;
  shell();
  renderContent();
}

function moverTooltip(item) {
  return [
    `${item.symbol}${hasValue(item.name) ? ` - ${item.name}` : ""}`,
    Number.isFinite(Number(item.price)) ? `Price: ${money(item.price)}` : "",
    Number.isFinite(Number(item.change)) ? `Move: ${formatDelta(item.change)}` : "",
    hasValue(item.sector) ? `Sector: ${item.sector}` : "",
    "Click to load full analysis",
  ].filter(Boolean).join("\n");
}

function showStockTooltip(button) {
  const tip = $("#stockTooltip");
  if (!tip) return;
  const rect = button.getBoundingClientRect();
  tip.textContent = button.dataset.tooltip || "";
  tip.style.left = `${Math.min(window.innerWidth - 260, Math.max(12, rect.left + rect.width / 2 - 120))}px`;
  tip.style.top = `${Math.max(12, rect.top - 104)}px`;
  tip.classList.add("show");
}

function hideStockTooltip() {
  const tip = $("#stockTooltip");
  if (tip) tip.classList.remove("show");
}

function derivedMarketSentiment() {
  const direct = first(state.macro?.sentiment, state.analysis?.market_sentiment);
  if (direct && (hasValue(direct.score) || hasValue(direct.label) || hasValue(direct.state))) return direct;
  const indexMoves = arr(first(
    state.macro?.market_indices,
    state.macro?.indices,
    state.analysis?.market_indices,
    state.analysis?.indices
  ))
    .map((item) => firstNumber(item.change_pct, item.changePercent, item.percent_change))
    .filter((value) => Number.isFinite(value));
  const tickerMove = firstNumber(state.analysis?.change_pct, state.analysis?.quote?.change_pct);
  const moves = indexMoves.length ? indexMoves : (Number.isFinite(tickerMove) ? [tickerMove] : []);
  const setupScore = firstNumber(state.analysis?.setup_quality, state.analysis?.score, state.analysis?.decision?.score);
  const avgMove = moves.length ? moves.reduce((sum, value) => sum + value, 0) / moves.length : null;
  const score = Number.isFinite(setupScore)
    ? setupScore
    : Number.isFinite(avgMove)
      ? Math.max(0, Math.min(100, 50 + avgMove * 8))
      : null;
  const label = first(
    state.macro?.market_regime,
    state.analysis?.market_regime,
    state.analysis?.trend,
    Number.isFinite(score) ? (score >= 60 ? "Bullish" : score <= 40 ? "Bearish" : "Mixed") : ""
  );
  if (!Number.isFinite(score) && !hasValue(label)) return null;
  return {
    score,
    label,
    bullish_pct: Number.isFinite(score) && score > 55 ? 100 : null,
    neutral_pct: Number.isFinite(score) && score >= 40 && score <= 55 ? 100 : null,
    bearish_pct: Number.isFinite(score) && score < 40 ? 100 : null,
  };
}

function bindGlobalControls() {
  $$("[data-open-calendar]").forEach((b) => b.onclick = () => {
    state.calendarOpen = true;
    shell();
    renderContent();
  });
  $$("[data-close-calendar]").forEach((b) => b.onclick = () => {
    state.calendarOpen = false;
    shell();
    renderContent();
  });
  $$("[data-event]").forEach((b) => b.onclick = () => {
    state.selectedEvent = b.dataset.event;
    if (b.closest(".calendar-modal")) state.calendarOpen = false;
    shell();
    renderContent();
  });
  $$("[data-calendar-tab]").forEach((b) => b.onclick = () => {
    state.calendarTab = b.dataset.calendarTab;
    shell();
    renderContent();
  });
  $$("[data-mover-mode]").forEach((b) => b.onclick = () => {
    state.moverMode = b.dataset.moverMode;
    shell();
    renderContent();
    loadFallbackMovers();
  });
}

function calendarModal() {
  const items = calendarEvents();
  return `<div class="modal-backdrop" data-close-calendar="1">
    <section class="calendar-modal" onclick="event.stopPropagation()">
      <header><div><span>Market Calendar</span><h2>Impact Calendar</h2><p>${esc(todayLabel())}</p></div><button data-close-calendar="1">Close</button></header>
      <div class="tabs calendar-tabs">${CALENDAR_TABS.map((tab) => `<button class="${state.calendarTab === tab ? "active" : ""}" data-calendar-tab="${tab}">${tab}</button>`).join("")}</div>
      <div class="calendar-list">${items.length ? items.map((event) => `<button class="calendar-row" data-event="${esc(event.title)}" data-close-calendar="1"><b>${esc(event.level)}</b><span>${esc(event.title)}</span><em>${esc(event.dateLabel)} · ${esc(event.category)}</em><small>${esc(event.time)}<br>${esc(event.impact)}</small></button>`).join("") : `<div class="empty">No dated impact events returned by provider.</div>`}</div>
    </section>
  </div>`;
}

function sentimentBox(extra = "") {
  const data = derivedMarketSentiment() || {};
  const score = first(data.score, data.value, data.market_score);
  const label = first(data.label, data.state, data.regime);
  if (!hasValue(score) && !hasValue(label)) return "";
  const rowsData = {
    Bullish: first(data.bullish_pct, data.bullish),
    Neutral: first(data.neutral_pct, data.neutral),
    Bearish: first(data.bearish_pct, data.bearish),
  };
  return `<section class="sentiment-box ${extra}" data-testid="market-sentiment">
    <h3>Market Sentiment</h3>
    <div class="gauge"><i></i><i></i><i></i></div>
    <strong>${esc(hasValue(score) ? num(score, 0) : "-")}</strong>${hasValue(label) ? `<b>${esc(label)}</b>` : ""}
    ${rows(rowsData)}
  </section>`;
}

async function load(ticker = state.ticker, tf = state.tf) {
  const raw = String(ticker || "").trim().toUpperCase();
  const lookup = raw.replace(/[^A-Z0-9.-]/g, "");
  const clean = TICKER_ALIASES[lookup] || lookup;
  if (!/^[A-Z0-9.-]{1,12}$/.test(clean)) return;
  const [period, interval] = TIMEFRAMES[tf] || TIMEFRAMES["5m"];
  state.ticker = clean;
  state.query = clean;
  state.tf = tf;
  if (state.page === "Trade Scanner") state.page = "Stock Analysis";
  state.loading = true;
  state.error = "";
  state.chartZoom = 1;
  state.chartOffset = 0;
  state.company = null;
  state.fundamental = null;
  state.fallbackMovers = null;
  renderContent();
  const companyRequest = api(`/company-intelligence/${encodeURIComponent(clean)}`).catch(() => api(`/company/${encodeURIComponent(clean)}`));
  const [analysis, news, macro, fundamental, insiders] = await Promise.allSettled([
    api(`/market/analysis?ticker=${encodeURIComponent(clean)}&period=${period}&interval=${interval}&include_mtf=${interval === "1d"}`),
    api(`/market/news?ticker=${encodeURIComponent(clean)}`),
    api(`/market/macro?ticker=${encodeURIComponent(clean)}`),
    api(`/fundamental/${encodeURIComponent(clean)}`),
    api(`/market/insiders?ticker=${encodeURIComponent(clean)}`),
  ]);
  state.analysis = analysis.status === "fulfilled" ? analysis.value || {} : {};
  state.news = news.status === "fulfilled" ? arr(news.value?.items || news.value) : [];
  state.macro = macro.status === "fulfilled" ? macro.value : null;
  state.fundamental = fundamental.status === "fulfilled" ? fundamental.value : null;
  state.insiders = insiders.status === "fulfilled" ? insiders.value : null;
  state.error = analysis.status !== "fulfilled" ? analysis.reason?.message || "Market analysis was not returned by provider." : "";
  state.loading = false;
  shell();
  renderContent();
  loadFallbackMovers();
  companyRequest.then((company) => {
    if (state.ticker !== clean) return;
    state.company = company || null;
    shell();
    renderContent();
  }).catch(() => {
    if (state.ticker !== clean) return;
    state.company = null;
  });
}

function dataNotice() {
  if (!state.error) return "";
  const local = API.includes("127.0.0.1");
  const hint = local
    ? "Local API is not reachable on port 8000. Start the backend, then retry."
    : "Provider request failed. Retry after the data service is healthy.";
  return `<section class="data-notice">
    <div><b>Data connection issue</b><span>${esc(state.error)}</span><small>${esc(hint)}</small></div>
    <button id="retry" type="button">Retry</button>
  </section>`;
}

function bindNotice() {
  const retry = $("#retry");
  if (retry) retry.onclick = () => load(state.ticker, state.tf);
}

function renderContent() {
  const c = $("#content");
  if (!c) return;
  if (state.loading) {
    c.innerHTML = `<div class="state">Loading ${esc(state.ticker)} command center...</div>`;
    return;
  }
  const showNotice = ["Dashboard", "Stock Analysis", "Technical", "Decision", "Risk", "Backtesting", "Trade Scanner", "AI Trade Planner"].includes(state.page);
  const notice = showNotice ? dataNotice() : "";
  if (state.page === "Dashboard" || state.page === "Stock Analysis") {
    c.innerHTML = notice + tradingDesk();
    bindNotice();
    bindDesk();
    drawChart();
    return;
  }
  if (state.page === "Trade Scanner") {
    c.innerHTML = notice + tradeScannerPage();
    bindNotice();
    bindScanner();
    return;
  }
  if (state.page === "AI Trade Planner") {
    c.innerHTML = notice + tradePlannerPage();
    bindNotice();
    bindPlanner();
    return;
  }
  c.innerHTML = notice + modulePage(state.page);
  bindNotice();
  bindDesk();
  drawChart();
}

function tradingDesk() {
  const a = state.analysis || {};
  const profile = state.company?.profile || state.company || {};
  const price = Number(a.price);
  const change = Number(a.change_pct);
  const stats = sessionStats();
  const cap = marketCap();
  const capMetric = cap !== "Not returned" ? `<div class="range"><label>Market Cap</label><b>${esc(cap)}</b><small>Provider field</small></div>` : "";
  const classification = [profile.sector, profile.industry].filter(hasValue).join(" - ");
  return `
    <div class="desk">
      <section class="chart-zone">
        <div class="quote-head">
          <div><h1>${esc(state.ticker)}</h1><span>${esc(displayValue(profile.name, state.ticker))}</span>${classification ? `<small>${esc(classification)}</small>` : ""}</div>
          <div class="price-block"><strong>${money(price)}</strong><em class="${change < 0 ? "bad" : "good"}">${signedPct(change)}</em><small>Real-time</small></div>
          ${stats.range !== "Not returned" ? `<div class="range"><label>Session Range</label><b title="Computed from returned intraday candle high/low values">${esc(stats.range)}</b><small>From live candles</small></div>` : ""}
          ${stats.volume !== "Not returned" ? `<div class="range"><label>Session Volume</label><b>${esc(stats.volume)}</b>${hasValue(a.volume_ratio) ? `<small>${num(a.volume_ratio)}x Avg</small>` : ""}</div>` : ""}
          ${capMetric}
        </div>
        ${chartPanel()}
        ${lowerDeskPanels()}
      </section>
      <aside class="right-rail">
        ${setupPanel()}
        ${contextPanel()}
        ${tradePlanPanel()}
        ${patternPanel()}
        ${whyPanel()}
        ${livePricePanel()}
        ${aiPanel()}
      </aside>
    </div>`;
}

function lowerDeskPanels() {
  const panels = [impactCalendar(), eventImpact(), mtfPanel()].filter(Boolean);
  return panels.length ? `<div class="lower-grid">${panels.join("")}</div>` : "";
}

function chartPanel() {
  const a = state.analysis || {};
  return card("Trading Chart", `
    <div class="chart-toolbar">
      ${Object.keys(TIMEFRAMES).map((tf) => `<button class="${state.tf === tf ? "active" : ""}" data-tf="${tf}" data-testid="tf-${tf}">${tf}</button>`).join("")}
      <span></span>
      ${["Indicators", "Draw", "Templates", "Camera", "Fullscreen"].map((tool) => `<button class="tool ${state.chartTool === tool ? "active" : ""}" data-chart-tool="${tool}" title="${tool}" aria-label="${tool}">${toolIcon(tool)}</button>`).join("")}
      <button class="tool" id="resetChart" title="Reset View" aria-label="Reset View">${toolIcon("Reset")}</button>
    </div>
    <div class="chart-stats">
      <div><span>Session Range</span><b>${esc(sessionStats().range)}</b></div>
      <div><span>Session Volume</span><b>${esc(sessionStats().volume)}</b><em>${hasValue(a.volume_ratio) ? `${num(a.volume_ratio)}x Avg` : "Volume ratio not returned"}</em></div>
      <div><span>Active Tool</span><b>${esc(state.chartTool)}</b><em>${esc(toolStatusText())}</em></div>
    </div>
    <div class="chart-shell">
      ${indicatorList()}
      <canvas id="chart" class="chart" data-testid="trading-chart"></canvas>
      <div id="charttip" class="charttip"></div>
    </div>
    <div id="chartReadout" class="chart-readout">Hover over a candle to inspect OHLC, volume, RSI and pattern context.</div>
    <div class="oscillator"><i></i><b>RSI (14)</b><span>MACD (12,26,9)</span></div>
  `);
}

function indicatorList() {
  const a = state.analysis || {};
  const items = [
    ["SMA 20", a.sma_20 || a.sma20],
    ["SMA 50", a.sma_50 || a.sma50],
    ["SMA 200", a.sma_200 || a.sma200],
    ["VWAP", a.vwap],
    ["Volume", a.volume],
  ].filter(([, value]) => hasValue(value));
  if (!items.length) return "";
  return `<div class="indicator-list">${items.map(([label, value]) => `<b>${esc(label)}</b><em>${esc(label === "Volume" ? compactNumber(value) : money(value))}</em>`).join("")}</div>`;
}

function toolIcon(tool) {
  const names = {Indicators: "bars", Draw: "draw", Templates: "templates", Camera: "camera", Fullscreen: "expand", Reset: "reset"};
  return `<i>${icon(names[tool] || "grid")}</i>`;
}

function toolStatusText() {
  if (state.chartTool === "Indicators") return state.showIndicators ? state.indicatorMode : "Indicators hidden";
  if (state.chartTool === "Draw") return `${state.drawPoints.length} chart marker${state.drawPoints.length === 1 ? "" : "s"}`;
  if (state.chartTool === "Templates") return state.chartTemplate;
  if (state.chartTool === "Camera") return "Download chart snapshot";
  if (state.chartTool === "Fullscreen") return "Expand chart panel";
  return "Ready";
}

function setupPanel() {
  const a = state.analysis || {};
  const signal = a.signal || "WAIT";
  const price = Number(a.price);
  const vwap = Number(a.vwap);
  const vwapState = Number.isFinite(price) && Number.isFinite(vwap) ? (price >= vwap ? "Above" : "Below") : "Not returned";
  const macdState = Number.isFinite(Number(a.macd)) && Number.isFinite(Number(a.macd_signal))
    ? (Number(a.macd) >= Number(a.macd_signal) ? "Bullish" : "Bearish")
    : "Not returned";
  const detailRows = rows({Trend: a.trend, Momentum: a.momentum, Volume: hasValue(a.volume_ratio) ? `${num(a.volume_ratio)}x` : null, VWAP: vwapState === "Not returned" ? null : vwapState, "RSI (14)": hasValue(a.rsi) ? num(a.rsi) : null, MACD: macdState === "Not returned" ? null : macdState});
  if (!hasValue(a.setup_quality) && !detailRows) return "";
  return card("Trade Setup", `
    <div class="setup-title"><div><strong>${esc(signal)} SETUP</strong><span>${signal === "BUY" ? "High Probability" : "Await confirmation"}</span></div><b>${hasValue(a.setup_quality) ? num(a.setup_quality, 0) : "-"}<small>/100</small></b></div>
    ${detailRows}
  `);
}

function contextPanel() {
  const p = state.company?.profile || state.company || {};
  const a = state.analysis || {};
  const sentiment = state.macro?.sentiment || {};
  const context = {
    "Overall Market": first(a.market_regime, a.market_context?.overall_market, state.macro?.market_regime, sentiment.label),
    Sector: p.sector,
    "Sector Trend": first(a.sector_trend, a.market_context?.sector_trend),
    "Volatility (VIX)": first(a.vix_regime, a.market_context?.volatility, state.macro?.vix_regime),
    "Market Regime": first(state.macro?.market_regime, sentiment.market_regime, a.trend, state.macro?.regime),
    Liquidity: first(a.liquidity, a.market_context?.liquidity, hasValue(a.volume_ratio) ? `${num(a.volume_ratio)}x Avg Volume` : null),
  };
  const filtered = Object.fromEntries(Object.entries(context).filter(([, value]) => hasValue(value)));
  return Object.keys(filtered).length ? card("Market Context", rows(filtered)) : "";
}

function whyPanel() {
  const a = state.analysis || {};
  return a.pattern?.description ? card("Why This Trade?", `<p class="small-copy">${esc(a.pattern.description)}</p>`) : "";
}

function tradePlanPanel() {
  const a = state.analysis || {};
  const entry = Number(a.levels?.entry);
  const stop = Number(a.levels?.stop);
  const t1 = Number(a.levels?.target1);
  const risk = Number.isFinite(entry) && Number.isFinite(stop) ? Math.abs(entry - stop) : NaN;
  return card("Trade Plan", `
    <div class="trade-plan">
      <div><span>Entry Zone</span><b>${money(entry)}</b></div>
      <div class="stop"><span>Stop Loss</span><b>${money(stop)}</b></div>
      <div class="target"><span>Target 1</span><b>${money(t1)}</b></div>
      <div class="target"><span>Target 2</span><b>${money(a.levels?.target2)}</b></div>
      <div><span>Risk / Reward</span><b>${Number.isFinite(risk) && risk > 0 && Number.isFinite(t1) ? `1 : ${((t1 - entry) / risk).toFixed(2)}` : "-"}</b></div>
      <div><span>Timeframe</span><b>${esc(state.tf)}</b></div>
    </div>
  `);
}

function patternPanel() {
  const a = state.analysis || {};
  const pattern = a.pattern || {};
  if (!hasValue(pattern.name) && !hasValue(pattern.description)) return "";
  return card("Pattern Details", `
    ${pattern.name ? `<div class="pattern-name">${esc(pattern.name)}</div>` : ""}
    ${pattern.description ? `<p class="small-copy">${esc(pattern.description)}</p>` : ""}
    ${rows({
      Confidence: pattern.confidence != null ? `${num(pattern.confidence, 0)}%` : null,
      Trend: a.trend,
      Momentum: a.momentum,
      Volatility: a.volatility,
      Invalidation: hasValue(a.levels?.stop) ? `Below ${money(a.levels?.stop)}` : null,
    })}
  `);
}

function livePricePanel() {
  const a = state.analysis || {};
  if (!Number.isFinite(Number(a.price))) return "";
  return card("Live Price", `<div class="mini-price">${money(a.price)} <em class="${a.change_pct < 0 ? "bad" : "good"}">${signedPct(a.change_pct)}</em></div><div class="mini-spark"></div><div class="day-range"><i></i></div>`);
}

function aiPanel() {
  const a = state.analysis || {};
  const probability = first(a.probability_of_continuation, a.continuation_probability, a.setup_quality);
  const insights = [
    hasValue(probability) ? `Probability of continuation: ${num(probability, 0)}%` : null,
    hasValue(a.levels?.stop) ? `Key support level: ${money(a.levels.stop)}` : null,
    hasValue(a.levels?.target1) ? `Key resistance level: ${money(a.levels.target1)}` : null,
    a.ai_summary,
  ].filter(hasValue);
  if (!insights.length) return "";
  return card("AI Insight Summary", `
    <ul class="ai-list">${insights.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
  `);
}

function impactCalendar() {
  const selected = calendarEvents();
  if (!selected.length) return "";
  return card("Impact Calendar", `
    <div class="tabs">${CALENDAR_TABS.map((tab) => `<button class="${state.calendarTab === tab ? "active" : ""}" data-calendar-tab="${tab}">${tab}</button>`).join("")}</div>
    <div class="impact-list">${selected.map((event) => `<button class="impact-row ${event.level.toLowerCase()} ${state.selectedEvent === event.title ? "selected" : ""}" data-event="${esc(event.title)}"><b>${esc(event.level)}</b><span>${esc(event.title)}<small>${esc(event.dateLabel)} · ${esc(event.time)}</small></span><em>${esc(event.impact)}</em></button>`).join("")}</div>
  `);
}

function eventImpact() {
  const event = eventByTitle(state.selectedEvent);
  if (!event || event.scenario === "Provider did not return event impact detail.") return "";
  return card("Event Impact Analysis", `
    <h4>${esc(event.title)}</h4>
    <div class="event-meta"><span>${esc(event.level)}</span><span>${esc(event.category)}</span><span>${esc(event.dateLabel)}</span><span>${esc(event.time)}</span><span>${esc(event.impact)}</span></div>
    <p class="small-copy">${esc(event.scenario)}</p>
  `);
}

function eventByTitle(title) {
  const events = calendarEvents();
  return events.find((event) => event.title === title) || events[0] || null;
}

function calendarEvents() {
  const direct = arr(first(state.macro?.events, state.macro?.calendar, state.macro?.economic_calendar, state.macro?.impact_calendar, state.macro?.items, state.macro?.rows));
  const macroNews = [
    ...arr(state.macro?.macro).map((event) => ({...event, category: first(event.category, "Macro")})),
    ...arr(state.macro?.politics).map((event) => ({...event, category: first(event.category, "Politics")})),
    ...arr(state.macro?.geopolitical).map((event) => ({...event, category: first(event.category, "Geopolitical")})),
  ];
  const raw = direct.length ? direct : macroNews;
  const events = raw.map(normalizeEvent).filter((event) => event.title && event.title !== "Not returned");
  if (state.calendarTab === "All" || state.calendarTab === "Upcoming") return events;
  return events.filter((event) => String(event.category).toLowerCase().includes(state.calendarTab.toLowerCase()));
}

function todayLabel() {
  return new Date().toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric", year: "numeric"});
}

function eventDateLabel(event) {
  return normalizeEvent(event).dateLabel;
}

function eventEta(event) {
  return normalizeEvent(event).status;
}

function normalizeEvent(event) {
  const title = displayValue(first(event.title, event.name, event.event, event.label, event.description));
  const category = displayValue(first(event.category, event.type, event.group, event.section, "Economic"));
  const sentiment = event.sentiment || {};
  const levelRaw = String(first(event.level, event.importance, sentiment.impact, event.impact_label, event.impact, event.severity, "INFO")).toUpperCase();
  const level = levelRaw.includes("HIGH") ? "HIGH" : levelRaw.includes("MED") ? "MEDIUM" : levelRaw.includes("LOW") ? "LOW" : "INFO";
  const when = first(event.datetime, event.date_time, event.starts_at, event.released_at, event.published_iso, event.published, event.updated_at, event.date, event.time);
  const parsed = when && !Number.isNaN(new Date(when).getTime()) ? new Date(when) : null;
  const dateLabel = parsed ? parsed.toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric", year: "numeric"}) : displayValue(first(event.date, event.day), "Date not returned");
  const time = parsed ? parsed.toLocaleTimeString(undefined, {hour: "numeric", minute: "2-digit", timeZoneName: "short"}) : displayValue(first(event.time, event.hour), "Time not returned");
  const status = displayValue(first(event.status, event.state, event.recency), parsed && parsed < new Date() ? "completed" : "upcoming");
  return {
    title,
    category,
    level,
    dateLabel,
    time,
    status,
    impact: displayValue(first(event.impact_label, sentiment.label, event.impact, event.importance, event.severity), level),
    scenario: displayValue(first(event.analysis, event.summary, event.impact_summary, event.reason, event.description, event.note), "Provider did not return event impact detail."),
    sourceUrl: first(event.url, event.link, event.source_url, "#"),
    proof: displayValue(first(event.proof, event.source, event.publisher, event.source_name), "Provider source"),
  };
}

function mtfPanel() {
  const a = state.analysis || {};
  const rows = arr(a.mtf);
  const confidence = Number(first(a.mtf_confidence, a.setup_quality));
  if (!rows.length) return "";
  const body = rows.map((r) => `<div class="mtf"><b>${esc(r.tf || r.label)}</b><span>${esc(formatCell(r.data?.trend || r.trend))}</span><em>${esc(formatCell(r.data?.signal || r.signal))}</em></div>`).join("");
  return card("Multi-Timeframe Analysis", body + (Number.isFinite(confidence) ? `<div class="confidence"><i style="width:${Math.min(100, confidence)}%"></i></div>` : ""));
}

function modulePage(page) {
  const a = state.analysis || {};
  if (page === "Company Intelligence") return `<div class="module-hero"><span>360 Company Intelligence</span><h1>${esc(state.ticker)}</h1></div>${companyModule()}`;
  if (page === "Fundamentals") return `<div class="module-hero"><span>Fundamental Intelligence</span><h1>${esc(state.ticker)}</h1></div>${fundamentalModule()}`;
  if (page === "Technical") return `<div class="module-hero"><span>Technical Intelligence</span><h1>${esc(state.ticker)}</h1></div>${technicalModule()}`;
  if (page === "Decision") return decisionModule();
  if (page === "AI Trade Planner") return tradePlannerPage();
  if (page === "Trade Scanner") return tradeScannerPage();
  if (page === "News") return `<div class="module-hero"><span>News & Events</span><h1>${esc(state.ticker)}</h1></div>${newsModule()}`;
  if (page === "Calendar") return calendarPage();
  if (page === "Portfolio") return `<div class="module-hero"><span>Private Portfolio</span><h1>Authentication Required</h1></div>${card("Secure Portfolio", `<p class="small-copy">Portfolio data is protected by the existing bearer-token authentication flow. Sign in through the authenticated production flow before loading private holdings.</p>`)}`;
  if (page === "Risk") return riskModule();
  if (page === "Backtesting" || page === "Evidence Research") return researchModule(page);
  return tradingDesk();
}

function decisionTier() {
  const a = state.analysis || {};
  const score = Number(a.setup_quality || 0);
  if ((a.signal === "BUY" && score >= 78) || score >= 85) return "STRONG BUY";
  if (a.signal === "BUY" || score >= 65) return "BUY";
  if (a.signal === "SELL" || score <= 25) return "SELL";
  return "WAIT";
}

function decisionTimeframe() {
  const a = state.analysis || {};
  const tier = decisionTier();
  if (tier === "STRONG BUY") return "1-3 trading days if volume confirms";
  if (tier === "BUY") return "3-10 trading days after breakout confirmation";
  if (tier === "SELL") return "Downside risk is active now; reassess after support reclaim";
  return "No entry yet; reassess over the next 2-5 sessions";
}

function estimatedMove() {
  const a = state.analysis || {};
  const entry = Number(a.levels?.entry);
  const t1 = Number(a.levels?.target1);
  const t2 = Number(a.levels?.target2);
  return {
    t1pct: Number.isFinite(entry) && Number.isFinite(t1) && entry ? ((t1 / entry - 1) * 100).toFixed(2) : "-",
    t2pct: Number.isFinite(entry) && Number.isFinite(t2) && entry ? ((t2 / entry - 1) * 100).toFixed(2) : "-",
  };
}

function decisionModule() {
  const a = state.analysis || {};
  const move = estimatedMove();
  return `<div class="module-hero decision-hero"><span>Production Decision Engine</span><h1>${esc(decisionTier())}</h1><p>${esc(decisionTimeframe())}</p></div>
    <div class="module-grid">${metric("Current Price", money(a.price))}${metric("Setup Score", `${num(a.setup_quality, 0)}/100`)}${metric("Target 1 Move", `${move.t1pct}%`)}${metric("Target 2 Move", `${move.t2pct}%`)}</div>
    ${card("Decision Factors", rows({Trend: a.trend || "-", Momentum: a.momentum || "-", "Volume Expansion": `${num(a.volume_ratio)}x`, "RSI (14)": num(a.rsi), Pattern: a.pattern?.name || "-", "Approx Timeframe": decisionTimeframe()}))}
    ${setupPanel()}${aiPanel()}`;
}

function riskModule() {
  const a = state.analysis || {};
  const entry = Number(a.levels?.entry);
  const stop = Number(a.levels?.stop);
  const riskPct = Number.isFinite(entry) && Number.isFinite(stop) && entry ? Math.abs((entry - stop) / entry * 100).toFixed(2) : "-";
  const riskLevel = Number(a.atr) / Math.max(1, Number(a.price)) > .035 ? "Elevated" : Number(a.setup_quality) < 40 ? "High" : "Controlled";
  return `<div class="module-hero"><span>Risk Engine</span><h1>${esc(riskLevel)} Risk</h1></div>
    <div class="module-grid">${metric("Entry", money(entry))}${metric("Stop", money(stop))}${metric("Risk To Stop", `${riskPct}%`)}${metric("ATR", money(a.atr))}</div>
    ${card("Risk Controls", rows({"Decision Tier": decisionTier(), Trend: a.trend || "-", Momentum: a.momentum || "-", "Volume Liquidity": `${num(a.volume_ratio)}x`, "Invalidation": `Below ${money(stop)}`, "Next Review": decisionTimeframe()}))}
    ${card("Risk Notes", `<p class="small-copy">Risk is separate from the trade action. A WAIT decision means no confirmed entry yet; it does not mean the risk engine is empty.</p>`)}`;
}

function researchModule(page) {
  const a = state.analysis || {};
  const proofRows = calendarEvents().map((event) => `<a class="proof-row" href="${esc(event.sourceUrl)}" target="_blank" rel="noreferrer"><b>${esc(eventDateLabel(event))}</b><span>${esc(event.title)}</span><em>${esc(event.time)} · ${esc(event.proof)}</em></a>`).join("");
  return `<div class="module-hero"><span>${esc(page)}</span><h1>${esc(state.ticker)}</h1><p>Evidence, dates, sources, and validation context for the current setup.</p></div>
    <div class="module-grid">${metric("Decision", decisionTier())}${metric("Timeframe", decisionTimeframe())}${metric("Pattern", a.pattern?.name || "-")}${metric("Updated", a.updated_at ? new Date(a.updated_at).toLocaleString() : "-")}</div>
    ${card("Research Validation", `<p class="small-copy">Evidence research and backtesting are validation layers. They do not rewrite the production BUY/SELL/WATCH decision; they show why the setup is or is not supported.</p>${rows({Trend: a.trend || "-", Momentum: a.momentum || "-", RSI: num(a.rsi), "Volume Ratio": `${num(a.volume_ratio)}x`, Support: money(a.support), Resistance: money(a.resistance)})}`)}
    ${card("Dates And Proofs", `<div class="proof-list">${proofRows || `<div class="empty compact">No dated proof rows returned by provider.</div>`}</div>`)}
    ${newsModule()}`;
}

function calendarPage() {
  const proofRows = calendarEvents().map((event) => `<a class="proof-row ${event.level.toLowerCase()}" href="${esc(event.sourceUrl)}" target="_blank" rel="noreferrer"><b>${esc(eventDateLabel(event))}</b><span>${esc(event.title)}</span><em>${esc(event.time)} · ${esc(event.proof)}</em></a>`).join("");
  return `<div class="module-hero"><span>Dated Market Events</span><h1>Impact Calendar</h1><p>Scheduled macro, Fed, earnings and market events with source links and expected stock impact.</p></div>
    ${impactCalendar()}${eventImpact()}
    ${card("Source Proofs", `<div class="proof-list">${proofRows || `<div class="empty compact">No calendar source proofs returned by provider.</div>`}</div>`)}`;
}

function technicalModule() {
  const a = state.analysis || {};
  return `${chartPanel()}${setupPanel()}${card("Technical Detail", rows({Trend: a.trend || "-", Momentum: a.momentum || "-", "Decision Tier": decisionTier(), "Approx Timeframe": decisionTimeframe(), Support: money(a.support), Resistance: money(a.resistance), ATR: money(a.atr), Pattern: a.pattern?.name || "-"}))}`;
}

function companyModule() {
  const p = state.company?.profile || state.company || {};
  const s = state.company?.scores || {};
  const cap = marketCap();
  const hasProfilePayload = hasValue(p.sector) || hasValue(p.industry) || hasValue(p.name) || hasValue(p.description) || hasValue(p.summary) || cap !== "Not returned";
  if (!hasProfilePayload) return "";
  const metrics = [
    ["Sector", p.sector],
    ["Industry", p.industry],
    ["Market Cap", cap],
    ["Employees", p.employees?.toLocaleString?.()],
    ["Overall Score", hasValue(s.overall_company_score) ? num(s.overall_company_score, 1) : null],
    ["Financial Strength", hasValue(s.financial_strength) ? num(s.financial_strength, 1) : null],
  ];
  const overview = first(p.description, p.summary);
  return `<div class="module-grid">${metricList(metrics)}</div>${overview ? card("Business Overview", `<p class="small-copy">${esc(overview)}</p>`) : ""}`;
}

function fundamentalModule() {
  const f = state.fundamental || {};
  const p = f.profile || {};
  const v = f.valuation || {};
  const companyScores = state.company?.scores || {};
  const revenueGrowth = first(f.growth?.revenue_growth, f.revenueGrowth, state.company?.profile?.revenue_growth);
  const profitMargin = first(f.profitMargins, f.profit_margin, state.company?.profile?.profit_margin);
  const roe = first(f.returnOnEquity, f.roe, state.company?.profile?.roe);
  const cap = firstPositiveNumber(p.market_cap, p.marketCap, f.marketCap, f.market_cap, state.company?.profile?.market_cap, state.company?.profile?.marketCap);
  const metrics = [
    ["Company Score", hasValue(first(f.scores?.fundamental_score, companyScores.overall_company_score)) ? num(first(f.scores?.fundamental_score, companyScores.overall_company_score), 1) : null],
    ["Market Cap", cap ? money(cap) : null],
    ["P/E", hasValue(first(v.trailing_pe, p.trailing_pe, f.trailingPE, f.trailing_pe, state.company?.profile?.trailing_pe)) ? num(first(v.trailing_pe, p.trailing_pe, f.trailingPE, f.trailing_pe, state.company?.profile?.trailing_pe)) : null],
    ["Forward P/E", hasValue(first(v.forward_pe, p.forward_pe, f.forwardPE, f.forward_pe)) ? num(first(v.forward_pe, p.forward_pe, f.forwardPE, f.forward_pe)) : null],
    ["Revenue Growth", hasValue(revenueGrowth) ? pct(Number(revenueGrowth) * (Math.abs(Number(revenueGrowth)) <= 1 ? 100 : 1)) : null],
    ["EPS", hasValue(first(f.earnings?.trailing_eps, f.epsTrailingTwelveMonths, f.trailingEps, state.company?.earnings?.trailing_eps)) ? money(first(f.earnings?.trailing_eps, f.epsTrailingTwelveMonths, f.trailingEps, state.company?.earnings?.trailing_eps)) : null],
    ["Profit Margin", hasValue(profitMargin) ? pct(Number(profitMargin) * (Math.abs(Number(profitMargin)) <= 1 ? 100 : 1)) : null],
    ["ROE", hasValue(roe) ? pct(Number(roe) * (Math.abs(Number(roe)) <= 1 ? 100 : 1)) : null],
    ["Dividend Yield", hasValue(first(f.dividendYield, f.dividend_yield)) ? pct(Number(first(f.dividendYield, f.dividend_yield)) * (Math.abs(Number(first(f.dividendYield, f.dividend_yield))) <= 1 ? 100 : 1)) : null],
    ["Beta", hasValue(first(f.beta, state.company?.stock_level?.beta)) ? num(first(f.beta, state.company?.stock_level?.beta)) : null],
  ];
  const sourceRows = rows({Source: f.source, Updated: first(f.updated_at, state.analysis?.updated_at)});
  return `<div class="module-grid">${metricList(metrics)}</div>
    ${sourceRows ? card("Fundamental Sources", sourceRows) : ""}
    ${insiderModule()}`;
}

function insiderModule() {
  const data = state.insiders || {};
  const items = arr(data.items).slice(0, 8);
  const holders = arr(data.holders).slice(0, 4);
  const holderLabels = {
    insidersPercentHeld: "Insiders Held",
    institutionsPercentHeld: "Institutions Held",
    institutionsFloatPercentHeld: "Institution Float",
    institutionsCount: "Institution Count",
  };
  const body = items.length ? items.map((r) => {
    const date = first(r["Start Date"], r.StartDate, r.Date, r.date);
    const action = first(r.Text, r.Transaction, r.transaction, r.Type, r.type, "Transaction detail not returned");
    const shares = first(r.Shares, r.shares);
    return `<div class="insider-row"><b>${esc(first(r.Insider, r.insider, r.Name, r.name, "Insider"))}</b><span>${esc(action)}</span><em>${esc([shares ? `${compactNumber(shares)} shares` : "", date ? new Date(date).toLocaleDateString() : ""].filter(Boolean).join(" · "))}</em></div>`;
  }).join("") : `<div class="empty">No recent insider transaction rows returned by the provider.</div>`;
  const holderBody = holders.length ? `<div class="holder-list">${holders.map((r) => {
    const key = first(r.index, r.label, r.name);
    const value = first(r.Value, r.value);
    const rendered = String(key).includes("Count") ? compactNumber(value) : pct(Number(value) * 100);
    return `<span><b>${esc(holderLabels[key] || key)}</b>${esc(rendered)}</span>`;
  }).join("")}</div>` : "";
  return `${card("Insiders / Major Holders", `${body}${holderBody}<p class="small-copy">Celebrity or CEO buying is only shown when a public provider reports it. Unverified social-media claims are not used as proof.</p>`)}`;
}

function newsModule() {
  const items = arr(state.news).slice(0, 12);
  return card(`${state.ticker} News Sentiment`, items.length ? `<div class="news-board">${items.map(newsSentimentItem).join("")}</div>` : `<div class="empty">No recent news returned.</div>`);
}

function newsSentimentItem(n) {
  const sentiment = n.sentiment || {label: "Neutral", impact: "Low"};
  const label = String(sentiment.label || "Neutral");
  const cls = label.toLowerCase() === "positive" ? "positive" : label.toLowerCase() === "negative" ? "negative" : "neutral";
  const url = n.url || n.link || "#";
  return `<article class="news-item sentiment-${cls}">
    <div class="news-line"><span class="sentiment-dot ${cls}"></span><b>${esc(label)}</b><em>${esc(sentiment.impact || "Low")} impact</em></div>
    <a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(n.title || n.headline || "Market update")}</a>
    <span>${esc(n.publisher || n.source || "")} ${n.published_iso ? `· ${esc(new Date(n.published_iso).toLocaleString())}` : ""}</span>
    <p>${esc(n.summary || n.description || "")}</p>
  </article>`;
}

function tradeScannerPage() {
  const data = state.scanner || {};
  const items = arr(data.items);
  const sectors = arr(data.sectors).length ? arr(data.sectors) : ["All", "AI / Semiconductors", "Software / Cloud", "Biotech / Healthcare", "Space / Defense", "EV / Mobility", "Crypto / Fintech", "Energy / Commodities", "Consumer / Internet", "Financials", "ETFs / Macro"];
  return `
    <div class="module-hero scanner-hero">
      <span>Market-Wide Catalyst Scan</span>
      <h1>Trade Scanner</h1>
      <p>Scans a broad watch universe for early catalyst language, volume expansion, momentum, product progress, upcoming announcements, and technical setups before the move becomes obvious.</p>
    </div>
    <section class="scanner-controls">
      <label>Sector
        <select id="scannerSector">${sectors.map((sector) => `<option value="${esc(sector)}" ${state.scannerSector === sector ? "selected" : ""}>${esc(sector)}</option>`).join("")}</select>
      </label>
      <button id="runGeopolitics" class="scanner-secondary">${state.geopoliticalLoading ? "Scanning policy..." : "Scan Geopolitics / Policy"}</button>
      <div class="sector-chips">${sectors.slice(0, 8).map((sector) => `<button class="${state.scannerSector === sector ? "active" : ""}" data-sector-chip="${esc(sector)}">${esc(sector)}</button>`).join("")}</div>
    </section>
    <section class="scanner-actions">
      <button id="runScanner" class="scanner-primary">${state.scannerLoading ? "Scanning..." : "Scan World News + Setups"}</button>
      <div><b>${hasValue(data.universe_size) ? esc(data.universe_size) : "-"}</b><span>symbols checked</span></div>
      <div><b>${items.length ? `Top ${items.length}` : "-"}</b><span>ranked opportunities</span></div>
      <div><b>${esc(data.sector || state.scannerSector)}</b><span>selected sector</span></div>
      <div><b>${data.updated_at ? esc(new Date(data.updated_at).toLocaleTimeString()) : "-"}</b><span>last scan</span></div>
    </section>
    ${geopoliticalPanel()}
    ${state.scannerError ? `<div class="error"><b>Scanner error</b><span>${esc(state.scannerError)}</span></div>` : ""}
    ${state.scannerLoading && !items.length ? `<div class="state">Scanning articles, catalysts, volume and chart setups...</div>` : ""}
    <div class="scanner-grid">
      ${items.length ? items.map(scannerCard).join("") : `<div class="empty">Run the scanner to find catalyst-driven watchlist candidates.</div>`}
    </div>
    ${data.method || data.disclaimer ? card("Scanner Method", `<p class="small-copy">${esc(data.method || "")}</p><p class="small-copy">${esc(data.disclaimer || "")}</p>`) : ""}
  `;
}

function geopoliticalPanel() {
  const data = state.geopolitical || {};
  const items = arr(data.items);
  if (state.geopoliticalLoading && !items.length) return `<div class="state">Scanning policy, tariffs, speeches, sanctions and global politics...</div>`;
  if (state.geopoliticalError) return `<div class="error"><b>Geopolitics scanner error</b><span>${esc(state.geopoliticalError)}</span></div>`;
  if (!items.length) return "";
  return card("Geopolitics / Policy Impact", `
    <p class="small-copy">${esc(data.method || "Scans government policy, tariffs, speeches, regulation and global politics.")}</p>
    <div class="geo-grid">${items.map(geoCard).join("")}</div>
    <p class="small-copy">${esc(data.disclaimer || "Confirm policy impact with price, volume and official releases.")}</p>
  `);
}

function geoCard(item) {
  const details = arr(item.policy_details).slice(0, 4);
  return `<article class="geo-card">
    <header><b>${esc(item.theme)}</b><strong>${num(item.heat, 0)}<span>heat</span></strong></header>
    <p>${esc(item.why || "")}</p>
    <div class="geo-cols">
      <div><b>Benefits</b><section>${arr(item.benefiting_sectors).map((x) => `<span>${esc(x)}</span>`).join("")}</section></div>
      <div><b>Pressure</b><section>${arr(item.pressured_sectors).map((x) => `<span>${esc(x)}</span>`).join("")}</section></div>
      <div><b>Stocks</b><section>${arr(item.stocks_to_watch).map((x) => `<button data-scan-open="${esc(x)}">${esc(x)}</button>`).join("")}</section></div>
    </div>
    <div class="policy-detail-list">${details.length ? details.map(policyDetailRow).join("") : `<div class="empty">No article-level details returned for this theme.</div>`}</div>
  </article>`;
}

function policyDetailRow(detail) {
  const reported = detail.announced_or_reported && !Number.isNaN(new Date(detail.announced_or_reported).getTime())
    ? new Date(detail.announced_or_reported).toLocaleString()
    : (detail.announced_or_reported || "Date not provided");
  return `<a class="policy-detail" href="${esc(detail.url || "#")}" target="_blank" rel="noreferrer">
    <b>${esc(detail.headline || "Policy headline")}</b>
    <span><strong>Place</strong>${esc(detail.place || "Not specified")}</span>
    <span><strong>Policy</strong>${esc(detail.policy || "Policy signal")}</span>
    <span><strong>Reported</strong>${esc(reported)}</span>
    <span><strong>Ends</strong>${esc(detail.end_date || "Not stated")}</span>
    <em>${esc(detail.source || "News source")} - open article</em>
  </a>`;
}

function scannerCard(item, index) {
  const articles = arr(item.articles).slice(0, 3);
  const why = arr(item.why).slice(0, 3);
  const confirms = arr(item.confirmation).slice(0, 3);
  const risks = arr(item.risk_watch).slice(0, 3);
  const score = Number(item.score || 0);
  const nextWatch = first(item.next_announcement_watch?.summary, item.product_progress_watch);
  const detailBlocks = [
    confirms.length ? `<div><b>Confirm</b>${confirms.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : "",
    risks.length ? `<div><b>Risk</b>${risks.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : "",
  ].filter(Boolean).join("");
  const nextBlocks = [
    hasValue(item.estimated_bullish_timeframe) ? `<b>Approx Bullish Timeframe</b><span>${esc(item.estimated_bullish_timeframe)}</span>` : "",
    hasValue(nextWatch) ? `<b>Next Linked Catalyst</b><span>${esc(nextWatch)}</span>` : "",
  ].filter(Boolean).join("");
  return `<article class="scanner-card">
    <header>
      <div><small>#${index + 1}</small><button data-scan-open="${esc(item.ticker)}">${esc(item.ticker)}</button></div>
      <strong>${num(score, 1)}<span>rank score</span></strong>
    </header>
    <div class="scanner-metrics">
      <span>${money(item.price)}</span>
      <em class="${Number(item.change_pct) < 0 ? "bad" : "good"}">${Number(item.change_pct) >= 0 ? "+" : ""}${pct(item.change_pct)}</em>
      <span>${esc(item.signal || "WATCH")}</span>
      <span>${esc(item.trend || "-")}</span>
      <span>${plusPct(item.estimated_upside_pct)}</span>
      <span>${money(item.estimated_target_price)}</span>
    </div>
    <div class="confidence"><i style="width:${Math.max(0, Math.min(100, score))}%"></i></div>
    ${first(item.upside_thesis, why[0]) ? `<section class="scanner-thesis">
      <b>Why it can go up</b>
      <p>${esc(first(item.upside_thesis, why[0]))}</p>
    </section>` : ""}
    ${detailBlocks ? `<div class="scanner-detail">${detailBlocks}</div>` : ""}
    ${nextBlocks ? `<div class="scanner-next">${nextBlocks}</div>` : ""}
    <ul>${why.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <div class="scanner-news">${articles.map((a) => `<a href="${esc(a.url || "#")}" target="_blank" rel="noreferrer">${esc(a.title || "Market headline")}</a>`).join("")}</div>
  </article>`;
}

function scannerUniverse() {
  const selected = SECTOR_UNIVERSES[state.scannerSector];
  return (selected && selected.length ? selected : SCAN_UNIVERSE).slice(0, 30);
}

function scannerItemFromAnalysis(a) {
  const price = firstNumber(a.price, a.quote?.price);
  const change = firstNumber(a.change_pct, a.quote?.change_pct);
  const score = firstNumber(a.setup_quality, a.score, a.decision?.score, a.decision?.technical_score);
  const volumeRatio = firstNumber(a.volume_ratio, a.technical?.volume_ratio, a.technical?.volumeRatio);
  const rsi = firstNumber(a.rsi, a.technical?.rsi);
  const sma20 = firstNumber(a.sma_20, a.sma20, a.technical?.sma_20, a.technical?.sma20);
  const why = [
    Number.isFinite(price) && Number.isFinite(sma20) && price > sma20 ? `Price is above the 20-day average (${money(sma20)}).` : "",
    Number.isFinite(volumeRatio) && volumeRatio >= 1.2 ? `Volume is ${volumeRatio.toFixed(2)}x recent average.` : "",
    Number.isFinite(rsi) && rsi >= 45 && rsi <= 75 ? `RSI is in a tradable range (${rsi.toFixed(1)}).` : "",
    Number.isFinite(change) ? `Latest provider move is ${formatDelta(change)}.` : "",
  ].filter(Boolean);
  const risks = [
    Number.isFinite(rsi) && rsi > 75 ? `RSI is extended (${rsi.toFixed(1)}).` : "",
    Number.isFinite(price) && Number.isFinite(sma20) && price < sma20 ? `Price is below the 20-day average (${money(sma20)}).` : "",
  ].filter(Boolean);
  const computedScore = Number.isFinite(score)
    ? score
    : [
      Number.isFinite(change) && change > 0 ? 20 : 0,
      Number.isFinite(volumeRatio) && volumeRatio >= 1.2 ? 25 : 0,
      Number.isFinite(price) && Number.isFinite(sma20) && price > sma20 ? 25 : 0,
      Number.isFinite(rsi) && rsi >= 45 && rsi <= 75 ? 20 : 0,
    ].reduce((sum, value) => sum + value, 0);
  return {
    ticker: a.ticker || a.symbol,
    signal: first(a.signal, a.decision?.signal, computedScore >= 60 ? "WATCH" : ""),
    score: computedScore,
    price,
    change_pct: change,
    trend: first(a.trend, a.technical?.trend),
    estimated_target_price: firstNumber(a.levels?.target1, a.resistance),
    estimated_upside_pct: price && firstNumber(a.levels?.target1, a.resistance)
      ? ((firstNumber(a.levels?.target1, a.resistance) / price - 1) * 100)
      : null,
    estimated_bullish_timeframe: first(a.eta_days ? `${a.eta_days} days` : "", a.timeframe),
    why,
    confirmation: why,
    risk_watch: risks,
    articles: [],
  };
}

async function scannerFallback(reason) {
  const symbols = scannerUniverse();
  const settled = await Promise.allSettled(symbols.map((symbol) =>
    api(`/market/analysis?ticker=${encodeURIComponent(symbol)}&period=3mo&interval=1d`)
  ));
  const items = settled
    .filter((result) => result.status === "fulfilled")
    .map((result) => scannerItemFromAnalysis(result.value))
    .filter((item) => hasValue(item.ticker) && Number.isFinite(Number(item.price)))
    .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
    .slice(0, 50);
  if (!items.length) throw Error(reason || "Unable to scan trade opportunities.");
  return {
    sector: state.scannerSector,
    sectors: Object.keys(SECTOR_UNIVERSES),
    universe_size: symbols.length,
    items,
    updated_at: new Date().toISOString(),
    method: "Provider-backed chart scan from market analysis route.",
  };
}

async function runScanner() {
  state.scannerLoading = true;
  state.scannerError = "";
  renderContent();
  try {
    state.scanner = await api(`/market/trade-scanner?limit=50&sector=${encodeURIComponent(state.scannerSector)}`);
  } catch (e) {
    try {
      state.scanner = await scannerFallback(e.message);
    } catch (fallbackError) {
      state.scannerError = fallbackError.message || "Unable to scan trade opportunities.";
    }
  } finally {
    state.scannerLoading = false;
    renderContent();
  }
}

async function runGeopolitics() {
  state.geopoliticalLoading = true;
  state.geopoliticalError = "";
  renderContent();
  try {
    state.geopolitical = await api("/market/geopolitics?limit=8");
  } catch (e) {
    state.geopoliticalError = e.message || "Unable to scan geopolitical policy impact.";
  } finally {
    state.geopoliticalLoading = false;
    renderContent();
  }
}

function bindScanner() {
  const btn = $("#runScanner");
  if (btn) btn.onclick = runScanner;
  const geo = $("#runGeopolitics");
  if (geo) geo.onclick = runGeopolitics;
  const sector = $("#scannerSector");
  if (sector) sector.onchange = () => { state.scannerSector = sector.value; state.scanner = null; runScanner(); };
  $$("[data-sector-chip]").forEach((b) => b.onclick = () => { state.scannerSector = b.dataset.sectorChip; state.scanner = null; runScanner(); });
  $$("[data-scan-open]").forEach((b) => b.onclick = () => load(b.dataset.scanOpen, state.tf));
  if (!state.scanner && !state.scannerLoading && !state.scannerError) runScanner();
}

function tradePlannerPage() {
  const form = state.plannerForm;
  const data = state.planner || {};
  const recommendations = arr(data.recommendations);
  return `
    <div class="module-hero planner-hero">
      <span>What Can My Money Do?</span>
      <h1>AI Trade Planner</h1>
      <p>Builds a risk-adjusted deployment plan from provider-backed market data, scanner candidates, technicals, fundamentals, news, policy risk, and historical forward returns.</p>
    </div>
    <section class="planner-console">
      <label>Capital
        <input id="plannerCapital" inputmode="decimal" value="${esc(form.capital)}" aria-label="Capital">
      </label>
      <label>Maximum Loss
        <input id="plannerMaxLoss" inputmode="decimal" value="${esc(form.max_loss_amount)}" aria-label="Maximum loss">
      </label>
      <label>Positions
        <select id="plannerPositions">${[1,2,3,5].map((n) => `<option value="${n}" ${Number(form.number_of_positions) === n ? "selected" : ""}>${n}</option>`).join("")}</select>
      </label>
      <div class="planner-segments" data-planner-group="risk_profile">
        ${["conservative", "balanced", "aggressive"].map((v) => `<button class="${form.risk_profile === v ? "active" : ""}" data-planner-risk="${v}">${esc(v[0].toUpperCase() + v.slice(1))}</button>`).join("")}
      </div>
      <div class="planner-segments wide" data-planner-group="strategy">
        ${[
          ["auto", "AI Decide"],
          ["day_trade", "Day"],
          ["swing_trade", "Swing"],
          ["position_trade", "Position"],
          ["long_term", "Long Term"],
        ].map(([v, label]) => `<button class="${form.strategy === v ? "active" : ""}" data-planner-strategy="${v}">${esc(label)}</button>`).join("")}
      </div>
      <label class="planner-toggle"><input id="plannerFractional" type="checkbox" ${form.allow_fractional_shares ? "checked" : ""}> Fractional shares</label>
      <button id="runPlanner" class="planner-primary">${state.plannerLoading ? "Analyzing..." : "Analyze Opportunities"}</button>
    </section>
    ${state.plannerError ? `<div class="error"><b>Planner error</b><span>${esc(state.plannerError)}</span></div>` : ""}
    ${state.plannerLoading ? `<div class="state">Building risk-adjusted trade plan from live data...</div>` : ""}
    ${data.decision ? plannerResults(data, recommendations) : `<div class="empty planner-empty">Enter your capital and run the planner. The engine can deploy partially or recommend WAIT if the evidence is not strong enough.</div>`}
  `;
}

function plannerResults(data, recommendations) {
  const regime = data.market_regime || {};
  const decision = data.decision || "WAIT";
  const allocation = data.allocation || {};
  return `
    <section class="planner-result-head">
      <div><span>AI Decision</span><strong class="${decision === "WAIT" ? "warn" : "good"}">${esc(decision)}</strong><em>${esc(data.summary || "")}</em></div>
      <div><span>Deploy</span><strong>${money(allocation.allocated_capital)}</strong><em>Cash reserve ${money(data.cash_reserve)}</em></div>
      <div><span>Potential Profit</span><strong>${money(first(data.potential_profit_at_target, data.expected_profit))}</strong><em>Expected value ${first(data.expected_value, null) === null ? "Not estimated" : money(data.expected_value)}</em></div>
      <div><span>Planned Risk</span><strong>${money(first(data.planned_risk, data.maximum_expected_loss))}</strong><em>Confidence ${num(data.confidence, 0)}/100</em></div>
    </section>
    <div class="planner-mode ${data.planner_mode === "fallback" ? "limited" : "full"}">${data.planner_mode === "fallback" ? "Limited analysis" : "Full analysis"}</div>
    ${card("Market Environment", `
      ${rows({
        Regime: regime.regime,
        Trend: regime.trend,
        Volatility: regime.volatility,
        Confidence: hasValue(regime.confidence) ? `${num(regime.confidence, 0)}/100` : null,
        "Data As Of": regime.market_data_as_of,
      })}
      <div class="planner-evidence-strip">${arr(regime.evidence).map((x) => `<span><b>${esc(x.symbol || x.ticker)}</b>${money(x.price)} <em class="${Number(x.change_pct) < 0 ? "bad" : "good"}">${esc(formatDelta(x.change_pct))}</em></span>`).join("")}</div>
    `)}
    ${recommendations.length ? `<div class="planner-recs">${recommendations.map(plannerCard).join("")}</div>` : plannerWait(data)}
    ${plannerAlternatives(data)}
    ${plannerRejected(data)}
  `;
}

function plannerCard(item, index) {
  const horizons = Object.entries(item.horizons || {}).filter(([, h]) => h && !h.insufficient_data);
  const evidence = item.evidence || {};
  const scenarios = item.scenarios || {};
  return `<article class="planner-card">
    <header>
      <div><small>Rank ${index + 1}</small><button data-scan-open="${esc(item.ticker)}">${esc(item.ticker)}</button><span>${esc(item.company || item.sector || "")}</span></div>
      <strong>${num(item.confidence, 0)}<em>/100</em></strong>
    </header>
    <div class="planner-metrics">
      ${metric("Trade Type", plannerStrategyLabel(item.strategy))}
      ${metric("Current Price", money(item.current_price))}
      ${metric("Entry", money(item.entry))}
      ${metric("Capital", money(item.capital_allocation))}
      ${metric("Shares", num(item.shares, 3))}
      ${metric("HaVi Score", hasValue(item.havi_score) ? `${num(item.havi_score, 0)}/100` : "-")}
      ${metric("Target 1", money(item.target_1))}
      ${metric("Target 2", money(item.target_2))}
      ${metric("Stop", money(item.stop_loss))}
      ${metric("Risk / Reward", hasValue(first(item.reward_risk_ratio, item.risk_reward)) ? `1 : ${num(first(item.reward_risk_ratio, item.risk_reward))}` : "-")}
      ${metric("Expected Return", pct(Number(item.expected_return || 0) * 100))}
      ${metric("Potential Profit", money(first(item.potential_profit_at_target, item.expected_profit)))}
      ${metric("Potential Loss", money(first(item.potential_loss_at_stop, item.possible_loss)))}
      ${metric("Expected Value", first(item.expected_value, null) === null ? "Not estimated" : money(item.expected_value))}
      ${metric("Positive Probability", hasValue(item.positive_probability) ? pct(Number(item.positive_probability) * 100) : "-")}
    </div>
    <div class="horizon-grid">${horizons.map(([label, h]) => `<div><b>${esc(label.toUpperCase())}</b><span>${pct(Number(h.expected_return || 0) * 100)}</span><em>${pct(Number(h.positive_probability || 0) * 100)} positive</em><small>${pct(Number(h.low_return || 0) * 100)} to ${pct(Number(h.high_return || 0) * 100)}</small></div>`).join("")}</div>
    <div class="scenario-grid">${["bull", "base", "bear"].map((name) => {
      const s = scenarios[name] || {};
      return `<div><b>${esc(name.toUpperCase())}</b><span>${pct(Number(s.probability || 0) * 100)}</span><em>${pct(Number(s.return_percent || 0))} return</em></div>`;
    }).join("")}</div>
    <section class="planner-why">
      <b>Why HaViQuant selected this</b>
      <p>${esc(plannerWhyText(item, evidence))}</p>
    </section>
    <div class="evidence-grid">
      ${plannerEvidence("Technical", evidence.technical)}
      ${plannerEvidence("Volume", evidence.volume)}
      ${plannerEvidence("Fundamental", evidence.fundamental)}
      ${plannerEvidence("News", evidence.news_sentiment)}
      ${plannerEvidence("Policy Risk", evidence.geopolitical_policy)}
      ${plannerEvidence("Backtest", evidence.backtest)}
    </div>
  </article>`;
}

function plannerStrategyLabel(value) {
  return ({
    auto: "AI Decide",
    day_trade: "Day Trade",
    swing_trade: "Swing Trade",
    position_trade: "Position Trade",
    long_term: "Long Term",
  })[value] || value;
}

function plannerWhyText(item, evidence) {
  const pieces = [
    hasValue(evidence.technical?.status) ? `technical trend is ${evidence.technical.status}` : "",
    hasValue(evidence.momentum?.status) ? `momentum is ${evidence.momentum.status}` : "",
    hasValue(evidence.volume?.evidence?.[0]?.value) ? `volume is ${num(evidence.volume.evidence[0].value)}x average` : "",
    hasValue(evidence.pattern?.status) ? `pattern is ${evidence.pattern.status}` : "",
    hasValue(evidence.geopolitical_policy?.status) ? `policy risk is ${evidence.geopolitical_policy.status}` : "",
  ].filter(Boolean);
  return pieces.length
    ? `${item.ticker} ranks as a ${plannerStrategyLabel(item.strategy)} because ${pieces.join(", ")}. Allocation is limited by stop distance, confidence, and selected risk profile.`
    : `${item.ticker} was selected from provider-backed scanner and analysis data. Review evidence before acting.`;
}

function plannerEvidence(title, data = {}) {
  const evidence = arr(data.evidence).slice(0, 2).map((x) => first(x.metric && `${x.metric}: ${formatCell(x.value)}`, x.theme && `${x.theme}: ${formatCell(x.heat)} heat`, x.status, x.value)).filter(hasValue);
  return `<div><b>${esc(title)}</b><span>${esc(formatCell(first(data.status, data.score)))}</span>${evidence.map((x) => `<em>${esc(x)}</em>`).join("")}</div>`;
}

function plannerWait(data) {
  return `<section class="planner-wait"><strong>WAIT</strong><p>${esc(data.summary || "No opportunity satisfied the current planner criteria.")}</p>${arr(data.warnings).map((x) => `<span>${esc(x)}</span>`).join("")}</section>`;
}

function plannerAlternatives(data) {
  const items = arr(data.alternative_strategies);
  if (!items.length) return "";
  return card("Strategy Comparison", `<div class="strategy-table">${items.map((x) => `<div><b>${esc(plannerStrategyLabel(x.strategy))}</b><span>${num(x.average_score, 1)}</span></div>`).join("")}</div>`);
}

function plannerRejected(data) {
  const items = arr(data.rejected_candidates).slice(0, 8);
  if (!items.length) return "";
  return card("Rejected Candidates", `<div class="rejected-list">${items.map((x) => `<span><b>${esc(x.ticker)}</b>${esc(x.reason || "Did not pass planner criteria")}</span>`).join("")}</div>`);
}

async function plannerFallback(reason) {
  const form = state.plannerForm;
  const scan = await scannerFallback(reason);
  const candidates = arr(scan.items)
    .filter((item) => hasValue(item.ticker) && Number.isFinite(Number(item.price)))
    .sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const selected = candidates.slice(0, Math.max(1, Number(form.number_of_positions || 1)));
  const recommendations = selected.map((item) => {
    const price = firstNumber(item.price, item.current_price) || 0;
    const confidence = Math.max(0, Math.min(100, Number(item.score || 0)));
    return {
      ticker: item.ticker,
      company: item.company || item.sector || "",
      strategy: form.strategy === "auto" ? "swing_trade" : form.strategy,
      data_quality: "partial",
      planner_mode: "fallback",
      confidence,
      havi_score: confidence,
      current_price: price,
      entry: price,
      capital_allocation: null,
      shares: null,
      target_1: firstNumber(item.estimated_target_price),
      stop_loss: null,
      risk_reward: null,
      expected_profit: null,
      expected_value: null,
      potential_profit_at_target: null,
      potential_loss_at_stop: null,
      positive_probability: null,
      evidence: {
        technical: {status: item.trend || item.signal || "WATCH", score: confidence},
        volume: {status: hasValue(item.volume_ratio) ? `${num(item.volume_ratio)}x average` : "Returned by scanner"},
        news_sentiment: {status: first(arr(item.why)[0], item.upside_thesis, "Provider-backed scanner candidate")},
        geopolitical_policy: {status: "Confirm before execution"},
        backtest: {status: "Planner endpoint unavailable; using live scanner fallback"},
      },
      why: item.why,
      articles: item.articles,
    };
  });
  const safeReason = String(reason || "Planner unavailable").includes("Not Found")
    ? "Planner service is not available in this deployed backend."
    : String(reason || "Planner unavailable");
  return {
    decision: recommendations.length ? "REVIEW" : "WAIT",
    planner_mode: "fallback",
    fallback_code: "PLANNER_UNAVAILABLE",
    summary: recommendations.length
      ? "Limited analysis: planner intelligence was unavailable, so only scanner-backed candidates are shown."
      : "Planner endpoint was unavailable and no provider-backed scanner candidates were returned.",
    recommendations,
    allocation: {allocated_capital: 0},
    cash_reserve: Number(form.capital || 0),
    potential_profit_at_target: null,
    expected_value: null,
    expected_portfolio_return: 0,
    maximum_expected_loss: 0,
    confidence: recommendations.length
      ? recommendations.reduce((sum, item) => sum + Number(item.confidence || 0), 0) / recommendations.length
      : 0,
    market_regime: {
      regime: "Provider-backed fallback",
      trend: "Scanner derived",
      volatility: "Confirm live",
      confidence: recommendations.length
        ? recommendations.reduce((sum, item) => sum + Number(item.confidence || 0), 0) / recommendations.length
        : 0,
      market_data_as_of: new Date().toISOString(),
      evidence: recommendations.map((item) => ({symbol: item.ticker, price: item.current_price, change_pct: first(candidates.find((c) => c.ticker === item.ticker)?.change_pct, 0)})),
    },
    alternative_strategies: [],
    rejected_candidates: candidates.slice(recommendations.length, recommendations.length + 8).map((item) => ({
      ticker: item.ticker,
      reason: "Lower scanner rank than selected candidates",
      score: item.score,
    })),
    warnings: [safeReason],
  };
}

async function runPlanner() {
  const form = state.plannerForm;
  form.capital = Number($("#plannerCapital")?.value || form.capital || 500);
  form.max_loss_amount = Number($("#plannerMaxLoss")?.value || form.max_loss_amount || 0);
  form.number_of_positions = Number($("#plannerPositions")?.value || form.number_of_positions || 3);
  form.allow_fractional_shares = Boolean($("#plannerFractional")?.checked);
  state.plannerLoading = true;
  state.plannerError = "";
  renderContent();
  try {
    state.planner = await api("/planner/analyze", {
      method: "POST",
      body: JSON.stringify({
        ...form,
        sector: state.scannerSector,
        portfolio_aware: false,
      }),
    });
  } catch (e) {
    try {
      state.planner = await plannerFallback(e.message);
      state.plannerError = "";
    } catch (fallbackError) {
      state.plannerError = fallbackError.message || "Unable to build trade plan.";
    }
  } finally {
    state.plannerLoading = false;
    renderContent();
  }
}

function bindPlanner() {
  const run = $("#runPlanner");
  if (run) run.onclick = runPlanner;
  $$("[data-planner-risk]").forEach((b) => b.onclick = () => { state.plannerForm.risk_profile = b.dataset.plannerRisk; renderContent(); });
  $$("[data-planner-strategy]").forEach((b) => b.onclick = () => { state.plannerForm.strategy = b.dataset.plannerStrategy; renderContent(); });
  $$("[data-scan-open]").forEach((b) => b.onclick = () => load(b.dataset.scanOpen, state.tf));
}

function bindDesk() {
  $$("[data-tf]").forEach((b) => b.onclick = () => load(state.ticker, b.dataset.tf));
  $$("[data-chart-tool]").forEach((b) => b.onclick = () => {
    state.chartTool = b.dataset.chartTool;
    if (state.chartTool === "Indicators") {
      state.showIndicators = !state.showIndicators;
      state.indicatorMode = state.showIndicators ? "EMA + VWAP + RSI" : "Hidden";
      renderContent();
    } else if (state.chartTool === "Templates") {
      state.chartTemplate = state.chartTemplate === "Trade Setup" ? "Clean Price" : state.chartTemplate === "Clean Price" ? "Multi-Timeframe" : "Trade Setup";
      renderContent();
    } else if (state.chartTool === "Camera") {
      downloadChart();
      renderContent();
    } else if (state.chartTool === "Fullscreen") {
      const shell = $(".chart-shell");
      if (shell?.requestFullscreen) shell.requestFullscreen();
      renderContent();
    } else {
      renderContent();
    }
  });
  $$("#content [data-calendar-tab]").forEach((b) => b.onclick = () => {
    state.calendarTab = b.dataset.calendarTab;
    renderContent();
  });
  $$("#content [data-event]").forEach((b) => b.onclick = () => {
    state.selectedEvent = b.dataset.event;
    renderContent();
  });
  const reset = $("#resetChart");
  if (reset) reset.onclick = () => { state.chartZoom = 1; state.chartOffset = 0; state.drawPoints = []; state.chartTool = "Indicators"; state.showIndicators = true; state.indicatorMode = "EMA + VWAP + RSI"; renderContent(); };
}

function downloadChart() {
  const canvas = $("#chart");
  if (!canvas) return;
  const link = document.createElement("a");
  link.download = `${state.ticker}-${state.tf}-chart.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function drawChart() {
  const canvas = $("#chart");
  const a = state.analysis || {};
  const dataAll = arr(a.candles).filter((r) => [r.open, r.high, r.low, r.close].every((k) => Number.isFinite(Number(k))));
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const W = Math.max(900, rect.width);
  const H = Math.max(500, rect.height);
  canvas.width = Math.floor(W * dpr);
  canvas.height = Math.floor(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!dataAll.length) {
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, "#071827");
    bg.addColorStop(1, "#06111d");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#17304a";
    ctx.strokeRect(18, 18, W - 36, H - 36);
    ctx.fillStyle = "#8fa5bd";
    ctx.font = "18px Inter, system-ui";
    ctx.textAlign = "center";
    ctx.fillText("No chart candles returned by provider for this timeframe.", W / 2, H / 2);
    ctx.font = "13px Inter, system-ui";
    ctx.fillText("Try another timeframe or retry after the data service refreshes.", W / 2, H / 2 + 28);
    return;
  }

  const padL = 70, padR = 84, padT = 28, priceH = H * .68, volH = H * .16, oscY = priceH + volH + 34;
  const baseVisible = Math.max(60, Math.min(120, Math.floor((W - padL - padR) / 8)));
  const visible = Math.max(36, Math.min(dataAll.length, Math.floor(baseVisible / Math.max(1, state.chartZoom))));
  const maxOffset = Math.max(0, dataAll.length - visible);
  const offset = Math.max(0, Math.min(maxOffset, Math.floor(state.chartOffset)));
  const start = Math.max(0, dataAll.length - visible - offset);
  const data = dataAll.slice(start, start + visible);
  const min = Math.min(...data.map((r) => Number(r.low)), Number(a.levels?.stop || Infinity));
  const max = Math.max(...data.map((r) => Number(r.high)), Number(a.levels?.target2 || -Infinity));
  const span = max - min || 1;
  const x = (i) => padL + (i / Math.max(1, data.length - 1)) * (W - padL - padR);
  const y = (v) => padT + (max - v) / span * (priceH - padT);
  const bw = Math.max(3, Math.min(13, (W - padL - padR) / data.length * .68));

  ctx.clearRect(0, 0, W, H);
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, "#071827");
  bg.addColorStop(1, "#06111d");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  ctx.strokeStyle = "#143149";
  ctx.fillStyle = "#6f89a4";
  ctx.font = "12px Inter, system-ui";
  for (let i = 0; i < 6; i++) {
    const yy = padT + i * (priceH - padT) / 5;
    const label = max - (span * i / 5);
    ctx.beginPath();
    ctx.moveTo(padL, yy);
    ctx.lineTo(W - padR, yy);
    ctx.stroke();
    ctx.fillText(label.toFixed(2), W - padR + 12, yy + 4);
  }

  if (state.showIndicators) {
    drawMovingAverage(ctx, data, 9, x, y, "#f7c846");
    drawMovingAverage(ctx, data, 20, x, y, "#2e8cff");
    drawMovingAverage(ctx, data, 50, x, y, "#8a5cff");
  }

  data.forEach((r, i) => {
    const open = Number(r.open), close = Number(r.close), high = Number(r.high), low = Number(r.low);
    const up = close >= open;
    const color = up ? "#20e188" : "#ff5368";
    const xx = x(i), top = y(Math.max(open, close)), bottom = y(Math.min(open, close));
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(xx, y(high));
    ctx.lineTo(xx, y(low));
    ctx.stroke();
    ctx.fillRect(xx - bw / 2, top, bw, Math.max(2, bottom - top));
    const volTop = priceH + 22 + (1 - Math.min(1, Number(r.volume || 0) / Math.max(...data.map((z) => Number(z.volume || 1))))) * volH;
    ctx.globalAlpha = .38;
    ctx.fillRect(xx - bw / 2, volTop, bw, priceH + 22 + volH - volTop);
    ctx.globalAlpha = 1;
  });

  if (state.chartTemplate !== "Clean Price") {
    const placedLevels = [];
    [
      ["T2", a.levels?.target2, "#20e188"],
      ["T1", a.levels?.target1, "#20e188"],
      ["Entry", a.levels?.entry, "#2e8cff"],
      ["Stop", a.levels?.stop, "#ff5368"],
    ].forEach(([label, value, color]) => drawLevel(ctx, label, value, color, W, padL, padR, priceH, y, placedLevels));
  }

  const last = data[data.length - 1];
  const lx = x(data.length - 8), ly = y(Number(last.close));
  if (state.chartTemplate === "Trade Setup") {
    ctx.strokeStyle = "#1fe36f";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(lx, ly + 38);
    ctx.lineTo(lx + 34, ly + 10);
    ctx.lineTo(lx + 58, ly + 22);
    ctx.lineTo(lx + 96, ly - 34);
    ctx.stroke();
  }

  ctx.strokeStyle = "#263f59";
  ctx.beginPath();
  ctx.moveTo(padL, oscY);
  ctx.lineTo(W - padR, oscY);
  ctx.stroke();
  const rsiRows = data.map((row, index) => ({index, value: Number(row.rsi)})).filter((row) => Number.isFinite(row.value));
  if (rsiRows.length > 1) {
    ctx.strokeStyle = "#8d55ff";
    ctx.beginPath();
    rsiRows.forEach((row, index) => {
      const yy = oscY + 55 - (row.value / 100) * 90;
      if (index) ctx.lineTo(x(row.index), yy); else ctx.moveTo(x(row.index), yy);
    });
    ctx.stroke();
  } else {
    ctx.fillStyle = "#6f89a4";
    ctx.fillText("RSI not returned", padL + 4, oscY + 34);
  }

  drawUserMarkers(ctx, W, H);

  bindChartPointer(canvas, data, x, y, W, padL, padR, visible);
}

function drawUserMarkers(ctx, W, H) {
  state.drawPoints.forEach((point, index) => {
    const x = point.x * W;
    const y = point.y * H;
    ctx.fillStyle = "#7de6ff";
    ctx.strokeStyle = "#07111d";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#eef5ff";
    ctx.font = "11px Inter, system-ui";
    ctx.fillText(`DRAW ${index + 1}`, x + 10, y - 10);
  });
  if (state.chartTool === "Draw") {
    ctx.fillStyle = "#7de6ff";
    ctx.font = "12px Inter, system-ui";
    ctx.fillText("Draw mode: click chart to place markers", 76, 22);
  }
}

function drawMovingAverage(ctx, data, n, x, y, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  data.forEach((r, i) => {
    const slice = data.slice(Math.max(0, i - n + 1), i + 1);
    const avg = slice.reduce((s, z) => s + Number(z.close), 0) / slice.length;
    if (i) ctx.lineTo(x(i), y(avg)); else ctx.moveTo(x(i), y(avg));
  });
  ctx.stroke();
}

function drawLevel(ctx, label, value, color, W, padL, padR, priceH, y, placed) {
  const v = Number(value);
  if (!Number.isFinite(v)) return;
  const yy = y(v);
  ctx.strokeStyle = color;
  ctx.setLineDash([9, 7]);
  ctx.beginPath();
  ctx.moveTo(padL, yy);
  ctx.lineTo(W - padR - 8, yy);
  ctx.stroke();
  ctx.setLineDash([]);
  const text = `${label} ${v.toFixed(2)}`;
  ctx.font = "10px Inter, system-ui";
  const width = Math.max(62, padR - 14);
  let labelY = Math.max(22, Math.min(priceH - 12, yy));
  for (let guard = 0; guard < 8 && placed.some((p) => Math.abs(p - labelY) < 18); guard++) {
    labelY = Math.min(priceH - 12, labelY + 18);
  }
  if (placed.some((p) => Math.abs(p - labelY) < 18)) {
    labelY = Math.max(22, Math.min(priceH - 12, yy - 18 * (placed.length + 1)));
  }
  placed.push(labelY);
  const x0 = W - padR + 6;
  ctx.fillStyle = "rgba(5, 18, 29, .92)";
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.beginPath();
  roundedRect(ctx, x0, labelY - 10, width, 18, 5);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.fillText(text, x0 + 5, labelY + 2);
}

function roundedRect(ctx, x, y, w, h, r) {
  if (ctx.roundRect) {
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
}

function bindChartPointer(canvas, data, x, y, W, padL, padR, visible) {
  const tip = $("#charttip");
  const readout = $("#chartReadout");
  let drag = false, sx = 0, old = 0;
  const maxOffset = Math.max(0, arr(state.analysis?.candles).length - visible);
  const show = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const i = Math.max(0, Math.min(data.length - 1, Math.round((mx - padL) / (W - padL - padR) * (data.length - 1))));
    const r = data[i];
    if (!r) return;
    const move = Number(r.open) ? (Number(r.close) / Number(r.open) - 1) * 100 : 0;
    const txt = `${Number(r.close) >= Number(r.open) ? "Bullish" : "Bearish"} candle | ${pct(move)} | O ${money(r.open)} H ${money(r.high)} L ${money(r.low)} C ${money(r.close)} | Volume ${Number(r.volume || 0).toLocaleString()}`;
    if (readout) readout.textContent = txt;
    if (tip) {
      tip.style.display = "block";
      tip.style.left = `${Math.min(rect.width - 230, Math.max(12, mx + 12))}px`;
      tip.style.top = `${Math.max(12, my - 86)}px`;
      tip.innerHTML = `<b>${esc(new Date(r.time || r.date || Date.now()).toLocaleString())}</b><br>O ${money(r.open)} H ${money(r.high)}<br>L ${money(r.low)} C ${money(r.close)}<br>Vol ${Number(r.volume || 0).toLocaleString()}<br>Pattern: ${esc(state.analysis?.pattern?.name || "Monitoring")}`;
    }
  };
  canvas.onmousemove = show;
  canvas.onmouseleave = () => { if (tip) tip.style.display = "none"; };
  canvas.onwheel = (e) => { e.preventDefault(); state.chartZoom = Math.max(1, Math.min(14, state.chartZoom * (e.deltaY < 0 ? 1.18 : .85))); state.chartOffset = Math.min(maxOffset, state.chartOffset); drawChart(); };
  canvas.onpointerdown = (e) => {
    if (state.chartTool === "Draw") {
      const rect = canvas.getBoundingClientRect();
      state.drawPoints.push({x: (e.clientX - rect.left) / Math.max(1, rect.width), y: (e.clientY - rect.top) / Math.max(1, rect.height)});
      drawChart();
      return;
    }
    drag = true; sx = e.clientX; old = state.chartOffset; canvas.setPointerCapture?.(e.pointerId); canvas.style.cursor = "grabbing";
  };
  canvas.onpointermove = (e) => {
    if (!drag) return show(e);
    state.chartOffset = Math.max(0, Math.min(maxOffset, old + (e.clientX - sx) * data.length / Math.max(120, W)));
    drawChart();
  };
  canvas.onpointerup = canvas.onpointercancel = () => { drag = false; canvas.style.cursor = "crosshair"; };
  canvas.ondblclick = () => { state.chartZoom = 1; state.chartOffset = 0; drawChart(); };
}

shell();
load(state.ticker, state.tf);
