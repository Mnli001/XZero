export type Checklist = Record<string, boolean>;

export interface SignalInfo {
  action: string;
  side?: string;
  price?: number;
  sl?: number;
  tp?: number;
  reason?: string;
  risk_dist?: number;
}

export interface Confluence {
  score: number;
  bias: string;
  votes: Record<string, number>;
  weights: Record<string, number>;
  disclaimer: string;
}

export interface SMCState {
  bias: string;
  bias_source?: string;
  checklist?: Checklist;
  sweep?: any;
  structure?: any;
  active_fvgs?: any[];
  valuation?: any;
}

export interface Analysis {
  symbol: string;
  timeframe: string;
  data_source: string;
  time: string;
  price: number;
  candles: any[];
  signal: SignalInfo;
  explanation?: { rules_passed: string[]; rules_failed: string[]; confidence?: number; bias_source?: string } | null;
  confluence?: Confluence | null;
  smc: SMCState;
  risk?: any;
  ai_review?: {
    verdict: string;
    confidence: number;
    reasoning: string;
    checklist: Checklist;
    referenced_sources: string[];
    provider: string;
    advisory_only: boolean;
  } | null;
  strategy?: { name: string; mode: string };
}

export interface StrategyRow {
  name: string;
  symbol: string;
  timeframe: string;
  mode: string;
  status: string;
  backtest_gate?: any;
  paper_gate?: any;
  paper_metrics?: any;
  live_trades: number;
  live_auto_allowed: boolean;
  gate_reasons: string[];
}
