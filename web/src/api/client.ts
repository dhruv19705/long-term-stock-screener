import axios from "axios";
import type { ScreenRow } from "../types/screen";

const api = axios.create({ baseURL: "/api" });

export type RiskProfile = {
  id: string;
  label: string;
  sector_filter: string;
  scores?: Record<string, number>;
  max_stock_risk?: number;
  max_beta?: number;
  cyclical_ok?: boolean;
  diversify_sectors?: boolean;
  diversification_level?: string;
  needs_liquidity?: boolean;
  valuation_pref?: string;
  profile_summary?: string[];
  profile_scores?: Record<string, number>;
};

export type QuestionnaireChapter = {
  id: string;
  label: string;
  description: string;
};

export type QuestionnairePreview = {
  profile_scores: Record<string, number>;
  leading_profile_id: string;
  leading_profile_label: string;
  profile_summary: string[];
  answered_count: number;
  total_questions: number;
};

export type Fit = {
  ticker: string;
  fit_score: number;
  fit_label: string;
  exclude: boolean;
  reasons: string[];
  recommendation: string;
  action_label: string;
  headline: string;
  composite_score: number;
  stock_risk_score: number;
  quality_grade: string;
  peer_percentile?: number | null;
  peer_band: string;
  sector_focus: string;
  data_quality_flags?: string[];
};

export type QuestionAnswer = {
  id: string;
  question: string;
  dimension: string;
  signal: string;
  metrics: Record<string, unknown>;
  peer_rank?: string | null;
  answer: string;
};

export type QuoteSnapshot = {
  ticker?: string | null;
  company_name?: string | null;
  currency?: string | null;
  current_price?: number | null;
  previous_close?: number | null;
  change?: number | null;
  change_pct?: number | null;
  day_open?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  week_52_high?: number | null;
  week_52_low?: number | null;
  volume?: number | null;
  avg_volume?: number | null;
  market_cap?: number | null;
  pe?: number | null;
  pb?: number | null;
  dividend_yield_pct?: number | null;
  roe_pct?: number | null;
  return_1y_pct?: number | null;
};

export type Quote = QuoteSnapshot & {
  ticker: string;
  history: { date: string; close: number }[];
};

export type Interpretation = {
  ticker: string;
  sector: string;
  sector_focus: string;
  model_sector?: string;
  recommendation: string;
  raw_recommendation?: string | null;
  calibration_applied?: boolean;
  composite_score: number;
  composite_percentile?: number | null;
  quality_grade?: string;
  peer_band?: string;
  stock_risk_score: number;
  confidence: number;
  valuation_label: string;
  headline: string;
  questions: QuestionAnswer[];
  bull_case: string[];
  bear_case: string[];
  key_risk: string;
  verdict: string;
  score_breakdown: Record<string, number>;
  peer_rank?: number | null;
  peer_count?: number | null;
  red_flag: boolean;
  hard_gate_fail: boolean;
  risk_flags?: string[];
  quote?: QuoteSnapshot | null;
};

export type SectorBucket = {
  id: string;
  model_sector: string;
  display_sector: string;
  cyclical: boolean;
  ticker_count: number;
};

export async function fetchQuestionnaire() {
  const { data } = await api.get("/questionnaire");
  return data as {
    profiles: { id: string; label: string }[];
    chapters: QuestionnaireChapter[];
    questions: {
      id: string;
      text: string;
      chapter: string;
      options: { id: string; label: string }[];
    }[];
  };
}

export async function previewQuestionnaire(answers: Record<string, string>) {
  const { data } = await api.post("/questionnaire/preview", { answers });
  return data as QuestionnairePreview;
}

export async function submitQuestionnaire(answers: Record<string, string>) {
  const { data } = await api.post("/questionnaire/submit", { answers });
  return data as RiskProfile;
}

export async function fetchRecommendations(profile: RiskProfile) {
  const { data } = await api.post("/recommend", {
    risk_profile_id: profile.id,
    sector_filter: profile.sector_filter || "all",
    label: profile.label,
    max_stock_risk: profile.max_stock_risk,
    max_beta: profile.max_beta,
    cyclical_ok: profile.cyclical_ok,
    diversify_sectors: profile.diversify_sectors,
    diversification_level: profile.diversification_level,
    needs_liquidity: profile.needs_liquidity,
    valuation_pref: profile.valuation_pref,
    scores: profile.scores,
  });
  return data as {
    risk_profile: RiskProfile;
    picks: Fit[];
    avoid: Fit[];
    summary: string;
    picks_by_sector: Record<string, Fit[]>;
  };
}

export async function fetchSectors() {
  const { data } = await api.get("/sectors");
  return data as { sectors: SectorBucket[]; filters: string[] };
}

export async function fetchScreen(sector: string = "all") {
  const { data } = await api.get("/screen", { params: { sector } });
  return data as {
    rows: ScreenRow[];
    dropped: { ticker: string; reason: string }[];
    count: number;
    total_universe?: number;
  };
}

export type BenchmarkSummary = {
  distribution: {
    counts: Record<string, number>;
    total: number;
    bullish_pct: number;
    bearish_pct: number;
    targets: { bullish_min: number; bullish_max: number; bearish_min: number; bearish_max: number };
  };
  nifty50: {
    suite: string;
    direction_pct: number;
    severity_pct: number;
    false_sell_on_buy: number;
    matched: number;
    top_mismatches: { ticker: string; ours?: string; street?: string; causes?: string[]; error?: string }[];
  };
  golden: {
    suite: string;
    direction_pct: number;
    severity_pct: number;
    false_sell_on_buy: number;
    matched: number;
    top_mismatches: { ticker: string; ours?: string; street?: string; causes?: string[]; error?: string }[];
  };
  calibrated_count: number;
  generated_at: number;
};

export async function fetchBenchmarkSummary(refresh = false) {
  const { data } = await api.get("/benchmark/summary", { params: refresh ? { refresh: true } : {} });
  return data as BenchmarkSummary;
}

export async function fetchSectorSummary(sector: string) {
  const { data } = await api.get(`/sectors/${sector}/summary`);
  return data;
}

export async function fetchInterpret(ticker: string) {
  const { data } = await api.get(`/stock/${encodeURIComponent(ticker)}/interpret`);
  return data as Interpretation;
}

export async function fetchQuote(ticker: string) {
  const { data } = await api.get("/quote", { params: { t: ticker } });
  return data as Quote;
}

export function mergeQuotes(
  ...parts: Array<QuoteSnapshot | Quote | null | undefined>
): QuoteSnapshot & { history: { date: string; close: number }[] } {
  const out: QuoteSnapshot & { history: { date: string; close: number }[] } = { history: [] };
  for (const part of parts) {
    if (!part) continue;
    for (const [key, value] of Object.entries(part)) {
      if (key === "history") {
        if (Array.isArray(value) && value.length && out.history.length === 0) {
          out.history = value;
        }
        continue;
      }
      if (value == null || value === "") continue;
      const current = (out as Record<string, unknown>)[key];
      if (current == null || current === "") {
        (out as Record<string, unknown>)[key] = value;
      }
    }
  }
  return out;
}
