const API = (location.hostname === "127.0.0.1" || location.hostname === "localhost")
  ? "http://127.0.0.1:8000/api/v1"
  : "https://haviquant-1.onrender.com/api/v1";

const NAV = [
  "Dashboard",
  "Stock Analysis",
  "Company Intelligence",
  "Fundamentals",
  "Technical",
  "Decision",
  "Trade Scanner",
  "Evidence Research",
  "Portfolio",
  "Risk",
  "Backtesting",
  "News",
  "Calendar",
];

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

const CALENDAR_TABS = ["Upcoming", "Earnings", "Economic", "Fed", "All"];
const EVENTS = [
  {category: "Economic", level: "HIGH", title: "Personal Income and PCE Deflator", date: "2026-08-26", time: "8:30 AM ET", impact: "Very High", proof: "New York Fed Economic Indicators Calendar", sourceUrl: "https://www.newyorkfed.org/research/calendars/i-aug26.html", scenario: "PCE inflation can move yields and growth-stock multiples. Softer inflation can support risk appetite; hotter inflation can pressure high-multiple names."},
  {category: "Economic", level: "HIGH", title: "Gross Domestic Product 2nd Release", date: "2026-08-26", time: "8:30 AM ET", impact: "High", proof: "New York Fed Economic Indicators Calendar", sourceUrl: "https://www.newyorkfed.org/research/calendars/i-aug26.html", scenario: "GDP revisions affect growth expectations, yields, cyclicals and broad market risk appetite."},
  {category: "Economic", level: "MEDIUM", title: "Advance Durable Goods", date: "2026-08-26", time: "8:30 AM ET", impact: "Medium", proof: "New York Fed Economic Indicators Calendar", sourceUrl: "https://www.newyorkfed.org/research/calendars/i-aug26.html", scenario: "Durable goods can influence industrials, transports, rates and demand expectations."},
  {category: "Economic", level: "MEDIUM", title: "Corporate Bond Market Distress Index", date: "2026-08-26", time: "10:00 AM ET", impact: "Medium", proof: "New York Fed Economic Indicators Calendar", sourceUrl: "https://www.newyorkfed.org/research/calendars/i-aug26.html", scenario: "Credit stress readings can affect market risk appetite and highly leveraged sectors."},
  {category: "Fed", level: "HIGH", title: "Fed Chair Jackson Hole Speech", date: "2026-08-28", time: "10:00 AM ET", impact: "Very High", proof: "Federal Reserve Board Calendar", sourceUrl: "https://www.federalreserve.gov/newsevents/2026-august.htm", scenario: "This is not scheduled for today. Market impact depends on inflation language, rate guidance, and bond-yield reaction."},
];

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
  company: null,
  fundamental: null,
  insiders: null,
  chartZoom: 1,
  chartOffset: 0,
  selected: null,
  calendarTab: "Upcoming",
  selectedEvent: "Personal Income and PCE Deflator",
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

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const first = (...xs) => xs.find((x) => x !== null && x !== undefined && x !== "" && x !== "N/A");
const arr = (x) => Array.isArray(x) ? x : !x ? [] : Array.isArray(x.items) ? x.items : Array.isArray(x.rows) ? x.rows : Array.isArray(x.data) ? x.data : [x];
const num = (x, d = 2) => Number.isFinite(Number(x)) ? Number(x).toFixed(d) : "-";
const pct = (x) => Number.isFinite(Number(x)) ? `${Number(x).toFixed(2)}%` : "-";
const plusPct = (x) => Number.isFinite(Number(x)) ? `+${Number(x).toFixed(2)}%` : "-";
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
const GEOPOLITICS_FALLBACK = [
  {theme: "Tariffs / Trade Policy", heat: 35, direction: "Watch", benefiting_sectors: ["domestic industrials", "materials", "defense supply chain"], pressured_sectors: ["retail importers", "hardware margins", "global autos"], stocks_to_watch: ["CAT", "DE", "XME", "FCX", "AAPL", "TSLA", "XLY"], why: "Live policy endpoint is not available in production yet. Use this as a watchlist only until linked article proof is returned.", policy_details: []},
  {theme: "Defense / Global Conflict", heat: 35, direction: "Watch", benefiting_sectors: ["defense", "aerospace", "cybersecurity"], pressured_sectors: ["airlines", "travel", "risk assets"], stocks_to_watch: ["LMT", "RTX", "NOC", "BA", "PANW", "CRWD", "CCL", "NCLH"], why: "Live policy endpoint is not available in production yet. Confirm with official releases and source articles before trading.", policy_details: []},
  {theme: "Technology Regulation / AI Policy", heat: 35, direction: "Watch", benefiting_sectors: ["approved AI infrastructure", "cybersecurity", "domestic semiconductors"], pressured_sectors: ["restricted chip exports", "high multiple software"], stocks_to_watch: ["NVDA", "AMD", "AVGO", "TSM", "CRWD", "PANW", "NET", "XLK"], why: "Live policy endpoint is not available in production yet. Treat this as a monitoring panel, not a confirmed catalyst.", policy_details: []},
];
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

async function api(path) {
  const token = localStorage.getItem("haviquant_access_token");
  const headers = token ? {Authorization: `Bearer ${token}`} : {};
  const r = await fetch(API + path, {headers});
  const raw = await r.text();
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch {}
  if (!r.ok) throw Error(data?.detail || raw || `${r.status} API request failed`);
  return data;
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

function scannerSymbolsForSector(sector) {
  const selected = String(sector || "All");
  return (selected === "All" ? SCAN_UNIVERSE : (SECTOR_UNIVERSES[selected] || SCAN_UNIVERSE)).slice(0, 50);
}

function fallbackScannerRow(analysis, newsItems) {
  const ticker = analysis.ticker || "-";
  const setup = Number(analysis.setup_quality || 0);
  const change = Number(analysis.change_pct || 0);
  const volume = Number(analysis.volume_ratio || 0);
  const catalystScore = newsItems.length ? Math.min(24, newsItems.length * 4) : 0;
  const score = Math.max(0, Math.min(100, setup * .72 + catalystScore + Math.max(0, change) * .8 + Math.min(10, volume * 2)));
  const upside = Math.max(1.5, Math.min(12, 2.5 + Math.max(0, score - 55) / 9));
  const price = Number(analysis.price);
  return {
    ticker,
    score: Number(score.toFixed(1)),
    signal: analysis.signal || "WATCH",
    trend: analysis.trend || "-",
    momentum: analysis.momentum || "-",
    price: Number.isFinite(price) ? price : null,
    change_pct: Number.isFinite(change) ? change : null,
    volume_ratio: Number.isFinite(volume) ? volume : null,
    estimated_upside_pct: Number(upside.toFixed(1)),
    estimated_target_price: Number.isFinite(price) ? Number((price * (1 + upside / 100)).toFixed(2)) : null,
    estimated_bullish_timeframe: setup >= 70 ? "1-5 trading days after volume confirmation" : setup >= 50 ? "1-3 weeks if price confirms breakout" : "No bullish timeframe yet; wait for confirmation",
    upside_thesis: `${ticker} is ranked from live production analysis because the setup score is ${setup}/100 with ${analysis.trend || "mixed"} trend and ${analysis.momentum || "neutral"} momentum.`,
    confirmation: ["Break above resistance or prior day high", "Volume expansion above recent average", "Fresh positive source or company event confirmation"],
    risk_watch: ["Backend scanner route is unavailable, so this row uses production fallback ranking", "Do not trade without confirming price, volume, and source news"],
    why: [`Production fallback scan from live ${ticker} analysis`, newsItems[0]?.title ? `Latest headline: ${newsItems[0].title}` : "No fresh headline returned"],
    articles: newsItems.slice(0, 3).map((x) => ({title: x.title || x.headline, publisher: x.publisher || x.source, url: x.url || x.link, sentiment: x.sentiment})),
    next_announcement_watch: {summary: newsItems[0]?.title || "Watch next company filing, earnings, product update, or analyst revision."},
    product_progress_watch: "Track product launches, contracts, production updates, regulatory milestones, and management guidance.",
  };
}

async function fallbackTradeScanner() {
  const symbols = scannerSymbolsForSector(state.scannerSector);
  const rows = [];
  for (let i = 0; i < symbols.length; i += 8) {
    const batch = symbols.slice(i, i + 8);
    const results = await Promise.allSettled(batch.map(async (ticker) => {
      const analysis = await api(`/market/analysis?ticker=${encodeURIComponent(ticker)}&period=60d&interval=5m`);
      let newsData = {items: []};
      try {
        newsData = await apiFirst([`/market/news?ticker=${encodeURIComponent(ticker)}`, `/news/${encodeURIComponent(ticker)}?limit=6`]);
      } catch {}
      return fallbackScannerRow(analysis, arr(newsData.items || newsData));
    }));
    results.forEach((result, idx) => {
      if (result.status === "fulfilled") rows.push(result.value);
      else rows.push({ticker: batch[idx], score: 0, signal: "WATCH", why: [`Fallback scan failed: ${result.reason?.message || "No data"}`], articles: [], risk_watch: ["No production data returned for this symbol"]});
    });
    state.scanner = {sector: state.scannerSector, universe_size: symbols.length, items: rows.slice().sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 50), fallback: true};
    renderContent();
  }
  rows.sort((a, b) => (b.score || 0) - (a.score || 0));
  return {updated_at: new Date().toISOString(), sector: state.scannerSector, sectors: ["All", ...Object.keys(SECTOR_UNIVERSES)], universe_size: symbols.length, items: rows.slice(0, 50), method: "Production fallback ranks existing live analysis plus available news.", disclaimer: "Research signal only. This does not guarantee that the stock price will rise.", fallback: true};
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
  return `<div class="metric ${cls}"><span>${esc(label)}</span><strong>${esc(value ?? "-")}</strong></div>`;
}

function rows(obj) {
  return Object.entries(obj || {}).map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("");
}

function shell() {
  $("#app").innerHTML = `
    <div class="terminal">
      <aside class="sidebar">
        <div class="brand">
          <div class="brandmark">HQ</div>
          <div><strong>HaViQuant</strong><small>Market Intelligence Command Center</small></div>
        </div>
        <nav>${NAV.map((n) => `<button class="${state.page === n ? "active" : ""}" data-nav="${esc(n)}">${icon(ICONS[n])}<span>${esc(n)}</span></button>`).join("")}</nav>
        ${sentimentBox("sidebar")}
        <div class="market-status"><b>Market Open</b><span>Live API connected</span></div>
      </aside>
      <main class="workspace">
        <header class="topbar">
          <div class="searchbox">${icon("search")}<input id="tickerInput" value="${esc(state.query)}" placeholder="Search ticker, company or event..."><button id="analyze">Analyze</button></div>
          ${marketTape()}
          <div class="tools">${icon("bell")}${icon("moon")}<div class="user">Hari M <span>Pro Trader</span></div></div>
        </header>
        <section class="eventbar">${events()}</section>
        <div id="content" class="content"></div>
        ${topMovers()}
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
  const items = [
    ["S&P 500", "5,543.22", "+0.98%"],
    ["NASDAQ", "17,875.58", "+1.35%"],
    ["DOW", "40,123.78", "+0.62%"],
    ["VIX", "15.24", "-6.25%"],
    [state.ticker, money(a.price), Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${pct(change)}` : "LIVE"],
  ];
  return `<div class="tape">${items.map(([l, v, d]) => `<span><b>${esc(l)}</b>${esc(v)}<em class="${String(d).startsWith("-") ? "bad" : "good"}">${esc(d)}</em></span>`).join("")}</div>`;
}

function events() {
  return `<button class="event-intro" data-open-calendar="1">Impact Calendar<br><small>${esc(todayLabel())}</small></button>${EVENTS.slice(0, 4).map((event) => `
    <button class="event-card ${event.level.toLowerCase()} ${state.selectedEvent === event.title ? "selected" : ""}" data-event="${esc(event.title)}"><i></i><div><b>${event.level}</b><span>${esc(event.title.replace("{ticker}", state.ticker))}</span><em>${esc(eventDateLabel(event))}</em></div><small><strong>${esc(event.time)}</strong><em>${esc(eventEta(event))}</em></small></button>`).join("")}<button class="calendar-btn" data-open-calendar="1">View Full Calendar</button>`;
}

function topMovers() {
  const symbols = ["NVDA", "AMD", "AVGO", "TSLA", "META", "INTC", "CCL", "NFLX", "QQQ", "SPY"];
  return `<footer class="movers" data-testid="top-movers"><b>TOP MOVERS</b><button class="${state.moverMode === "Gainers" ? "active" : ""}" data-mover-mode="Gainers">Gainers</button><button class="${state.moverMode === "Most Active" ? "active" : ""}" data-mover-mode="Most Active">Most Active</button>${symbols.map((s, i) => `
    <button data-mover="${s}" class="mover" data-tooltip="${esc(moverTooltip(s, i))}"><i>${moverIcon(s)}</i><span>${s}</span><em class="${i > 5 ? "bad" : "good"}">${i > 5 ? "-1.85%" : `+${(2.02 + i * .22).toFixed(2)}%`}</em></button>`).join("")}</footer>`;
}

function moverIcon(symbol) {
  const domains = {NVDA: "nvidia.com", AMD: "amd.com", AVGO: "broadcom.com", TSLA: "tesla.com", META: "meta.com", INTC: "intel.com", CCL: "carnivalcorp.com", NFLX: "netflix.com", QQQ: "invesco.com", SPY: "ssga.com"};
  const domain = domains[symbol];
  return domain ? `<img alt="${esc(symbol)} logo" src="https://logo.clearbit.com/${domain}" onerror="this.replaceWith(document.createTextNode('${esc(symbol.slice(0, 1))}'))">` : esc(symbol.slice(0, 1));
}

function moverTooltip(symbol, index) {
  const names = {NVDA: "NVIDIA", AMD: "Advanced Micro Devices", AVGO: "Broadcom", TSLA: "Tesla", META: "Meta Platforms", INTC: "Intel", CCL: "Carnival", NFLX: "Netflix", QQQ: "Invesco QQQ", SPY: "SPDR S&P 500"};
  const sectors = {NVDA: "AI chips", AMD: "Semiconductors", AVGO: "Chips / infrastructure", TSLA: "EV / autonomy", META: "Social / AI", INTC: "Semiconductors", CCL: "Cruise travel", NFLX: "Streaming", QQQ: "Nasdaq ETF", SPY: "S&P 500 ETF"};
  const move = index > 5 ? "-1.85%" : `+${(2.02 + index * .22).toFixed(2)}%`;
  return `${symbol} - ${names[symbol] || symbol}\nMove: ${move} (${index > 5 ? "lagging" : "gainer"})\nFocus: ${sectors[symbol] || "Market mover"}\nClick to load full analysis`;
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
  });
}

function calendarModal() {
  return `<div class="modal-backdrop" data-close-calendar="1">
    <section class="calendar-modal" onclick="event.stopPropagation()">
      <header><div><span>Market Calendar</span><h2>Impact Calendar</h2><p>${esc(todayLabel())}</p></div><button data-close-calendar="1">Close</button></header>
      <div class="tabs calendar-tabs">${CALENDAR_TABS.map((tab) => `<button class="${state.calendarTab === tab ? "active" : ""}" data-calendar-tab="${tab}">${tab}</button>`).join("")}</div>
      <div class="calendar-list">${calendarEvents().map((event) => `<button class="calendar-row" data-event="${esc(event.title)}" data-close-calendar="1"><b>${event.level}</b><span>${esc(event.title.replace("{ticker}", state.ticker))}</span><em>${esc(eventDateLabel(event))} · ${esc(event.category)}</em><small>${esc(event.time)}<br>${esc(event.impact)}</small></button>`).join("")}</div>
    </section>
  </div>`;
}

function sentimentBox(extra = "") {
  return `<section class="sentiment-box ${extra}" data-testid="market-sentiment">
    <h3>Market Sentiment</h3>
    <div class="gauge"><i></i><i></i><i></i></div>
    <strong>78</strong><b>BULLISH</b>
    ${rows({Bullish: "62%", Neutral: "23%", Bearish: "15%"})}
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
  renderContent();
  try {
    const [analysis, news, macro, company, fundamental, insiders] = await Promise.allSettled([
      api(`/market/analysis?ticker=${encodeURIComponent(clean)}&period=${period}&interval=${interval}&include_mtf=${interval === "1d"}`),
      api(`/market/news?ticker=${encodeURIComponent(clean)}`),
      api(`/market/macro?ticker=${encodeURIComponent(clean)}`),
      api(`/company-intelligence/${encodeURIComponent(clean)}`).catch(() => api(`/company/${encodeURIComponent(clean)}`)),
      api(`/fundamental/${encodeURIComponent(clean)}`),
      api(`/market/insiders?ticker=${encodeURIComponent(clean)}`),
    ]);
    if (analysis.status !== "fulfilled") throw analysis.reason;
    state.analysis = analysis.value || {};
    state.news = news.status === "fulfilled" ? arr(news.value?.items || news.value) : [];
    state.macro = macro.status === "fulfilled" ? macro.value : null;
    state.company = company.status === "fulfilled" ? company.value : null;
    state.fundamental = fundamental.status === "fulfilled" ? fundamental.value : null;
    state.insiders = insiders.status === "fulfilled" ? insiders.value : null;
  } catch (e) {
    state.error = e.message || "Unable to load market intelligence.";
  } finally {
    state.loading = false;
    shell();
    renderContent();
  }
}

function renderContent() {
  const c = $("#content");
  if (!c) return;
  if (state.loading) {
    c.innerHTML = `<div class="state">Loading ${esc(state.ticker)} command center...</div>`;
    return;
  }
  if (state.error) {
    c.innerHTML = `<div class="error"><b>Data error</b><span>${esc(state.error)}</span><button id="retry">Retry</button></div>`;
    $("#retry").onclick = () => load(state.ticker, state.tf);
    return;
  }
  if (state.page === "Dashboard" || state.page === "Stock Analysis") {
    c.innerHTML = tradingDesk();
    bindDesk();
    drawChart();
    return;
  }
  if (state.page === "Trade Scanner") {
    c.innerHTML = tradeScannerPage();
    bindScanner();
    return;
  }
  c.innerHTML = modulePage(state.page);
  bindDesk();
  drawChart();
}

function tradingDesk() {
  const a = state.analysis || {};
  const profile = state.company?.profile || state.company || {};
  const price = Number(a.price);
  const change = Number(a.change_pct);
  return `
    <div class="desk">
      <section class="chart-zone">
        <div class="quote-head">
          <div><h1>${esc(state.ticker)}</h1><span>${esc(profile.name || "NVIDIA Corporation")}</span><small>${esc(first(profile.sector, "Technology"))} - ${esc(first(profile.industry, "Semiconductors"))}</small></div>
          <div class="price-block"><strong>${money(price)}</strong><em class="${change < 0 ? "bad" : "good"}">${change >= 0 ? "+" : ""}${pct(change)}</em><small>Real-time</small></div>
          <div class="range"><label>Day's Range</label><b>929.40 - 949.80</b></div>
          <div class="range"><label>Volume</label><b>53.28M</b><small>1.82x Avg</small></div>
          <div class="range"><label>Market Cap</label><b>${money(first(profile.market_cap, profile.marketCap, state.fundamental?.marketCap))}</b></div>
          <button class="watch">In Watchlist</button>
        </div>
        ${chartPanel()}
        <div class="lower-grid">
          ${impactCalendar()}
          ${eventImpact()}
          ${mtfPanel()}
        </div>
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

function chartPanel() {
  return card("Trading Chart", `
    <div class="chart-toolbar">
      ${Object.keys(TIMEFRAMES).map((tf) => `<button class="${state.tf === tf ? "active" : ""}" data-tf="${tf}" data-testid="tf-${tf}">${tf}</button>`).join("")}
      <span></span>
      ${["Indicators", "Draw", "Templates", "Camera", "Fullscreen"].map((tool) => `<button class="tool ${state.chartTool === tool ? "active" : ""}" data-chart-tool="${tool}" title="${tool}" aria-label="${tool}">${toolIcon(tool)}</button>`).join("")}
      <button class="tool" id="resetChart" title="Reset View" aria-label="Reset View">${toolIcon("Reset")}</button>
    </div>
    <div class="chart-stats">
      <div><span>Day's Range</span><b>929.40 - 949.80</b></div>
      <div><span>Volume</span><b>53.28M</b><em>1.82x Avg</em></div>
      <div><span>Market Cap</span><b>${money(first((state.company?.profile || state.company || {}).market_cap, state.fundamental?.marketCap))}</b></div>
      <div><span>Active Tool</span><b>${esc(state.chartTool)}</b><em>${esc(toolStatusText())}</em></div>
    </div>
    <div class="chart-shell">
      <div class="indicator-list">
        <b>EMA 9</b><em>944.21</em>
        <b>EMA 20</b><em>942.11</em>
        <b>EMA 50</b><em>939.27</em>
        <b>VWAP</b><em>943.65</em>
        <b>Volume</b><em>1.24M</em>
      </div>
      <canvas id="chart" class="chart" data-testid="trading-chart"></canvas>
      <div id="charttip" class="charttip"></div>
    </div>
    <div id="chartReadout" class="chart-readout">Hover over a candle to inspect OHLC, volume, RSI and pattern context.</div>
    <div class="oscillator"><i></i><b>RSI (14)</b><span>MACD (12,26,9)</span></div>
  `);
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
  return card("Trade Setup", `
    <div class="setup-title"><div><strong>${esc(signal)} SETUP</strong><span>${signal === "BUY" ? "High Probability" : "Await confirmation"}</span></div><b>${num(a.setup_quality, 0)}<small>/100</small></b></div>
    ${rows({Trend: a.trend || "-", Momentum: a.momentum || "-", Volume: `${num(a.volume_ratio)}x`, VWAP: "Above", "RSI (14)": num(a.rsi), MACD: a.macd >= a.macd_signal ? "Bullish" : "Neutral"})}
    <div class="stars">★★★★☆</div>
  `);
}

function contextPanel() {
  const p = state.company?.profile || state.company || {};
  const a = state.analysis || {};
  return card("Market Context", rows({
    "Overall Market": "Bullish",
    QQQ: "Bullish",
    SPY: "Bullish",
    Sector: first(p.sector, "Semiconductors"),
    "Volatility (VIX)": "Moderate",
    "Market Regime": first(a.trend, "Trending"),
    Liquidity: "High",
  }));
}

function whyPanel() {
  const a = state.analysis || {};
  return card("Why This Trade?", `<p class="small-copy">${esc(a.pattern?.description || "The setup is monitored using price structure, volume, RSI, trend and validated support/resistance levels. Wait for confirmation before acting.")}</p>`);
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
  return card("Pattern Details", `
    <div class="pattern-name">${esc(pattern.name || "Pattern monitoring")}</div>
    <p class="small-copy">${esc(pattern.description || "No single high-confidence candle pattern dominates. Continue watching trend, volume and support/resistance confirmation.")}</p>
    ${rows({
      Confidence: pattern.confidence != null ? `${num(pattern.confidence, 0)}%` : "-",
      Trend: a.trend || "-",
      Momentum: a.momentum || "-",
      Volatility: a.volatility || "-",
      Invalidation: `Below ${money(a.levels?.stop)}`,
    })}
  `);
}

function livePricePanel() {
  const a = state.analysis || {};
  return card("Live Price", `<div class="mini-price">${money(a.price)} <em class="${a.change_pct < 0 ? "bad" : "good"}">${a.change_pct >= 0 ? "+" : ""}${pct(a.change_pct)}</em></div><div class="mini-spark"></div><div class="day-range"><i></i></div>`);
}

function aiPanel() {
  const a = state.analysis || {};
  return card("AI Insight Summary", `
    <ul class="ai-list">
      <li>Probability of continuation: ${num(first(a.setup_quality, 72), 0)}%</li>
      <li>Key support level: ${money(a.levels?.stop)}</li>
      <li>Key resistance level: ${money(a.levels?.target1)}</li>
      <li>Watch volume around key levels</li>
    </ul>
  `);
}

function impactCalendar() {
  const selected = calendarEvents();
  return card("Impact Calendar", `
    <div class="tabs">${CALENDAR_TABS.map((tab) => `<button class="${state.calendarTab === tab ? "active" : ""}" data-calendar-tab="${tab}">${tab}</button>`).join("")}</div>
    <div class="impact-list">${selected.map((event) => `<button class="impact-row ${event.level.toLowerCase()} ${state.selectedEvent === event.title ? "selected" : ""}" data-event="${esc(event.title)}"><b>${event.level}</b><span>${esc(event.title.replace("{ticker}", state.ticker))}<small>${esc(eventDateLabel(event))} · ${esc(event.time)}</small></span><em>${event.impact}</em></button>`).join("")}</div>
  `);
}

function eventImpact() {
  const event = eventByTitle(state.selectedEvent);
  return card("Event Impact Analysis", `
    <h4>${esc(event.title.replace("{ticker}", state.ticker))}</h4>
    <div class="event-meta"><span>${esc(event.level)}</span><span>${esc(event.category)}</span><span>${esc(eventDateLabel(event))}</span><span>${esc(event.time)}</span><span>${esc(event.impact)}</span></div>
    <p class="small-copy">${esc(event.scenario.replace("{ticker}", state.ticker))}</p>
  `);
}

function eventByTitle(title) {
  return EVENTS.find((event) => event.title === title) || EVENTS[0];
}

function calendarEvents() {
  const now = new Date();
  const upcoming = EVENTS.filter((event) => eventDateTime(event) >= new Date(now.getFullYear(), now.getMonth(), now.getDate()));
  const source = state.calendarTab === "Upcoming" ? upcoming : EVENTS;
  if (state.calendarTab === "All" || state.calendarTab === "Upcoming") return source;
  return source.filter((event) => event.category === state.calendarTab);
}

function eventDateTime(event) {
  const m = String(event.time || "").match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  let hour = m ? Number(m[1]) : 9;
  const minute = m ? Number(m[2]) : 0;
  const ap = m ? m[3].toUpperCase() : "AM";
  if (ap === "PM" && hour < 12) hour += 12;
  if (ap === "AM" && hour === 12) hour = 0;
  return new Date(`${event.date}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00-04:00`);
}

function todayLabel() {
  return new Date().toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric", year: "numeric"});
}

function eventDateLabel(event) {
  const d = eventDateTime(event);
  return d.toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric"});
}

function eventEta(event) {
  const diff = eventDateTime(event) - new Date();
  const abs = Math.abs(diff);
  const mins = Math.round(abs / 60000);
  if (diff < -6 * 3600000) return "completed";
  if (diff < 0) return "released";
  if (mins < 60) return `in ${mins}m`;
  if (mins < 1440) return `in ${Math.floor(mins / 60)}h ${mins % 60}m`;
  return `in ${Math.round(mins / 1440)}d`;
}

function mtfPanel() {
  const a = state.analysis || {};
  const rows = arr(a.mtf);
  const body = rows.length ? rows.map((r) => `<div class="mtf"><b>${esc(r.tf || r.label)}</b><span>${esc(r.data?.trend || r.trend || "-")}</span><em>${esc(r.data?.signal || r.signal || "WAIT")}</em></div>`).join("") : ["1D", "4H", "1H", "15m", "5m", "1m"].map((tf, i) => `<div class="mtf"><b>${tf}</b><span>${i < 5 ? "Bullish" : "Neutral"}</span><em>${i < 5 ? "Buy" : "Wait"}</em></div>`).join("");
  return card("Multi-Timeframe Analysis", body + `<div class="confidence"><i style="width:${Math.min(100, Number(first(a.setup_quality, 72)))}%"></i></div>`);
}

function modulePage(page) {
  const a = state.analysis || {};
  if (page === "Company Intelligence") return `<div class="module-hero"><span>360 Company Intelligence</span><h1>${esc(state.ticker)}</h1></div>${companyModule()}`;
  if (page === "Fundamentals") return `<div class="module-hero"><span>Fundamental Intelligence</span><h1>${esc(state.ticker)}</h1></div>${fundamentalModule()}`;
  if (page === "Technical") return `<div class="module-hero"><span>Technical Intelligence</span><h1>${esc(state.ticker)}</h1></div>${technicalModule()}`;
  if (page === "Decision") return decisionModule();
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
  const proofRows = EVENTS.map((event) => `<a class="proof-row" href="${esc(event.sourceUrl)}" target="_blank" rel="noreferrer"><b>${esc(eventDateLabel(event))}</b><span>${esc(event.title)}</span><em>${esc(event.time)} · ${esc(event.proof)}</em></a>`).join("");
  return `<div class="module-hero"><span>${esc(page)}</span><h1>${esc(state.ticker)}</h1><p>Evidence, dates, sources, and validation context for the current setup.</p></div>
    <div class="module-grid">${metric("Decision", decisionTier())}${metric("Timeframe", decisionTimeframe())}${metric("Pattern", a.pattern?.name || "-")}${metric("Updated", a.updated_at ? new Date(a.updated_at).toLocaleString() : "-")}</div>
    ${card("Research Validation", `<p class="small-copy">Evidence research and backtesting are validation layers. They do not rewrite the production BUY/SELL/WATCH decision; they show why the setup is or is not supported.</p>${rows({Trend: a.trend || "-", Momentum: a.momentum || "-", RSI: num(a.rsi), "Volume Ratio": `${num(a.volume_ratio)}x`, Support: money(a.support), Resistance: money(a.resistance)})}`)}
    ${card("Dates And Proofs", `<div class="proof-list">${proofRows}</div>`)}
    ${newsModule()}`;
}

function calendarPage() {
  return `<div class="module-hero"><span>Dated Market Events</span><h1>Impact Calendar</h1><p>Scheduled macro, Fed, earnings and market events with source links and expected stock impact.</p></div>
    ${impactCalendar()}${eventImpact()}
    ${card("Source Proofs", `<div class="proof-list">${EVENTS.map((event) => `<a class="proof-row ${event.level.toLowerCase()}" href="${esc(event.sourceUrl)}" target="_blank" rel="noreferrer"><b>${esc(eventDateLabel(event))}</b><span>${esc(event.title)}</span><em>${esc(event.time)} · ${esc(event.proof)}</em></a>`).join("")}</div>`)}`;
}

function technicalModule() {
  const a = state.analysis || {};
  return `${chartPanel()}${setupPanel()}${card("Technical Detail", rows({Trend: a.trend || "-", Momentum: a.momentum || "-", "Decision Tier": decisionTier(), "Approx Timeframe": decisionTimeframe(), Support: money(a.support), Resistance: money(a.resistance), ATR: money(a.atr), Pattern: a.pattern?.name || "-"}))}`;
}

function companyModule() {
  const p = state.company?.profile || state.company || {};
  const s = state.company?.scores || {};
  return `<div class="module-grid">${metric("Sector", p.sector)}${metric("Industry", p.industry)}${metric("Market Cap", money(first(p.market_cap, p.marketCap)))}${metric("Employees", p.employees?.toLocaleString?.())}${metric("Overall Score", num(s.overall_company_score, 1))}${metric("Financial Strength", num(s.financial_strength, 1))}</div>${card("Business Overview", `<p class="small-copy">${esc(p.description || p.summary || "Business summary unavailable from provider.")}</p>`)}`;
}

function fundamentalModule() {
  const f = state.fundamental || {};
  const p = f.profile || {};
  const v = f.valuation || {};
  return `<div class="module-grid">${metric("Fundamental Score", num(f.scores?.fundamental_score, 1))}${metric("Market Cap", money(first(p.market_cap, f.marketCap)))}${metric("P/E", num(first(v.trailing_pe, p.trailing_pe, f.trailingPE)))}${metric("Forward P/E", num(first(v.forward_pe, p.forward_pe, f.forwardPE)))}${metric("Revenue Growth", pct(Number(first(f.growth?.revenue_growth, f.revenueGrowth)) * 100))}${metric("EPS", money(first(f.earnings?.trailing_eps, f.epsTrailingTwelveMonths)))}</div>${insiderModule()}`;
}

function insiderModule() {
  const data = state.insiders || {};
  const items = arr(data.items).slice(0, 8);
  const holders = arr(data.holders).slice(0, 4);
  const body = items.length ? items.map((r) => `<div class="insider-row"><b>${esc(first(r.Insider, r.insider, r.Name, r.name, "Insider"))}</b><span>${esc(first(r.Transaction, r.transaction, r.Type, r.type, "Activity"))}</span><em>${esc(first(r.StartDate, r.Date, r.date, ""))}</em></div>`).join("") : `<div class="empty">No recent insider transaction rows returned by the provider.</div>`;
  const holderBody = holders.length ? `<div class="holder-list">${holders.map((r) => `<span>${esc(Object.values(r).filter(Boolean).slice(0, 2).join(" "))}</span>`).join("")}</div>` : "";
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
      <div><b>${esc(data.universe_size || "50")}</b><span>symbols checked</span></div>
      <div><b>Top ${items.length || 50}</b><span>ranked opportunities</span></div>
      <div><b>${esc(data.sector || state.scannerSector)}</b><span>selected sector</span></div>
      <div><b>${data.updated_at ? esc(new Date(data.updated_at).toLocaleTimeString()) : "-"}</b><span>last scan</span></div>
    </section>
    ${geopoliticalPanel()}
    ${state.scannerError ? `<div class="error"><b>Scanner error</b><span>${esc(state.scannerError)}</span></div>` : ""}
    ${state.scannerLoading && !items.length ? `<div class="state">Scanning articles, catalysts, volume and chart setups...</div>` : ""}
    <div class="scanner-grid">
      ${items.length ? items.map(scannerCard).join("") : `<div class="empty">Run the scanner to find catalyst-driven watchlist candidates.</div>`}
    </div>
    ${card("Scanner Method", `<p class="small-copy">${esc(data.method || "Ranks symbols by recent catalyst headlines, technical setup, momentum, volume expansion, and positive event language.")}</p><p class="small-copy">${esc(data.disclaimer || "Research signal only. This does not guarantee that the stock price will rise.")}</p>`)}
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
    <section class="scanner-thesis">
      <b>Why it can go up</b>
      <p>${esc(item.upside_thesis || why[0] || "The scanner found an early watchlist setup, but needs confirmation.")}</p>
    </section>
    <div class="scanner-detail">
      <div><b>Confirm</b>${confirms.map((x) => `<span>${esc(x)}</span>`).join("")}</div>
      <div><b>Risk</b>${risks.map((x) => `<span>${esc(x)}</span>`).join("")}</div>
    </div>
    <div class="scanner-next">
      <b>Approx Bullish Timeframe</b><span>${esc(item.estimated_bullish_timeframe || "Needs confirmation first")}</span>
      <b>Next Announcement / Product Progress</b><span>${esc(item.next_announcement_watch?.summary || item.product_progress_watch || "Watch next company update, product launch, filing, or earnings call.")}</span>
    </div>
    <ul>${why.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <div class="scanner-news">${articles.map((a) => `<a href="${esc(a.url || "#")}" target="_blank" rel="noreferrer">${esc(a.title || "Market headline")}</a>`).join("")}</div>
  </article>`;
}

async function runScanner() {
  state.scannerLoading = true;
  state.scannerError = "";
  renderContent();
  try {
    try {
      state.scanner = await api(`/market/trade-scanner?limit=50&sector=${encodeURIComponent(state.scannerSector)}`);
    } catch {
      state.scanner = await fallbackTradeScanner();
    }
  } catch (e) {
    state.scannerError = e.message || "Unable to scan trade opportunities.";
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
    try {
      state.geopolitical = await api("/market/geopolitics?limit=8");
    } catch {
      state.geopolitical = {items: GEOPOLITICS_FALLBACK, fallback: true};
    }
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
  if (!canvas || !dataAll.length) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const W = Math.max(900, rect.width);
  const H = Math.max(500, rect.height);
  canvas.width = Math.floor(W * dpr);
  canvas.height = Math.floor(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const visible = Math.max(45, Math.min(dataAll.length, Math.floor(dataAll.length / state.chartZoom)));
  const maxStart = Math.max(0, dataAll.length - visible);
  const start = Math.max(0, Math.min(maxStart, Math.floor(state.chartOffset)));
  const data = dataAll.slice(start, start + visible);
  const padL = 70, padR = 84, padT = 28, priceH = H * .68, volH = H * .16, oscY = priceH + volH + 34;
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
    drawLevel(ctx, "ENTRY ZONE", a.levels?.entry, "#2e8cff", W, padL, padR, y);
    drawLevel(ctx, "TARGET 1", a.levels?.target1, "#20e188", W, padL, padR, y);
    drawLevel(ctx, "TARGET 2", a.levels?.target2, "#20e188", W, padL, padR, y);
    drawLevel(ctx, "STOP LOSS", a.levels?.stop, "#ff5368", W, padL, padR, y);
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
    ctx.fillStyle = "#1fe36f";
    ctx.fillText("BREAKOUT", Math.max(padL + 20, lx - 110), Math.max(38, ly - 72));
    ctx.fillText("BUY SIGNAL", Math.max(padL + 20, lx - 300), Math.max(60, ly - 26));
  }

  ctx.strokeStyle = "#263f59";
  ctx.beginPath();
  ctx.moveTo(padL, oscY);
  ctx.lineTo(W - padR, oscY);
  ctx.stroke();
  ctx.strokeStyle = "#8d55ff";
  ctx.beginPath();
  for (let i = 0; i < data.length; i++) {
    const rsi = Number(first(data[i].rsi, 50 + Math.sin(i / 5) * 16));
    const yy = oscY + 55 - (rsi / 100) * 90;
    if (i) ctx.lineTo(x(i), yy); else ctx.moveTo(x(i), yy);
  }
  ctx.stroke();

  drawUserMarkers(ctx, W, H);

  bindChartPointer(canvas, data, x, y, W, padL, padR);
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

function drawLevel(ctx, label, value, color, W, padL, padR, y) {
  const v = Number(value);
  if (!Number.isFinite(v)) return;
  const yy = y(v);
  ctx.strokeStyle = color;
  ctx.setLineDash([9, 7]);
  ctx.beginPath();
  ctx.moveTo(padL, yy);
  ctx.lineTo(W - padR, yy);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = color;
  ctx.fillText(`${label} ${money(v)}`, W - padR - 132, yy - 6);
}

function bindChartPointer(canvas, data, x, y, W, padL, padR) {
  const tip = $("#charttip");
  const readout = $("#chartReadout");
  let drag = false, sx = 0, old = 0;
  const maxStart = Math.max(0, arr(state.analysis?.candles).length - data.length);
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
  canvas.onwheel = (e) => { e.preventDefault(); state.chartZoom = Math.max(1, Math.min(14, state.chartZoom * (e.deltaY < 0 ? 1.18 : .85))); state.chartOffset = Math.min(maxStart, state.chartOffset); drawChart(); };
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
    state.chartOffset = Math.max(0, Math.min(maxStart, old - (e.clientX - sx) * data.length / Math.max(120, W)));
    drawChart();
  };
  canvas.onpointerup = canvas.onpointercancel = () => { drag = false; canvas.style.cursor = "crosshair"; };
  canvas.ondblclick = () => { state.chartZoom = 1; state.chartOffset = 0; drawChart(); };
}

shell();
load(state.ticker, state.tf);
