import React, {useCallback, useEffect, useState} from "react";
import {
  ActivityIndicator,
  Linking,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {Ionicons} from "@expo/vector-icons";

type AnyRecord = Record<string, any>;
type Page =
  | "Dashboard"
  | "Stock Analysis"
  | "Company Intelligence"
  | "Fundamentals"
  | "Technical"
  | "Decision"
  | "Evidence Research"
  | "Portfolio"
  | "Risk"
  | "Backtesting"
  | "News";

const API = (
  process.env.EXPO_PUBLIC_API_URL || "https://haviquant-1.onrender.com/api/v1"
).replace(/\/$/, "");

const NAV: {id: Page; icon: keyof typeof Ionicons.glyphMap}[] = [
  {id: "Dashboard", icon: "grid-outline"},
  {id: "Stock Analysis", icon: "trending-up-outline"},
  {id: "Company Intelligence", icon: "business-outline"},
  {id: "Fundamentals", icon: "bar-chart-outline"},
  {id: "Technical", icon: "pulse-outline"},
  {id: "Decision", icon: "flash-outline"},
  {id: "Evidence Research", icon: "flask-outline"},
  {id: "Portfolio", icon: "wallet-outline"},
  {id: "Risk", icon: "shield-checkmark-outline"},
  {id: "Backtesting", icon: "analytics-outline"},
  {id: "News", icon: "newspaper-outline"},
];

function isObj(value: any): value is AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value);
}

function arr(value: any): any[] {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  if (isObj(value)) {
    for (const key of [
      "items",
      "rows",
      "results",
      "records",
      "values",
      "data",
      "positions",
      "findings",
      "issues",
      "risks",
      "competitors",
      "quarters",
      "sources",
      "news",
    ]) {
      if (Array.isArray(value[key])) return value[key];
    }
    return [value];
  }
  return [value];
}

function first(...values: any[]) {
  return values.find((value) => value !== null && value !== undefined && value !== "");
}

function text(value: any) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function num(value: any, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "-";
}

function pct(value: any) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : "-";
}

function money(value: any) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toLocaleString(undefined, {maximumFractionDigits: 2})}`;
}

async function api(path: string, token?: string | null) {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API}${path}`, {headers});
  const body = await response.text();
  const data = parseJson(body);

  if (!response.ok) {
    throw new Error(data?.detail || body || `API request failed (${response.status})`);
  }

  return data;
}

async function postApi(path: string, body: AnyRecord, token?: string | null) {
  const headers: Record<string, string> = {"Content-Type": "application/json"};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API}${path}`, {
    body: JSON.stringify(body),
    headers,
    method: "POST",
  });
  const raw = await response.text();
  const data = parseJson(raw);

  if (!response.ok) {
    throw new Error(data?.detail || raw || `API request failed (${response.status})`);
  }

  return data;
}

function parseJson(raw: string) {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function normalizeAnalysis(data: AnyRecord) {
  const quote = {
    price: first(data.price, data.quote?.price),
    change_pct: first(data.change_pct, data.quote?.change_pct, data.quote?.change_percent),
    updated_at: data.updated_at,
  };

  const technical = {
    price: quote.price,
    sma_20: first(data.sma_20, data.sma20, data.SMA20),
    sma_50: first(data.sma_50, data.sma50, data.SMA50),
    sma_200: first(data.sma_200, data.sma200, data.SMA200),
    rsi: first(data.rsi, data.rsi14, data.RSI14),
    macd: data.macd,
    macd_signal: data.macd_signal,
    volume_ratio: data.volume_ratio,
    trend: data.trend,
    momentum: data.momentum,
    volatility: data.volatility,
    pattern: data.pattern,
    mtf: data.mtf,
  };

  const decision = {
    action: first(data.action, data.signal),
    signal: data.signal,
    technical_score: first(data.technical_score, data.setup_quality),
    confidence: first(data.confidence, data.setup_quality),
    rationale: data.pattern?.description || "Production decision engine output is isolated from research validation.",
  };

  return {
    ...data,
    quote,
    technical,
    decision,
    chart: arr(first(data.chart, data.candles, data.rows)),
  };
}

function useWorkspace(ticker: string) {
  const [data, setData] = useState<AnyRecord>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [analysisResult, companyResult, fundamentalResult, planResult, newsResult, macroResult] =
        await Promise.allSettled([
          api(`/market/analysis?ticker=${encodeURIComponent(ticker)}&period=6mo&interval=1d&include_mtf=true`),
          api(`/company-intelligence/${encodeURIComponent(ticker)}`),
          api(`/fundamental/${encodeURIComponent(ticker)}`),
          api(`/trade-plan?ticker=${encodeURIComponent(ticker)}`),
          api(`/market/news?ticker=${encodeURIComponent(ticker)}`),
          api(`/market/macro?ticker=${encodeURIComponent(ticker)}`),
        ]);

      if (analysisResult.status !== "fulfilled") throw analysisResult.reason;

      setData({
        analysis: normalizeAnalysis(analysisResult.value || {}),
        company: companyResult.status === "fulfilled" ? companyResult.value || {} : {},
        fundamental: fundamentalResult.status === "fulfilled" ? fundamentalResult.value || {} : {},
        tradePlan: planResult.status === "fulfilled" ? planResult.value || {} : {},
        news: newsResult.status === "fulfilled" ? newsResult.value || {} : {},
        macro: macroResult.status === "fulfilled" ? macroResult.value || {} : {},
      });
    } catch (e: any) {
      setError(e?.message || "Unable to load HaViQuant intelligence.");
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    load();
  }, [load]);

  return {data, loading, error, reload: load};
}

export default function App() {
  const [ticker, setTicker] = useState("NVDA");
  const [input, setInput] = useState("NVDA");
  const [page, setPage] = useState<Page>("Dashboard");
  const [token, setToken] = useState<string | null>(null);
  const {data, loading, error, reload} = useWorkspace(ticker);

  const submitTicker = () => {
    const clean = input.trim().toUpperCase();
    if (!clean) return;
    setTicker(clean);
    setPage("Stock Analysis");
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" />
      <View style={styles.topbar}>
        <View style={styles.brandRow}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>HQ</Text>
          </View>
          <View style={styles.brandText}>
            <Text style={styles.eyebrow}>MARKET INTELLIGENCE TERMINAL</Text>
            <Text style={styles.title}>HaViQuant</Text>
            <Text style={styles.subtitle}>360° Investment Intelligence</Text>
          </View>
        </View>
        <View style={styles.livePill}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      <View style={styles.search}>
        <Ionicons name="search-outline" size={18} color="#7087a3" />
        <TextInput
          autoCapitalize="characters"
          autoCorrect={false}
          onChangeText={(value) => setInput(value.toUpperCase())}
          onSubmitEditing={submitTicker}
          placeholder="Ticker (e.g. NVDA)"
          placeholderTextColor="#52677f"
          returnKeyType="search"
          style={styles.input}
          value={input}
        />
        <TouchableOpacity accessibilityLabel="Analyze ticker" onPress={submitTicker} style={styles.iconButton}>
          <Ionicons name="trending-up-outline" size={18} color="#7de6ff" />
        </TouchableOpacity>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.nav} contentContainerStyle={styles.navContent}>
        {NAV.map((item) => (
          <TouchableOpacity key={item.id} onPress={() => setPage(item.id)} style={[styles.navItem, page === item.id && styles.navItemActive]}>
            <Ionicons name={item.icon} size={17} color={page === item.id ? "#58d7ff" : "#8094ad"} />
            <Text style={[styles.navText, page === item.id && styles.navTextActive]}>{item.id}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
        <View style={styles.pageHead}>
          <Text style={styles.pageTitle}>{page}</Text>
          <TouchableOpacity onPress={reload} style={styles.refresh}>
            <Ionicons name="refresh-outline" size={16} color="#b9cbe0" />
            <Text style={styles.refreshText}>Refresh</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <Loading label="Loading V26.2 intelligence..." />
        ) : error ? (
          <ErrorBox error={error} retry={reload} />
        ) : (
          <PageContent data={data} page={page} setPage={setPage} ticker={ticker} token={token} setToken={setToken} />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function PageContent({
  data,
  page,
  setPage,
  ticker,
  token,
  setToken,
}: {
  data: AnyRecord;
  page: Page;
  setPage: (page: Page) => void;
  ticker: string;
  token: string | null;
  setToken: (token: string | null) => void;
}) {
  const analysis = data.analysis || {};
  const company = data.company || {};
  const fundamental = data.fundamental || {};
  const tradePlan = data.tradePlan || {};
  const news = data.news || {};
  const macro = data.macro || {};
  const profile = company.profile || company || {};

  if (page === "Dashboard") {
    return (
      <>
        <Hero ticker={ticker} name={profile.name} badge="360° LIVE INTELLIGENCE" />
        <MetricGrid
          items={[
            ["Live Price", money(analysis.quote?.price)],
            ["Change", pct(analysis.quote?.change_pct)],
            ["Technical Score", num(analysis.decision?.technical_score, 1)],
            ["Decision", analysis.decision?.action || "WATCH"],
          ]}
        />
        <ChartPanel rows={analysis.chart} ticker={ticker} />
        <Panel title="Technical Snapshot">
          <TechnicalCards analysis={analysis} />
        </Panel>
        <Panel title="Production Decision">
          <DecisionBox decision={analysis.decision} />
        </Panel>
        <TouchableOpacity onPress={() => setPage("Stock Analysis")} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Open Stock Analysis</Text>
          <Ionicons name="chevron-forward-outline" size={16} color="#7de6ff" />
        </TouchableOpacity>
      </>
    );
  }

  if (page === "Stock Analysis") {
    return (
      <>
        <Hero ticker={ticker} name={profile.name} badge="STOCK ANALYSIS · ENGINE CONNECTED" />
        <MetricGrid
          items={[
            ["Price", money(analysis.quote?.price)],
            ["Technical Score", num(analysis.decision?.technical_score, 1)],
            ["Fundamental Score", num(first(fundamental.scores?.fundamental_score, company.scores?.overall_company_score), 1)],
            ["Market Cap", money(first(profile.market_cap, profile.marketCap, fundamental.marketCap))],
            ["Decision", analysis.decision?.action || "WATCH"],
          ]}
        />
        <ChartPanel rows={analysis.chart} ticker={ticker} />
        <Panel title="Technical Intelligence">
          <TechnicalCards analysis={analysis} />
        </Panel>
        <FundamentalPanel company={company} fundamental={fundamental} />
        <Panel title="Evidence Research · Validation">
          <Text style={styles.noticeText}>Research is isolated from the production BUY/SELL decision.</Text>
        </Panel>
      </>
    );
  }

  if (page === "Company Intelligence") return <CompanyPage company={company} ticker={ticker} />;
  if (page === "Fundamentals") return <FundamentalsPage company={company} fundamental={fundamental} ticker={ticker} />;
  if (page === "Technical") return <TechnicalPage analysis={analysis} ticker={ticker} />;
  if (page === "Decision") return <DecisionPage analysis={analysis} tradePlan={tradePlan} ticker={ticker} />;
  if (page === "Evidence Research") return <ResearchPage macro={macro} news={news} ticker={ticker} />;
  if (page === "Portfolio") return <AuthPortfolio token={token} setToken={setToken} />;
  if (page === "Risk") return <RiskPage token={token} />;
  if (page === "Backtesting") return <BacktestingPage analysis={analysis} macro={macro} ticker={ticker} />;
  return <NewsPage news={news} ticker={ticker} />;
}

function Hero({ticker, name, badge}: {ticker: string; name?: string; badge: string}) {
  return (
    <View style={styles.hero}>
      <Text style={styles.badge}>{badge}</Text>
      <Text style={styles.heroTicker}>{ticker}</Text>
      <Text style={styles.heroName}>{name || "Market data, intelligence engines, portfolio context and research validation in one workspace."}</Text>
    </View>
  );
}

function Loading({label}: {label: string}) {
  return (
    <View style={styles.stateBox}>
      <ActivityIndicator color="#55d9ff" />
      <Text style={styles.stateText}>{label}</Text>
    </View>
  );
}

function ErrorBox({error, retry}: {error: string; retry: () => void}) {
  return (
    <View style={styles.errorBox}>
      <Text style={styles.errorTitle}>Data error</Text>
      <Text style={styles.errorText}>{error}</Text>
      <TouchableOpacity onPress={retry} style={styles.retryButton}>
        <Text style={styles.retryText}>Retry</Text>
      </TouchableOpacity>
    </View>
  );
}

function EmptyState({label}: {label: string}) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyText}>{label}</Text>
    </View>
  );
}

function Panel({title, children}: {title: string; children: React.ReactNode}) {
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>{title}</Text>
      {children}
    </View>
  );
}

function MetricGrid({items}: {items: [string, any][]}) {
  return (
    <View style={styles.cards}>
      {items.map(([label, value]) => (
        <View key={label} style={styles.card}>
          <Text style={styles.cardLabel}>{label}</Text>
          <Text numberOfLines={2} adjustsFontSizeToFit style={styles.cardValue}>
            {value ?? "-"}
          </Text>
        </View>
      ))}
    </View>
  );
}

function ChartPanel({rows, ticker}: {rows: any[]; ticker: string}) {
  const closes = arr(rows).map((row) => Number(row.close)).filter(Number.isFinite);
  const visible = closes.slice(-36);
  const min = visible.length ? Math.min(...visible) : 0;
  const max = visible.length ? Math.max(...visible) : 1;
  const span = max - min || 1;

  return (
    <Panel title={`Market Chart · ${ticker}`}>
      {visible.length ? (
        <>
          <View style={styles.spark}>
            {visible.map((price, index) => (
              <View
                key={`${price}-${index}`}
                style={[
                  styles.sparkBar,
                  {
                    height: 24 + ((price - min) / span) * 110,
                    backgroundColor: index === visible.length - 1 ? "#d9fbff" : "#42d7ff",
                  },
                ]}
              />
            ))}
          </View>
          <View style={styles.chartMeta}>
            <Text style={styles.metaText}>{visible.length} observations</Text>
            <Text style={styles.metaText}>Range {money(min)} to {money(max)}</Text>
          </View>
        </>
      ) : (
        <EmptyState label="No historical price rows returned." />
      )}
    </Panel>
  );
}

function TechnicalCards({analysis}: {analysis: AnyRecord}) {
  const t = analysis.technical || {};
  return (
    <MetricGrid
      items={[
        ["Price", money(first(t.price, analysis.quote?.price))],
        ["SMA 20", money(first(t.sma_20, t.sma20))],
        ["SMA 50", money(first(t.sma_50, t.sma50))],
        ["SMA 200", money(first(t.sma_200, t.sma200))],
        ["RSI", num(t.rsi)],
        ["MACD", num(t.macd)],
        ["MACD Signal", num(t.macd_signal)],
        ["Volume Ratio", num(t.volume_ratio)],
      ]}
    />
  );
}

function DecisionBox({decision}: {decision: AnyRecord}) {
  return (
    <View>
      <Text style={styles.decisionMain}>{decision?.action || decision?.signal || "WATCH"}</Text>
      <ValueRow label="Technical Score" value={num(first(decision?.technical_score, decision?.score), 1)} />
      <ValueRow label="Confidence" value={num(decision?.confidence, 1)} />
      <Text style={styles.longText}>{text(decision?.rationale || "Production decision engine output is preserved separately from research validation.")}</Text>
    </View>
  );
}

function CompanyPage({company, ticker}: {company: AnyRecord; ticker: string}) {
  const p = company.profile || company || {};
  const scores = company.scores || {};

  return (
    <>
      <Hero ticker={ticker} name={p.name} badge="360° COMPANY INTELLIGENCE" />
      <MetricGrid
        items={[
          ["Sector", p.sector],
          ["Industry", p.industry],
          ["Market Cap", money(first(p.market_cap, p.marketCap))],
          ["Employees", p.employees?.toLocaleString?.()],
          ["Overall Score", num(scores.overall_company_score, 1)],
          ["Business Quality", num(scores.business_quality, 1)],
          ["Growth Score", num(scores.growth_score, 1)],
          ["Financial Strength", num(scores.financial_strength, 1)],
        ]}
      />
      <Panel title="Business Overview">
        <Text style={styles.longText}>{p.description || p.summary || "No extended company description returned."}</Text>
      </Panel>
      <DataList title="Products / Demand" data={company.products_demand?.future_demand || company.products_demand} />
      <DataList title="Backlog" data={company.backlog} />
      <DataList title="Competition" data={company.competition} />
      <DataList title="Risks" data={company.risks} />
      <DataList title="Governance & Ethics" data={company.governance_ethics} />
      <DataList title="Sources" data={company.sources} />
    </>
  );
}

function FundamentalsPage({company, fundamental, ticker}: {company: AnyRecord; fundamental: AnyRecord; ticker: string}) {
  return (
    <>
      <Hero ticker={ticker} name={company.profile?.name || company.name} badge="FUNDAMENTAL INTELLIGENCE" />
      <FundamentalPanel company={company} fundamental={fundamental} />
    </>
  );
}

function FundamentalPanel({company, fundamental}: {company: AnyRecord; fundamental: AnyRecord}) {
  const p = company.profile || company || {};
  const valuation = fundamental.valuation || {};
  const profitability = fundamental.profitability || {};
  const growth = fundamental.growth || {};

  return (
    <>
      <Panel title="Fundamental Intelligence">
        <MetricGrid
          items={[
            ["Fundamental Score", num(first(fundamental.scores?.fundamental_score, company.scores?.overall_company_score), 1)],
            ["Sector", first(p.sector, fundamental.sector)],
            ["Industry", first(p.industry, fundamental.industry)],
            ["Market Cap", money(first(p.market_cap, p.marketCap, fundamental.marketCap))],
            ["P/E", num(first(valuation.trailing_pe, p.trailing_pe, fundamental.trailingPE))],
            ["Forward P/E", num(first(valuation.forward_pe, p.forward_pe, fundamental.forwardPE))],
            ["Profit Margin", pct(Number(first(profitability.profit_margin, fundamental.profitMargins)) * 100)],
            ["ROE", pct(Number(first(profitability.roe, fundamental.returnOnEquity)) * 100)],
            ["Revenue Growth", pct(Number(first(growth.revenue_growth, fundamental.revenueGrowth)) * 100)],
            ["EPS", money(first(fundamental.earnings?.trailing_eps, fundamental.epsTrailingTwelveMonths))],
          ]}
        />
        <Text style={styles.longText}>{p.description || p.summary || "No company description returned."}</Text>
      </Panel>
      <DataList title="Quarterly Fundamentals" data={fundamental.quarters || company.quarters} />
      <DataList title="Competition" data={company.competition} />
      <DataList title="Fundamental Risks" data={fundamental.risks || company.risks} />
    </>
  );
}

function TechnicalPage({analysis, ticker}: {analysis: AnyRecord; ticker: string}) {
  return (
    <>
      <Hero ticker={ticker} badge="TECHNICAL INTELLIGENCE" />
      <Panel title="Technical Snapshot">
        <TechnicalCards analysis={analysis} />
      </Panel>
      <ChartPanel rows={analysis.chart} ticker={ticker} />
      <DataList title="Multi-Timeframe Intelligence" data={analysis.technical?.mtf} />
    </>
  );
}

function DecisionPage({analysis, tradePlan, ticker}: {analysis: AnyRecord; tradePlan: AnyRecord; ticker: string}) {
  return (
    <>
      <Hero ticker={ticker} badge="PRODUCTION DECISION ENGINE" />
      <MetricGrid
        items={[
          ["Price", money(analysis.quote?.price)],
          ["Action", analysis.decision?.action || analysis.decision?.signal || "-"],
          ["Technical Score", num(first(analysis.decision?.technical_score, analysis.setup_quality), 1)],
          ["Engine", "CONNECTED"],
        ]}
      />
      <Panel title="BUY / SELL / WATCH Decision">
        <DecisionBox decision={analysis.decision} />
      </Panel>
      <Panel title="Trade Plan">
        <MetricGrid
          items={[
            ["Entry", money(tradePlan.entry)],
            ["Shares", tradePlan.shares ?? "-"],
            ["Stop", money(tradePlan.stop_pct ? tradePlan.entry * (1 - tradePlan.stop_pct / 100) : undefined)],
            ["Target 1", money(tradePlan.target1)],
            ["Target 2", money(tradePlan.target2)],
            ["Target 3", money(tradePlan.target3)],
          ]}
        />
        <Text style={styles.noticeText}>{tradePlan.note || "Position sizing is an estimate, not a guarantee."}</Text>
      </Panel>
    </>
  );
}

function ResearchPage({macro, news, ticker}: {macro: AnyRecord; news: AnyRecord; ticker: string}) {
  return (
    <>
      <Hero ticker={ticker} badge="EVIDENCE RESEARCH" />
      <Panel title="Research Validation">
        <Text style={styles.noticeText}>Evidence and macro research are isolated from the production BUY/SELL decision.</Text>
      </Panel>
      <DataList title="Geopolitical Signals" data={macro.geopolitical} />
      <DataList title="Policy / Regulation Signals" data={macro.politics} />
      <DataList title="Macro Signals" data={macro.macro} />
      <DataList title="News Evidence" data={news.items || news} />
    </>
  );
}

function AuthPortfolio({token, setToken}: {token: string | null; setToken: (token: string | null) => void}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [portfolio, setPortfolio] = useState<AnyRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadPortfolio = useCallback(async (accessToken: string) => {
    setLoading(true);
    setError("");
    try {
      const me = await api("/auth/me", accessToken);
      if (!me?.authenticated && !me?.username) throw new Error("Secure session could not be verified.");
      setPortfolio(await api("/portfolio", accessToken));
    } catch (e: any) {
      setPortfolio(null);
      setToken(null);
      setError(e?.message || "Unable to verify secure portfolio session.");
    } finally {
      setLoading(false);
    }
  }, [setToken]);

  useEffect(() => {
    if (token) loadPortfolio(token);
  }, [loadPortfolio, token]);

  const login = async () => {
    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await postApi("/auth/login", {username: username.trim(), password});
      if (!data?.access_token) throw new Error("Login succeeded but no access token was returned.");
      setPassword("");
      setToken(data.access_token);
      await loadPortfolio(data.access_token);
    } catch (e: any) {
      setError(e?.message || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  };

  if (!token || !portfolio) {
    return (
      <>
        <Hero ticker="PORTFOLIO" badge="PRIVATE PORTFOLIO ACCESS" />
        <Panel title="Sign In">
          <Text style={styles.noticeText}>Your portfolio is protected by the existing HaViQuant bearer-token authentication flow.</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={setUsername}
            placeholder="Username"
            placeholderTextColor="#52677f"
            style={styles.authInput}
            value={username}
          />
          <TextInput
            onChangeText={setPassword}
            onSubmitEditing={login}
            placeholder="Password"
            placeholderTextColor="#52677f"
            secureTextEntry
            style={styles.authInput}
            value={password}
          />
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <TouchableOpacity disabled={loading} onPress={login} style={styles.primaryButton}>
            {loading ? <ActivityIndicator color="#7de6ff" /> : <Text style={styles.primaryButtonText}>Sign In</Text>}
          </TouchableOpacity>
        </Panel>
      </>
    );
  }

  const doc = portfolio.doctor || {};
  const positions = arr(portfolio.positions);
  return (
    <>
      <Hero ticker="PORTFOLIO" badge="PORTFOLIO INTELLIGENCE" />
      <MetricGrid
        items={[
          ["Cash", money(first(portfolio.portfolio?.cash, portfolio.cash))],
          ["Health", num(doc.health, 1)],
          ["Risk Score", num(doc.risk_score, 1)],
          ["Positions", positions.length],
          ["P/L", money(first(doc.pnl, doc.total_pnl))],
        ]}
      />
      <DataList title="Positions" data={positions} />
      <DataList title="Risk Findings" data={doc.findings || doc.risk_findings} />
      <TouchableOpacity onPress={() => setToken(null)} style={styles.secondaryButton}>
        <Text style={styles.secondaryButtonText}>Sign Out</Text>
      </TouchableOpacity>
    </>
  );
}

function RiskPage({token}: {token: string | null}) {
  const [risk, setRisk] = useState<AnyRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRisk(await api("/risk", token));
    } catch (e: any) {
      setError(e?.message || "Unable to load risk.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Loading label="Loading risk engine..." />;
  if (error) return <ErrorBox error={error} retry={load} />;

  const doc = risk?.doctor || risk || {};
  return (
    <>
      <Hero ticker="RISK" badge="PORTFOLIO RISK ENGINE" />
      <MetricGrid
        items={[
          ["Health", num(doc.health, 1)],
          ["Risk Score", num(doc.risk_score, 1)],
          ["Valuation Coverage", pct(doc.valuation_coverage)],
          ["P/L", money(first(doc.pnl, doc.total_pnl))],
        ]}
      />
      <DataList title="Risk Findings" data={doc.findings || doc.risk_findings || risk} />
    </>
  );
}

function BacktestingPage({analysis, macro, ticker}: {analysis: AnyRecord; macro: AnyRecord; ticker: string}) {
  const rows = arr(analysis.chart);
  const returns = rows
    .map((row, index) => {
      if (!index) return null;
      const prev = Number(rows[index - 1]?.close);
      const now = Number(row?.close);
      return Number.isFinite(prev) && Number.isFinite(now) && prev !== 0 ? ((now / prev) - 1) * 100 : null;
    })
    .filter((value) => value !== null) as number[];
  const avg = returns.reduce((sum, value) => sum + value, 0) / Math.max(1, returns.length);

  return (
    <>
      <Hero ticker={ticker} badge="BACKTESTING & VALIDATION" />
      <Panel title="Evidence Validation">
        <Text style={styles.noticeText}>Backtesting presents validation context and does not rewrite the production decision.</Text>
      </Panel>
      <MetricGrid
        items={[
          ["Candles", rows.length],
          ["Avg Daily Return", pct(avg)],
          ["Setup Quality", num(analysis.setup_quality, 1)],
          ["Signal", analysis.signal || "WAIT"],
        ]}
      />
      <DataList title="Multi-Timeframe Inputs" data={analysis.technical?.mtf} />
      <DataList title="Macro Validation Inputs" data={macro.macro} />
    </>
  );
}

function NewsPage({news, ticker}: {news: AnyRecord; ticker: string}) {
  const items = arr(news.items || news);
  return (
    <>
      <Hero ticker={ticker} badge="MARKET NEWS & EVENTS" />
      <Panel title={`${ticker} News`}>
        {items.length ? (
          items.map((item, index) => (
            <TouchableOpacity
              key={`${item.title || "news"}-${index}`}
              onPress={() => {
                const url = item.url || item.link;
                if (url) Linking.openURL(url);
              }}
              style={styles.newsItem}
            >
              <Text style={styles.newsTitle}>{item.title || item.headline || "Market update"}</Text>
              <Text style={styles.newsMeta}>{first(item.publisher, item.source, item.sentiment?.label, "Market source")}</Text>
              <Text style={styles.longText}>{item.summary || item.description || ""}</Text>
            </TouchableOpacity>
          ))
        ) : (
          <EmptyState label="No recent news returned by the available feeds." />
        )}
      </Panel>
    </>
  );
}

function DataList({title, data}: {title: string; data: any}) {
  const rows = arr(data).slice(0, 20);
  return (
    <Panel title={title}>
      {rows.length ? rows.map((row, index) => <DataRow key={index} row={row} />) : <EmptyState label="No provider data returned." />}
    </Panel>
  );
}

function DataRow({row}: {row: any}) {
  if (!isObj(row)) {
    return <Text style={styles.longText}>{text(row)}</Text>;
  }

  const entries = Object.entries(row).slice(0, 8);
  return (
    <View style={styles.dataRow}>
      {entries.map(([key, value]) => (
        <View key={key} style={styles.dataCell}>
          <Text style={styles.dataLabel}>{key.replace(/_/g, " ")}</Text>
          <Text style={styles.dataValue}>{text(value)}</Text>
        </View>
      ))}
    </View>
  );
}

function ValueRow({label, value}: {label: string; value: string}) {
  return (
    <View style={styles.valueRow}>
      <Text style={styles.valueLabel}>{label}</Text>
      <Text style={styles.valueValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: "#060b14"},
  topbar: {
    alignItems: "center",
    borderBottomColor: "#15253a",
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  brandRow: {alignItems: "center", flex: 1, flexDirection: "row", gap: 12, minWidth: 0},
  logo: {alignItems: "center", backgroundColor: "#1f8ad8", borderRadius: 12, height: 42, justifyContent: "center", width: 42},
  logoText: {color: "#ffffff", fontSize: 14, fontWeight: "900"},
  brandText: {flex: 1, minWidth: 0},
  eyebrow: {color: "#55708e", fontSize: 9, fontWeight: "800", letterSpacing: 1.5},
  title: {color: "#eaf2ff", fontSize: 22, fontWeight: "900", marginTop: 2},
  subtitle: {color: "#7286a1", fontSize: 11, marginTop: 1},
  livePill: {alignItems: "center", backgroundColor: "#0b211c", borderColor: "#1e483b", borderRadius: 999, borderWidth: 1, flexDirection: "row", gap: 6, paddingHorizontal: 9, paddingVertical: 6},
  liveDot: {backgroundColor: "#5ce19b", borderRadius: 99, height: 7, width: 7},
  liveText: {color: "#74e6ae", fontSize: 10, fontWeight: "900"},
  search: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#20334b", borderRadius: 12, borderWidth: 1, flexDirection: "row", gap: 8, marginHorizontal: 12, marginTop: 12, paddingHorizontal: 10},
  input: {color: "#e9f3ff", flex: 1, fontSize: 14, fontWeight: "800", paddingVertical: 11},
  iconButton: {alignItems: "center", backgroundColor: "#16304a", borderRadius: 8, height: 34, justifyContent: "center", width: 34},
  nav: {maxHeight: 56},
  navContent: {gap: 8, paddingHorizontal: 12, paddingVertical: 10},
  navItem: {alignItems: "center", backgroundColor: "#08111d", borderColor: "#16263a", borderRadius: 11, borderWidth: 1, flexDirection: "row", gap: 7, paddingHorizontal: 12, paddingVertical: 9},
  navItemActive: {backgroundColor: "#10233a", borderColor: "#235b75"},
  navText: {color: "#8094ad", fontSize: 12, fontWeight: "800"},
  navTextActive: {color: "#58d7ff"},
  body: {flex: 1},
  bodyContent: {paddingBottom: 36, paddingHorizontal: 12},
  pageHead: {alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 12, marginTop: 8},
  pageTitle: {color: "#eaf2ff", flex: 1, fontSize: 22, fontWeight: "900"},
  refresh: {alignItems: "center", borderColor: "#273b55", borderRadius: 9, borderWidth: 1, flexDirection: "row", gap: 6, paddingHorizontal: 10, paddingVertical: 7},
  refreshText: {color: "#b9cbe0", fontSize: 11, fontWeight: "800"},
  hero: {backgroundColor: "#0b1726", borderColor: "#1b3048", borderRadius: 16, borderWidth: 1, marginBottom: 14, padding: 18},
  badge: {alignSelf: "flex-start", backgroundColor: "#0a2636", borderColor: "#174d65", borderRadius: 999, borderWidth: 1, color: "#5edcff", fontSize: 9, fontWeight: "900", letterSpacing: 1, marginBottom: 8, overflow: "hidden", paddingHorizontal: 9, paddingVertical: 5},
  heroTicker: {color: "#ffffff", fontSize: 34, fontWeight: "900"},
  heroName: {color: "#8397b0", fontSize: 13, lineHeight: 20, marginTop: 4},
  cards: {flexDirection: "row", flexWrap: "wrap", gap: 9, marginBottom: 10},
  card: {backgroundColor: "#0b1725", borderColor: "#1a2d44", borderRadius: 12, borderWidth: 1, minHeight: 84, padding: 12, width: "48%"},
  cardLabel: {color: "#68809c", fontSize: 9, fontWeight: "800", letterSpacing: 0.8, textTransform: "uppercase"},
  cardValue: {color: "#edf5ff", fontSize: 19, fontWeight: "900", marginTop: 8},
  panel: {backgroundColor: "#091522", borderColor: "#1a2c43", borderRadius: 15, borderWidth: 1, marginBottom: 14, overflow: "hidden", padding: 15},
  panelTitle: {color: "#e7f2ff", fontSize: 15, fontWeight: "900", marginBottom: 12},
  spark: {alignItems: "flex-end", backgroundColor: "#07111d", borderColor: "#14263a", borderRadius: 11, borderWidth: 1, flexDirection: "row", gap: 3, height: 160, overflow: "hidden", paddingHorizontal: 8, paddingVertical: 12},
  sparkBar: {borderRadius: 4, flex: 1, minWidth: 3},
  chartMeta: {flexDirection: "row", justifyContent: "space-between", marginTop: 8},
  metaText: {color: "#607994", fontSize: 10},
  decisionMain: {color: "#68dcff", fontSize: 34, fontWeight: "900", marginBottom: 8},
  valueRow: {borderBottomColor: "#17283d", borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 10},
  valueLabel: {color: "#7086a0", fontSize: 12},
  valueValue: {color: "#eaf2ff", fontSize: 12, fontWeight: "900"},
  longText: {color: "#9aadc3", fontSize: 12, lineHeight: 19},
  noticeText: {backgroundColor: "#0b1928", borderColor: "#27405b", borderRadius: 11, borderWidth: 1, color: "#83a0bb", fontSize: 12, lineHeight: 19, padding: 12},
  stateBox: {alignItems: "center", gap: 10, justifyContent: "center", minHeight: 220},
  stateText: {color: "#657e99", fontSize: 13},
  errorBox: {backgroundColor: "#1d1112", borderColor: "#60322e", borderRadius: 12, borderWidth: 1, gap: 10, marginBottom: 16, padding: 16},
  errorTitle: {color: "#ffd0c9", fontSize: 15, fontWeight: "900"},
  errorText: {color: "#ffb6ab", fontSize: 12, lineHeight: 18},
  retryButton: {alignSelf: "flex-start", backgroundColor: "#2a1b1b", borderColor: "#693c36", borderRadius: 8, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 8},
  retryText: {color: "#ffd0c9", fontSize: 12, fontWeight: "900"},
  empty: {alignItems: "center", justifyContent: "center", minHeight: 72},
  emptyText: {color: "#657e99", fontSize: 12, textAlign: "center"},
  dataRow: {borderBottomColor: "#17283d", borderBottomWidth: 1, gap: 8, paddingVertical: 10},
  dataCell: {gap: 3},
  dataLabel: {color: "#66809a", fontSize: 10, fontWeight: "800", textTransform: "capitalize"},
  dataValue: {color: "#9fb2c8", fontSize: 12, lineHeight: 18},
  newsItem: {borderBottomColor: "#17283c", borderBottomWidth: 1, paddingVertical: 13},
  newsTitle: {color: "#e8f1ff", fontSize: 14, fontWeight: "900", lineHeight: 20},
  newsMeta: {color: "#5e7792", fontSize: 10, marginTop: 4},
  authInput: {backgroundColor: "#07111d", borderColor: "#20334b", borderRadius: 10, borderWidth: 1, color: "#ffffff", fontSize: 14, marginTop: 10, paddingHorizontal: 12, paddingVertical: 12},
  primaryButton: {alignItems: "center", alignSelf: "flex-start", backgroundColor: "#113a50", borderColor: "#35bfe8", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 8, justifyContent: "center", marginTop: 10, minHeight: 42, paddingHorizontal: 14},
  primaryButtonText: {color: "#7de6ff", fontSize: 13, fontWeight: "900"},
  secondaryButton: {alignItems: "center", alignSelf: "flex-start", backgroundColor: "#0c1827", borderColor: "#273b55", borderRadius: 10, borderWidth: 1, marginTop: 2, paddingHorizontal: 14, paddingVertical: 10},
  secondaryButtonText: {color: "#b9cbe0", fontSize: 13, fontWeight: "900"},
});
