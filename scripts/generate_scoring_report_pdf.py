"""Generate PDF technical report: docs/SCORING_ARCHITECTURE_REPORT.pdf"""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SCORING_ARCHITECTURE_REPORT.pdf"


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.set_x(self.l_margin)
            self.cell(140, 8, "Full Universe NSE Stock Screener - Technical Report", align="L")
            self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.line(self.l_margin, 16, self.w - self.r_margin, 16)
            self.ln(4)
            self.set_x(self.l_margin)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, "Confidential - Internal Technical Documentation", align="C")

    def chapter_title(self, num: str, title: str):
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 40, 80)
        self.multi_cell(0, 10, f"{num}. {title}")
        self.ln(2)
        self.set_draw_color(20, 40, 80)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def section(self, title: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.multi_cell(0, 7, title)
        self.ln(2)

    def body(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet_list(self, items: list[str]):
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.set_x(self.l_margin)
            self.multi_cell(0, 5, f"  - {item}")
        self.ln(2)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        if col_widths is None:
            w = 190 // len(headers)
            col_widths = [w] * len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 235, 245)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 8)
        fill = False
        for row in rows:
            if self.get_y() > 270:
                self.add_page()
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, cell[:40], border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(3)


def build() -> None:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- Cover ---
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(20, 40, 80)
    pdf.multi_cell(0, 14, "Full Universe NSE\nStock Screener", align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 8, "Technical Architecture & Scoring Methodology", align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "Document type: Technical Reference Report\n"
        "Version: 2.0 (Recommendation Strategy v3)\n"
        "Universe: ~181 NSE tickers, 8 sector buckets\n"
        "Stack: Python screener | FastAPI | React UI",
        align="C",
    )
    pdf.ln(30)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "Generated from quant screener codebase", align="C")

    # --- TOC ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    toc = [
        "1. Executive Summary",
        "2. System Architecture Overview",
        "3. Sector Taxonomy & Peer Groups",
        "4. Data Acquisition Layer",
        "5. Pipeline & Quality Control",
        "6. Scoring Framework (Shared Mechanics)",
        "7. Sector-Specific Scoring Models",
        "8. Recommendation Engine (Three-Axis v3)",
        "9. Interpretation & Risk Question Engine",
        "10. Profile Matching & Personalization",
        "11. Configuration Reference",
        "12. API, UI & Operational Scripts",
        "13. Worked Examples",
        "Appendix A: Formulas & Thresholds",
        "Appendix B: Glossary",
    ]
    pdf.set_font("Helvetica", "", 11)
    for line in toc:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    # --- 1 Executive Summary ---
    pdf.chapter_title("1", "Executive Summary")
    pdf.body(
        "This report documents the full-universe Indian equity screener: how stocks are "
        "classified, fetched, scored, interpreted, and matched to investor risk profiles. "
        "The system screens approximately 181 NSE-listed names across eight curated sector "
        "buckets using a two-tier analysis model (deep for Banking and IT; standard for all "
        "other sectors)."
    )
    pdf.section("Key design decisions")
    pdf.bullet_list([
        "Sectors are assigned via universe.yaml, not yfinance sector/industry fields.",
        "yfinance provides prices, fundamentals, and financial statements; banking asset-quality "
        "ratios come from curated JSON.",
        "Composite scores are peer-relative within cohorts (e.g. private banks vs PSU banks).",
        "Recommendations use three axes: absolute quality (A-F), peer rank band, and action label.",
        "Large-cap floor prevents mega-caps from AVOID/SELL unless hard gates fail.",
        "Rule-based inference (YAML + Python); no LLM in the scoring path.",
    ])
    pdf.section("Current recommendation distribution (typical full screen)")
    pdf.bullet_list([
        "STRONG BUY / BUY: ~30-35% of universe",
        "HOLD: ~40-45%",
        "AVOID / SELL: ~20-25%",
        "181/181 tickers typically pass QC after cache refresh",
    ])

    # --- 2 Architecture ---
    pdf.chapter_title("2", "System Architecture Overview")
    pdf.body(
        "Data flows: Configuration (universe.yaml, weights, risk YAML) -> Fetcher (yfinance + cache "
        "+ NSE fallback) -> QC filter -> Scoring (composite.py / generic.py) -> Interpretation "
        "(stock_analyst.py) -> Profile matcher (risk_matcher.py) -> API / CLI / React UI."
    )
    pdf.table(
        ["Layer", "Primary modules", "Output"],
        [
            ["Config", "config_loader.py, universe.yaml", "Ticker metadata, peer sets"],
            ["Data", "fetcher.py, banking.py, normalize.py", "StockMetrics per ticker"],
            ["Score", "composite.py, generic.py, action_matrix.py", "ScoreResult"],
            ["Interpret", "stock_analyst.py, signals.py", "StockInterpretation"],
            ["Match", "risk_matcher.py, questionnaire.py", "FitResult picks"],
            ["Serve", "api/main.py, cli.py, web/", "REST + UI"],
        ],
        [35, 75, 80],
    )

    # --- 3 Sectors ---
    pdf.chapter_title("3", "Sector Taxonomy & Peer Groups")
    pdf.table(
        ["Bucket", "Model", "Depth", "Cyclical", "Peer group"],
        [
            ["banking", "BANKING", "deep", "No", "private OR psu sub-cohort"],
            ["it", "IT", "deep", "No", "all IT tickers (~31)"],
            ["fmcg", "FMCG", "standard", "No", "FMCG bucket"],
            ["pharma", "PHARMA", "standard", "No", "Pharma bucket"],
            ["auto", "AUTO", "standard", "Yes", "Auto bucket"],
            ["energy", "ENERGY", "standard", "Yes", "Energy bucket"],
            ["metals", "METALS", "standard", "Yes", "Metals bucket"],
            ["capital_goods", "CAPITAL_GOODS", "standard", "Yes", "Industrials bucket"],
        ],
        [30, 28, 22, 22, 88],
    )
    pdf.body(
        "Banking percentiles are never computed across private and PSU banks together. "
        "IT percentiles use the full IT universe as one peer set. Standard sectors rank "
        "within their bucket only."
    )

    # --- 4 Data ---
    pdf.chapter_title("4", "Data Acquisition Layer")
    pdf.section("Primary source: yfinance")
    pdf.bullet_list([
        "get_info(): PE, PB, ROE, margins, market cap, beta proxies",
        "history(5y): returns, volatility, drawdown, beta vs Nifty (^NSEI)",
        "Financial statements: CAGR, credit growth (banks), margin trends",
    ])
    pdf.section("Overrides & fallbacks")
    pdf.bullet_list([
        "banking_metrics.json: GNPA, NNPA, CAR, NIM (curated, overrides Yahoo)",
        "ticker_aliases.yaml: symbol fallbacks (M&M.NS, CUB.NS)",
        "NSE chart API when yfinance history too short",
        "24-hour disk cache at .cache/screener/",
        "sanitize_metrics(): clamp ROE, PE, debt/equity outliers",
    ])

    # --- 5 Pipeline ---
    pdf.chapter_title("5", "Pipeline & Quality Control")
    pdf.body("Orchestrator: screener/pipeline.py (ScreenState singleton for API).")
    pdf.section("QC drop conditions")
    pdf.bullet_list([
        "fetch_failed = true",
        "sector_focus = unknown",
        "price_history_rows < min_price_history_rows (default 20)",
        "both PE and PB missing",
        "data_completeness < min_completeness (default 0.35)",
    ])
    pdf.body(
        "After QC: enrich_sector_relative_momentum() sets rs_vs_sector_pct = 6m return "
        "minus sector median 6m return."
    )

    # --- 6 Scoring framework ---
    pdf.chapter_title("6", "Scoring Framework (Shared Mechanics)")
    pdf.section("Routing (score_universe)")
    pdf.body(
        "for each peer group from peer_set(): if banking -> _score_banking(); "
        "elif it -> _score_it(); else -> score_generic_group()."
    )
    pdf.section("Factor utilities (factors.py)")
    pdf.bullet_list([
        "soft_score_higher/lower: map metric to 0-1 via good/bad thresholds",
        "percentile_rank: 0-100 within peers, winsorized at 5th/95th percentile",
        "shrink_percentile: blend toward 50 when peer_count < min_peers_for_rank (10)",
        "weighted_mean: composite factor blend, skips missing factors",
    ])
    pdf.section("ScoreResult fields")
    pdf.bullet_list([
        "composite_score (0-100), fundamental_strength (0-1)",
        "valuation_label: Under | Fair | Over | Unknown",
        "composite_percentile, peer_rank, peer_count",
        "quality_grade (A-F), peer_band, recommendation",
        "red_flag, hard_gate_fail, risk_flags, confidence",
    ])

    # --- 7 Sector models ---
    pdf.chapter_title("7", "Sector-Specific Scoring Models")
    pdf.section("7.1 Banking (deep)")
    pdf.table(
        ["Factor", "Weight", "Key inputs"],
        [
            ["Asset quality", "30%", "GNPA, NNPA, CAR, GNPA peer pctile"],
            ["Franchise", "25%", "NIM, ROA, ROE, peer pctiles"],
            ["Valuation", "25%", "P/B-ROE residual regression"],
            ["Momentum", "10%", "6m return pctile or RS"],
            ["Risk penalty", "10%", "Max drawdown pctile"],
        ],
        [40, 25, 125],
    )
    pdf.body(
        "Hard gates: GNPA>=3.5%, NNPA>=1.2%, CAR<12%. Valuation via pb_roe_residual() in "
        "banking_valuation.py. Seven risk questions (BQ1-BQ7)."
    )
    pdf.section("7.2 IT (deep)")
    pdf.table(
        ["Factor", "Weight", "Key inputs"],
        [
            ["Margin quality", "25%", "Op margin, margin trend, ROE"],
            ["Growth", "30%", "Rev CAGR (fallback), profit growth"],
            ["Valuation", "25%", "PEG, P/E vs peers, FCF yield"],
            ["Momentum", "10%", "6m return or RS"],
            ["Risk penalty", "10%", "Drawdown pctile"],
        ],
        [40, 25, 125],
    )
    pdf.body(
        "Hard gates: op margin<0, ROE<0, D/E>2.5. Seven risk questions (IQ1-IQ7). "
        "Growth fallbacks in growth.py when 3y CAGR missing."
    )
    pdf.section("7.3 Standard sectors (generic.py + sector_weights.yaml)")
    pdf.table(
        ["Sector", "Quality", "Growth", "Value", "Momentum", "Extra"],
        [
            ["FMCG", "35%", "15%", "25%", "10%", "risk 15%"],
            ["PHARMA", "35%", "25%", "20%", "10%", "risk 10%"],
            ["AUTO", "25%", "25%", "25%", "15%", "cyclical"],
            ["ENERGY", "28%", "12%", "28%", "12%", "cashflow 18%"],
            ["METALS", "22%", "18%", "32%", "15%", "value-heavy"],
            ["CAPITAL_GOODS", "30%", "30%", "20%", "10%", "growth focus"],
        ],
        [32, 22, 22, 22, 22, 70],
    )
    pdf.body(
        "Valuation: valuation.py multi-metric vote (P/E, P/B, EV/EBITDA z-scores). Cyclical "
        "margin-peak penalty prevents false cheap labels. Five generic risk questions with "
        "sector_risk_overrides.yaml bands."
    )

    # --- 8 Recommendations ---
    pdf.chapter_title("8", "Recommendation Engine (Three-Axis v3)")
    pdf.section("Axis 1: Absolute quality (quality_grade.py)")
    pdf.body(
        "quality_score = 0.45*fundamental_strength + 0.40*(composite/100) + 0.15*completeness. "
        "Grades: A>=0.75, B>=0.55, C>=0.40, D below, F if hard_gate_fail."
    )
    pdf.section("Axis 2: Peer band")
    pdf.table(
        ["Band", "Percentile"],
        [["Top", ">=70"], ["Upper-Mid", "50-70"], ["Lower-Mid", "30-50"], ["Bottom", "<30"]],
        [60, 130],
    )
    pdf.section("Axis 3: Action label (action_matrix.py)")
    pdf.bullet_list([
        "Hard fail + Over -> SELL; hard fail else -> AVOID",
        "Grade A/B + Top/Upper-Mid + not Over -> STRONG BUY or BUY",
        "Grade A/B + Under -> BUY (value)",
        "Grade A/B/C + not Bottom -> HOLD",
        "Bottom + Over -> AVOID",
        "Large-cap floor (>=500B INR): minimum HOLD unless hard_gate or red_flag",
        "Confidence <0.35: downgrade one step on action ladder",
    ])

    # --- 9 Interpretation ---
    pdf.chapter_title("9", "Interpretation & Risk Question Engine")
    pdf.body(
        "For each stock, stock_analyst.py loads YAML questions, evaluates good/warn/bad "
        "signals via signals.py, computes stock_risk_score (0-100), updates confidence, "
        "re-runs assign_action(), and generates narrative headline/bull/bear/key_risk."
    )
    pdf.table(
        ["Analysis type", "Sectors", "Questions"],
        [["Deep", "Banking, IT", "7 sector-specific"], ["Standard", "All others", "5 generic + overrides"]],
        [40, 50, 100],
    )

    # --- 10 Profile matching ---
    pdf.chapter_title("10", "Profile Matching & Personalization")
    pdf.body(
        "User questionnaire maps to RiskProfile (conservative/moderate/growth/aggressive). "
        "match_stock() computes profile fit score and exclusion flags."
    )
    pdf.section("Profile fit formula")
    pdf.body(
        "fit = 0.27*risk_alignment + 0.25*quality_norm + 0.18*valuation_fit "
        "+ 0.10*profile_bonus + 0.20*composite_score"
    )
    pdf.section("Diversification (risk_profile_matrix.yaml)")
    pdf.bullet_list([
        "Top 20 picks total, max 3 per sector",
        "deep_sector_min: at least 2 banking + 2 IT in diversified picks",
        "Conservative: excludes cyclical sectors, high beta, overvaluation",
    ])

    # --- 11 Config ---
    pdf.chapter_title("11", "Configuration Reference")
    pdf.table(
        ["File", "Purpose"],
        [
            ["universe.yaml", "Ticker lists, buckets, depth, cyclical"],
            ["settings.yaml", "Cache, QC, composite weights, cap tiers"],
            ["sector_weights.yaml", "Standard sector factor weights"],
            ["banking_metrics.json", "Curated bank GNPA/NNPA/CAR/NIM"],
            ["*_risk_questions.yaml", "Banking/IT/generic risk Q definitions"],
            ["sector_risk_overrides.yaml", "Per-sector signal band overrides"],
            ["risk_profile_matrix.yaml", "Matcher penalties, diversification"],
            ["user_questionnaire.yaml", "Investor profile questionnaire"],
            ["ticker_aliases.yaml", "yfinance symbol fallbacks"],
        ],
        [70, 120],
    )

    # --- 12 API ---
    pdf.chapter_title("12", "API, UI & Operational Scripts")
    pdf.table(
        ["Endpoint / Script", "Purpose"],
        [
            ["GET /api/screen", "Full scored universe"],
            ["GET /api/stock/{t}/interpret", "Stock interpretation"],
            ["POST /api/recommend", "Profile-matched picks"],
            ["scripts/e2e_audit.py", "End-to-end audit"],
            ["scripts/sector_audit.py", "Per-sector breakdown"],
            ["scripts/rec_audit.py", "Blue-chip sanity check"],
            ["python -m pytest", "41+ automated tests"],
        ],
        [80, 110],
    )

    # --- 13 Examples ---
    pdf.chapter_title("13", "Worked Examples")
    pdf.section("ZYDUSLIFE.NS (Pharma)")
    pdf.body(
        "Bucket pharma from config. Generic PHARMA weights -> composite ~83. Top peer "
        "percentile -> grade A -> STRONG BUY. Stock risk ~23. High profile fit for "
        "Capital Preservation."
    )
    pdf.section("TCS.NS (IT)")
    pdf.body(
        "Deep IT scorer. Strong fundamentals but may rank Bottom vs 31 IT peers on "
        "composite percentile. Quality grade B. Large-cap floor -> HOLD minimum (not AVOID). "
        "Seven IT risk questions including PEG valuation."
    )
    pdf.section("HDFCBANK.NS (Banking)")
    pdf.body(
        "Deep banking scorer within private bank cohort. Curated NNPA/CAR from JSON. "
        "P/B-ROE residual valuation. Typically STRONG BUY or BUY with grade A."
    )

    # --- Appendix A ---
    pdf.chapter_title("Appendix A", "Formulas & Thresholds")
    pdf.section("Banking hard gates")
    pdf.body("GNPA >= 3.5% | NNPA >= 1.2% | CAR < 12%")
    pdf.section("IT hard gates")
    pdf.body("Operating margin < 0 | ROE < 0 | Debt/Equity > 2.5")
    pdf.section("Generic hard gates")
    pdf.body("ROE < -5% | Op margin < -2% | D/E > 3 (4 for FMCG/pharma) | Interest coverage < 0.8")
    pdf.section("Cap tiers (settings.yaml)")
    pdf.body("Mega: >= INR 2T | Large: >= INR 500B | Floor: HOLD unless hard_gate_fail or red_flag")

    # --- Appendix B Glossary ---
    pdf.chapter_title("Appendix B", "Glossary")
    glossary = [
        ("sector_focus", "Internal bucket id: banking, it, fmcg, etc."),
        ("model_sector", "Scoring model key: BANKING, IT, FMCG, ..."),
        ("analysis_depth", "deep (7 Qs) or standard (5 Qs)"),
        ("composite_score", "0-100 weighted factor score within scoring engine"),
        ("composite_percentile", "Rank within peer cohort, 0-100"),
        ("quality_grade", "A-F absolute quality, independent of peer rank"),
        ("peer_band", "Top | Upper-Mid | Lower-Mid | Bottom"),
        ("action_label", "STRONG BUY | BUY | HOLD | AVOID | SELL"),
        ("fit_score", "0-100 profile match for personalized picks"),
        ("stock_risk_score", "0-100 from risk question signals"),
        ("valuation_label", "Under | Fair | Over from peer-relative valuation"),
        ("rs_vs_sector_pct", "6m return minus sector median 6m return"),
    ]
    pdf.set_font("Helvetica", "", 9)
    for term, defn in glossary:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(45, 5, term)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, defn)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
