import React, {useCallback, useEffect, useState} from "react";
import {
  ActivityIndicator,
  Image,
  ImageBackground,
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";
import {Ionicons} from "@expo/vector-icons";
import * as SplashScreen from "expo-splash-screen";

const APP_ICON = require("./assets/icon.png");
const LAUNCH_IMAGE = require("./assets/splash.png");

type AnyRecord = Record<string, any>;
type Page =
  | "Dashboard"
  | "Stock Analysis"
  | "Company Intelligence"
  | "Fundamentals"
  | "Technical"
  | "Decision"
  | "Scanner"
  | "Alerts"
  | "Evidence Research"
  | "Portfolio"
  | "Risk"
  | "Backtesting"
  | "News"
  | "Calendar"
  | "More";

const PAGE_LABELS: Record<Page, string> = {
  Dashboard: "Market Pulse",
  "Stock Analysis": "HaVi Finance",
  "Company Intelligence": "HaVi 360",
  Fundamentals: "Fundamentals",
  Technical: "Technicals",
  Decision: "Trade Setup",
  Scanner: "Trade Scanner",
  Alerts: "Alerts",
  "Evidence Research": "Evidence",
  Portfolio: "Portfolio",
  Risk: "Risk Management",
  Backtesting: "Backtesting",
  News: "News Hub",
  Calendar: "Economic Calendar",
  More: "More",
};

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
  {id: "Scanner", icon: "scan-outline"},
  {id: "Alerts", icon: "notifications-outline"},
  {id: "Evidence Research", icon: "flask-outline"},
  {id: "Portfolio", icon: "wallet-outline"},
  {id: "Risk", icon: "shield-checkmark-outline"},
  {id: "Backtesting", icon: "analytics-outline"},
  {id: "News", icon: "newspaper-outline"},
  {id: "Calendar", icon: "calendar-outline"},
];

const BOTTOM_NAV: {id: Page; label: string; icon: keyof typeof Ionicons.glyphMap}[] = [
  {id: "Dashboard", label: "Pulse", icon: "pulse-outline"},
  {id: "Stock Analysis", label: "Finance", icon: "business-outline"},
  {id: "Scanner", label: "Scanner", icon: "scan-outline"},
  {id: "Company Intelligence", label: "360", icon: "analytics-outline"},
  {id: "Alerts", label: "Alerts", icon: "notifications-outline"},
  {id: "Calendar", label: "Calendar", icon: "calendar-outline"},
];

const SECTORS = ["All", "AI / Semiconductors", "Software / Cloud", "Biotech / Healthcare", "Space / Defense", "Energy", "Financials"];
const SCAN_TRIGGERS = ["Top 10 new rank", "Score > 75", "BUY / STRONG BUY", "Upside > 5%", "Fresh catalyst", "Volume spike", "Policy impact"];
const ALERT_INTERVALS = ["5 min", "15 min", "30 min", "1 hour", "Market open"];

const TIMEFRAME_OPTIONS = ["1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W", "1M"] as const;
type Timeframe = typeof TIMEFRAME_OPTIONS[number];

const TIMEFRAME_API: Record<Timeframe, {period: string; interval: string}> = {
  "1m": {period: "7d", interval: "1m"},
  "5m": {period: "60d", interval: "5m"},
  "15m": {period: "60d", interval: "15m"},
  "30m": {period: "60d", interval: "30m"},
  "1H": {period: "60d", interval: "1h"},
  "4H": {period: "60d", interval: "1h"},
  "1D": {period: "5y", interval: "1d"},
  "1W": {period: "5y", interval: "1wk"},
  "1M": {period: "10y", interval: "1mo"},
};

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
  if (value === null || value === undefined || value === "" || value === "-") return "Not returned";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    const useful = value.filter(hasUsefulValue).slice(0, 4);
    if (!useful.length) return "Not returned";
    return useful.map(text).join(", ");
  }
  if (isObj(value)) {
    const preferred = first(
      value.label,
      value.name,
      value.title,
      value.headline,
      value.symbol,
      value.status,
      value.summary,
      value.description,
      value.value
    );
    if (preferred !== undefined) return text(preferred);
    return hasUsefulValue(value) ? "Provider details available" : "Not returned";
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function num(value: any, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "Not returned";
}

function pct(value: any) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : "Not returned";
}

function money(value: any) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "Not returned";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toLocaleString(undefined, {maximumFractionDigits: 2})}`;
}

function compactNumber(value: any) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "Not returned";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(2)}K`;
  return `${sign}${abs.toLocaleString(undefined, {maximumFractionDigits: 2})}`;
}

function friendlyDate(value: any) {
  if (!value) return "Not returned";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return text(value);
  return date.toLocaleString(undefined, {
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function friendlyKey(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function friendlyValue(key: string, value: any) {
  if (value === null || value === undefined || value === "" || value === "-") return "Not returned";
  const lower = key.toLowerCase();
  if (Array.isArray(value)) return text(value);
  if (isObj(value)) return text(value);
  if (lower.includes("date") || lower.includes("time") || lower.includes("published") || lower.includes("period")) return friendlyDate(value);
  if (lower.includes("margin") || lower.includes("growth") || lower.includes("pct") || lower.includes("percent")) return pct(Math.abs(Number(value)) <= 1 ? Number(value) * 100 : value);
  if (lower.includes("revenue") || lower.includes("profit") || lower.includes("income") || lower.includes("cash") || lower.includes("marketcap") || lower.includes("market cap")) return money(value);
  if (typeof value === "number") return compactNumber(value);
  if (typeof value === "string" && value.length > 120) return `${value.slice(0, 117)}...`;
  return text(value);
}

function hasUsefulValue(value: any): boolean {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    value === "-" ||
    value === "N/A" ||
    value === "Not returned"
  ) return false;
  if (Array.isArray(value)) return value.some(hasUsefulValue);
  if (isObj(value)) return Object.values(value).some(hasUsefulValue);
  return true;
}

function hasUsefulRows(data: any): boolean {
  return arr(data).some(hasUsefulValue);
}

function sentimentLabel(item: AnyRecord) {
  const raw = first(item.sentiment?.label, item.sentiment, item.tone, item.sentiment_label, "Neutral");
  const value = typeof raw === "string" ? raw : raw?.label || raw?.classification || "Neutral";
  const clean = String(value).toLowerCase();
  if (clean.includes("bull") || clean.includes("positive")) return "Positive";
  if (clean.includes("bear") || clean.includes("negative")) return "Negative";
  return "Neutral";
}

function displayData(value: any, fallback = "Not returned") {
  const v = value === null || value === undefined || value === "" || value === "-" || value === "N/A" ? null : value;
  return v ?? fallback;
}

function sessionStats(analysis: AnyRecord) {
  const rows = arr(first(analysis.candles, analysis.chart, analysis.rows)).filter(
    (row) => Number.isFinite(Number(row.high)) && Number.isFinite(Number(row.low))
  );
  if (!rows.length) return {range: "Not returned", volume: "Not returned"};
  const latest = String(first(rows[rows.length - 1]?.time, rows[rows.length - 1]?.date, "")).slice(0, 10);
  const sessionRows = latest ? rows.filter((row) => String(first(row.time, row.date, "")).slice(0, 10) === latest) : rows.slice(-78);
  const high = Math.max(...sessionRows.map((row) => Number(row.high)));
  const low = Math.min(...sessionRows.map((row) => Number(row.low)));
  const volume = sessionRows.reduce((sum, row) => sum + (Number(row.volume) || 0), 0);
  return {
    range: Number.isFinite(high) && Number.isFinite(low) ? `${money(low)} - ${money(high)}` : "Not returned",
    volume: volume > 0 ? compactNumber(volume) : "Not returned",
  };
}

function marketCapText(profile: AnyRecord, fundamental?: AnyRecord) {
  return displayData(money(first(profile.market_cap, profile.marketCap, fundamental?.profile?.market_cap, fundamental?.profile?.marketCap, fundamental?.market_cap, fundamental?.marketCap)));
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

async function companyProfile(ticker: string) {
  let rich: AnyRecord = {};
  try {
    rich = await api(`/company-intelligence/${encodeURIComponent(ticker)}`);
  } catch {
    rich = {};
  }

  try {
    const legacy = await api(`/company/${encodeURIComponent(ticker)}`);
    const profile = rich.profile || rich || {};
    return {
      ...rich,
      profile: {
        ...profile,
        name: better(profile.name, legacy.name, ticker),
        sector: better(profile.sector, legacy.sector),
        industry: better(profile.industry, legacy.industry),
        market_cap: better(profile.market_cap, legacy.marketCap),
        employees: better(profile.employees, legacy.employees),
        description: better(profile.description, profile.summary, legacy.description, legacy.summary),
      },
      scores: rich.scores || {},
    };
  } catch {
    return rich.profile ? rich : {profile: rich, scores: rich.scores || {}};
  }
}

function better(...values: any[]) {
  return values.find((value) => value !== null && value !== undefined && value !== "" && value !== "N/A") ?? values[values.length - 1];
}

function useWorkspace(ticker: string, timeframe: Timeframe) {
  const [data, setData] = useState<AnyRecord>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const tf = TIMEFRAME_API[timeframe];
      const includeMtf = tf.interval === "1d";
      const [analysisResult, companyResult, fundamentalResult, planResult, newsResult, macroResult] =
        await Promise.allSettled([
          api(`/market/analysis?ticker=${encodeURIComponent(ticker)}&period=${tf.period}&interval=${tf.interval}&include_mtf=${includeMtf}`),
          companyProfile(ticker),
          api(`/fundamental/${encodeURIComponent(ticker)}`),
          api(`/trade-plan?ticker=${encodeURIComponent(ticker)}`),
          api(`/market/news?ticker=${encodeURIComponent(ticker)}`),
          api(`/market/macro?ticker=${encodeURIComponent(ticker)}`),
        ]);

      setData({
        analysis: analysisResult.status === "fulfilled"
          ? normalizeAnalysis(analysisResult.value || {})
          : normalizeAnalysis({symbol: ticker, quote: {}, chart: []}),
        company: companyResult.status === "fulfilled" ? companyResult.value || {} : {},
        fundamental: fundamentalResult.status === "fulfilled" ? fundamentalResult.value || {} : {},
        tradePlan: planResult.status === "fulfilled" ? planResult.value || {} : {},
        news: newsResult.status === "fulfilled" ? newsResult.value || {} : {},
        macro: macroResult.status === "fulfilled" ? macroResult.value || {} : {},
      });
      if (analysisResult.status !== "fulfilled") {
        setError(analysisResult.reason?.message || `No market data returned for ${ticker}.`);
      }
    } catch (e: any) {
      setError(e?.message || "Unable to load HaViQuant intelligence.");
    } finally {
      setLoading(false);
    }
  }, [ticker, timeframe]);

  useEffect(() => {
    load();
  }, [load]);

  return {data, loading, error, reload: load};
}

export default function App() {
  const {width} = useWindowDimensions();
  const [ticker, setTicker] = useState("NVDA");
  const [input, setInput] = useState("NVDA");
  const [page, setPage] = useState<Page>("Dashboard");
  const [token, setToken] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe>("5m");
  const {data, loading, error, reload} = useWorkspace(ticker, timeframe);
  const analysis = data.analysis || {};
  const macro = data.macro || {};

  useEffect(() => {
    SplashScreen.hideAsync().catch(() => {});
  }, []);

  const submitTicker = () => {
    const clean = input.trim().toUpperCase();
    if (!clean) return;
    setTicker(clean);
    setPage("Stock Analysis");
  };

  if (width >= 900) {
    return (
      <DesktopTerminal
        data={data}
        error={error}
        input={input}
        loading={loading}
        page={page}
        reload={reload}
        setInput={setInput}
        setPage={setPage}
        setTicker={setTicker}
        submitTicker={submitTicker}
        timeframe={timeframe}
        ticker={ticker}
        token={token}
        setToken={setToken}
        setTimeframe={setTimeframe}
      />
    );
  }

  if (loading) {
    return (
      <View style={styles.launchRoot}>
        <StatusBar barStyle="light-content" />
        <Loading fullScreen label="Loading market intelligence..." />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" />
      <View style={styles.topbar}>
        <View style={styles.brandRow}>
          <Image source={APP_ICON} style={styles.logoImage} />
          <View style={styles.brandText}>
            <Text style={styles.eyebrow}>MARKET INTELLIGENCE TERMINAL</Text>
            <Text style={styles.title}>HaViQuant</Text>
            <Text style={styles.subtitle}>Evidence. Edge. Execution.</Text>
          </View>
        </View>
        <View style={styles.livePill}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      <ScrollView
        alwaysBounceVertical
        bounces
        contentContainerStyle={styles.bodyContent}
        contentInset={{bottom: 16}}
        directionalLockEnabled={false}
        keyboardShouldPersistTaps="handled"
        nestedScrollEnabled
        scrollEnabled
        scrollEventThrottle={16}
        scrollIndicatorInsets={{bottom: 74}}
        showsVerticalScrollIndicator
        style={styles.body}
      >
        <MarketTape analysis={analysis} macro={macro} ticker={ticker} />
        <View style={styles.search}>
          <Ionicons name="search-outline" size={17} color="#7087a3" />
          <TextInput
            autoCapitalize="characters"
            autoCorrect={false}
            onChangeText={(value) => setInput(value.toUpperCase())}
            onSubmitEditing={submitTicker}
            placeholder="Ticker, company or event..."
            placeholderTextColor="#52677f"
            returnKeyType="search"
            style={styles.input}
            value={input}
          />
          <TouchableOpacity accessibilityLabel="Analyze ticker" onPress={submitTicker} style={styles.iconButton}>
            <Ionicons name="trending-up-outline" size={17} color="#7de6ff" />
          </TouchableOpacity>
        </View>
        <EventStrip macro={macro} />

        <View style={styles.pageHead}>
          <Text style={styles.pageTitle}>{PAGE_LABELS[page]}</Text>
          <TouchableOpacity onPress={reload} style={styles.refresh}>
            <Ionicons name="refresh-outline" size={16} color="#b9cbe0" />
            <Text style={styles.refreshText}>Refresh</Text>
          </TouchableOpacity>
        </View>

        {error ? <ErrorBox error={error} retry={reload} /> : null}
        <PageContent
          data={data}
          page={page}
          setPage={setPage}
          setTimeframe={setTimeframe}
          ticker={ticker}
          timeframe={timeframe}
          token={token}
          setToken={setToken}
        />
      </ScrollView>
      <MobileBottomNav page={page} setPage={setPage} />
    </SafeAreaView>
  );
}

function MobileBottomNav({page, setPage}: {page: Page; setPage: (page: Page) => void}) {
  return (
    <View style={styles.bottomNav}>
      {BOTTOM_NAV.map((item) => {
        const active = page === item.id;
        return (
          <TouchableOpacity
            accessibilityLabel={`Open ${item.label}`}
            key={item.id}
            onPress={() => setPage(item.id)}
            style={[styles.bottomNavItem, active && styles.bottomNavItemActive]}
          >
            <Ionicons name={item.icon} size={19} color={active ? "#74e6ff" : "#7c90a8"} />
            <Text style={[styles.bottomNavText, active && styles.bottomNavTextActive]}>{item.label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function DesktopTerminal({
  data,
  error,
  input,
  loading,
  page,
  reload,
  setInput,
  setPage,
  setTicker,
  submitTicker,
  timeframe,
  ticker,
  token,
  setToken,
  setTimeframe,
}: {
  data: AnyRecord;
  error: string;
  input: string;
  loading: boolean;
  page: Page;
  reload: () => void;
  setInput: (value: string) => void;
  setPage: (page: Page) => void;
  setTicker: (ticker: string) => void;
  submitTicker: () => void;
  timeframe: Timeframe;
  ticker: string;
  token: string | null;
  setToken: (token: string | null) => void;
  setTimeframe: (timeframe: Timeframe) => void;
}) {
  const analysis = data.analysis || {};
  const company = data.company || {};
  const fundamental = data.fundamental || {};
  const macro = data.macro || {};
  const profile = company.profile || company || {};
  const watch = arr(first(data.watchlist, data.watch, data.movers, analysis.watchlist))
    .map((item) => text(first(item.symbol, item.ticker, item)))
    .filter((symbol) => symbol !== "Not returned");

  const chooseTicker = (symbol: string) => {
    setInput(symbol);
    setTicker(symbol);
    setPage("Stock Analysis");
  };

  return (
    <SafeAreaView style={styles.desktopRoot}>
      <StatusBar barStyle="light-content" />
      <View style={styles.desktopShell}>
        <View style={styles.desktopSide}>
          <View style={styles.desktopBrand}>
            <Image source={APP_ICON} style={styles.desktopLogoImage} />
            <View>
              <Text style={styles.desktopBrandName}>HaViQuant</Text>
              <Text style={styles.desktopBrandSub}>Evidence. Edge. Execution.</Text>
            </View>
          </View>
          {NAV.map((item) => (
            <TouchableOpacity key={item.id} onPress={() => setPage(item.id)} style={[styles.desktopNavItem, page === item.id && styles.desktopNavActive]}>
              <Ionicons name={item.icon} size={17} color={page === item.id ? "#ffffff" : "#b7c7d8"} />
              <Text style={styles.desktopNavText}>{PAGE_LABELS[item.id]}</Text>
            </TouchableOpacity>
          ))}
          <SentimentGauge analysis={analysis} macro={macro} />
        </View>

        <View style={styles.desktopMain}>
          <View style={styles.desktopTop}>
            <View style={styles.desktopSearch}>
              <Ionicons name="search-outline" size={16} color="#8da4b7" />
              <TextInput
                autoCapitalize="characters"
                autoCorrect={false}
                onChangeText={(value) => setInput(value.toUpperCase())}
                onSubmitEditing={submitTicker}
                placeholder="Search ticker, company or event..."
                placeholderTextColor="#7c91a6"
                style={styles.desktopInput}
                value={input}
              />
            </View>
            <MarketTape analysis={analysis} macro={macro} ticker={ticker} />
            <TouchableOpacity onPress={reload} style={styles.desktopIconButton}>
              <Ionicons name="refresh-outline" size={16} color="#cfd8e3" />
            </TouchableOpacity>
          </View>

          <EventStrip macro={macro} />

          {loading ? (
            <Loading label="Loading market intelligence..." />
          ) : error ? (
            <ErrorBox error={error} retry={reload} />
          ) : page === "Dashboard" || page === "Stock Analysis" ? (
            <ScrollView style={styles.desktopScroll} contentContainerStyle={styles.desktopContent}>
              <View style={styles.desktopGrid}>
                <View style={styles.desktopChartColumn}>
                  <DesktopQuoteHeader analysis={analysis} profile={profile} ticker={ticker} />
                  <DesktopChart analysis={analysis} rows={analysis.chart} setTimeframe={setTimeframe} timeframe={timeframe} />
                </View>
                <View style={styles.desktopRightRail}>
                  <SetupPanel analysis={analysis} />
                  <MarketContext analysis={analysis} macro={macro} profile={profile} />
                  <SentimentPanel analysis={analysis} macro={macro} />
                  <ChartIntelPanel analysis={analysis} timeframe={timeframe} />
                  <DecisionPage analysis={analysis} tradePlan={data.tradePlan || {}} ticker={ticker} />
                </View>
              </View>
              <BottomMovers macro={macro} watch={watch} chooseTicker={chooseTicker} />
              <View style={styles.desktopLowerGrid}>
                <ImpactCalendar macro={macro} />
                <EventImpact macro={macro} ticker={ticker} />
                <Panel title="Multi-Timeframe Analysis">
                  <DataList title="Confluence" data={analysis.technical?.mtf} />
                </Panel>
                <AiSummary analysis={analysis} />
              </View>
            </ScrollView>
          ) : (
            <ScrollView style={styles.desktopScroll} contentContainerStyle={styles.desktopContent}>
              <PageContent data={data} page={page} setPage={setPage} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} token={token} setToken={setToken} />
            </ScrollView>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

function DesktopQuoteHeader({analysis, profile, ticker}: {analysis: AnyRecord; profile: AnyRecord; ticker: string}) {
  const change = Number(analysis.quote?.change_pct);
  const stats = sessionStats(analysis);
  return (
    <View style={styles.desktopQuote}>
      <View style={styles.desktopQuoteIdentity}>
        <Text style={styles.desktopTicker}>{ticker}</Text>
        <Text style={styles.desktopCompany}>{text(first(profile.name, profile.longName))}</Text>
        <Text style={styles.desktopSector}>{text(profile.sector)} • {text(profile.industry)}</Text>
      </View>
      <View style={styles.desktopQuotePrice}>
        <Text style={styles.desktopPrice}>{money(analysis.quote?.price)}</Text>
        <Text style={styles.desktopGain}>{Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${pct(change)}` : "-"}</Text>
        <Text style={styles.realTime}>Real-time</Text>
      </View>
      <View style={styles.desktopQuoteMetrics}>
        {[
          ["Session Range", stats.range],
          ["Session Volume", stats.volume],
          ["Market Cap", marketCapText(profile, analysis.fundamental)],
        ].map(([label, value]) => (
          <View key={label} style={styles.desktopRangeCard}>
            <Text style={styles.cardLabel}>{label}</Text>
            <Text numberOfLines={1} adjustsFontSizeToFit style={styles.desktopRangeValue}>{value}</Text>
          </View>
        ))}
      </View>
      <View style={styles.watchButton}><Text style={styles.watchText}>In Watchlist</Text></View>
    </View>
  );
}

function DesktopChart({
  analysis,
  rows,
  timeframe,
  setTimeframe,
}: {
  analysis: AnyRecord;
  rows: any[];
  timeframe: Timeframe;
  setTimeframe: (timeframe: Timeframe) => void;
}) {
  const technical = analysis.technical || {};
  const last = chartRows(rows).slice(-1)[0];
  const indicators = [
    ["SMA 20", money(first(technical.sma_20, technical.sma20))],
    ["SMA 50", money(first(technical.sma_50, technical.sma50))],
    ["SMA 200", money(first(technical.sma_200, technical.sma200))],
    ["VWAP", money(technical.vwap)],
    ["RSI", num(technical.rsi)],
    ["Volume", compactNumber(last?.volume)],
  ].filter(([, value]) => hasUsefulValue(value) && value !== "Not returned");

  return (
    <Panel title="Trading Chart">
      <View style={styles.desktopToolbar}>
        {TIMEFRAME_OPTIONS.map((item) => (
          <TouchableOpacity key={item} onPress={() => setTimeframe(item)} testID={`tf-${item}`}>
            <Text style={[styles.toolbarText, item === timeframe && styles.toolbarActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.candleArea}>
        <View style={styles.indicatorRail}>
          {indicators.length ? indicators.map(([label, value]) => (
            <Text key={label} style={styles.indicatorText}>{label} {value}</Text>
          )) : <Text style={styles.indicatorMuted}>Indicators not returned</Text>}
        </View>
        <CandleChart analysis={analysis} rows={rows} height={350} count={72} desktop />
      </View>
      <View style={styles.oscillator}><View style={styles.oscillatorLine} /></View>
    </Panel>
  );
}

function macroEvents(macro: AnyRecord) {
  const direct = arr(first(macro.events, macro.calendar, macro.economic_calendar, macro.impact_calendar, macro.items, macro.rows));
  const newsFallback = [
    ...arr(macro.macro).map((item) => ({...item, category: first(item.category, "Macro")})),
    ...arr(macro.politics).map((item) => ({...item, category: first(item.category, "Politics")})),
    ...arr(macro.geopolitical).map((item) => ({...item, category: first(item.category, "Geopolitical")})),
  ];
  return (direct.length ? direct : newsFallback)
    .filter(hasUsefulValue)
    .slice(0, 12);
}

function eventTitle(event: AnyRecord) {
  return text(first(event.title, event.name, event.event, event.label, event.description));
}

function eventLevel(event: AnyRecord) {
  const raw = String(first(event.importance, event.impact, event.impact_label, event.sentiment?.impact, event.level, event.severity, "INFO")).toUpperCase();
  if (raw.includes("HIGH")) return "HIGH";
  if (raw.includes("MED")) return "MED";
  if (raw.includes("LOW")) return "LOW";
  return raw === "INFO" ? "INFO" : raw.slice(0, 12);
}

function eventTime(event: AnyRecord) {
  const value = first(event.datetime, event.date_time, event.starts_at, event.released_at, event.published_iso, event.published, event.date, event.time);
  if (!value) return "Not returned";
  const parsed = new Date(value);
  if (Number.isFinite(parsed.getTime())) return friendlyDate(value);
  return text(value);
}

function ImpactCalendar({macro}: {macro: AnyRecord}) {
  const events = macroEvents(macro).slice(0, 5);
  return (
    <Panel title="Impact Calendar">
      {events.length ? events.map((event, index) => (
        <ValueRow key={`${eventTitle(event)}-${index}`} label={eventLevel(event)} value={`${eventTitle(event)} · ${eventTime(event)}`} />
      )) : <EmptyState label="No impact calendar events returned by provider." />}
    </Panel>
  );
}

function CalendarPage({macro, ticker}: {macro: AnyRecord; ticker: string}) {
  return (
    <>
      <Hero ticker="Economic Calendar" badge="DATED MARKET EVENTS" name="Macro, earnings, policy, and market events returned by the connected provider." />
      <ImpactCalendar macro={macro} />
      <EventImpact macro={macro} ticker={ticker} />
      <Panel title="Source Proofs">
        {macroEvents(macro).length ? macroEvents(macro).map((event, index) => (
          <ValueRow key={`${eventTitle(event)}-${index}`} label={eventLevel(event)} value={`${eventTime(event)} · ${eventTitle(event)}`} />
        )) : <EmptyState label="No calendar source proofs returned by provider." />}
      </Panel>
    </>
  );
}

function EventImpact({macro, ticker}: {macro: AnyRecord; ticker: string}) {
  const event = macroEvents(macro)[0];
  return (
    <Panel title="Event Impact Analysis">
      {event ? (
        <>
          <Text style={styles.newsTitle}>{eventTitle(event)}</Text>
          <Text style={styles.longText}>
            {text(first(event.analysis, event.summary, event.impact_summary, event.reason, `Provider returned this event for ${ticker}; confirm price and volume before acting.`))}
          </Text>
          <ValueRow label="When" value={eventTime(event)} />
          <ValueRow label="Impact" value={eventLevel(event)} />
        </>
      ) : <EmptyState label="No event impact analysis returned by provider." />}
    </Panel>
  );
}

function AiSummary({analysis}: {analysis: AnyRecord}) {
  const decision = analysis.decision || {};
  return (
    <Panel title="AI Insight Summary">
      <Text style={styles.longText}>Probability of continuation: {num(decision.confidence, 0)}%</Text>
      <Text style={styles.longText}>Key support: {money(analysis.levels?.stop)}</Text>
      <Text style={styles.longText}>{text(first(decision.rationale, decision.reason, "Decision summary not returned by provider."))}</Text>
    </Panel>
  );
}

function SentimentGauge({analysis, macro}: {analysis?: AnyRecord; macro?: AnyRecord}) {
  return (
    <View style={styles.sentimentCard}>
      <Text style={styles.panelTitle}>Market Sentiment</Text>
      <SentimentBody analysis={analysis || {}} macro={macro || {}} />
    </View>
  );
}

function SentimentPanel({analysis, macro}: {analysis: AnyRecord; macro: AnyRecord}) {
  return (
    <View testID="market-sentiment">
      <Panel title="Market Sentiment">
        <SentimentBody analysis={analysis} macro={macro} />
      </Panel>
    </View>
  );
}

function SentimentBody({analysis, macro}: {analysis: AnyRecord; macro: AnyRecord}) {
  const data = first(macro.sentiment, analysis.market_sentiment, analysis.market_context?.sentiment, {});
  const score = first(data.score, data.value, data.market_score);
  const label = first(data.label, data.state, data.regime, data.market_regime);
  if (!hasUsefulValue(score) && !hasUsefulValue(label)) {
    return <EmptyState label="Market sentiment feed not returned by provider." />;
  }
  return (
    <View style={styles.sentimentBody}>
      <Text style={styles.sentimentScore}>{hasUsefulValue(score) ? num(score, 0) : "Not returned"}</Text>
      <Text style={styles.sentimentLabel}>{text(label)}</Text>
      <ValueRow label="Bullish" value={hasUsefulValue(data.bullish_pct) ? pct(data.bullish_pct) : data.bullish} />
      <ValueRow label="Neutral" value={hasUsefulValue(data.neutral_pct) ? pct(data.neutral_pct) : data.neutral} />
      <ValueRow label="Bearish" value={hasUsefulValue(data.bearish_pct) ? pct(data.bearish_pct) : data.bearish} />
      <Text style={styles.noticeText}>{text(first(data.source, data.updated_at))}</Text>
    </View>
  );
}

function moverItems(macro: AnyRecord, mode = "gainers") {
  const source = first(macro.top_movers, macro.movers, {});
  const data = mode === "active" ? first(source.most_active, source.active, source.items, source) : first(source.gainers, source.items, source);
  return arr(data)
    .map((item) => ({
      change: first(item.change_pct, item.changePercent, item.percent_change),
      price: first(item.price, item.last, item.value),
      symbol: text(first(item.symbol, item.ticker)),
    }))
    .filter((item) => item.symbol !== "Not returned")
    .slice(0, 12);
}

function BottomMovers({macro, watch, chooseTicker}: {macro: AnyRecord; watch: string[]; chooseTicker: (ticker: string) => void}) {
  const movers = moverItems(macro, "gainers");
  const fallback = watch.map((symbol) => ({symbol, change: undefined, price: undefined}));
  const items = movers.length ? movers : fallback;
  return (
    <ScrollView directionalLockEnabled horizontal nestedScrollEnabled showsHorizontalScrollIndicator={false} style={styles.bottomMovers} contentContainerStyle={styles.bottomMoverContent} testID="top-movers">
      <Text style={styles.bottomTitle}>TOP MOVERS</Text>
      {items.length ? items.map((item) => (
        <TouchableOpacity key={item.symbol} onPress={() => chooseTicker(item.symbol)} style={styles.mover}>
          <Text style={styles.moverSymbol}>{item.symbol}</Text>
          <Text style={[styles.moverDelta, Number(item.change) < 0 && styles.moverDeltaBad]}>
            {hasUsefulValue(item.change) ? `${Number(item.change) >= 0 ? "+" : ""}${pct(item.change)}` : "Open"}
          </Text>
        </TouchableOpacity>
      )) : <Text style={styles.emptyText}>No top movers returned by provider.</Text>}
    </ScrollView>
  );
}

function MarketTape({analysis, macro, ticker}: {analysis: AnyRecord; macro: AnyRecord; ticker: string}) {
  const change = Number(analysis.quote?.change_pct);
  const indexItems = arr(first(analysis.market_indices, analysis.indices, analysis.market?.indices, macro.market_indices, macro.indices, macro.market?.indices)).map((item) => [
    text(first(item.symbol, item.name, item.label)),
    displayData(first(item.value, item.price, item.last)),
    Number.isFinite(Number(first(item.change_pct, item.changePercent, item.percent_change)))
      ? `${Number(first(item.change_pct, item.changePercent, item.percent_change)) >= 0 ? "+" : ""}${pct(first(item.change_pct, item.changePercent, item.percent_change))}`
      : text(first(item.status, item.state, "")),
  ]);
  const tickerItem = [
    ticker,
    money(analysis.quote?.price),
    Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${pct(change)}` : "Live data",
  ];
  const marketItems = [...indexItems, tickerItem].filter(([, value]) => hasUsefulValue(value) && value !== "Not returned");

  return (
    <ScrollView directionalLockEnabled horizontal nestedScrollEnabled showsHorizontalScrollIndicator={false} style={styles.tape} contentContainerStyle={styles.tapeContent}>
      {marketItems.map(([label, value, delta], index) => (
        <View key={`${label}-${index}`} style={styles.tapeItem}>
          <Text style={styles.tapeLabel}>{label}</Text>
          <Text style={styles.tapeValue}>{value}</Text>
          <Text style={[styles.tapeDelta, String(delta).startsWith("-") && styles.tapeDeltaBad]}>{delta}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function EventStrip({macro}: {macro: AnyRecord}) {
  const events = macroEvents(macro).slice(0, 6);

  return (
    <ScrollView directionalLockEnabled horizontal nestedScrollEnabled showsHorizontalScrollIndicator={false} style={styles.events} contentContainerStyle={styles.eventContent}>
      <View style={styles.eventIntro}>
        <Text style={styles.eventIntroText}>Today's Key Events</Text>
      </View>
      {events.length ? events.map((event, index) => {
        const level = eventLevel(event);
        return (
        <View key={`${eventTitle(event)}-${index}`} style={styles.eventCard}>
          <View style={[styles.eventDot, level !== "HIGH" && styles.eventDotMed]} />
          <View>
            <Text style={[styles.eventLevel, level !== "HIGH" && styles.eventLevelMed]}>{level}</Text>
            <Text numberOfLines={2} style={styles.eventTitle}>{eventTitle(event)}</Text>
          </View>
          <Text numberOfLines={2} style={styles.eventTime}>{eventTime(event)}</Text>
        </View>
      );}) : (
        <View style={styles.eventCard}>
          <View style={styles.eventDotMed} />
          <View>
            <Text style={styles.eventLevelMed}>INFO</Text>
            <Text style={styles.eventTitle}>No impact events returned</Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function PageContent({
  data,
  page,
  setPage,
  setTimeframe,
  ticker,
  timeframe,
  token,
  setToken,
}: {
  data: AnyRecord;
  page: Page;
  setPage: (page: Page) => void;
  setTimeframe: (timeframe: Timeframe) => void;
  ticker: string;
  timeframe: Timeframe;
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
        <QuoteTerminal analysis={analysis} profile={profile} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />
        <ChartPanel analysis={analysis} rows={analysis.chart} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />
        <ChartIntelPanel analysis={analysis} timeframe={timeframe} />
        <TerminalGrid>
          <SetupPanel analysis={analysis} />
          <MarketContext analysis={analysis} macro={macro} profile={profile} />
        </TerminalGrid>
        <MarketTrendPanel analysis={analysis} />
        <SentimentPanel analysis={analysis} macro={macro} />
        <TopMoversPanel macro={macro} />
        <MetricGrid
          items={[
            ["Live Price", money(analysis.quote?.price)],
            ["Change", pct(analysis.quote?.change_pct)],
            ["Technical Score", num(analysis.decision?.technical_score, 1)],
            ["Decision", text(first(analysis.decision?.action, analysis.decision?.signal, analysis.signal))],
          ]}
        />
        <TerminalGrid>
          <Panel title="Technical Snapshot">
            <TechnicalCards analysis={analysis} />
          </Panel>
          <Panel title="Production Decision">
            <DecisionBox decision={analysis.decision} />
          </Panel>
        </TerminalGrid>
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
        <QuoteTerminal analysis={analysis} profile={profile} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />
        <ChartPanel analysis={analysis} rows={analysis.chart} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />
        <ChartIntelPanel analysis={analysis} timeframe={timeframe} />
        <TerminalGrid>
          <SetupPanel analysis={analysis} />
          <MarketContext analysis={analysis} macro={macro} profile={profile} />
        </TerminalGrid>
        <MetricGrid
          items={[
            ["Price", money(analysis.quote?.price)],
            ["Technical Score", num(analysis.decision?.technical_score, 1)],
            ["Fundamental Score", num(first(fundamental.scores?.fundamental_score, company.scores?.overall_company_score), 1)],
            ["Market Cap", money(first(profile.market_cap, profile.marketCap, fundamental.marketCap))],
            ["Decision", text(first(analysis.decision?.action, analysis.decision?.signal, analysis.signal))],
          ]}
        />
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
  if (page === "Technical") return <TechnicalPage analysis={analysis} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />;
  if (page === "Decision") return <DecisionPage analysis={analysis} tradePlan={tradePlan} ticker={ticker} />;
  if (page === "Scanner") return <ScannerPage ticker={ticker} />;
  if (page === "Alerts") return <AlertsPage analysis={analysis} news={news} ticker={ticker} />;
  if (page === "Evidence Research") return <ResearchPage macro={macro} news={news} ticker={ticker} />;
  if (page === "Calendar") return <CalendarPage macro={macro} ticker={ticker} />;
  if (page === "Portfolio") return <AuthPortfolio token={token} setToken={setToken} />;
  if (page === "Risk") return <RiskPage token={token} />;
  if (page === "Backtesting") return <BacktestingPage analysis={analysis} macro={macro} ticker={ticker} />;
  if (page === "More") return <MorePage setPage={setPage} />;
  return <NewsPage news={news} ticker={ticker} />;
}

function QuoteTerminal({
  analysis,
  profile,
  setTimeframe,
  ticker,
  timeframe,
}: {
  analysis: AnyRecord;
  profile: AnyRecord;
  setTimeframe: (timeframe: Timeframe) => void;
  ticker: string;
  timeframe: Timeframe;
}) {
  const price = analysis.quote?.price;
  const change = Number(analysis.quote?.change_pct);
  const changeText = Number.isFinite(change) ? pct(change) : "-";

  return (
    <View style={styles.quotePanel}>
      <View style={styles.quoteTop}>
        <View style={styles.quoteIdentity}>
          <Text style={styles.quoteTicker}>{ticker}</Text>
          <Text numberOfLines={1} style={styles.quoteName}>
            {text(first(profile.name, profile.longName))}
          </Text>
          <Text numberOfLines={1} style={styles.quoteSector}>
            {text(profile.sector)} • {text(profile.industry)}
          </Text>
        </View>
        <View style={styles.quotePriceBox}>
          <Text style={styles.quotePrice}>{money(price)}</Text>
          <Text style={[styles.quoteChange, change < 0 && styles.quoteChangeBad]}>{changeText}</Text>
          <Text style={styles.realTime}>Real-time</Text>
        </View>
      </View>
      <View style={styles.timeframes}>
        {TIMEFRAME_OPTIONS.slice(0, 7).map((item) => (
          <TouchableOpacity key={item} onPress={() => setTimeframe(item)} style={[styles.timeframe, item === timeframe && styles.timeframeActive]} testID={`tf-${item}`}>
            <Text style={[styles.timeframeText, item === timeframe && styles.timeframeTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

function TerminalGrid({children}: {children: React.ReactNode}) {
  return <View style={styles.terminalGrid}>{children}</View>;
}

function SetupPanel({analysis}: {analysis: AnyRecord}) {
  const signal = text(first(analysis.decision?.action, analysis.signal));
  const score = num(first(analysis.decision?.technical_score, analysis.setup_quality), 0);
  return (
    <Panel title="Trade Setup">
      <View style={styles.setupHead}>
        <View>
          <Text style={styles.setupSignal}>{signal} SETUP</Text>
          <Text style={styles.setupSub}>{signal === "BUY" ? "High Probability" : "Await confirmation"}</Text>
        </View>
        <Text style={styles.setupScore}>{score}<Text style={styles.scoreSuffix}>/100</Text></Text>
      </View>
      <ValueRow label="Trend" value={text(analysis.technical?.trend)} />
      <ValueRow label="Momentum" value={text(analysis.technical?.momentum)} />
      <ValueRow label="RSI (14)" value={num(analysis.technical?.rsi)} />
      <ValueRow label="Volume" value={num(analysis.technical?.volume_ratio)} />
    </Panel>
  );
}

function MarketContext({analysis, macro, profile}: {analysis: AnyRecord; macro: AnyRecord; profile: AnyRecord}) {
  const sentiment = first(macro.sentiment, analysis.market_sentiment, {});
  return (
    <Panel title="Market Context">
      <ValueRow label="Overall Market" value={text(first(analysis.market_context?.overall, analysis.market?.regime, macro.market_regime, sentiment.label))} />
      <ValueRow label="Sector" value={text(profile.sector)} />
      <ValueRow label="Regime" value={text(first(macro.market_regime, sentiment.market_regime, analysis.technical?.trend))} />
      <ValueRow label="Volatility" value={text(first(macro.vix_regime, analysis.technical?.volatility))} />
      <ValueRow label="Liquidity" value={hasUsefulValue(analysis.technical?.volume_ratio) ? `${num(analysis.technical.volume_ratio)}x Avg Volume` : "Not returned"} />
    </Panel>
  );
}

function MarketTrendPanel({analysis}: {analysis: AnyRecord}) {
  const technical = analysis.technical || {};
  const trend = text(first(technical.trend, analysis.trend));
  const momentum = text(technical.momentum);
  const action = text(first(analysis.decision?.action, analysis.signal));
  return (
    <Panel title="Market Trend">
      <View style={styles.trendRow}>
        <View style={styles.trendBadge}>
          <Ionicons name="pulse-outline" size={18} color="#74e6ff" />
          <Text style={styles.trendBadgeText}>{trend}</Text>
        </View>
        <View style={styles.trendCopy}>
          <Text style={styles.trendTitle}>{action} bias</Text>
          <Text style={styles.trendText}>Momentum is {momentum}. Confirm with volume, price levels, and the latest market news before acting.</Text>
        </View>
      </View>
    </Panel>
  );
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

function Loading({label, fullScreen = false}: {label: string; fullScreen?: boolean}) {
  return (
    <ImageBackground
      accessibilityLabel={label}
      source={LAUNCH_IMAGE}
      resizeMode="cover"
      style={[styles.launchScreen, fullScreen && styles.launchScreenFull]}
      imageStyle={!fullScreen ? styles.launchImage : undefined}
    >
      <View style={[styles.launchShade, fullScreen && styles.launchShadeFull]}>
        <View style={styles.launchContent}>
          <View style={styles.launchProgress}><View style={styles.launchProgressFill} /></View>
          <ActivityIndicator color="#55d9ff" />
          <Text style={styles.launchText}>{label}</Text>
          <Text style={styles.launchSubtext}>Preparing live market context, signals, and evidence.</Text>
        </View>
      </View>
    </ImageBackground>
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
  const visible = items.filter(([, value]) => hasUsefulValue(displayData(value)));
  return (
    <View style={styles.cards}>
      {visible.length ? visible.map(([label, value]) => (
        <View key={label} style={styles.card}>
          <Text style={styles.cardLabel}>{label}</Text>
          <Text numberOfLines={2} adjustsFontSizeToFit style={styles.cardValue}>
            {displayData(value)}
          </Text>
        </View>
      )) : <EmptyState label="No metrics returned by provider." />}
    </View>
  );
}

function ChartPanel({
  analysis,
  rows,
  setTimeframe,
  ticker,
  timeframe,
}: {
  analysis: AnyRecord;
  rows: any[];
  setTimeframe: (timeframe: Timeframe) => void;
  ticker: string;
  timeframe: Timeframe;
}) {
  const valid = chartRows(rows);

  return (
    <Panel title={`Market Chart · ${ticker}`}>
      <View style={styles.compactToolbar}>
        {TIMEFRAME_OPTIONS.slice(0, 7).map((item) => (
          <TouchableOpacity key={item} onPress={() => setTimeframe(item)} style={[styles.timeframe, item === timeframe && styles.timeframeActive]} testID={`chart-tf-${item}`}>
            <Text style={[styles.timeframeText, item === timeframe && styles.timeframeTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
      {valid.length ? (
        <>
          <CandleChart analysis={analysis} rows={valid} height={260} count={36} />
          <View style={styles.chartMeta}>
            <Text style={styles.metaText}>{valid.slice(-42).length} real candles</Text>
            <Text style={styles.metaText}>{timeframe}</Text>
          </View>
        </>
      ) : (
        <EmptyState label={`No chart data returned for ${timeframe}. Try another ticker or timeframe.`} />
      )}
    </Panel>
  );
}

function ChartIntelPanel({analysis, timeframe}: {analysis: AnyRecord; timeframe: Timeframe}) {
  const technical = analysis.technical || {};
  const decision = analysis.decision || {};
  const pattern = first(
    technical.pattern?.name,
    technical.pattern?.label,
    analysis.pattern?.name,
    analysis.pattern?.label,
    analysis.pattern?.type
  );
  const confidence = first(decision.confidence, decision.technical_score, analysis.setup_quality);

  return (
    <Panel title="Pattern Analysis">
      <Text style={styles.longText}>
        {hasUsefulValue(pattern)
          ? `${text(pattern)} is being monitored on the ${timeframe} chart with production decision output held separate from research validation.`
          : `Pattern analysis was not returned for the ${timeframe} chart.`}
      </Text>
      <ValueRow label="Predicted Bias" value={text(first(decision.action, decision.signal, analysis.signal))} />
      <ValueRow label="Trend" value={text(technical.trend)} />
      <ValueRow label="Momentum" value={text(technical.momentum)} />
      <ValueRow label="Volatility" value={text(technical.volatility)} />
      <ValueRow label="Confidence" value={num(confidence, 0)} />
    </Panel>
  );
}

function TopMoversPanel({macro}: {macro: AnyRecord}) {
  const movers = moverItems(macro, "gainers").slice(0, 6);
  return (
    <Panel title="Top Movers">
      {movers.length ? movers.map((item) => (
        <ValueRow
          key={item.symbol}
          label={item.symbol}
          value={`${hasUsefulValue(item.price) ? money(item.price) : "Price not returned"} · ${hasUsefulValue(item.change) ? `${Number(item.change) >= 0 ? "+" : ""}${pct(item.change)}` : "Move not returned"}`}
        />
      )) : <EmptyState label="Top movers feed not returned by provider." />}
    </Panel>
  );
}

function ScannerPage({ticker}: {ticker: string}) {
  const [sector, setSector] = useState(SECTORS[0]);
  const [trigger, setTrigger] = useState(SCAN_TRIGGERS[1]);
  const [interval, setInterval] = useState(ALERT_INTERVALS[1]);

  return (
    <>
      <Hero
        ticker="Trade Scanner"
        badge="TOP 50 OPPORTUNITY ALERTS"
        name="Create scanner alerts by sector, upside threshold, catalysts, policy impact, and technical confirmation."
      />
      <Panel title="Scanner Alert Setup">
        <Text style={styles.sectionLabel}>Sector scope</Text>
        <ScrollView directionalLockEnabled horizontal nestedScrollEnabled showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {SECTORS.map((item) => (
            <TouchableOpacity key={item} onPress={() => setSector(item)} style={[styles.filterChip, sector === item && styles.filterChipActive]}>
              <Text style={[styles.filterChipText, sector === item && styles.filterChipTextActive]}>{item}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <Text style={styles.sectionLabel}>Alert trigger</Text>
        <ScrollView directionalLockEnabled horizontal nestedScrollEnabled showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {SCAN_TRIGGERS.map((item) => (
            <TouchableOpacity key={item} onPress={() => setTrigger(item)} style={[styles.filterChip, trigger === item && styles.filterChipActive]}>
              <Text style={[styles.filterChipText, trigger === item && styles.filterChipTextActive]}>{item}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <Text style={styles.sectionLabel}>Check every</Text>
        <View style={styles.segmentGrid}>
          {ALERT_INTERVALS.map((item) => (
            <TouchableOpacity key={item} onPress={() => setInterval(item)} style={[styles.segmentButton, interval === item && styles.segmentButtonActive]}>
              <Text style={[styles.segmentText, interval === item && styles.segmentTextActive]}>{item}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={styles.alertSummary}>
          <Ionicons name="notifications-outline" size={18} color="#74e6ff" />
          <Text style={styles.alertSummaryText}>
            Notify when {sector === "All" ? "any sector" : sector} produces {trigger.toLowerCase()} during a {interval} scan.
          </Text>
        </View>
      </Panel>
      <Panel title="Current Top Candidates">
        <EmptyState label={`Live top-50 scanner rankings were not returned for ${sector}. Keep the alert rule, then connect the scanner API feed for candidates, upside, catalysts, and timeframes.`} />
      </Panel>
    </>
  );
}

function AlertsPage({analysis, news, ticker}: {analysis: AnyRecord; news: AnyRecord; ticker: string}) {
  const [portfolioOn, setPortfolioOn] = useState(true);
  const [scannerOn, setScannerOn] = useState(true);
  const [portfolioInterval, setPortfolioInterval] = useState(ALERT_INTERVALS[2]);
  const [scannerInterval, setScannerInterval] = useState(ALERT_INTERVALS[1]);
  const signal = text(first(analysis.decision?.action, analysis.decision?.signal, analysis.signal));
  const change = Number(analysis.quote?.change_pct);
  const headlines = arr(first(news.items, news.news, news.articles)).slice(0, 2);

  return (
    <>
      <Hero
        ticker="Alerts"
        badge="PORTFOLIO + SCANNER MONITOR"
        name="Control how often the app checks your portfolio, world news, scanner ranks, technicals, and market-impact events."
      />
      <Panel title="Portfolio Monitor">
        <ToggleRow enabled={portfolioOn} label="Portfolio news and analysis timer" onPress={() => setPortfolioOn(!portfolioOn)} value={portfolioOn ? "ON" : "OFF"} />
        <View style={styles.segmentGrid}>
          {ALERT_INTERVALS.map((item) => (
            <TouchableOpacity key={item} onPress={() => setPortfolioInterval(item)} style={[styles.segmentButton, portfolioInterval === item && styles.segmentButtonActive]}>
              <Text style={[styles.segmentText, portfolioInterval === item && styles.segmentTextActive]}>{item}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.longText}>
          When holdings are added to Portfolio, the app can re-check news sentiment, catalysts, risk, chart setup, and decision changes on this schedule.
        </Text>
      </Panel>
      <Panel title="Trade Scanner Alerts">
        <ToggleRow enabled={scannerOn} label="Top 50 scanner alert rules" onPress={() => setScannerOn(!scannerOn)} value={scannerOn ? "ON" : "OFF"} />
        <View style={styles.segmentGrid}>
          {ALERT_INTERVALS.map((item) => (
            <TouchableOpacity key={item} onPress={() => setScannerInterval(item)} style={[styles.segmentButton, scannerInterval === item && styles.segmentButtonActive]}>
              <Text style={[styles.segmentText, scannerInterval === item && styles.segmentTextActive]}>{item}</Text>
            </TouchableOpacity>
          ))}
        </View>
        {["New stock enters Top 10", "Score moves above 75", "Decision upgrades to BUY", "Estimated upside above 5%", "Fresh catalyst headline"].map((item) => (
          <View key={item} style={styles.ruleRow}>
            <Ionicons name="checkmark-circle-outline" size={17} color="#33e68a" />
            <Text style={styles.ruleText}>{item}</Text>
          </View>
        ))}
      </Panel>
      <Panel title="Live Alert Preview">
        <View style={styles.alertEvent}>
          <View style={[styles.alertDot, signal.includes("BUY") && styles.alertDotGood]} />
          <View style={styles.alertEventBody}>
            <Text style={styles.alertEventTitle}>{ticker} decision is {signal}</Text>
            <Text style={styles.alertEventText}>
              Price {money(analysis.quote?.price)} · {Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${pct(change)}` : "change not returned"} · check every {portfolioInterval}
            </Text>
          </View>
        </View>
        {headlines.map((item, index) => (
          <View key={`${text(item.title)}-${index}`} style={styles.alertEvent}>
            <View style={styles.alertDot} />
            <View style={styles.alertEventBody}>
              <Text numberOfLines={2} style={styles.alertEventTitle}>{text(first(item.title, item.headline))}</Text>
              <Text style={styles.alertEventText}>News sentiment and catalyst scan queued for portfolio impact.</Text>
            </View>
          </View>
        ))}
      </Panel>
    </>
  );
}

function ToggleRow({enabled, label, onPress, value}: {enabled: boolean; label: string; onPress: () => void; value: string}) {
  return (
    <TouchableOpacity onPress={onPress} style={styles.toggleRow}>
      <View style={styles.toggleTextGroup}>
        <Text style={styles.toggleLabel}>{label}</Text>
        <Text style={styles.toggleSub}>Tap to change alert state</Text>
      </View>
      <View style={[styles.togglePill, enabled && styles.togglePillActive]}>
        <View style={[styles.toggleKnob, enabled && styles.toggleKnobActive]} />
      </View>
      <Text style={styles.toggleValue}>{value}</Text>
    </TouchableOpacity>
  );
}

function MorePage({setPage}: {setPage: (page: Page) => void}) {
  const pages = NAV.filter((item) => !["Dashboard", "Stock Analysis", "Company Intelligence", "Scanner", "Alerts", "Calendar", "Portfolio"].includes(item.id));
  return (
    <>
      <Hero ticker="More" badge="RESEARCH WORKSPACE" name="Open the deeper company, technical, decision, risk, backtesting, and news views." />
      <View style={styles.moreGrid}>
        {pages.map((item) => (
          <TouchableOpacity key={item.id} onPress={() => setPage(item.id)} style={styles.moreTile}>
            <Ionicons name={item.icon} size={19} color="#74e6ff" />
            <Text style={styles.moreTitle}>{PAGE_LABELS[item.id]}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </>
  );
}

function chartRows(rows: any[]) {
  return arr(rows)
    .map((row) => ({
      close: Number(row.close),
      high: Number(first(row.high, row.close)),
      low: Number(first(row.low, row.close)),
      open: Number(first(row.open, row.close)),
      time: row.time || row.date,
      volume: Number(row.volume),
    }))
    .filter((row) => [row.open, row.high, row.low, row.close].every(Number.isFinite));
}

function CandleChart({
  analysis,
  rows,
  height,
  count,
  desktop = false,
}: {
  analysis: AnyRecord;
  rows: any[];
  height: number;
  count: number;
  desktop?: boolean;
}) {
  const visible = chartRows(rows).slice(-count);
  const [selectedIndex, setSelectedIndex] = useState(Math.max(0, visible.length - 1));
  if (!visible.length) return <EmptyState label="No OHLC candles returned." />;

  const rawLevels = analysis.levels || {};
  const levelSpecs = [
    {label: "Entry", value: Number(first(rawLevels.entry, rawLevels.entry_zone, analysis.quote?.price)), style: styles.levelEntry},
    {label: "Target 1", value: Number(first(rawLevels.target1, rawLevels.target_1)), style: styles.levelTarget},
    {label: "Target 2", value: Number(first(rawLevels.target2, rawLevels.target_2)), style: styles.levelTarget},
    {label: "Stop", value: Number(first(rawLevels.stop, rawLevels.stop_loss)), style: styles.levelStop},
  ].filter((item) => Number.isFinite(item.value));
  const highs = visible.map((row) => row.high);
  const lows = visible.map((row) => row.low);
  const levelValues = levelSpecs.map((item) => item.value);
  const min = Math.min(...lows, ...levelValues);
  const max = Math.max(...highs, ...levelValues);
  const span = max - min || 1;
  const y = (value: number) => ((max - value) / span) * (height - 26) + 13;
  const last = visible[visible.length - 1];
  const activeIndex = Math.min(selectedIndex, visible.length - 1);
  const active = visible[activeIndex] || last;
  const activeMove = active.open ? ((active.close / active.open) - 1) * 100 : 0;
  const activeBias = active.close >= active.open ? "Bullish candle" : "Bearish candle";

  return (
    <View>
      <View style={[styles.candleChart, {height}]}>
        {[0, 1, 2, 3].map((line) => (
          <View key={line} style={[styles.chartGridLine, {top: 16 + line * ((height - 32) / 3)}]} />
        ))}
        <Text style={[styles.priceAxis, {top: 8}]}>{money(max)}</Text>
        <Text style={[styles.priceAxis, {bottom: 5}]}>{money(min)}</Text>
        {levelSpecs.map((level) => (
          <View key={`${level.label}-${level.value}`} style={[styles.chartLevel, level.style, {top: y(level.value)}]}>
            <Text numberOfLines={1} style={[styles.chartLevelText, level.style]}>
              {level.label} {money(level.value)}
            </Text>
          </View>
        ))}
        <View style={[styles.chartPricePill, {top: y(last.close)}]}>
          <Text style={styles.chartPricePillText}>{money(last.close)}</Text>
        </View>
        <View style={styles.candleRow}>
          {visible.map((row, index) => {
            const up = row.close >= row.open;
            const color = up ? "#20e188" : "#ff5368";
            const wickTop = y(row.high);
            const wickBottom = y(row.low);
            const bodyTop = y(Math.max(row.open, row.close));
            const bodyBottom = y(Math.min(row.open, row.close));
            return (
              <Pressable
                key={`${row.time || index}-${index}`}
                onFocus={() => setSelectedIndex(index)}
                onHoverIn={() => setSelectedIndex(index)}
                onPress={() => setSelectedIndex(index)}
                style={styles.candleSlot}
                testID={`candle-${index}`}
              >
                <View style={[styles.candleWick, {backgroundColor: color, height: Math.max(4, wickBottom - wickTop), top: wickTop}]} />
                <View style={[styles.candleBody, desktop && styles.candleBodyDesktop, index === activeIndex && styles.candleBodyActive, {backgroundColor: color, height: Math.max(5, bodyBottom - bodyTop), top: bodyTop}]} />
              </Pressable>
            );
          })}
        </View>
      </View>
      <View testID="chart-selected-candle" style={styles.chartReadout}>
        <Text style={styles.chartReadoutTitle}>{activeBias} · {pct(activeMove)}</Text>
        <Text style={styles.chartReadoutText}>O {money(active.open)}  H {money(active.high)}  L {money(active.low)}  C {money(active.close)}</Text>
        <Text style={styles.chartReadoutText}>
          {friendlyDate(active.time)} · Volume {compactNumber(active.volume)}
        </Text>
      </View>
      {levelSpecs.length ? (
        <View style={styles.chartLegend}>
          {levelSpecs.slice(0, 4).map((level) => (
            <Text key={`legend-${level.label}`} style={[styles.chartLegendText, level.style]}>{level.label}</Text>
          ))}
        </View>
      ) : null}
    </View>
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
        ["Volume Ratio", hasUsefulValue(t.volume_ratio) ? `${num(t.volume_ratio)}x` : "Not returned"],
      ]}
    />
  );
}

function DecisionBox({decision}: {decision: AnyRecord}) {
  return (
    <View>
      <Text style={styles.decisionMain}>{text(first(decision?.action, decision?.signal))}</Text>
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
      <OptionalDataList title="Products / Demand" data={company.products_demand?.future_demand || company.products_demand} />
      <OptionalDataList title="Backlog" data={company.backlog} />
      <OptionalDataList title="Competition" data={company.competition} />
      <OptionalDataList title="Risks" data={company.risks} />
      <OptionalDataList title="Governance & Ethics" data={company.governance_ethics} />
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
      <OptionalDataList title="Quarterly Fundamentals" data={fundamental.quarters || company.quarters} />
      <OptionalDataList title="Competition" data={company.competition} />
      <OptionalDataList title="Fundamental Risks" data={fundamental.risks || company.risks} />
    </>
  );
}

function TechnicalPage({
  analysis,
  setTimeframe,
  ticker,
  timeframe,
}: {
  analysis: AnyRecord;
  setTimeframe: (timeframe: Timeframe) => void;
  ticker: string;
  timeframe: Timeframe;
}) {
  return (
    <>
      <Hero ticker={ticker} badge="TECHNICAL INTELLIGENCE" />
      <Panel title="Technical Snapshot">
        <TechnicalCards analysis={analysis} />
      </Panel>
      <ChartPanel analysis={analysis} rows={analysis.chart} setTimeframe={setTimeframe} ticker={ticker} timeframe={timeframe} />
      <ChartIntelPanel analysis={analysis} timeframe={timeframe} />
      <OptionalDataList title="Multi-Timeframe Intelligence" data={analysis.technical?.mtf} />
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
      <OptionalDataList title="Geopolitical Signals" data={macro.geopolitical} />
      <OptionalDataList title="Policy / Regulation Signals" data={macro.politics} />
      <OptionalDataList title="Macro Signals" data={macro.macro} />
      <OptionalDataList title="News Evidence" data={news.items || news} />
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
          ["Signal", text(first(analysis.signal, analysis.decision?.action, analysis.decision?.signal))],
        ]}
      />
      <OptionalDataList title="Multi-Timeframe Inputs" data={analysis.technical?.mtf} />
      <OptionalDataList title="Macro Validation Inputs" data={macro.macro} />
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
              <View style={styles.newsHead}>
                <View style={[styles.newsDot, sentimentLabel(item) === "Positive" && styles.newsDotGood, sentimentLabel(item) === "Negative" && styles.newsDotBad]} />
                <View style={styles.newsBody}>
                  <Text style={styles.newsTitle}>{item.title || item.headline || "Market update"}</Text>
                  <Text style={styles.newsMeta}>
                    {sentimentLabel(item)} · {text(first(item.publisher, item.source, "Market source"))} · {friendlyDate(first(item.published_at, item.published, item.published_iso, item.publishedIso, item.date))}
                  </Text>
                  {item.summary || item.description ? <Text style={styles.longText}>{item.summary || item.description}</Text> : null}
                </View>
              </View>
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
  const rows = arr(data).filter(hasUsefulValue).slice(0, 20);
  return (
    <Panel title={title}>
      {rows.length ? rows.map((row, index) => <DataRow key={index} row={row} />) : <EmptyState label="Not available from the current data provider." />}
    </Panel>
  );
}

function OptionalDataList({title, data}: {title: string; data: any}) {
  if (!hasUsefulRows(data)) return null;
  return <DataList title={title} data={data} />;
}

function DataRow({row}: {row: any}) {
  if (!isObj(row)) {
    return <Text style={styles.longText}>{text(row)}</Text>;
  }

  const hidden = new Set(["url", "link", "source_url", "published_iso", "publishedIso", "recency", "sources", "source"]);
  const entries = Object.entries(row)
    .filter(([key, value]) => !hidden.has(key) && hasUsefulValue(value))
    .slice(0, 6);
  if (!entries.length) return null;
  return (
    <View style={styles.dataRow}>
      {entries.map(([key, value]) => (
        <View key={key} style={styles.dataCell}>
          <Text style={styles.dataLabel}>{friendlyKey(key)}</Text>
          <Text style={styles.dataValue}>{friendlyValue(key, value)}</Text>
        </View>
      ))}
    </View>
  );
}

function ValueRow({label, value}: {label: string; value: any}) {
  return (
    <View style={styles.valueRow}>
      <Text style={styles.valueLabel}>{label}</Text>
      <Text style={styles.valueValue}>{text(value)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: "#060b14"},
  launchRoot: {backgroundColor: "#020814", flex: 1},
  desktopRoot: {backgroundColor: "#06101b", flex: 1},
  desktopShell: {flex: 1, flexDirection: "row"},
  desktopSide: {backgroundColor: "#07111d", borderRightColor: "#18283d", borderRightWidth: 1, padding: 12, width: 218},
  desktopBrand: {alignItems: "center", flexDirection: "row", gap: 10, marginBottom: 14},
  desktopLogo: {alignItems: "center", backgroundColor: "#5b2cff", borderColor: "#24dcff", borderRadius: 8, borderWidth: 1, height: 34, justifyContent: "center", width: 34},
  desktopLogoImage: {borderColor: "#24dcff", borderRadius: 8, borderWidth: 1, height: 34, width: 34},
  desktopBrandName: {color: "#edf5ff", fontSize: 20, fontWeight: "900"},
  proText: {color: "#a16bff"},
  desktopBrandSub: {color: "#c0ccda", fontSize: 11, marginTop: 2},
  desktopNavItem: {alignItems: "center", borderRadius: 7, flexDirection: "row", gap: 9, marginBottom: 3, paddingHorizontal: 9, paddingVertical: 8},
  desktopNavActive: {backgroundColor: "#3b2575"},
  desktopNavText: {color: "#e5eef9", fontSize: 12, fontWeight: "700"},
  proCard: {backgroundColor: "#111a2d", borderColor: "#223552", borderRadius: 8, borderWidth: 1, marginTop: 20, padding: 12},
  proCardTitle: {color: "#e7c8ff", fontSize: 13, fontWeight: "900"},
  proCardText: {color: "#aebfd0", fontSize: 11, lineHeight: 16, marginTop: 6},
  upgradeButton: {alignItems: "center", backgroundColor: "#6e38f5", borderRadius: 6, marginTop: 10, paddingVertical: 8},
  upgradeText: {color: "#ffffff", fontSize: 11, fontWeight: "900"},
  sentimentCard: {backgroundColor: "#0a1b2b", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, marginTop: 14, padding: 12},
  sentimentArc: {borderRadius: 99, flexDirection: "row", height: 10, marginBottom: 8, overflow: "hidden"},
  sentimentSegment: {flex: 1},
  sentimentRed: {backgroundColor: "#ff5368"},
  sentimentAmber: {backgroundColor: "#f7c846"},
  sentimentGreen: {backgroundColor: "#20e188", flex: 1.8},
  sentimentBody: {gap: 4},
  sentimentScore: {color: "#2fed86", fontSize: 30, fontWeight: "900", textAlign: "center"},
  sentimentLabel: {color: "#2fed86", fontSize: 11, fontWeight: "900", marginBottom: 8, textAlign: "center"},
  desktopMain: {flex: 1, minWidth: 0},
  desktopTop: {alignItems: "center", flexDirection: "row", gap: 10, paddingHorizontal: 14, paddingTop: 10},
  desktopSearch: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#20334b", borderRadius: 8, borderWidth: 1, flexDirection: "row", gap: 8, paddingHorizontal: 10, width: 300},
  desktopInput: {color: "#edf5ff", flex: 1, fontSize: 12, paddingVertical: 9},
  desktopIconButton: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#20334b", borderRadius: 8, borderWidth: 1, height: 38, justifyContent: "center", width: 38},
  desktopScroll: {flex: 1},
  desktopContent: {padding: 14, paddingBottom: 20},
  desktopGrid: {flexDirection: "row", gap: 12},
  desktopChartColumn: {flex: 1.9, minWidth: 0},
  desktopRightRail: {flex: 1, maxWidth: 390, minWidth: 320},
  desktopLowerGrid: {flexDirection: "row", gap: 12},
  desktopQuote: {alignItems: "stretch", backgroundColor: "#0a1c2a", borderColor: "#1c4862", borderRadius: 8, borderWidth: 1, flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 10, padding: 12},
  desktopQuoteIdentity: {flex: 1.2, minWidth: 150},
  desktopQuotePrice: {minWidth: 105},
  desktopQuoteMetrics: {flex: 2, flexDirection: "row", flexWrap: "wrap", gap: 8, minWidth: 280},
  desktopRangeCard: {backgroundColor: "#0b1625", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, minWidth: 126, paddingHorizontal: 10, paddingVertical: 9},
  desktopRangeValue: {color: "#edf5ff", fontSize: 15, fontWeight: "900", marginTop: 5},
  desktopTicker: {color: "#ffffff", fontSize: 26, fontWeight: "900"},
  desktopCompany: {color: "#dbe9f5", fontSize: 13},
  desktopSector: {color: "#89a4b8", fontSize: 11, marginTop: 3},
  desktopPrice: {color: "#ffffff", fontSize: 23, fontWeight: "900"},
  desktopGain: {color: "#32e881", fontSize: 13, fontWeight: "900"},
  watchButton: {borderColor: "#6337b8", borderRadius: 8, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 9},
  watchText: {color: "#bd83ff", fontSize: 11, fontWeight: "800"},
  desktopToolbar: {borderBottomColor: "#13283f", borderBottomWidth: 1, flexDirection: "row", gap: 18, paddingBottom: 10},
  toolbarText: {color: "#9fb2c8", fontSize: 12},
  toolbarActive: {backgroundColor: "#163d5e", borderRadius: 5, color: "#6dcfff", overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4},
  candleArea: {backgroundColor: "#071522", borderColor: "#14263a", borderRadius: 8, borderWidth: 1, flexDirection: "row", height: 380, marginTop: 10, overflow: "hidden"},
  indicatorRail: {padding: 12, width: 120},
  indicatorText: {color: "#aabbd0", fontSize: 11, marginBottom: 11},
  indicatorMuted: {color: "#7d91aa", fontSize: 10, fontWeight: "800", lineHeight: 14},
  candleGrid: {alignItems: "flex-end", flex: 1, flexDirection: "row", gap: 5, padding: 22},
  candle: {borderRadius: 2, width: 8},
  candleChart: {backgroundColor: "#06111d", borderColor: "#14263a", borderRadius: 9, borderWidth: 1, flex: 1, margin: 8, overflow: "hidden", position: "relative"},
  candleRow: {bottom: 16, flexDirection: "row", gap: 3, left: 12, position: "absolute", right: 52, top: 14},
  candleSlot: {flex: 1, minWidth: 4, position: "relative"},
  candleWick: {left: "48%", position: "absolute", width: 1},
  candleBody: {borderRadius: 2, left: "25%", position: "absolute", width: "50%"},
  candleBodyActive: {borderColor: "#d9fbff", borderWidth: 1},
  candleBodyDesktop: {left: "20%", width: "60%"},
  chartGridLine: {backgroundColor: "#17304a", height: 1, left: 0, opacity: 0.65, position: "absolute", right: 0},
  priceAxis: {color: "#6f87a1", fontSize: 9, position: "absolute", right: 8},
  chartLevel: {borderTopWidth: 1, left: 12, opacity: 0.95, position: "absolute", right: 52},
  chartLevelText: {alignSelf: "flex-end", backgroundColor: "#06111d", fontSize: 8, fontWeight: "900", marginTop: -10, overflow: "hidden", paddingHorizontal: 4},
  chartPricePill: {alignItems: "center", backgroundColor: "#113a50", borderColor: "#2a9ac0", borderRadius: 4, borderWidth: 1, paddingHorizontal: 4, paddingVertical: 2, position: "absolute", right: 8},
  chartPricePillText: {color: "#9bf3ff", fontSize: 8, fontWeight: "900"},
  levelEntry: {borderColor: "#2f8cff", color: "#4aa3ff"},
  levelTarget: {borderColor: "#20e188", color: "#20e188"},
  levelStop: {borderColor: "#ff5368", color: "#ff5368"},
  chartLegend: {flexDirection: "row", flexWrap: "wrap", gap: 7, marginHorizontal: 8, marginTop: 6},
  chartLegendText: {fontSize: 9, fontWeight: "900"},
  tradeZone: {backgroundColor: "rgba(32,225,136,0.14)", borderColor: "rgba(32,225,136,0.35)", borderRadius: 4, borderWidth: 1, height: 46, position: "absolute", right: 52, width: "24%"},
  signalBuy: {backgroundColor: "#092f1a", borderColor: "#1ad675", borderRadius: 4, borderWidth: 1, color: "#26f084", fontSize: 8, fontWeight: "900", left: "26%", overflow: "hidden", paddingHorizontal: 4, paddingVertical: 3, position: "absolute", top: "28%"},
  signalBuyDesktop: {fontSize: 10, left: "30%", padding: 5},
  signalBreak: {backgroundColor: "#092f1a", borderColor: "#1ad675", borderRadius: 4, borderWidth: 1, color: "#26f084", fontSize: 8, fontWeight: "900", left: "58%", overflow: "hidden", paddingHorizontal: 4, paddingVertical: 3, position: "absolute", top: "18%"},
  signalBreakDesktop: {fontSize: 10, left: "62%", padding: 5},
  signalStop: {color: "#ff5265", fontSize: 8, fontWeight: "900", position: "absolute", right: 54, top: "66%"},
  signalStopDesktop: {fontSize: 10, right: 70},
  chartReadout: {backgroundColor: "#081929", borderColor: "#1b3048", borderRadius: 8, borderWidth: 1, gap: 3, marginHorizontal: 8, marginTop: 3, padding: 9},
  chartReadoutTitle: {color: "#7de6ff", fontSize: 11, fontWeight: "900"},
  chartReadoutText: {color: "#90a6bf", fontSize: 10},
  oscillator: {backgroundColor: "#0c1430", borderColor: "#223552", borderRadius: 7, borderWidth: 1, height: 82, marginTop: 8, overflow: "hidden"},
  oscillatorLine: {backgroundColor: "#8d55ff", borderRadius: 99, height: 2, marginLeft: 18, marginTop: 36, width: "80%"},
  bottomMovers: {backgroundColor: "#0a1b2b", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, marginTop: 4},
  bottomMoverContent: {alignItems: "center", gap: 14, padding: 10},
  bottomTitle: {color: "#5aa8ff", fontSize: 11, fontWeight: "900", marginRight: 8},
  mover: {alignItems: "center", borderLeftColor: "#284057", borderLeftWidth: 1, flexDirection: "row", gap: 8, paddingLeft: 14},
  moverSymbol: {color: "#dbe9f5", fontSize: 12, fontWeight: "900"},
  moverDelta: {color: "#2fed86", fontSize: 10, fontWeight: "900"},
  moverDeltaBad: {color: "#ff5368"},
  topbar: {
    alignItems: "center",
    borderBottomColor: "#15253a",
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  brandRow: {alignItems: "center", flex: 1, flexDirection: "row", gap: 12, minWidth: 0},
  logo: {alignItems: "center", backgroundColor: "#6d38ff", borderColor: "#2de0ff", borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36},
  logoText: {color: "#ffffff", fontSize: 12, fontWeight: "900"},
  logoImage: {borderColor: "#2de0ff", borderRadius: 10, borderWidth: 1, height: 40, width: 40},
  brandText: {flex: 1, minWidth: 0},
  eyebrow: {color: "#55708e", fontSize: 8, fontWeight: "800", letterSpacing: 1.3},
  title: {color: "#eaf2ff", fontSize: 20, fontWeight: "900", marginTop: 1},
  subtitle: {color: "#7286a1", fontSize: 10, marginTop: 0},
  livePill: {alignItems: "center", backgroundColor: "#0b211c", borderColor: "#1e483b", borderRadius: 999, borderWidth: 1, flexDirection: "row", gap: 5, paddingHorizontal: 8, paddingVertical: 5},
  liveDot: {backgroundColor: "#5ce19b", borderRadius: 99, height: 7, width: 7},
  liveText: {color: "#74e6ae", fontSize: 9, fontWeight: "900"},
  tape: {backgroundColor: "#050b13", borderBottomColor: "#122235", borderBottomWidth: 1, maxHeight: 48},
  tapeContent: {gap: 7, paddingHorizontal: 10, paddingVertical: 6},
  tapeItem: {backgroundColor: "#0b1625", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, minWidth: 118, paddingHorizontal: 9, paddingVertical: 6, position: "relative"},
  tapeLabel: {color: "#c8d7e8", fontSize: 8, fontWeight: "900"},
  tapeValue: {color: "#edf5ff", fontSize: 11, fontWeight: "800", marginRight: 38, marginTop: 2},
  tapeDelta: {color: "#29e77c", fontSize: 10, fontWeight: "900", position: "absolute", right: 8, top: 6},
  tapeDeltaBad: {color: "#ff5d6c"},
  search: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#20334b", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 8, marginHorizontal: 10, marginTop: 8, paddingHorizontal: 10},
  input: {color: "#e9f3ff", flex: 1, fontSize: 13, fontWeight: "800", paddingVertical: 9},
  iconButton: {alignItems: "center", backgroundColor: "#16304a", borderRadius: 8, height: 31, justifyContent: "center", width: 31},
  events: {maxHeight: 48},
  eventContent: {gap: 8, paddingHorizontal: 10, paddingTop: 8},
  eventIntro: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, justifyContent: "center", paddingHorizontal: 10},
  eventIntroText: {color: "#edf5ff", fontSize: 10, fontWeight: "900"},
  eventCard: {alignItems: "center", backgroundColor: "#10141d", borderColor: "#2b3041", borderRadius: 8, borderWidth: 1, flexDirection: "row", gap: 7, minWidth: 165, paddingHorizontal: 9, paddingVertical: 7},
  eventDot: {backgroundColor: "#ff4d5f", borderRadius: 99, height: 8, width: 8},
  eventDotMed: {backgroundColor: "#ffbf30"},
  eventLevel: {color: "#ff5d6c", fontSize: 8, fontWeight: "900"},
  eventLevelMed: {color: "#ffbf30"},
  eventTitle: {color: "#dceaff", fontSize: 10, fontWeight: "800"},
  eventTime: {color: "#7187a1", fontSize: 9, marginLeft: "auto"},
  nav: {maxHeight: 48},
  navContent: {gap: 7, paddingHorizontal: 10, paddingVertical: 8},
  navItem: {alignItems: "center", backgroundColor: "#08111d", borderColor: "#16263a", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 6, paddingHorizontal: 10, paddingVertical: 8},
  navItemActive: {backgroundColor: "#10233a", borderColor: "#235b75"},
  navText: {color: "#8094ad", fontSize: 11, fontWeight: "800"},
  navTextActive: {color: "#58d7ff"},
  body: {flex: 1},
  bodyContent: {flexGrow: 1, paddingBottom: 100, paddingHorizontal: 10},
  bottomNav: {
    alignItems: "center",
    backgroundColor: "#07111d",
    borderTopColor: "#16283d",
    borderTopWidth: 1,
    flexDirection: "row",
    gap: 6,
    justifyContent: "space-around",
    paddingBottom: 9,
    paddingHorizontal: 8,
    paddingTop: 8,
  },
  bottomNavItem: {
    alignItems: "center",
    borderColor: "transparent",
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    gap: 3,
    minHeight: 52,
    justifyContent: "center",
  },
  bottomNavItemActive: {backgroundColor: "#10233a", borderColor: "#245f7a"},
  bottomNavText: {color: "#7c90a8", fontSize: 8, fontWeight: "800"},
  bottomNavTextActive: {color: "#74e6ff"},
  pageHead: {alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 7, marginTop: 4},
  pageTitle: {color: "#eaf2ff", flex: 1, fontSize: 18, fontWeight: "900"},
  refresh: {alignItems: "center", borderColor: "#273b55", borderRadius: 8, borderWidth: 1, flexDirection: "row", gap: 5, paddingHorizontal: 9, paddingVertical: 6},
  refreshText: {color: "#b9cbe0", fontSize: 10, fontWeight: "800"},
  quotePanel: {backgroundColor: "#081929", borderColor: "#1b3048", borderRadius: 10, borderWidth: 1, marginBottom: 9, overflow: "hidden"},
  quoteTop: {alignItems: "flex-start", flexDirection: "row", flexWrap: "wrap", gap: 10, justifyContent: "space-between", padding: 12},
  quoteIdentity: {flex: 1, minWidth: 0},
  quoteTicker: {color: "#ffffff", fontSize: 22, fontWeight: "900"},
  quoteName: {color: "#c8d7e8", fontSize: 11, marginTop: 2},
  quoteSector: {color: "#7187a1", fontSize: 9, marginTop: 2},
  quotePriceBox: {alignItems: "flex-end"},
  quotePrice: {color: "#edf5ff", fontSize: 19, fontWeight: "900"},
  quoteChange: {color: "#29e77c", fontSize: 11, fontWeight: "900", marginTop: 2},
  quoteChangeBad: {color: "#ff5d6c"},
  realTime: {color: "#74e6ae", fontSize: 9, marginTop: 2},
  timeframes: {borderTopColor: "#13283f", borderTopWidth: 1, flexDirection: "row", gap: 5, paddingHorizontal: 10, paddingVertical: 7},
  timeframe: {borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4},
  timeframeActive: {backgroundColor: "#153b52"},
  timeframeText: {color: "#8499b1", fontSize: 10},
  timeframeTextActive: {color: "#67ddff", fontWeight: "900"},
  compactToolbar: {flexDirection: "row", flexWrap: "wrap", gap: 5, marginBottom: 7},
  hero: {backgroundColor: "#0b1726", borderColor: "#1b3048", borderRadius: 12, borderWidth: 1, marginBottom: 10, padding: 13},
  badge: {alignSelf: "flex-start", backgroundColor: "#0a2636", borderColor: "#174d65", borderRadius: 999, borderWidth: 1, color: "#5edcff", fontSize: 8, fontWeight: "900", letterSpacing: 1, marginBottom: 6, overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4},
  heroTicker: {color: "#ffffff", fontSize: 23, fontWeight: "900"},
  heroName: {color: "#8397b0", fontSize: 12, lineHeight: 18, marginTop: 3},
  cards: {flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8},
  card: {backgroundColor: "#0b1725", borderColor: "#1a2d44", borderRadius: 9, borderWidth: 1, minHeight: 62, padding: 9, width: "48%"},
  cardLabel: {color: "#68809c", fontSize: 8, fontWeight: "800", letterSpacing: 0.7, textTransform: "uppercase"},
  cardValue: {color: "#edf5ff", fontSize: 15, fontWeight: "900", marginTop: 5},
  terminalGrid: {flexDirection: "row", gap: 8, marginBottom: 0},
  panel: {backgroundColor: "#091522", borderColor: "#1a2c43", borderRadius: 10, borderWidth: 1, flex: 1, marginBottom: 9, minWidth: 0, overflow: "hidden", padding: 11},
  panelTitle: {color: "#e7f2ff", fontSize: 13, fontWeight: "900", marginBottom: 8},
  mobileMovers: {flexDirection: "row", flexWrap: "wrap", gap: 8},
  mobileMover: {alignItems: "center", backgroundColor: "#0b1625", borderColor: "#1a2d44", borderRadius: 8, borderWidth: 1, flexDirection: "row", gap: 8, paddingHorizontal: 10, paddingVertical: 8},
  trendRow: {alignItems: "flex-start", flexDirection: "row", gap: 10},
  trendBadge: {alignItems: "center", backgroundColor: "#071522", borderColor: "#1c4862", borderRadius: 10, borderWidth: 1, gap: 5, justifyContent: "center", minHeight: 64, paddingHorizontal: 10, width: 92},
  trendBadgeText: {color: "#e9f3ff", fontSize: 11, fontWeight: "900", textAlign: "center"},
  trendCopy: {flex: 1, minWidth: 0},
  trendTitle: {color: "#74e6ff", fontSize: 14, fontWeight: "900", marginBottom: 4},
  trendText: {color: "#9aadc3", fontSize: 11, lineHeight: 17},
  sectionLabel: {color: "#7d93ad", fontSize: 10, fontWeight: "900", letterSpacing: 0.8, marginBottom: 7, marginTop: 4, textTransform: "uppercase"},
  chipRow: {gap: 7, paddingBottom: 8},
  filterChip: {backgroundColor: "#07111d", borderColor: "#20334b", borderRadius: 999, borderWidth: 1, paddingHorizontal: 11, paddingVertical: 8},
  filterChipActive: {backgroundColor: "#10334d", borderColor: "#2a9ac0"},
  filterChipText: {color: "#8ea2ba", fontSize: 11, fontWeight: "800"},
  filterChipTextActive: {color: "#74e6ff"},
  segmentGrid: {flexDirection: "row", flexWrap: "wrap", gap: 7, marginBottom: 9},
  segmentButton: {backgroundColor: "#07111d", borderColor: "#1b3048", borderRadius: 9, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 8},
  segmentButtonActive: {backgroundColor: "#122f45", borderColor: "#2a9ac0"},
  segmentText: {color: "#879bb3", fontSize: 11, fontWeight: "800"},
  segmentTextActive: {color: "#80e6ff"},
  alertSummary: {alignItems: "flex-start", backgroundColor: "#071522", borderColor: "#1c3f55", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 9, marginTop: 4, padding: 10},
  alertSummaryText: {color: "#b8c9dc", flex: 1, fontSize: 11, lineHeight: 17},
  scanRow: {alignItems: "flex-start", borderBottomColor: "#17283d", borderBottomWidth: 1, flexDirection: "row", gap: 10, paddingVertical: 11},
  rankBubble: {alignItems: "center", backgroundColor: "#10233a", borderColor: "#235b75", borderRadius: 9, borderWidth: 1, height: 30, justifyContent: "center", width: 30},
  rankText: {color: "#74e6ff", fontSize: 11, fontWeight: "900"},
  scanBody: {flex: 1, minWidth: 0},
  scanHead: {alignItems: "center", flexDirection: "row", justifyContent: "space-between"},
  scanSymbol: {color: "#edf5ff", fontSize: 15, fontWeight: "900"},
  scanScore: {color: "#2fed86", fontSize: 13, fontWeight: "900"},
  scanReason: {color: "#98abc2", fontSize: 11, lineHeight: 17, marginTop: 4},
  scanMetaRow: {flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 7},
  scanMeta: {backgroundColor: "#081929", borderColor: "#1d334d", borderRadius: 999, borderWidth: 1, color: "#9fc1da", fontSize: 9, fontWeight: "800", overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4},
  toggleRow: {alignItems: "center", backgroundColor: "#071522", borderColor: "#1b3048", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 10, marginBottom: 10, padding: 10},
  toggleTextGroup: {flex: 1, minWidth: 0},
  toggleLabel: {color: "#e9f3ff", fontSize: 12, fontWeight: "900"},
  toggleSub: {color: "#7187a1", fontSize: 9, marginTop: 2},
  togglePill: {backgroundColor: "#202b39", borderRadius: 999, height: 24, padding: 3, width: 43},
  togglePillActive: {backgroundColor: "#143e2e"},
  toggleKnob: {backgroundColor: "#8191a4", borderRadius: 99, height: 18, width: 18},
  toggleKnobActive: {backgroundColor: "#34e889", marginLeft: 19},
  toggleValue: {color: "#9fb2c8", fontSize: 10, fontWeight: "900", width: 28},
  ruleRow: {alignItems: "center", borderTopColor: "#17283d", borderTopWidth: 1, flexDirection: "row", gap: 8, paddingVertical: 8},
  ruleText: {color: "#b8c9dc", flex: 1, fontSize: 11, fontWeight: "700"},
  alertEvent: {alignItems: "flex-start", borderBottomColor: "#17283d", borderBottomWidth: 1, flexDirection: "row", gap: 9, paddingVertical: 10},
  alertDot: {backgroundColor: "#ffcc4d", borderRadius: 99, height: 10, marginTop: 4, width: 10},
  alertDotGood: {backgroundColor: "#32e881"},
  alertEventBody: {flex: 1, minWidth: 0},
  alertEventTitle: {color: "#edf5ff", fontSize: 12, fontWeight: "900", lineHeight: 17},
  alertEventText: {color: "#8ea2ba", fontSize: 10, lineHeight: 15, marginTop: 2},
  moreGrid: {flexDirection: "row", flexWrap: "wrap", gap: 9},
  moreTile: {alignItems: "center", backgroundColor: "#0b1725", borderColor: "#1a2d44", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 9, minHeight: 56, padding: 12, width: "48%"},
  moreTitle: {color: "#dceaff", flex: 1, fontSize: 12, fontWeight: "900"},
  setupHead: {alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", marginBottom: 6},
  setupSignal: {color: "#43e778", fontSize: 14, fontWeight: "900"},
  setupSub: {color: "#74e6ae", fontSize: 10, marginTop: 2},
  setupScore: {color: "#edf5ff", fontSize: 22, fontWeight: "900"},
  scoreSuffix: {color: "#8aa0b8", fontSize: 9},
  spark: {alignItems: "flex-end", backgroundColor: "#07111d", borderColor: "#14263a", borderRadius: 9, borderWidth: 1, flexDirection: "row", gap: 3, height: 132, overflow: "hidden", paddingHorizontal: 8, paddingVertical: 10},
  sparkBar: {borderRadius: 4, flex: 1, minWidth: 3},
  chartMeta: {flexDirection: "row", justifyContent: "space-between", marginTop: 6},
  metaText: {color: "#607994", fontSize: 9},
  decisionMain: {color: "#68dcff", fontSize: 24, fontWeight: "900", marginBottom: 5},
  valueRow: {borderBottomColor: "#17283d", borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 6},
  valueLabel: {color: "#7086a0", fontSize: 10},
  valueValue: {color: "#eaf2ff", fontSize: 10, fontWeight: "900", marginLeft: 6},
  longText: {color: "#9aadc3", fontSize: 11, lineHeight: 17},
  noticeText: {backgroundColor: "#0b1928", borderColor: "#27405b", borderRadius: 9, borderWidth: 1, color: "#83a0bb", fontSize: 11, lineHeight: 17, padding: 10},
  launchScreen: {borderColor: "#15314a", borderRadius: 18, borderWidth: 1, minHeight: 620, overflow: "hidden"},
  launchScreenFull: {borderRadius: 0, borderWidth: 0, flex: 1, minHeight: "100%"},
  launchImage: {borderRadius: 18},
  launchShade: {alignItems: "center", backgroundColor: "rgba(1, 7, 18, 0.18)", flex: 1, justifyContent: "flex-end", paddingBottom: 54, paddingHorizontal: 28},
  launchShadeFull: {backgroundColor: "rgba(1, 7, 18, 0.08)", paddingBottom: 70, paddingHorizontal: 28},
  launchContent: {alignItems: "center", gap: 12, width: "100%"},
  launchProgress: {backgroundColor: "rgba(85, 217, 255, 0.16)", borderRadius: 999, height: 3, maxWidth: 280, overflow: "hidden", width: "76%"},
  launchProgressFill: {backgroundColor: "#55d9ff", borderRadius: 999, height: 3, width: "58%"},
  launchText: {color: "#e8f2ff", fontSize: 15, fontWeight: "800", letterSpacing: 0.2, textAlign: "center"},
  launchSubtext: {color: "#91a6bc", fontSize: 12, lineHeight: 17, maxWidth: 290, textAlign: "center"},
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
  newsHead: {alignItems: "flex-start", flexDirection: "row", gap: 9},
  newsBody: {flex: 1, minWidth: 0},
  newsDot: {backgroundColor: "#f4c84a", borderRadius: 99, height: 10, marginTop: 5, width: 10},
  newsDotGood: {backgroundColor: "#2fed86"},
  newsDotBad: {backgroundColor: "#ff5368"},
  newsTitle: {color: "#e8f1ff", fontSize: 14, fontWeight: "900", lineHeight: 20},
  newsMeta: {color: "#5e7792", fontSize: 10, marginTop: 4},
  authInput: {backgroundColor: "#07111d", borderColor: "#20334b", borderRadius: 10, borderWidth: 1, color: "#ffffff", fontSize: 14, marginTop: 10, paddingHorizontal: 12, paddingVertical: 12},
  primaryButton: {alignItems: "center", alignSelf: "flex-start", backgroundColor: "#113a50", borderColor: "#35bfe8", borderRadius: 10, borderWidth: 1, flexDirection: "row", gap: 8, justifyContent: "center", marginTop: 10, minHeight: 42, paddingHorizontal: 14},
  primaryButtonText: {color: "#7de6ff", fontSize: 13, fontWeight: "900"},
  secondaryButton: {alignItems: "center", alignSelf: "flex-start", backgroundColor: "#0c1827", borderColor: "#273b55", borderRadius: 10, borderWidth: 1, marginTop: 2, paddingHorizontal: 14, paddingVertical: 10},
  secondaryButtonText: {color: "#b9cbe0", fontSize: 13, fontWeight: "900"},
});
