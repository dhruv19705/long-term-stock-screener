# A+ Robust Stock Screener — Validation & Improvement Plan

**Document:** `docs/A_PLUS_SCREENER_PLAN.md`  
**Date:** August 8, 2026  
**Scope:** Plan only — no code changes in this deliverable  
**Engine:** Recommendation Strategy v3 (Three-Axis: Quality Grade × Peer Band × Valuation Label)  
**Universe:** 181 NSE tickers across 8 sector buckets (`screener/config/universe.yaml`)

---

## 1. Executive Summary

The screener produces internally coherent outputs (zero STRONG BUY + Over valuation; zero Grade F + BUY), and its **distribution** (34% bullish, 23% bearish) sits within typical broker ranges. However, when tested against a **strict street-consensus golden set**, direction alignment is only **40.7%** (11/27 large caps ≥₹500B). The existing `scripts/market_alignment_audit.py` benchmark shows **100% alignment (19/19)** because it uses **wide acceptable ranges** (e.g., TCS street-Buy maps to `{HOLD, BUY}`), masking systematic conservatism on large-cap quality names.

### Top failure modes (verified Aug 8, 2026 run)

| Ticker | Screener | Street | Root cause |
|--------|----------|--------|------------|
| HEROMOTOCO | **SELL** | Buy (36 analysts) | yfinance D/E 3.57 from finance subsidiary → hard gate + red flag |
| BPCL | **SELL** | Hold (31 analysts) | Negative operating margin (-4%) → hard gate despite Top peer rank |
| ICICIBANK | HOLD | **Strong Buy** (39 analysts) | Valuation Over + Upper-Mid peer; cap floor prevents downgrade but not upgrade |
| TCS / INFY | HOLD | **Buy** (42 analysts each) | Bottom peer band in crowded IT cohort despite Grade B fundamentals |
| HCLTECH | **BUY** | Hold (40 analysts) | Upper-Mid peer + Fair val overrides street caution |

### Data quality blocker

**62.4% of tickers (113/181) lack ROE from yfinance**, degrading quality scores and peer percentiles. Missing ROE is concentrated in auto (87%), energy (82%), capital goods (79%), and metals (71%).

### Target state (A+ bar)

| Metric | Current | Target |
|--------|---------|--------|
| Direction alignment (large-cap golden set) | 40.7% | **≥90%** |
| False SELL/AVOID on street-Buy large caps | 5.3% (1/19) | **<5%** |
| Severity match (±1 tier) | 88.9% | **≥95%** |
| ROE coverage | 37.6% | **≥85%** for large caps |
| Loose benchmark (wide ranges) | 100% | Maintain ≥95% |

---

## 2. External Benchmark Ticker List

Sources: [stockanalysis.com](https://stockanalysis.com) (S&P Global analyst polls), [Trendlyne](https://trendlyne.com), [Economic Times](https://economictimes.indiatimes.com), [CNBC-TV18](https://www.cnbctv18.com), [PL Capital](https://www.plindia.com), broker reports (Jefferies, Motilal Oswal, Axis Direct, ICICI Securities). Consensus as of **July–August 2026**.

### 2.1 Core Golden Set (27 large caps — primary regression set)

#### Banking & Financial Services (7)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| HDFCBANK.NS | Buy | 38 buy calls | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |
| ICICIBANK.NS | **Strong Buy** | 39 | [stockanalysis.com](https://stockanalysis.com/quote/nse/ICICIBANK/forecast/) | ✓ |
| SBIN.NS | Buy | 34 | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |
| KOTAKBANK.NS | Hold | ~30 | Premium franchise, rich P/B | ✓ |
| AXISBANK.NS | Buy | 35 | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |
| INDUSINDBK.NS | Buy | ~25 | Broad coverage, recovery play | ✓ |
| ADANIPORTS.NS | **Strong Buy** | 18 unanimous Buy | [CNBC-TV18](https://www.cnbctv18.com/photos/market/stocks/top-10-stocks-with-only-buy-rating-will-you-invest-in-these-midcaps-small-caps-and-blue-chips-19627194.htm) | ✓ |

#### Information Technology (6)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| TCS.NS | Buy | 42 | [stockanalysis.com](https://stockanalysis.com/quote/nse/TCS/forecast/) | ✓ |
| INFY.NS | Buy | 42 | [stockanalysis.com](https://stockanalysis.com/quote/nse/INFY/forecast/) | ✓ |
| HCLTECH.NS | Hold | 40 | [stockanalysis.com](https://stockanalysis.com/quote/nse/HCLTECH/forecast/) | ✓ |
| WIPRO.NS | Hold | 40 | [stockanalysis.com](https://stockanalysis.com/quote/nse/WIPRO/forecast/) | ✓ |
| TECHM.NS | Hold | ~35 | [BusinessToday Jul 2026](https://www.businesstoday.in/markets/stocks/story/infosys-coforge-tcs-wipro-hcl-ltm-persistent-mphasis-stock-with-highest-st-target-542749-2026-07-14) | ✓ |
| PERSISTENT.NS | Buy | ~20 | IT mid-cap leader | ✓ |

#### Consumer (FMCG + Auto + Retail) (8)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| ITC.NS | Buy | 35 | [ET](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms), [PL Capital](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |
| HINDUNILVR.NS | Hold | ~30 | Defensive staple, premium val | ✓ |
| NESTLEIND.NS | Hold | ~25 | Premium FMCG | ✓ |
| MARUTI.NS | Buy | 33 | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |
| BAJAJ-AUTO.NS | Buy | ~28 | Strong franchise | ✓ |
| HEROMOTOCO.NS | **Buy** | 36 | [stockanalysis.com](https://stockanalysis.com/quote/bom/500182/forecast/) | ✓ |
| EICHERMOT.NS | Buy | ~22 | Premium auto | ✓ |
| TITAN.NS | Buy | ~30 | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |

#### Healthcare / Pharma (3)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| SUNPHARMA.NS | Buy | ~35 | Pharma leader | ✓ |
| DIVISLAB.NS | Buy | ~25 | Quality API/CDMO | ✓ |
| DRREDDY.NS | Buy | ~28 | Large-cap pharma | ✓ |

#### Energy & Materials (3)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| RELIANCE.NS | Buy | ~40 | Conglomerate anchor | ✓ |
| BPCL.NS | Hold | 31 | [stockanalysis.com](https://stockanalysis.com/quote/nse/BPCL/forecast/) | ✓ |
| JSWSTEEL.NS | Hold | ~20 | Cyclical metals | ✓ |

#### Industrials / Infra (3)

| Ticker | Street Consensus | Analyst Count | Source | In Universe |
|--------|-----------------|---------------|--------|-------------|
| LT.NS | Buy | ~30 | Infra bellwether | ✓ |
| ULTRACEMCO.NS | Buy | 35 | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |
| M&M.NS | Buy | 35 | [ET Jul 2025](https://economictimes.indiatimes.com/markets/stocks/news/10-nifty-large-cap-stocks-with-up-to-38-buy-calls-analysts-see-up-to-20-upside/top-picks/slideshow/122309316.cms) | ✓ |

---

### 2.2 Proposed Expansion — 38 Additional Benchmark Tickers

These extend coverage to mid-caps and under-tested sectors. **67/76 are already in `universe.yaml`**; 9 require universe addition (marked †).

#### Banking (6 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| CANBK.NS | Buy | PSU turnaround, ~20 analysts | ✓ |
| BANKBARODA.NS | Buy | PSU recovery | ✓ |
| FEDERALBNK.NS | Hold/Buy | Private mid-tier | ✓ |
| BANDHANBNK.NS | Buy | [stocktargetadvisor.com](https://www.stocktargetadvisor.com/blog/indian-stock-market-analyst-ratings/) | ✓ |
| PNB.NS | Hold | PSU, mixed | ✓ |
| IDFCFIRSTB.NS | Hold | Turnaround, mixed | ✓ |

#### IT (6 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| COFORGE.NS | Buy | [BusinessToday Jul 2026](https://www.businesstoday.in/markets/stocks/story/infosys-coforge-tcs-wipro-hcl-ltm-persistent-mphasis-stock-with-highest-st-target-542749-2026-07-14) | ✓ |
| MPHASIS.NS | Buy | ~8% upside consensus | ✓ |
| OFSS.NS | Hold | Niche banking IT, premium val | ✓ |
| KPITTECH.NS | Buy | Auto-tech growth | ✓ |
| LTTS.NS | Hold | Engineering R&D | ✓ |
| NAUKRI.NS | Hold | Platform, maturing growth | ✓ |

#### FMCG (6 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| DABUR.NS | Buy/Hold | Defensive, rural exposure | ✓ |
| BRITANNIA.NS | Hold | Premium bakery | ✓ |
| MARICO.NS | Buy | Consistent compounder | ✓ |
| GODREJCP.NS | Buy | Home/personal care | ✓ |
| COLPAL.NS | Hold | Premium oral care | ✓ |
| TATACONSUM.NS | Hold | Tata consumer pivot | ✓ |

#### Pharma (6 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| CIPLA.NS | Buy | Large-cap pharma | ✓ |
| LUPIN.NS | Buy | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |
| ALKEM.NS | Buy/Hold | Domestic formulations | ✓ |
| TORNTPHARM.NS | Buy | Chronic therapy focus | ✓ |
| ZYDUSLIFE.NS | Buy | Diversified healthcare | ✓ |
| BIOCON.NS | Hold | Biosimilars, volatile | ✓ |

#### Auto / Consumer Cyclical (4 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| TVSMOTOR.NS | Buy | Export growth | ✓ |
| BHARATFORG.NS | Hold | Auto components cyclical | ✓ |
| TRENT.NS | Buy | Retail compounder | ✓ |
| PAGEIND.NS | Hold | Ultra-premium niche | ✓ |

#### Energy / Utilities (4 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| ONGC.NS | Hold | PSU upstream | ✓ |
| NTPC.NS | Buy | Power utility, renewables | ✓ |
| COALINDIA.NS | Hold | Dividend yield play | ✓ |
| GAIL.NS | Hold | Gas utility | ✓ |

#### Metals (3 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| HINDALCO.NS | Buy | Integrated aluminium | ✓ |
| VEDL.NS | Hold | Diversified miner | ✓ |
| JINDALSTEL.NS | Strong Buy | [stocktargetadvisor.com](https://www.stocktargetadvisor.com/blog/indian-stock-market-analyst-ratings/) | ✓ |

#### Capital Goods / Industrials (3 new)

| Ticker | Street | Source | In Universe |
|--------|--------|--------|---------------|
| ABB.NS | Buy | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |
| HAL.NS | Buy | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |
| INDIGO.NS | Buy | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) | ✓ |

#### Recommended Universe Additions († — not in current 181)

| Ticker | Street | Rationale |
|--------|--------|-----------|
| BHARTIARTL.NS † | Buy | Nifty 50 telecom anchor; [PL Capital](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) |
| ASIANPAINT.NS † | Hold | Nifty 50 consumer staple benchmark |
| BAJFINANCE.NS † | Buy | Nifty financials, high analyst coverage |
| BAJAJFINSV.NS † | Strong Buy | [stocktargetadvisor.com](https://www.stocktargetadvisor.com/blog/indian-stock-market-analyst-ratings/) |
| PIDILITIND.NS † | Strong Buy | Adhesives leader, unanimous coverage |
| AMBUJACEM.NS † | Strong Buy | Cement sector peer for ULTRACEMCO |
| APOLLOHOSP.NS † | Buy | [PL Capital Jul 2025](https://www.plindia.com/news/high-conviction-stock-picks-india-july-2025/) |
| POWERGRID.NS † | Hold | Utility benchmark |
| LTIM.NS † | Buy | Large-cap IT (LTIMindtree), peer for TCS/INFY |

**Total benchmark universe after expansion:** 27 core + 38 additional = **65 tickers** (+ 9 universe additions recommended).

---

## 3. Golden Set Validation Methodology

### 3.1 Benchmark file structure

Create `screener/config/golden_set.yaml`:

```yaml
# ticker -> primary street view (single label, not range)
HEROMOTOCO.NS:
  street: BUY
  source: "stockanalysis.com, 36 analysts, Aug 2026"
  cap_tier: large
  sector: auto
  notes: "Finance subsidiary D/E distortion"
```

### 3.2 Alignment scoring dimensions

| Dimension | Rule | Weight |
|-----------|------|--------|
| **Direction match** | Map both to `{bullish, neutral, bearish}`; SELL/AVOID=bearish, HOLD=neutral, BUY/STRONG BUY=bullish | Primary KPI |
| **Severity match** | Ladder index diff ≤ 1 on `ACTION_LADDER = [SELL, AVOID, HOLD, BUY, STRONG BUY]` | Secondary KPI |
| **Exact match** | Screener label == street label | Diagnostic only |
| **False positive (bearish)** | Street bullish → screener SELL/AVOID | Critical error |
| **False negative (bullish)** | Street bearish → screener BUY/STRONG BUY | Quality concern |
| **Hard-gate override audit** | Flag when `hard_gate_fail=True` but street Buy and quality composite > 70 | Data bug detector |

### 3.3 Direction mapping

```
Street STRONG BUY / BUY     → bullish
Street HOLD                 → neutral
Street AVOID / SELL         → bearish

Screener STRONG BUY / BUY   → bullish
Screener HOLD               → neutral
Screener AVOID / SELL       → bearish
```

### 3.4 Regression workflow

1. `run_evaluation(sector_filter="all", use_cache=True)` via `screener.pipeline`
2. Load golden set YAML
3. Compare each ticker's `ScoreResult.recommendation` vs street
4. Emit JSON report: alignment %, mismatches with `{quality_grade, peer_band, valuation_label, hard_gate_fail, red_flag, composite_score, key metrics}`
5. Fail CI if direction alignment < threshold or false-SELL-on-Buy > threshold

### 3.5 Refresh cadence

- **Quarterly:** Update street labels from stockanalysis.com / Trendlyne after earnings season
- **On demand:** `--refresh` cache when yfinance/NSE data pipeline changes
- **Version pin:** Store `golden_set_version` and `screener_git_sha` in audit output

---

## 4. Current Alignment Results (Aug 8, 2026)

**Run commands:** `python scripts/market_alignment_audit.py`, `python scripts/market_recheck.py`, `python scripts/rec_audit.py`  
**Environment:** Cached yfinance data, 181/181 tickers scored

### 4.1 Universe distribution

| Recommendation | Count | % |
|----------------|-------|---|
| STRONG BUY | 20 | 11% |
| BUY | 41 | 23% |
| HOLD | 78 | 43% |
| AVOID | 34 | 19% |
| SELL | 8 | 4% |
| **Bullish (BUY+SB)** | **61** | **34%** |
| **Bearish (AVOID+SELL)** | **42** | **23%** |

Broker norm (~25–35% Buy, ~15–25% Sell/Underweight): **distribution is acceptable**.

### 4.2 Loose benchmark (`market_alignment_audit.py` — 19 tickers)

| Metric | Result |
|--------|--------|
| Direction match (wide ranges) | **19/19 (100%)** |
| Coherence: SB + Over val | 0 |
| Coherence: Grade F + BUY | 0 |
| Coherence: Grade A/B + SELL | 0 |

**Interpretation:** Wide ranges hide systematic HOLD bias on street-Buy names (TCS, INFY, ICICIBANK, SBIN, ITC, LT all pass because HOLD ∈ acceptable set).

### 4.3 Strict golden set (27 large caps, primary street label)

| Metric | Result |
|--------|--------|
| Direction match | **11/27 (40.7%)** |
| Severity match (±1 tier) | **24/27 (88.9%)** |
| False SELL/AVOID on street-Buy | **1/19 (5.3%)** — HEROMOTOCO only |
| Not in universe | ADANIPORTS scored; BHARTIARTL/ASIANPAINT not in universe |

### 4.4 Known mismatch detail (current run)

| Ticker | Ours | Street | Q | Peer | Val | Hard Gate | Key Metric Issue |
|--------|------|--------|---|------|-----|-----------|------------------|
| HEROMOTOCO | SELL | Buy | F | Top | Over | **Yes** | D/E=3.57 (finance sub) |
| BPCL | SELL | Hold | F | Top | Over | **Yes** | Op margin=-4.0% |
| ICICIBANK | HOLD | Strong Buy | A | Upper-Mid | Over | No | P/B-ROE residual rich |
| TCS | HOLD | Buy | B | **Bottom** | Over | No | pct=27, crowded IT peer set |
| INFY | HOLD | Buy | B | **Bottom** | Fair | No | pct=17, growth headwinds in rank |
| HCLTECH | BUY | Hold | B | Upper-Mid | Fair | No | Over-promoted vs street |
| SBIN | HOLD | Buy | B | Top | Over | No | Valuation Over caps action |
| MARUTI | HOLD | Buy | B | Upper-Mid | Over | No | Missing ROE, expensive PE |
| BAJAJ-AUTO | HOLD | Buy | A | Top | Over | No | Valuation Over → HOLD path |
| ITC | HOLD | Buy | B | Upper-Mid | Over | No | Defensive but Over val |
| LT | HOLD | Buy | B | Lower-Mid | Over | No | Peer rank + Over val |
| ULTRACEMCO | HOLD | Buy | B | Lower-Mid | Over | No | Cyclical, Over val |
| M&M | HOLD | Buy | B | Lower-Mid | Over | No | Missing ROE |
| ADANIPORTS | HOLD | Buy | B | Lower-Mid | Fair | No | Infrastructure peer mix |
| NESTLEIND | BUY | Hold | B | Lower-Mid | Under | No | Under-promoted vs street |
| JSWSTEEL | BUY | Hold | A | Upper-Mid | Fair | No | Cyclical over-promotion |

### 4.5 IT sector peer context (31 tickers — root of TCS/INFY issue)

| Ticker | Rec | Comp | Pctile | Q | Peer | Val |
|--------|-----|------|--------|---|------|-----|
| TCS | HOLD | 54.2 | 27 | B | Bottom | Over |
| INFY | HOLD | 50.9 | 17 | B | Bottom | Fair |
| HCLTECH | BUY | 60.2 | 50 | B | Upper-Mid | Fair |
| WIPRO | HOLD | 54.6 | 37 | B | Lower-Mid | Fair |
| TECHM | HOLD | 50.1 | 10 | B | Bottom | Fair |

Large-cap IT leaders rank Bottom because the IT peer set (31 names) includes high-growth mid-caps (HEXT, NETWEB, AFFLE) that inflate composite percentiles.

### 4.6 Data completeness

| Field | Missing | % |
|-------|---------|---|
| ROE | 113/181 | 62.4% |
| PE | 1/181 | 0.6% |
| Op margin | ~40/181 | ~22% |

Missing ROE by sector: auto 87%, energy 82%, capital_goods 79%, metals 71%, banking 0% (curated).

---

## 5. Root Cause Analysis

### 5.1 Category A — False hard gates (data artifacts)

**HEROMOTOCO (SELL vs street Buy)**

- yfinance reports `debt_to_equity=3.57`; Hero FinCorp finance subsidiary debt is consolidated on parent balance sheet
- Triggers `_hard_gate_generic()` at D/E > 3.0 (`screener/scoring/generic.py:53-61`) and `_red_flag_generic()` at D/E > 2.5
- `_derive_action()` returns SELL when `hard_fail=True` and `val_label=Over` (`action_matrix.py:68-69`)
- Cap floor (₹500B → min HOLD) is **bypassed** because `hard_gate_fail` is in `floor_exceptions` (`settings.yaml:19`, `action_matrix.py:47-49`)
- **Paradox:** composite=79.0, peer=Top, yet SELL — classic false negative

**BPCL (SELL vs street Hold)**

- `operating_margin_pct=-4.048%` triggers hard gate (margin < -2%)
- Likely yfinance TTM distortion from inventory/oil price timing, not structural unprofitability
- Same hard-gate → SELL path with cap floor bypassed
- Composite=76.8, peer=Top — quality rank contradicts action

### 5.2 Category B — Peer-relative rank compression (large-cap leaders)

**TCS / INFY (HOLD vs street Buy)**

- `_score_it()` ranks 31 IT peers on composite; TCS pctile=27, INFY pctile=17 → `peer_band=Bottom`
- `_derive_action()` line 79-80: Grade A/B/C with non-Bottom band → HOLD; Bottom band requires other conditions for BUY
- Grade B + Bottom + Over (TCS) or Fair (INFY) → HOLD (`action_matrix.py:79-80, 82-83`)
- **Design flaw:** Absolute quality (ROE 48%/32%, margins 24%/21%) ignored when peer rank is Bottom
- IT peer set mixes mega-cap exporters with small-cap IT services — distorts percentiles

**ICICIBANK (HOLD vs street Strong Buy)**

- Grade A but `valuation_label=Over` (P/B-ROE residual) and `peer_band=Upper-Mid` (not Top)
- Action matrix: no path to BUY without Top/Upper-Mid + non-Over (lines 71-74)
- Cap floor ensures HOLD minimum but **no upgrade path** for Grade A + Over valuation

### 5.3 Category C — Valuation conservatism (HOLD on street-Buy)

**SBIN, ITC, LT, MARUTI, BAJAJ-AUTO, ULTRACEMCO, M&M**

- Pattern: Quality Grade A/B + `valuation_label=Over` → capped at HOLD
- Banks: P/B-ROE residual flags rich valuation even for quality franchises
- Consumer/industrial: PE vs peer or historical band marks Over → HOLD
- **Street view:** analysts price in growth/moat premium; screener treats Over as action ceiling

### 5.4 Category D — Over-promotion

**HCLTECH (BUY vs street Hold)**

- Upper-Mid peer (pctile=50) + Grade B + Fair val → BUY (`action_matrix.py:71-74`)
- Street Hold reflects sector headwinds and full valuation (CNBC: "valuations cap upside")
- **Asymmetric:** Bottom peer caps large caps down, but Upper-Mid promotes to BUY without momentum/growth confirmation

**JSWSTEEL, NESTLEIND** — minor severity mismatches (±1 tier)

### 5.5 Category E — Missing fundamentals

- 62.4% missing ROE degrades `compute_quality_score()` (`quality_grade.py:11-14`) — falls back to composite + completeness
- `_quality_roe_band()` and peer ROE percentile skip None values, shrinking effective peer comparisons
- Auto/energy/metals most affected → unreliable quality grades and peer ranks

### 5.6 Category F — Benchmark methodology gap

- Current `MARKET_BENCHMARK` uses **sets** not **primary labels** → 100% misleading pass rate
- No tracking of false SELL rate, severity distance, or hard-gate override audit
- No CI gate on alignment regression

---

## 6. Phased Improvement Plan

### P0 — Critical fixes (target: 2 weeks)

| # | Change | Files | Expected impact |
|---|--------|-------|-----------------|
| P0-1 | **Finance subsidiary D/E normalization** for auto/banking: if ticker in `{HEROMOTOCO, BAJAJ-AUTO, M&M, EICHERMOT}` and D/E > 2.5, fetch/consolidated-adjust D/E or use sector override (cap at 1.5 for hard gate) | `screener/data/normalize.py`, new `screener/data/debt_adjustments.yaml`, `generic.py:_hard_gate_generic` | Fixes HEROMOTOCO false SELL |
| P0-2 | **Energy/refining margin sanity check**: if sector=ENERGY and op_margin < 0 but ROE > 8% and positive FCF, suppress hard gate (flag `margin_distortion` instead) | `generic.py`, `sector_risk_overrides.yaml` | Fixes BPCL false SELL |
| P0-3 | **Large-cap IT peer sub-cohort**: split IT peers into `{large_cap_it, mid_cap_it}` by market cap ≥₹500B; rank TCS/INFY/HCLTECH/WIPTECHM within large-cap sub-group only | `composite.py:_score_it`, `config_loader.py:peer_set` | TCS/INFY move from Bottom → Upper-Mid/Top |
| P0-4 | **Golden set YAML + CI test**: `tests/test_golden_set_alignment.py` fails if direction match < 75% (interim) or false-SELL-on-Buy > 5% | New `golden_set.yaml`, `scripts/golden_set_audit.py`, `tests/` | Prevents regression |
| P0-5 | **ROE backfill via NSE/BSE filings**: extend `nse_fallback.py` to pull ROE/ROCE from NSE XBRL or screener.in scrape for missing fields | `nse_fallback.py`, `fetcher.py` | ROE coverage 38% → 70%+ |

### P1 — Scoring & action matrix tuning (target: 4 weeks)

| # | Change | Files | Expected impact |
|---|--------|-------|-----------------|
| P1-1 | **Grade A cap-floor upgrade path**: if Grade A + mega/large cap + not hard_gate → floor BUY (not just HOLD); STRONG BUY requires Top + Fair/Under | `action_matrix.py:_apply_cap_floor`, `settings.yaml:cap_floor` | ICICIBANK, SBIN, ITC → BUY |
| P1-2 | **Valuation Over softening for quality**: Grade A + Over → HOLD (current) but Grade A + Over + Top peer → BUY | `action_matrix.py:_derive_action` | BAJAJ-AUTO, MARUTI upgrades |
| P1-3 | **Absolute quality override for peer Bottom**: if quality_score ≥ 0.70 and market_cap ≥ large, peer band floor = Lower-Mid (not Bottom) | `action_matrix.py`, `peer_stats.py:shrink_percentile` | TCS/INFY protection |
| P1-4 | **Banking valuation recalibration**: widen Fair band on P/B-ROE residual for private banks; or use forward P/B vs 5Y median | `banking_valuation.py`, `composite.py:_score_banking` | ICICIBANK, KOTAKBANK val=Over reduction |
| P1-5 | **HCLTECH-type guard**: BUY requires Top peer OR (Upper-Mid + Under val); Upper-Mid + Fair → HOLD | `action_matrix.py:_derive_action` | Reduces false BUY on Hold names |
| P1-6 | **Hard gate exception logging**: when hard_gate triggers on large cap with composite > 70, log + surface in UI as "data quality flag" not silent SELL | `pipeline.py`, API schemas | Transparency |

### P2 — Street overlay & expanded universe (target: 6–8 weeks)

| # | Change | Files | Expected impact |
|---|--------|-------|-----------------|
| P2-1 | **Optional street consensus overlay** for mega/large caps: fetch quarterly from stockanalysis.com API or cached CSV; if screener SELL and street Buy with ≥20 analysts, downgrade to AVOID/HOLD | New `screener/data/street_consensus.py`, `action_matrix.py` (optional post-process) | Safety net for remaining edge cases |
| P2-2 | **Add 9 Nifty benchmark tickers** to universe: BHARTIARTL, ASIANPAINT, BAJFINANCE, BAJAJFINSV, PIDILITIND, AMBUJACEM, APOLLOHOSP, POWERGRID, LTIM | `universe.yaml` | Benchmark coverage → 65+ names |
| P2-3 | **Automated quarterly golden set refresh** script with source URLs | `scripts/refresh_golden_set.py` | Sustainable validation |
| P2-4 | **Sector-specific hard gate tables** in YAML (replace hard-coded thresholds) | `rules.yaml`, `generic.py`, `composite.py` | Easier calibration |
| P2-5 | **Walk-forward backtest** on golden set: did screener BUY names outperform HOLD/SELL over 6/12M? | New `scripts/backtest_golden.py` | Validates signal, not just alignment |
| P2-6 | **Confidence-weighted action**: low data_completeness → auto downgrade one tier (partially exists in `_confidence_downgrade`) — extend to missing ROE penalty | `action_matrix.py`, `quality_grade.py` | Safer outputs on incomplete data |

---

## 7. Success Metrics

| KPI | Baseline (Aug 2026) | P0 Target | A+ Target |
|-----|---------------------|-----------|-----------|
| Direction alignment — large-cap golden set (27) | 40.7% | ≥75% | **≥90%** |
| Direction alignment — full golden set (65) | Not measured | ≥70% | **≥85%** |
| False SELL/AVOID on street-Buy (large cap) | 5.3% (1/19) | 0% | **<5%** |
| False BUY on street-Sell/Hold (large cap) | ~15% | <10% | **<5%** |
| Severity match (±1 tier) | 88.9% | ≥92% | **≥95%** |
| ROE coverage (all tickers) | 37.6% | ≥70% | **≥85%** |
| ROE coverage (large cap) | ~45% | ≥90% | **≥95%** |
| Hard gate on large cap + composite > 70 | 2 (HERO, BPCL) | 0 | **0** |
| Loose benchmark (wide ranges) | 100% | ≥95% | ≥95% |
| CI golden set test | None | Required | Required, blocking |

---

## 8. Test Plan

### 8.1 Unit tests (existing + new)

| Test | File | Purpose |
|------|------|---------|
| Action matrix tiers | `tests/test_action_matrix.py` | Grade/band/val combinations |
| Hard gate boundaries | `tests/test_hard_gates.py` (new) | D/E, margin thresholds per sector |
| D/E normalization | `tests/test_normalize.py` (new) | Finance sub adjustment, yfinance % fix |
| IT peer sub-cohort | `tests/test_it_peer_groups.py` (new) | TCS/INFY not Bottom in large-cap group |
| Golden set alignment | `tests/test_golden_set_alignment.py` (new) | CI regression gate |

### 8.2 Integration tests

```bash
# Full pipeline
PYTHONPATH=. python -m screener.pipeline  # or scripts/market_alignment_audit.py

# Golden set audit (to be created)
PYTHONPATH=. python scripts/golden_set_audit.py --strict --min-alignment 0.75

# Market recheck distribution
PYTHONPATH=. python scripts/market_recheck.py
```

### 8.3 Manual validation checklist

- [ ] HEROMOTOCO: not SELL; ideally HOLD or BUY
- [ ] BPCL: not SELL; HOLD
- [ ] TCS/INFY: BUY or HOLD with severity ≤1 from street Buy
- [ ] ICICIBANK: BUY or STRONG BUY
- [ ] HCLTECH: HOLD (not BUY)
- [ ] No Grade A/B + SELL on any large cap
- [ ] Distribution remains 25–35% bullish, 15–25% bearish
- [ ] ROE populated for all golden set tickers

### 8.4 Regression cadence

| Trigger | Action |
|---------|--------|
| Every PR | `pytest tests/test_golden_set_alignment.py` |
| Weekly cron | Full evaluation + golden set report artifact |
| Quarterly | Refresh `golden_set.yaml` street labels from stockanalysis.com |
| After yfinance/NSE pipeline change | `--refresh` cache + full re-audit |

---

## 9. Architecture Reference (Current State)

### 9.1 Recommendation flow

```
fetch_all_metrics → QC (_qc) → score_universe → assign_action
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              _score_banking    _score_it      score_generic_group
                    │                 │                 │
                    └──────── assign_quality_fields ────┘
                                      │
                              _derive_action (grade × band × val)
                                      │
                              _profile_adjust (optional)
                                      │
                              _apply_cap_floor (mega/large → min HOLD)
                                      │
                              _confidence_downgrade
```

### 9.2 Key thresholds (today)

| Gate | Location | Threshold |
|------|----------|-----------|
| Hard gate D/E (generic) | `generic.py:54` | > 3.0 (4.0 FMCG/pharma) |
| Red flag D/E | `generic.py:68` | > 2.5 (3.5 FMCG/pharma) |
| Hard gate op margin | `generic.py:58` | < -2% |
| Hard gate ROE | `generic.py:56` | < -5% |
| Quality Grade A | `quality_grade.py:26` | quality_score ≥ 0.75 |
| Peer band Top | `action_matrix.py:15` | pctile ≥ 70 |
| Cap floor | `settings.yaml:16-18` | mega/large → min HOLD |

### 9.3 Scripts inventory

| Script | Purpose |
|--------|---------|
| `scripts/market_alignment_audit.py` | Loose 19-ticker benchmark (wide ranges) |
| `scripts/market_recheck.py` | Distribution, SELL list, sector mix |
| `scripts/rec_audit.py` | Blue-chip watchlist + conservative fit spread |
| `scripts/golden_set_audit.py` | **To create** — strict YAML-based validation |
| `scripts/refresh_golden_set.py` | **To create** — quarterly street consensus update |

---

## 10. Appendix — SELL List Analysis (Aug 2026)

| Ticker | Cap | Q | Peer | Val | Comp | Issue |
|--------|-----|---|------|-----|------|-------|
| HEROMOTOCO | ₹1.15T | F | Top | Over | 79.0 | False hard gate (D/E) |
| BPCL | ₹1.37T | F | Top | Over | 76.8 | False hard gate (margin) |
| ASHOKLEY | ₹1.04T | F | Bottom | Over | 59.9 | Legitimate cyclical weak |
| ABFRL | ₹0.08T | F | Bottom | Over | 23.7 | Legitimate |
| BSOFT | ₹0.09T | F | Bottom | Over | 51.8 | Legitimate |
| GODREJIND | ₹0.44T | F | Lower-Mid | Over | 57.3 | Legitimate |
| IOB | ₹0.66T | F | Lower-Mid | Over | 38.3 | PSU weak |
| UJJIVANSFB | ₹0.14T | D | Bottom | Over | 24.6 | Small finance weak |

**2 of 8 SELLs (25%) are large-cap false positives** — both hard-gate data artifacts.

---

## 11. Summary — Top 5 P0 Fixes

1. **Finance subsidiary D/E normalization** (HEROMOTOCO) — highest-impact false SELL
2. **IT large-cap peer sub-cohort** (TCS, INFY) — fixes systematic Bottom rank
3. **Energy margin hard-gate sanity check** (BPCL) — second false SELL
4. **Golden set YAML + CI regression test** — measurable alignment tracking
5. **ROE backfill via NSE fallback** — fixes 62% missing fundamentals

---

*End of plan. Implementation tracked separately; do not modify `robust_stock_screener_93ee4fa4.plan.md`.*
