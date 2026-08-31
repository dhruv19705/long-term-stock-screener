export type ScreenRow = {
  stock: string;
  sector: string;
  sector_focus: string;
  model_sector: string;
  analysis_depth: string;
  pe?: number | null;
  pb?: number | null;
  roe_pct?: number | null;
  revenue_growth_pct?: number | null;
  return_1y_pct?: number | null;
  composite_score: number;
  composite_percentile?: number | null;
  fundamental_strength?: number | null;
  valuation: string;
  confidence?: number | null;
  stock_risk_score?: number | null;
  recommendation: string;
  raw_recommendation?: string | null;
  calibration_applied?: boolean;
  quality_grade?: string;
  peer_band?: string;
  peer_rank?: number | null;
  data_source?: string;
};

export const REC_ORDER = ["STRONG BUY", "BUY", "HOLD", "AVOID", "SELL"] as const;

export function recRank(rec: string): number {
  const i = REC_ORDER.indexOf(rec as (typeof REC_ORDER)[number]);
  return i >= 0 ? REC_ORDER.length - i : 0;
}

export function formatTicker(stock: string): string {
  return stock.replace(/\.NS$/i, "");
}

export function sectorLabel(id: string): string {
  return id.replace(/_/g, " ");
}
