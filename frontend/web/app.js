const API="http://127.0.0.1:8000/api/v1";
const state={ticker:"AAPL",tf:"6M",interval:"1d",period:"6mo",page:"Stock Analysis",analysis:null,news:[],macro:null,capital:10000,risk:1,stopPct:3,chartZoom:1,chartOffset:0};
const ICONS={
"Stock Analysis":`<svg viewBox="0 0 24 24"><path d="M3 17l5-6 4 3 7-8"/><path d="M17 6h2v2"/></svg>`,"Dashboard":`<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>`,"Company Intelligence":`<svg viewBox="0 0 24 24"><path d="M4 21V4h10v17M14 9h6v12M8 8h2M8 12h2M8 16h2M17 13h1M17 17h1"/></svg>`,"Fundamentals":`<svg viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-8M22 19V3"/></svg>`,"Technical":`<svg viewBox="0 0 24 24"><path d="M4 18l5-6 4 3 7-9"/><path d="M4 21h18"/></svg>`,"Decision":`<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>`,"Evidence Research":`<svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 10h6M10 7v6"/></svg>`,"Portfolio":`<svg viewBox="0 0 24 24"><path d="M3 8h18v12H3zM7 8V5h10v3M3 13h18"/></svg>`,"Risk":`<svg viewBox="0 0 24 24"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M9 12l2 2 4-4"/></svg>`,"Backtesting":`<svg viewBox="0 0 24 24"><path d="M5 6h14M5 12h10M5 18h7"/><path d="M19 15l3 3-3 3"/></svg>`,"News":`<svg viewBox="0 0 24 24"><path d="M4 4h16v16H4zM8 8h8M8 12h8M8 16h5"/></svg>`,"Watchlist":`<svg viewBox="0 0 24 24"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/></svg>`,"Alerts":`<svg viewBox="0 0 24 24"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>`,"Calendar":`<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>`,"Settings":`<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.8 1.8 0 0 0 .4 2l-1 1-2-1a1.8 1.8 0 0 0-2 .4l-.6 2.4h-2l-.6-2.4a1.8 1.8 0 0 0-2-.4l-2 1-1-1a1.8 1.8 0 0 0 .4-2 1.8 1.8 0 0 0-1.4-1.4L5.2 13v-2l2.4-.6A1.8 1.8 0 0 0 9 9l-.4-2 1-1 2 1a1.8 1.8 0 0 0 2-.4l.6-2.4h2l.6 2.4a1.8 1.8 0 0 0 2 .4l2-1 1 1-.4 2a1.8 1.8 0 0 0 1.4 1.4l2.4.6v2l-2.4.6A1.8 1.8 0 0 0 19.4 15z"/></svg>`};
const NAV=Object.keys(ICONS),$=s=>document.querySelector(s);
const money=x=>x==null||!Number.isFinite(Number(x))?"—":`$${Number(x).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(path){const r=await fetch(API+path);if(!r.ok)throw Error(`${r.status} ${await r.text()}`);return r.json()}
function toast(x){const e=document.createElement("div");e.className="toast";e.textContent=x;document.body.appendChild(e);setTimeout(()=>e.remove(),2400)}
function layout(){document.querySelector("#app").innerHTML=`<div class="app"><aside class="side"><div class="brand"><span class="brandmark">HQ</span><div><strong>HaViQuant</strong><small>360° TRADING INTELLIGENCE</small></div></div><div class="nav">${NAV.map(x=>`<button class="${x===state.page?"active":""}" data-nav="${esc(x)}" title="${esc(x)}">${ICONS[x]}<span>${esc(x)}</span></button>`).join("")}</div><div class="sidefoot">LIVE MARKET ENGINE<br><b>Yahoo Finance</b></div></aside><section class="main"><header class="top"><div class="search"><span class="searchicon">⌕</span><input id="ticker" value="${esc(state.ticker)}" maxlength="12" placeholder="Enter ticker e.g. NVDA"><button id="search">Analyze</button></div><div class="status" id="status">● CHECKING</div></header><div id="content" class="content"></div></section></div>`;document.querySelectorAll("[data-nav]").forEach(b=>b.onclick=()=>{state.page=b.dataset.nav;render()});$("#search").onclick=()=>load($("#ticker").value);$("#ticker").onkeydown=e=>{if(e.key==="Enter")load(e.target.value)};renderContent();healthStatus()}
function render(){layout()}
async function healthStatus(){try{await api("/health");if($("#status"))$("#status").textContent="● API LIVE"}catch(e){if($("#status"))$("#status").textContent="● API OFFLINE"}}
const RANGE={"1D":["1d","1d"],"1W":["1mo","1d"],"1M":["3mo","1d"],"3M":["6mo","1d"],"6M":["6mo","1d"]};
const INTRADAY={"1m":["7d","1m"],"5m":["60d","5m"],"15m":["60d","15m"],"1h":["60d","1h"],"4h":["60d","4h"]};
async function load(t,period=state.period,interval=state.interval){state.ticker=(t||"").trim().toUpperCase();if(!/^[A-Z0-9.-]{1,12}$/.test(state.ticker))return toast("Enter a valid ticker");state.page="Stock Analysis";state.analysis=null;state.period=period;state.interval=interval;state.chartZoom=1;state.chartOffset=0;render();$("#status").textContent="● LOADING";try{const [a,n,m]=await Promise.all([api(`/market/analysis?ticker=${encodeURIComponent(state.ticker)}&period=${encodeURIComponent(period)}&interval=${encodeURIComponent(interval)}&include_mtf=${interval==="1d"}`),api(`/market/news?ticker=${encodeURIComponent(state.ticker)}`),api(`/market/macro?ticker=${encodeURIComponent(state.ticker)}`)]);state.analysis=a;state.news=n.items||[];state.macro=m;$("#status").textContent="● API LIVE";renderContent()}catch(e){$("#status").textContent="● API ERROR";$("#content").innerHTML=`<div class="callout warning"><b>Market data error</b><br>${esc(e.message)}<br><br>Run <code>./start_all.sh</code> and refresh.</div>`}}
function card(title,body,cls=""){return `<div class="card ${cls}"><h3>${esc(title)}</h3><div class="body">${body}</div></div>`}
function metric(label,value,cls=""){return `<div class="metric ${cls}"><small>${esc(label)}</small><b>${esc(value)}</b></div>`}
function rows(obj){return Object.entries(obj).map(([k,v])=>`<div class="row"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}
function sentimentBadge(s){const x=s||{label:"Neutral",score:0,impact:"Low"};const c=x.label.toLowerCase();const dot=c==="positive"?"positive":c==="negative"?"negative":"neutral";return `<span class="sentiment ${dot}"><i></i>${esc(x.label.toUpperCase())}</span><span class="impact">${esc(x.impact||"Low")} IMPACT</span>`}
function newsItem(n){return `<div class="newsitem"><div class="newsline">${sentimentBadge(n.sentiment)}<span class="newsage">${esc(n.recency||"")}</span></div><a target="_blank" rel="noopener" href="${esc(n.url||"#")}">${esc(n.title)}</a><small>${esc(n.publisher||"")} · ${esc(n.published||n.published_iso||"")}</small></div>`}

function ciVal(v, fallback="—"){return v===null||v===undefined||v===""?fallback:typeof v==="number"?v.toLocaleString(undefined,{maximumFractionDigits:2}):String(v)}
function ciMoney(v){return v===null||v===undefined||!Number.isFinite(Number(v))?"—":money(v)}
function ciPct(v){if(v===null||v===undefined||!Number.isFinite(Number(v)))return "—";return `${(Number(v)*100).toFixed(2)}%`}
function ciTable(headers, rowsData){
  if(!Array.isArray(rowsData)||!rowsData.length)return `<div class="empty">No provider data returned.</div>`;
  return `<div class="tablewrap"><table class="ci-table"><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rowsData.map(r=>`<tr>${r.map(v=>`<td>${esc(ciVal(v))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function ciList(items){
  if(!Array.isArray(items)||!items.length)return `<div class="empty">No items returned.</div>`;
  return `<ul class="ci-list">${items.map(x=>`<li>${esc(typeof x==="string"?x:(x?.name||x?.description||x?.title||JSON.stringify(x)))}</li>`).join("")}</ul>`;
}
function ciScore(v){return v===null||v===undefined?"—":`${Number(v).toFixed(1)}/100`}
function renderCompanyIntelligence(x){
  const p=x?.profile||{}, q=x?.quarters||[], e=x?.earnings||{}, own=x?.ownership||{};
  const comp=x?.competition||{}, val=x?.valuation||{}, stock=x?.stock_level||{}, scores=x?.scores||{};
  const demand=x?.products_demand||{}, gov=x?.governance_ethics||{}, risks=x?.risks||{};
  const ownershipRows=(own.institutional_holders||[]).map(r=>[
    r.holder,r.shares,r.date_reported,ciMoney(r.value),r.pct_out==null?"—":ciPct(r.pct_out),r.pct_change==null?"—":ciPct(r.pct_change)
  ]);
  const insiderRows=(own.insider_transactions||[]).map(r=>[
    r.insider,r.relation,r.transaction,r.date,r.shares,ciMoney(r.value)
  ]);
  const purchaseRows=(own.insider_purchases||[]).map(r=>[
    r.insider,r.relation,r.transaction,r.date,r.shares,ciMoney(r.value)
  ]);
  const quarterRows=q.map(r=>[
    r.period||r.date||"—",ciMoney(r.revenue),ciMoney(r.net_income),
    r.revenue_qoq_pct==null?"—":`${Number(r.revenue_qoq_pct).toFixed(2)}%`,
    r.net_margin_pct==null?"—":`${Number(r.net_margin_pct).toFixed(2)}%`
  ]);
  return `
  <div class="ci-grid">
    ${card("Company Profile",rows({
      "Company":p.name||x.ticker,
      "Ticker":p.ticker||x.ticker,
      "Sector":p.sector,
      "Industry":p.industry,
      "Country":p.country,
      "Exchange":p.exchange,
      "Currency":p.currency,
      "Employees":p.employees==null?"—":Number(p.employees).toLocaleString(),
      "Market Cap":ciMoney(p.market_cap),
      "Website":p.website
    }))}
    ${card("Live Stock Level",rows({
      "Price":ciMoney(stock.price||x.live_quote?.price),
      "Previous Close":ciMoney(stock.previous_close||x.live_quote?.previous),
      "Change":ciMoney(stock.change||x.live_quote?.change),
      "Change %":x.live_quote?.change_pct==null?"—":`${Number(x.live_quote.change_pct).toFixed(2)}%`,
      "Beta":ciVal(stock.beta),
      "52W High":ciMoney(stock.fifty_two_week_high),
      "52W Low":ciMoney(stock.fifty_two_week_low)
    }))}
  </div>
  ${card("Business Overview",`<p class="ci-description">${esc(p.summary||p.description||"Business summary unavailable.")}</p>`)}
  <div class="ci-grid">
    ${card("Company Scores",rows({
      "Overall":ciScore(scores.overall_company_score),
      "Business Quality":ciScore(scores.business_quality),
      "Growth":ciScore(scores.growth_score),
      "Financial Strength":ciScore(scores.financial_strength),
      "Valuation":ciScore(scores.valuation_score),
      "Risk":ciScore(scores.risk)
    }))}
    ${card("Valuation",rows({
      "Analyst Target Reference":ciMoney(val.target_mean),
      "Current Price":ciMoney(val.current_price),
      "Reference Upside":val.reference_upside_pct==null?"—":`${Number(val.reference_upside_pct).toFixed(2)}%`,
      "P/S":ciVal(val.price_to_sales),
      "P/B":ciVal(val.price_to_book),
      "EV/Revenue":ciVal(val.enterprise_to_revenue),
      "EV/EBITDA":ciVal(val.enterprise_to_ebitda),
      "Trailing P/E":ciVal(p.trailing_pe),
      "Forward P/E":ciVal(p.forward_pe),
      "Profit Margin":ciPct(p.profit_margin),
      "ROE":ciPct(p.roe),
      "Revenue Growth":ciPct(p.revenue_growth),
      "Earnings Growth":ciPct(p.earnings_growth)
    }))}
  </div>
  ${card("Products & Demand",`
    <div class="ci-grid">
      ${rows({
        "Current Demand":demand.current_demand_proxy||demand.current_status||"—",
        "Future Demand":demand.future_demand?.status||demand.future_demand?.assessment||"—"
      })}
    </div>
    ${demand.future_demand?.note?`<div class="callout">${esc(demand.future_demand.note)}</div>`:""}
  `)}
  ${card("Quarterly Financials",ciTable(["Period","Revenue","Net Income","Revenue Growth","Net Margin"],quarterRows))}
  <div class="ci-grid">
    ${card("Earnings",rows({
      "Next Earnings":e.next_earnings,
      "Last Fiscal Year":e.last_fiscal_year,
      "Earnings Growth":e.earnings_growth_pct==null?"—":`${Number(e.earnings_growth_pct).toFixed(2)}%`,
      "Forward EPS":e.forward_eps,
      "Trailing EPS":e.trailing_eps
    }))}
    ${card("Backlog / Orders",typeof x.backlog==="object"?rows(x.backlog):`<p>${esc(ciVal(x.backlog))}</p>`)}
  </div>
  ${card("Institutional Ownership",ciTable(["Holder","Shares","Reported","Value","% Out","% Change"],ownershipRows))}
  ${card("Insider / Employee Purchase Activity",`
    <div class="callout">Provider-reported insider activity. Officers/directors and other reporting insiders are not automatically classified as ordinary employees.</div>
    ${ciTable(["Insider","Relation","Transaction","Date","Shares","Value"],purchaseRows)}
  `)}
  ${card("Insider Transactions",ciTable(["Insider","Relation","Transaction","Date","Shares","Value"],insiderRows))}
  ${card("Major Holders",ciTable(["Value","Category"],(own.major_holders||[]).map(r=>[r.value,r.label])))}
  ${card("Competition",typeof comp==="object"?`
    ${comp.summary?`<p class="ci-description">${esc(comp.summary)}</p>`:""}
    ${ciList(comp.competitors||comp.items||[])}
  `:ciList(comp))}
  <div class="ci-grid">
    ${card("Governance & Ethics",typeof gov==="object"?`
      ${rows({"Status":gov.status||"—","Filing Count":gov.filing_count??"—"})}
      ${gov.important_note?`<div class="callout">${esc(gov.important_note)}</div>`:""}
      ${ciList(gov.research_targets||[])}
    `:`<p>${esc(ciVal(gov))}</p>`)}
    ${card("Risks",typeof risks==="object"?`
      ${ciList(risks.items||risks.key_risks||[])}
      ${risks.summary?`<p class="ci-description">${esc(risks.summary)}</p>`:""}
    `:ciList(risks))}
  </div>
  ${card("Research Completeness",rows(x.research_status||{}))}
  ${card("Sources & Architecture",`
    ${rows(x.sources||{})}
    <div class="callout">Company Intelligence is separate from the production BUY/SELL Decision Engine. It does not silently change the trading signal.</div>
  `)}
  `;
}
function renderModule(page){const a=state.analysis||{};let html=`<div class="crumb">Command Center › ${esc(page)}</div><div class="hero"><div><div class="eyebrow">HA VI QUANT MODULE</div><h1>${esc(page)}</h1><p>Selected ticker: <b>${esc(state.ticker)}</b> · Dynamic data stays tied to the selected symbol.</p></div></div>`;
 if(page==="Dashboard")html+=`<div class="pagegrid">${metric("Ticker",state.ticker)}${metric("Price",money(a.price),"good")}${metric("Signal",a.signal||"—")}${metric("Setup quality",a.setup_quality?`${a.setup_quality}/100`:"—")}</div>${card("Market Snapshot",rows({"Trend":a.trend||"—","Momentum":a.momentum||"—","Volatility":a.volatility||"—","RSI":a.rsi?.toFixed?.(1)||"—","ATR":money(a.atr)}))}`;
 else if(page==="Company Intelligence")html+=`<div id="companyBox"><div class="callout">Loading full Company Intelligence…</div></div>`;
 else if(page==="Fundamentals")html+=card("Fundamental Snapshot",`<div id="fundBox">Loading fundamentals…</div>`);
 else if(page==="Technical")html+=card("Technical Engine",rows({"Trend":a.trend||"—","RSI":a.rsi?.toFixed?.(1)||"—","MACD":a.macd?.toFixed?.(2)||"—","ATR":money(a.atr),"Volume ratio":a.volume_ratio?`${a.volume_ratio.toFixed(2)}x`:"—","Pattern":a.pattern?.name||"—","Pattern confidence":a.pattern?.confidence!=null?`${a.pattern.confidence}%`:"—"}));
 else if(page==="Decision")html+=card("Decision Matrix",rows({"Signal":a.signal||"—","Setup quality":a.setup_quality?`${a.setup_quality}/100`:"—","Trend":a.trend||"—","Momentum":a.momentum||"—","Volatility":a.volatility||"—","Pattern":a.pattern?.name||"—"}))+tradeSummary();
 else if(page==="Evidence Research")html+=card("Evidence & Invalidation",`<p>Technical evidence comes from current OHLC/volume history.</p><p><b>Pattern:</b> ${esc(a.pattern?.description||"—")}</p><p><b>Invalidation:</b> A stop breach, trend reversal, volume deterioration, or material new information should trigger reassessment.</p>`);
 else if(page==="Portfolio")html+=card("Portfolio",`<div id="portfolioBox">Loading portfolio…</div>`);
 else if(page==="Risk")html+=card("Risk Controls",rows({"Entry":money(a.levels?.entry),"Stop":money(a.levels?.stop),"ATR":money(a.atr),"Daily stop (2% capital)":money(state.capital*.02),"Signal":a.signal||"—"}))+tradeSummary();
 else if(page==="Backtesting")html+=card("Backtesting Workspace",`<p>Historical candles are available for the selected ticker.</p><div class="callout">Backtests are not implemented as a broker-grade execution simulator in this package.</div>`);
 else if(page==="News")html+=card("Ticker News",state.news.length?state.news.map(newsItem).join(""):"No headlines returned.")+macroCards();
 else if(page==="Watchlist")html+=card("Watchlist",`<p>Selected ticker: <b>${esc(state.ticker)}</b></p><div class="watchchips">${["NVDA","AAPL","TSLA","MSFT","AMZN","GOOGL","SPY","QQQ"].map(t=>`<button class="chip" data-symbol="${t}">${t}</button>`).join("")}</div>`);
 else if(page==="Alerts")html+=card("Trade Alerts",rows({"Entry":money(a.levels?.entry),"Stop":money(a.levels?.stop),"Target 1":money(a.levels?.target1),"Target 2":money(a.levels?.target2),"Target 3":money(a.levels?.target3),"Current signal":a.signal||"—"}));
 else if(page==="Calendar")html+=card("Macro / Political Calendar",`<div class="calendarlegend"><span class="sentiment positive"><i></i>POSITIVE</span><span class="sentiment neutral"><i></i>NEUTRAL</span><span class="sentiment negative"><i></i>NEGATIVE</span></div><p>News-feed dates are publication dates. HaViQuant does not invent future event dates. Review Fed, jobs, inflation, political and geopolitical context before a trade.</p>`)+macroCards();
 else if(page==="Settings")html+=card("System",rows({"Frontend":"V26.1","Backend":"FastAPI + yfinance","API":"127.0.0.1:8000","Chart":"Interactive candlestick","Data":"Yahoo Finance","Sentiment":"Rule-based headline classifier"}));
 else html+=tradeSummary();
 $("#content").innerHTML=html;
 if(page==="Company Intelligence")api(`/company-intelligence/${encodeURIComponent(state.ticker)}?quarters=10`).then(x=>{const box=$("#companyBox");if(box)box.innerHTML=renderCompanyIntelligence(x)}).catch(e=>{const box=$("#companyBox");if(box)box.innerHTML=`<div class="callout warning"><b>Company Intelligence error</b><br>${esc(e.message)}</div>`});
 if(page==="Fundamentals")api(`/fundamental/${encodeURIComponent(state.ticker)}`).then(x=>$("#fundBox")&&( $("#fundBox").innerHTML=rows({"Market Cap":money(x.marketCap),"Trailing P/E":x.trailingPE??"—","Forward P/E":x.forwardPE??"—","EPS":x.epsTrailingTwelveMonths??"—","Revenue Growth":x.revenueGrowth!=null?`${(x.revenueGrowth*100).toFixed(1)}%`:"—","Profit Margin":x.profitMargins!=null?`${(x.profitMargins*100).toFixed(1)}%`:"—","ROE":x.returnOnEquity!=null?`${(x.returnOnEquity*100).toFixed(1)}%`:"—","Beta":x.beta??"—"}))).catch(e=>$("#fundBox").innerHTML=`<div class="callout warning">${esc(e.message)}</div>`);
 if(page==="Portfolio")api(`/portfolio`).then(x=>$("#portfolioBox")&&($("#portfolioBox").innerHTML=rows({"Status":x.status||"—","Cash":money(x.cash),"Positions":x.positions?.length??0,"Engine":x.engine||"—"}))).catch(e=>$("#portfolioBox").innerHTML=`<div class="callout warning">${esc(e.message)}</div>`);
 if(page==="Watchlist")setTimeout(()=>document.querySelectorAll("[data-symbol]").forEach(b=>b.onclick=()=>load(b.dataset.symbol)),0);
}
function macroCards(){const m=state.macro||{};return `<div class="twocol">${card("Geopolitical",feed(m.geopolitical))}${card("Politics",feed(m.politics))}${card("Macro",feed(m.macro))}</div>`}
function feed(arr){return (arr||[]).slice(0,6).map(newsItem).join("")||"No feed items."}
function tradeSummary(){const a=state.analysis||{};return card("Trade Plan Summary",rows({"Entry":money(a.levels?.entry),"Stop":money(a.levels?.stop),"Target 1":money(a.levels?.target1),"Target 2":money(a.levels?.target2),"Target 3":money(a.levels?.target3),"T1 ETA":a.eta_days?.target1?`${a.eta_days.target1} trading day(s)`:"—","T2 ETA":a.eta_days?.target2?`${a.eta_days.target2} trading day(s)`:"—","T3 ETA":a.eta_days?.target3?`${a.eta_days.target3} trading day(s)`:"—"}))}
function mtfRow(r){const d=r.data||{};return `<div class="mtfrow mtfdetail"><b>${esc(r.tf)}</b><span>${esc(r.label)}</span><span>${esc(d.trend||"—")}</span><span>${esc(d.signal||"WAIT")}</span><strong>${d.rsi==null?"—":Number(d.rsi).toFixed(1)}</strong><small>${d.pattern?esc(d.pattern):"—"}</small></div>`}
function renderAnalysis(){const a=state.analysis;if(!a){$("#content").innerHTML=`<div class="callout">Loading live market data for <b>${esc(state.ticker)}</b>…</div>`;return}const ch=a.candles||[];const ranges=Object.keys(RANGE),intraday=Object.keys(INTRADAY);
 $("#content").innerHTML=`<div class="crumb">Command Center › Stock Analysis</div><div class="hero"><div><div class="eyebrow">MARKET INTELLIGENCE TERMINAL</div><h1>${esc(a.ticker)}</h1><div class="price">${money(a.price)} <span class="${a.change_pct>=0?"up":"down"}">${a.change_pct>=0?"+":""}${a.change_pct.toFixed(2)}%</span><span class="livebadge">● LIVE</span></div></div><button class="primary" id="refresh">↻ Refresh</button></div><div class="grid"><main>${card("Interactive Trading Chart",`<div class="chartsection"><div class="chartlabel">Range</div><div class="tfrow">${ranges.map(x=>`<button class="tf ${state.tf===x?"active":""}" data-range="${x}">${x}</button>`).join("")}</div><div class="chartlabel">Intraday timeframe</div><div class="tfrow">${intraday.map(x=>`<button class="tf ${state.interval===INTRADAY[x][1]?"active":""}" data-intraday="${x}">${x}</button>`).join("")}<button class="tf" id="resetChart">Reset View</button></div><div class="legend"><span>● UP</span><span>● DOWN</span><span>— ENTRY</span><span>— TARGETS</span><span>— STOP</span></div><div class="chartwrap"><canvas id="chart" class="chart"></canvas><div id="charttip" class="charttip"></div></div></div>`)}${card("Multi-Timeframe Confluence",(a.mtf||[]).map(mtfRow).join("")||"No intraday confluence available.")}${card("360° Trade Plan Calculator",`<div class="callout infoBox"><b>How this works</b><br>Capital = maximum amount available. Risk budget = maximum planned loss if the stop is hit. Stop distance = percentage from entry to stop. Position size is limited by both capital and risk.</div><div class="tradegrid"><div class="field"><label>Capital ($) <span class="info" title="Total capital allocated to this trade.">ⓘ</span></label><input id="capital" type="number" value="${state.capital}" min="0" step="100"></div><div class="field"><label>Risk budget (%) <span class="info" title="Maximum percentage of your capital you are willing to risk if the stop is hit.">ⓘ</span></label><input id="riskpct" type="number" value="${state.risk}" min="0.1" max="20" step="0.1"></div><div class="field"><label>Stop distance (%) <span class="info" title="Distance from entry price to the planned stop-loss.">ⓘ</span></label><input id="stoppct" type="number" value="${state.stopPct}" min="0.5" max="50" step="0.5"></div></div><div id="calc"></div>`)}</main><aside>${card("Trade Plan",`<div class="levels"><div class="level"><small>ENTRY</small><b>${money(a.levels.entry)}</b></div><div class="level stop"><small>STOP LOSS</small><b>${money(a.levels.stop)}</b></div><div class="level target"><small>TARGET 1</small><b>${money(a.levels.target1)}</b></div><div class="level target"><small>TARGET 2</small><b>${money(a.levels.target2)}</b></div><div class="level target"><small>TARGET 3</small><b>${money(a.levels.target3)}</b></div></div><div class="callout">Estimated time: T1 <b>${a.eta_days.target1}d</b> · T2 <b>${a.eta_days.target2}d</b> · T3 <b>${a.eta_days.target3}d</b><br><small>ATR-based estimate; not a guarantee.</small></div>`)}${card("Market Context",rows({"Trend":a.trend,"Momentum":a.momentum,"Volatility":a.volatility,"Volume":`${a.volume_ratio.toFixed(2)}x`,"RSI":a.rsi.toFixed(1),"Interval":a.interval}))}${card("Pattern Radar",`<div class="pattern">${esc(a.pattern.name)}</div><p>${esc(a.pattern.description)}</p><div class="metric"><small>Confidence</small><b>${a.pattern.confidence}%</b></div>`)}</aside></div>`;
 document.querySelectorAll("[data-range]").forEach(b=>b.onclick=()=>{state.tf=b.dataset.range;const p=RANGE[state.tf];load(state.ticker,p[0],p[1])});document.querySelectorAll("[data-intraday]").forEach(b=>b.onclick=()=>{const x=INTRADAY[b.dataset.intraday];state.tf=b.dataset.intraday;load(state.ticker,x[0],x[1])});$("#refresh").onclick=()=>load(state.ticker,state.period,state.interval);$("#resetChart").onclick=()=>{state.chartZoom=1;state.chartOffset=0;drawChart()};$("#capital").oninput=calc;$("#riskpct").oninput=calc;$("#stoppct").oninput=calc;calc();drawChart()}
function calc(){const a=state.analysis;if(!a)return;state.capital=Math.max(0,Number($("#capital").value)||0);state.risk=Math.max(.1,Math.min(20,Number($("#riskpct").value)||.1));state.stopPct=Math.max(.5,Math.min(50,Number($("#stoppct").value)||.5));const price=a.price;if(state.capital<=0||price<=0){$("#calc").innerHTML=`<div class="callout warning">Enter capital greater than $0 to calculate position size.</div>`;return}const sharesAvail=Math.floor(state.capital/price),riskBudget=state.capital*state.risk/100,riskPer=price*state.stopPct/100,sharesRisk=Math.floor(riskBudget/riskPer),shares=Math.max(0,Math.min(sharesAvail,sharesRisk)),used=shares*price,loss=shares*riskPer,t1=shares*(a.levels.target1-price),t2=shares*(a.levels.target2-price),t3=shares*(a.levels.target3-price),rr1=riskPer?(a.levels.target1-price)/riskPer:0,rr2=riskPer?(a.levels.target2-price)/riskPer:0,rr3=riskPer?(a.levels.target3-price)/riskPer:0,daily=state.capital*.02;let explanation=shares===0?`No whole share fits both capital and risk limits. Increase capital/risk budget or reduce stop distance.`:`You are risking about ${money(loss)} of your ${money(state.capital)} capital.`;$("#calc").innerHTML=`<div class="calc">${metric("Capital",money(state.capital))}${metric("Entry price",money(price))}${metric("Shares",shares)}${metric("Capital used",money(used))}${metric("Risk / share",money(riskPer),"bad")}${metric("Maximum loss",money(loss),"bad")}${metric("Target 1 profit",money(t1),"good")}${metric("Target 2 profit",money(t2),"good")}${metric("Target 3 profit",money(t3),"good")}${metric("R/R T1",`1 : ${rr1.toFixed(2)}`)}${metric("R/R T2",`1 : ${rr2.toFixed(2)}`)}${metric("R/R T3",`1 : ${rr3.toFixed(2)}`)}${metric("Suggested daily stop",money(daily),"bad")}</div><div class="callout ${loss>daily?"warning":""}"><b>${esc(a.signal)}</b> · Risk budget ${money(riskBudget)}. ${esc(explanation)}<br><small>News, macro, geopolitical and political context should be reassessed immediately before entry. No model can guarantee a target or timing.</small></div>`}
function drawChart(){
 const c=$("#chart"); if(!c||!state.analysis)return;
 const ctx=c.getContext("2d"),rect=c.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
 const W=Math.max(600,rect.width),H=Math.max(330,rect.height);
 c.width=Math.floor(W*dpr);c.height=Math.floor(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
 const ch=state.analysis.candles||[]; if(!ch.length)return;
 const visible=Math.max(25,Math.min(ch.length,Math.floor(ch.length/state.chartZoom)));
 const maxStart=Math.max(0,ch.length-visible);
 const start=Math.max(0,Math.min(maxStart,Math.floor(state.chartOffset)));
 const data=ch.slice(start,start+visible);
 const min=Math.min(...data.map(x=>x.low),state.analysis.levels.stop);
 const max=Math.max(...data.map(x=>x.high),state.analysis.levels.target3);
 const pad=52, right=18, topPad=24, bottomPad=34;
 const x=i=>pad+i*(W-pad-right)/Math.max(1,data.length-1);
 const y=v=>H-bottomPad-(v-min)/(max-min||1)*(H-topPad-bottomPad);
 ctx.clearRect(0,0,W,H);
 ctx.fillStyle="#071522";ctx.fillRect(0,0,W,H);
 ctx.strokeStyle="#173b52";ctx.fillStyle="#6f8da2";ctx.font="11px system-ui";
 for(let i=0;i<6;i++){
   const yy=topPad+i*(H-topPad-bottomPad)/5;
   ctx.beginPath();ctx.moveTo(pad,yy);ctx.lineTo(W-right,yy);ctx.stroke();
   ctx.fillText((max-(max-min)*i/5).toFixed(2),4,yy+4);
 }
 const bw=Math.max(2,Math.min(12,(W-pad-right)/data.length*.68));
 data.forEach((r,i)=>{
   const xx=x(i),up=r.close>=r.open;
   ctx.strokeStyle=up?"#41e0b2":"#ff6577";ctx.fillStyle=ctx.strokeStyle;
   ctx.beginPath();ctx.moveTo(xx,y(r.high));ctx.lineTo(xx,y(r.low));ctx.stroke();
   const top=y(Math.max(r.open,r.close)),bot=y(Math.min(r.open,r.close));
   ctx.fillRect(xx-bw/2,top,bw,Math.max(2,bot-top));
 });
 const levels=[
   ["ENTRY",state.analysis.levels.entry,"#41e0b2"],
   ["T1",state.analysis.levels.target1,"#f4c75a"],
   ["T2",state.analysis.levels.target2,"#f4c75a"],
   ["T3",state.analysis.levels.target3,"#f4c75a"],
   ["STOP",state.analysis.levels.stop,"#ff6577"]
 ];
 levels.forEach(z=>{
   ctx.strokeStyle=z[2];ctx.setLineDash([6,5]);ctx.beginPath();ctx.moveTo(pad,y(z[1]));ctx.lineTo(W-right,y(z[1]));ctx.stroke();ctx.setLineDash([]);
   ctx.fillStyle=z[2];ctx.fillText(`${z[0]} ${money(z[1])}`,Math.max(pad,W-150),y(z[1])-5);
 });
 const tip=$("#charttip");
 const showTip=(e)=>{
   const rr=c.getBoundingClientRect(),mx=e.clientX-rr.left,my=e.clientY-rr.top;
   const i=Math.max(0,Math.min(data.length-1,Math.round((mx-pad)/(W-pad-right)*(data.length-1))));
   const r=data[i]; if(!r||!tip)return;
   tip.style.display="block";tip.style.left=Math.min(W-220,Math.max(8,mx+12))+"px";tip.style.top=Math.max(8,my-82)+"px";
   tip.innerHTML=`<b>${new Date(r.time).toLocaleString()}</b><br>O ${Number(r.open).toFixed(2)} · H ${Number(r.high).toFixed(2)}<br>L ${Number(r.low).toFixed(2)} · C ${Number(r.close).toFixed(2)}<br>Vol ${Number(r.volume).toLocaleString()}<br>RSI ${r.rsi==null?"—":Number(r.rsi).toFixed(1)} · Vol ${r.vol_ratio==null?"—":Number(r.vol_ratio).toFixed(2)}x`;
 };
 c.onmousemove=showTip;
 c.onmouseleave=()=>{if(tip)tip.style.display="none";};
 c.onwheel=e=>{e.preventDefault();state.chartZoom=Math.max(1,Math.min(12,state.chartZoom*(e.deltaY<0?1.18:.85)));state.chartOffset=Math.min(maxStart,state.chartOffset);drawChart();};
 let drag=false,sx=0,old=0;
 c.onpointerdown=e=>{drag=true;sx=e.clientX;old=state.chartOffset;c.setPointerCapture?.(e.pointerId);c.style.cursor="grabbing";};
 c.onpointermove=e=>{
   if(drag){
     state.chartOffset=Math.max(0,Math.min(maxStart,old-(e.clientX-sx)*data.length/Math.max(120,W)));
     drawChart();
   }else showTip(e);
 };
 c.onpointerup=c.onpointercancel=()=>{drag=false;c.style.cursor="crosshair";};
 c.ondblclick=()=>{state.chartZoom=1;state.chartOffset=0;drawChart();};
 if(!c.dataset.resizeBound){
   c.dataset.resizeBound="1";
   window.addEventListener("resize",()=>{if($("#chart"))drawChart();});
 }
 c.style.cursor="crosshair";
}

function renderContent(){if(state.page==="Stock Analysis")renderAnalysis();else renderModule(state.page)}
load(state.ticker);
