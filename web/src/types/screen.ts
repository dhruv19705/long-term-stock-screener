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

const SECTOR_DISPLAY_NAMES: Record<string, string> = {
  it: "IT",
  fmcg: "FMCG",
  psu: "PSU",
  banking: "Banking",
  pharma: "Pharma",
  auto: "Auto",
  energy: "Energy",
  metals: "Metals",
  capital_goods: "Capital Goods",
  insurance: "Insurance",
  defensive: "Defensive",
  cyclical: "Cyclical",
  no_financials: "Ex-Financials",
  both: "Banking & IT",
  all: "All Sectors",
};

export function sectorLabel(id: string): string {
  if (!id) return "";
  const key = id.toLowerCase().trim();
  if (SECTOR_DISPLAY_NAMES[key]) {
    return SECTOR_DISPLAY_NAMES[key];
  }
  return id
    .split("_")
    .map((w) => {
      const lower = w.toLowerCase();
      if (lower === "it") return "IT";
      if (lower === "fmcg") return "FMCG";
      if (lower === "psu") return "PSU";
      return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    })
    .join(" ");
}
