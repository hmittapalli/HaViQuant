export type Signal = "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "STRONG SELL" | "UNKNOWN";

export interface Quote {
  ticker: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  status: string;
  source?: string;
}

export interface Decision {
  ticker: string;
  decision: Signal | null;
  score: number | null;
  status: string;
}

export interface ResearchPhase {
  status: string;
  score?: number | null;
}

export interface ResearchStatus {
  ticker: string;
  status: string;
  production_signal_impact: boolean;
  phases: Record<string, string>;
}
