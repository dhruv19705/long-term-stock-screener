# How the Screener Selects Companies

**Audience:** investment, research, and product colleagues  
**Purpose:** explain, in plain language, on what grounds a company is included, scored, ranked, and labelled BUY / HOLD / SELL  
**Engine:** Recommendation Strategy v3 (quality grade × peer band × valuation)  
**Universe:** curated NSE list in `screener/config/universe.yaml` (~202 tickers, 9 sector buckets)  
**This is not a black box.** Every label comes from deterministic rules. There is no LLM in the scoring path.

---

## 1. What “selecting a company” means

The system does **not** crawl the whole market and pick winners. Selection happens in three layers:

| Layer | Question it answers | Who decides |
|-------|---------------------|-------------|
| **1. Universe** | Is this company even allowed into the model? | Human list in `universe.yaml` |
| **2. Quality control** | Is the data good enough to score? | Automatic QC filters |
| **3. Recommendation** | Should we BUY, HOLD, AVOID, or SELL — and does it fit this investor? | Scoring + action matrix + (optional) risk profile |

A company can be **in the universe**, **pass QC**, and still be labelled **AVOID** or **SELL**. Being listed is not an endorsement.

The global screen (what you see on the main results table) is **profile-agnostic**. Personalized “top picks” are a second pass that re-ranks those same scored names for a risk questionnaire.

---

## 2. One-page mental model

```
Curated NSE list
        │
        ▼
Fetch prices + fundamentals (yfinance, NSE fallback, curated bank/insurance files)
        │
        ▼
Drop names with broken / too-thin data
        │
        ▼
Score the company on sector-appropriate factors  →  composite 0–100
        │
        ▼
Rank it only against its own peer cohort          →  percentile + peer band
        │
        ▼
Grade absolute quality (A–F) and valuation (Under / Fair / Over)
        │
        ▼
Action matrix: quality + valuation + hard gates + relative strength
        │
        ▼
  STRONG BUY · BUY · HOLD · AVOID · SELL
        │
        ▼
Optional: match to investor risk profile → diversified top 20
```

**The three axes that matter most**

1. **Quality grade (A–F)** — how good is the business on its own numbers?  
2. **Peer band (Top / Upper-Mid / Lower-Mid / Bottom)** — how does the composite compare to similar Indian names?  
3. **Valuation (Under / Fair / Over)** — is the stock cheap or expensive on *absolute* sector bands (not “cheap vs a worse peer”)?

The final action is **not** “highest composite wins.” A high-quality expensive stock is usually HOLD. A broken balance sheet is AVOID/SELL even if the price chart looks strong.

---

## 3. Layer 1 — who is in the universe

Sectors are **assigned by us**, not by Yahoo Finance. Yahoo’s US-style sector tags are ignored.

### 3.1 Nine buckets

| Bucket | Display label | Depth | Cyclical? | How peers are defined |
|--------|---------------|-------|-----------|------------------------|
| Banking | Financial Services | Deep | No | Private vs PSU separately |
| Insurance | Financial Services | Deep | No | The insurance list (small set) |
| IT | Technology | Deep | No | Large-cap IT vs mid-cap IT when enough names exist |
| FMCG | Consumer Defensive | Standard | No | All FMCG names |
| Pharma | Healthcare | Standard | No | All pharma names |
| Auto | Consumer Cyclical | Standard | **Yes** | All auto names |
| Energy | Energy | Standard | **Yes** | All energy names |
| Metals | Basic Materials | Standard | **Yes** | All metals names |
| Capital goods | Industrials | Standard | **Yes** | All capital-goods names |

Approximate counts today: banking ~37, insurance 2, IT ~31, FMCG ~21, pharma ~19, auto ~16, energy ~19, metals ~14, capital goods ~43. Exact membership is always the YAML list.

### 3.2 Why this list, not “all NSE stocks”

- We need a **stable peer group**. Ranking TCS against 2,000 random names is meaningless.  
- Deep sectors (banks, IT, insurance) need **extra curated ratios** (GNPA, CAR, solvency) that Yahoo does not reliably provide.  
- Cyclical vs defensive flags change how margins and valuations are interpreted.

**Implication for colleagues:** if a name is missing from the screen, it was never selected — it is simply not on the list. Adding a ticker is a configuration change, not an algorithm change.

---

## 4. Layer 2 — data fetch and who gets dropped

### 4.1 Where numbers come from

| Data | Primary source | Notes |
|------|----------------|-------|
| Price history (5 years), PE, PB, ROE, margins, market cap | yfinance | Cached 24 hours |
| Income / balance / cash-flow statements | yfinance | Used for CAGRs and growth fallbacks |
| GNPA, NNPA, CAR, NIM (banks) | Curated `banking_metrics.json` | Overrides Yahoo when present |
| Solvency, VNB, persistency (insurers) | Curated `insurance_metrics.json` | Same idea |
| Sector / peer group | `universe.yaml` only | Never from Yahoo |
| Thin price history | NSE India chart API | Fallback if Yahoo rows are short |

Some auto names (Hero, Bajaj Auto, M&M, Eicher, TVS) have **debt-to-equity capped** because Yahoo consolidates finance-subsidiary debt onto the parent and would otherwise falsely fail the leverage gate.

### 4.2 Automatic drop rules (QC)

A ticker is **not scored** if any of these is true:

| Rule | Threshold (defaults) | Why |
|------|----------------------|-----|
| Fetch failed | — | No usable payload |
| Unknown bucket | not in universe map | Cannot choose a model |
| Price history too short | < 20 daily rows | Cannot compute returns / drawdown |
| Both PE and PB missing | — | Cannot value the name |
| Data completeness too low | < 35% of core fields | Score would be noise |
| Implausible operating margin | < −20% (non-bank) | Usually a data error |

Energy is treated more gently: a large-cap or a name with ROE ≥ 8% can keep a temporarily ugly refining margin (oil-price timing), instead of being dropped or hard-gated.

Dropped names appear in the pipeline log (`Dropped TICKER → reason`). They are **not** SELLs. They are “insufficient data.”

---

## 5. Layer 3 — how a company is scored

After QC, every surviving name gets a **composite score from 0 to 100**. Missing factors are skipped and the remaining weights are renormalized. That is intentional: a missing ROE does not invent a 0; it just reduces confidence later.

### 5.1 Soft scoring (the common building block)

Most metrics are mapped to a 0–1 “soft score” with a **good** and **bad** threshold, then linearly interpolated:

- At or better than *good* → 1.0  
- At or worse than *bad* → 0.0  
- In between → a straight line  

Example (generic ROE, default bands): ROE 15% → 1.0, ROE 6% → 0.0, ROE 10.5% → 0.5.

Peer ranks use **percentiles inside the cohort**, winsorized at the 5th–95th percentile so one outlier does not stretch the scale. Small peer groups are **shrunk toward 50** so a 4-name insurance set cannot produce a fake “Top 1%.”

After scoring a cohort, composites are **shifted** so the sector mean sits near 57.5. This keeps “70” meaning roughly the same thing in FMCG and metals. **Do not compare raw composites across sectors as if they share one scale** — use the percentile / peer band for relative rank, and the quality grade for absolute quality.

### 5.2 Which engine a company uses

| If the name is… | Engine | What it optimizes for |
|-----------------|--------|------------------------|
| Banking (deep) | Bank model | Asset quality, franchise, P/B vs ROE |
| Insurance (deep) | Insurance model | Solvency, persistency, VNB / growth |
| IT (deep) | IT model | Margins, growth, PEG / earnings yield |
| Everything else | Generic model | Quality + growth + value, with sector weights |

---

## 6. Deep engines (banking, IT, insurance)

### 6.1 Banking

**Weights**

| Factor | Weight | What goes in |
|--------|--------|----------------|
| Asset quality | 30% | GNPA, NNPA, CAR, GNPA vs private or PSU peers |
| Franchise | 25% | NIM, ROA, ROE, and those vs peers |
| Valuation | 25% | P/B–ROE residual (see below) |
| Momentum | 10% | 6-month return percentile, else relative strength vs sector / Nifty |
| Risk penalty | 10% | 1-year max drawdown (lower drawdown is better) |

**Valuation idea:** inside the private or PSU cohort, the model regresses P/B on ROE.  
- Residual **negative** → cheaper than the ROE the market usually pays for → leans Under.  
- Residual **positive and large** → expensive vs that ROE line → leans Over.  
If the residual is missing, it falls back to absolute P/B and earnings-yield bands.

**Hard gates (automatic fail):** GNPA ≥ 3.5%, or NNPA ≥ 1.2%, or CAR < 12%.  
A bank without GNPA **and** NIM cannot be labelled Top peer (percentile is capped at 69). Incomplete bank files also shrink the composite.

**Peers:** HDFC Bank is ranked against other **private** banks, not against SBI. That is by design.

### 6.2 IT

**Weights**

| Factor | Weight | What goes in |
|--------|--------|----------------|
| Margin quality | 25% | Operating margin, margin trend, ROE |
| Growth | 30% | Revenue and profit CAGR (YoY used if 3-year CAGR is missing) |
| Valuation | 25% | PEG, PE vs IT peers, FCF yield, earnings yield |
| Momentum | 10% | 6-month return or relative strength |
| Risk penalty | 10% | Drawdown percentile |

**Hard gates:** operating margin < 0, or ROE < 0, or D/E > 2.5.

**Peers:** if there are at least 5 large-cap IT names (market cap ≥ ₹500B), TCS / Infosys / HCL are ranked **against other large-cap IT**, not against high-growth mid-caps. Mid-caps are ranked among themselves. This stops a mid-cap growth burst from pushing TCS into “Bottom” by construction.

### 6.3 Insurance

**Weights:** solvency / persistency 25%, franchise & growth (VNB, ROE, AUM growth, profit growth) 30%, valuation 25%, momentum 10%, risk 10%.

**Hard gates:** solvency ratio < 150%, or 13-month persistency < 75%.  
Peer percentiles are **turned off** until the insurance set has at least 5 names — otherwise two names would always be “#1 and #2.”

---

## 7. Standard engine (FMCG, pharma, auto, energy, metals, capital goods)

Every standard name is scored on the same five pillars. Only the **weights and “what good looks like”** change by sector.

### 7.1 Pillars

| Pillar | Typical ingredients |
|--------|---------------------|
| **Quality** | ROE, ROCE, operating (or EBITDA) margin, D/E, interest coverage, ROE vs peers |
| **Growth** | 3-year revenue / profit CAGR (or YoY fallback), margin trend; auto and capital goods also use revenue *acceleration* (latest growth minus 3-year CAGR) |
| **Value** | PE vs peers (cheaper PE ranks higher), earnings yield, FCF yield |
| **Momentum** | 6-month return percentile, else relative strength vs sector |
| **Risk penalty** | Drawdown percentile (or downside deviation) |
| **Cashflow** | Energy only — FCF / dividend quality |

Sector overlays (for example FMCG ROCE, pharma interest coverage) nudge the quality pillar when those fields exist.

### 7.2 Sector weights (why metals is not scored like FMCG)

| Sector | Quality | Growth | Value | Momentum | Risk | Extra |
|--------|---------|--------|-------|----------|------|-------|
| FMCG | 35% | 15% | 25% | 10% | 15% | Wants ROCE and EBITDA margin |
| Pharma | 35% | 25% | 20% | 10% | 10% | Balance-sheet overlays |
| Auto | 25% | 25% | 25% | 15% | 10% | Cyclical; acceleration |
| Energy | 28% | 12% | 28% | 12% | 12% | **Cashflow 18%** |
| Metals | 22% | 18% | 32% | 15% | 13% | Value-heavy |
| Capital goods | 30% | 30% | 20% | 10% | 10% | Growth + quality |
| Default | 30% | 25% | 25% | 10% | 10% | Used if a bucket has no override |

**Read this as investment philosophy, not trivia:**

- **FMCG / pharma** — franchise quality and balance-sheet safety matter more than a hot growth print.  
- **Metals / energy** — the model is willing to pay more attention to cheapness and cash generation because earnings swing with the cycle.  
- **Capital goods** — growth and quality share the lead (order book / execution story).  
- **Auto** — more momentum than defensives, because the cycle shows up first in price and volumes.

### 7.3 Cyclical penalty

For AUTO, ENERGY, METALS, CAPITAL_GOODS: if operating margin is very high (> 18%) and/or expanding fast (trend > +3 pp), the model assumes **peak-cycle earnings**. It:

- trims the composite (up to ~15%), and  
- will not let valuation stay “Under” if that peak-margin penalty is strong — cheap P/E on peak margins is often a trap, so the label is lifted to Fair.

---

## 8. Hard gates and red flags — automatic disqualification

These fire **before** the pretty composite can save the name.

### 8.1 Standard sectors

| Condition | Hard fail (Grade F) | Red flag (softer) |
|-----------|---------------------|-------------------|
| ROE | < −5% | < 0% |
| Operating margin | < −2% | < 0% |
| Debt / equity | > 3.0 (4.0 for auto, FMCG, pharma) | > 2.5 (3.5 for those three) |
| Interest coverage | < 0.8× | — |

**Energy exception:** a negative operating margin does **not** hard-fail if ROE ≥ 8%, or the name is large-cap (≥ ₹500B), or FCF is positive. The row is tagged `margin_distortion` so you can see the exception.

### 8.2 What a hard fail does to the action

- Hard fail + **Over** valuation → **SELL**  
- Hard fail + anything else → **AVOID**  
- Grade is forced to **F**

A red flag without a hard fail typically caps the name at **AVOID** (unless valuation is already Over, in which case the Over path can go to SELL).

---

## 9. The three axes in detail

### 9.1 Axis 1 — absolute quality grade

```
quality_score = 0.85 × fundamental_strength + 0.15 × data_completeness
```

`fundamental_strength` is the average of the **quality and growth** pillars (or asset-quality + franchise for banks). Peer rank is **not** in this formula. A high-quality laggard can still be Grade A/B.

| Grade | Rule |
|-------|------|
| **A** | quality ≥ 0.85 and no red flag |
| **B** | quality ≥ 0.65 |
| **C** | quality ≥ 0.45 |
| **D** | below C, or red flag with quality < 0.55 |
| **F** | hard gate failed |

Large / mega caps with quality ≥ 0.70 get a **display floor** on percentile (mega floored to 50, large to 30) so a franchise leader is not shown as “Bottom” purely because mid-caps ran harder. The floor never pushes them into Top (≥ 70).

### 9.2 Axis 2 — peer band

From the composite percentile **inside the cohort**:

| Band | Percentile |
|------|------------|
| Top | ≥ 70 |
| Upper-Mid | 50–70 |
| Lower-Mid | 30–50 |
| Bottom | < 30 |

**Never say “this stock scored 80 so it is better than that bank that scored 72.”** Those 80 and 72 may be from different engines and different peer sets.

### 9.3 Axis 3 — absolute valuation

Valuation is **Under / Fair / Over** from fixed sector bands in `valuation_bands.yaml`, not from “cheaper than the worst peer.”

Several metrics vote; majority wins. Example bands:

| Sector | Under if… | Fair up to… | Then Over |
|--------|-----------|-------------|-----------|
| Default PE | PE ≤ 18 | PE ≤ 28 | PE > 28 |
| IT PE | ≤ 22 | ≤ 32 | > 32 |
| FMCG PE | ≤ 30 | ≤ 45 | > 45 |
| Energy PE | ≤ 12 | ≤ 18 | > 18 |
| Metals PE | ≤ 10 | ≤ 16 | > 16 |
| Banking P/B | ≤ 2.0 | ≤ 3.5 | > 3.5 |

IT also votes PEG and earnings yield. Banks vote P/B and earnings yield. Energy / capital goods vote EV/EBITDA. Yields work in reverse (higher yield = cheaper).

That is why a “cheap” metal name can still be Over on a PE of 20, while the same PE on an FMCG name can be Fair. **The band is the investment belief about what a normal multiple is in that industry.**

---

## 10. How BUY / HOLD / SELL is decided

This is the actual selection rule colleagues should remember. Implemented in `screener/scoring/action_matrix.py`.

### 10.1 Decision order (production defaults)

1. **Hard gate failed** → SELL if Over, else AVOID. Stop.  
2. **Valuation is Over**  
   - Grade D or F → SELL  
   - Relative strength vs Nifty ≤ −10% → SELL  
   - Red flag → SELL  
   - Bank with ROE < 8% or GNPA ≥ 2.8% → SELL  
   - IT with operating margin < 12% → SELL  
   - Grade C → AVOID  
   - Otherwise fall through (usually HOLD)  
3. **Fair valuation + Grade D/F** → AVOID  
4. **Red flag** (and not already on the Over path) → AVOID  
5. **Grade C/D/F and RS vs Nifty ≤ −15%** → AVOID  
6. **Grade A, no flags, not Over**  
   - Under → **STRONG BUY**  
   - Fair and RS vs Nifty ≥ 0 (or RS missing) → **STRONG BUY**  
7. **Grade A or B, valuation Under or Fair, no hard fail** → **BUY**  
8. **Everything else** → **HOLD**

### 10.2 What that means in English

| Situation | Typical label | Grounds |
|-----------|---------------|---------|
| Excellent business, not expensive, not failing gates | **STRONG BUY** or **BUY** | Quality A/B + Fair/Under |
| Excellent business but expensive | **HOLD** | Over valuation is a ceiling |
| Mediocre business, not a disaster | **HOLD** | No upgrade path without quality |
| Broken gates or red flags | **AVOID** / **SELL** | Safety first |
| Expensive + weak + down vs Nifty | **SELL** | Over + poor quality or poor RS |

**STRONG BUY is rare by design.** It needs Grade A and a non-expensive valuation (and, if Fair, the stock should not be losing to Nifty).

### 10.3 Safety valves after the core rule

| Valve | What it does |
|-------|----------------|
| **Large-cap floor** | Mega (≥ ₹2T) and large (≥ ₹500B) names that are Grade A/B, **Fair**, and not flagged cannot be SELL/AVOID — they are lifted to HOLD. Overvalued large caps are **not** protected. |
| **Confidence downgrade** | If model confidence < 0.35, or completeness < 50% **and** ROE is missing, the action steps one rung down (STRONG BUY → BUY → HOLD → …). |
| **Conservative profile** | Over valuation cannot stay BUY; Bottom + Over becomes AVOID. |
| **Aggressive profile** | Grade A + Bottom peer + positive RS can be upgraded HOLD/AVOID → BUY. |
| **Index anchor / street overlay** | Off in production. Used only in benchmark scripts so the live UI is not silently “fitted” to Street ratings. |

---

## 11. Risk questions (the narrative layer)

After the numeric score, the interpreter answers a fixed questionnaire. **No generative AI.** Each answer is `good` / `warn` / `bad` / `unknown` from YAML bands.

| Depth | Sectors | Questions |
|-------|---------|-----------|
| Deep | Banking | 7 — asset quality, capital, NIM, loan growth, valuation, distress, earnings |
| Deep | IT | 7 — margins, margin trend, growth, PEG, leverage, concentration proxy, data quality |
| Deep | Insurance | solvency / persistency / franchise set |
| Standard | All others | 5 — balance sheet, valuation, earnings quality, momentum/tail risk, data sufficiency |

Signals become a **stock risk score (0–100)**. Higher = riskier.

```
good = 0, warn/unknown = 1, bad = 2
risk = 100 × (weighted points) / (2 × total weight)
```

Confidence is then refreshed:

```
confidence = 0.35 × completeness + 0.35 × (1 − risk/100) + 0.30 × fundamental_strength
```

The action matrix is **run again** with the new confidence, so a pretty composite on rotten data can still be stepped down.

This layer writes the headline, bull case, bear case, and key risk you see on the stock page. It does not invent a new ranking — it explains and can slightly downgrade.

---

## 12. Personalized “top picks” (second selection)

If a colleague (or client) fills the risk questionnaire, a **profile** is built: conservative / moderate / growth / aggressive. That profile has a max stock-risk, max beta, whether cyclicals are allowed, and exclusion rules.

### 12.1 Fit score (0–100)

```
fit = 0.27 × risk alignment
    + 0.25 × quality
    + 0.18 × valuation fit
    + 0.10 × profile bonus
    + 0.20 × composite
```

- **Risk alignment** starts at 100 and is cut if stock risk or beta exceeds the profile.  
- **Valuation fit:** Under = 100, Fair = 70, Over = 30 (conservative) or 40 (others).  
- **Bonuses:** e.g. conservative likes FMCG/pharma; growth likes revenue growth > 10%; aggressive likes positive momentum.

### 12.2 Who is excluded from picks

Examples (conservative is strictest):

- Stock risk above the profile cap  
- Valuation on the profile’s exclude list (conservative excludes **Over**)  
- Hard gate fail (always)  
- Red flag when the profile requires hard gates  
- Cyclical sector when the user said cyclicals are not OK  
- Beta above the profile cap (conservative)

Excluded names are not “deleted from the universe.” They are simply not offered as *personalized* picks.

### 12.3 Diversification of the published list

From remaining names with fit ≥ 45:

- At most **20** names  
- At most **3** per sector  
- Reserved floors: at least **2 banking** and **2 IT** if those sectors have eligible names  

So the “recommended companies” on the profile page are: **passed QC → scored → not excluded by risk rules → high fit → sector-diversified.** That is a different list from “every STRONG BUY in the universe.”

---

## 13. Worked examples (how to talk about a name)

These are **illustrative paths**, not live prices. Always read the current row.

### Example A — quality compounder, fair price → selected as BUY / STRONG BUY

1. Listed under Pharma in `universe.yaml`.  
2. Passes QC (PE present, history long enough, completeness ≥ 35%).  
3. Generic engine with PHARMA weights (quality 35%, growth 25%).  
4. Strong ROE / margins → high `fundamental_strength` → **Grade A**.  
5. Absolute PE inside the pharma Fair band → valuation **Fair**.  
6. No hard gates. RS vs Nifty not deeply negative.  
7. Action: **STRONG BUY** (A + Fair) or **BUY** (A/B + Fair).  
8. Conservative profile: still eligible if stock risk is low and valuation is not Over.

**Grounds:** “We like the business and we are not overpaying on our pharma multiple bands.”

### Example B — excellent franchise, expensive → HOLD, not a pick for conservatives

1. Grade A or B.  
2. PE or P/B above the sector Fair ceiling → **Over**.  
3. Action matrix has **no upgrade to BUY** while Over (unless optional index-anchor is on, which production keeps off).  
4. Conservative matcher **excludes Over** entirely.

**Grounds:** “The company is fine. The *price* is not a buy on our rules.”

### Example C — hard-gate fail → never a buy

1. Composite can still look decent (momentum or peer rank).  
2. D/E, GNPA, or margin trips a hard gate → Grade **F**.  
3. Action: **SELL** if also Over, else **AVOID**.  
4. Profile matcher excludes hard-gate fails.

**Grounds:** “We do not override solvency / leverage / loss-making gates with a high score.”

### Example D — large-cap IT that used to look “Bottom”

TCS-type names used to rank against 30+ IT mid-caps and land Bottom despite Grade B. They are now ranked in the **large-cap IT** cohort. Combined with the large-cap percentile floor, they should not be punished only because a small-cap ran. If they are still HOLD, it is usually **valuation Over** or **Fair + not Grade A**, not “the model hates TCS.”

---

## 14. How to read a result with colleagues

When someone asks “why did we pick this?” walk the row in this order:

1. **Recommendation** — the action.  
2. **Quality grade** — do we like the business?  
3. **Valuation** — are we paying a sensible multiple for that sector?  
4. **Peer band / percentile** — is it strong *among its Indian peers*?  
5. **Hard gate / red flag / data-quality flags** — did something veto the score?  
6. **Composite and breakdown** — which pillar drove the number (quality vs growth vs value vs momentum)?  
7. **Stock risk and profile fit** — only if this is a personalized list.

A useful one-liner template:

> “**{Ticker}** is **{action}** because quality is **{grade}**, valuation is **{Under/Fair/Over}** on {sector} bands, it ranks **{band}** in the {peer group} cohort, and {no hard gates / failed X}.”

---

## 15. What this algorithm is not

Please do not describe the screener as any of the following:

- A forecast of next-quarter earnings or target prices  
- A replacement for a full initiation report (no management quality, no related-party deep dive, no forensic accounting)  
- Street-consensus copy. Analyst ratings are **not** an input in production.  
- Cross-sector “best stock in India” ranking. Composites are calibrated per sector; actions are comparable, raw scores are not.  
- Coverage of the full NSE. Unlisted names were never rejected by the model.  
- Advice that ignores position sizing, taxes, or liquidity.

Known structural limits:

- yfinance ROE / margins can be missing or distorted; missing ROE lowers confidence and can step the action down.  
- Conglomerates (e.g. Reliance) sit in one bucket even if the business mix is broader.  
- Insurance peer ranks are weak until the set is larger.  
- Capital-goods is a wide bucket (cement, defence, exchanges, realty, telecom sit there today) — peer “Top” means top of *that list*, not “best industrial in India.”

---

## 16. Where the knobs live (if we need to change philosophy)

| If we want to change… | Edit |
|-----------------------|------|
| Which companies exist | `screener/config/universe.yaml` |
| What “cheap” means | `screener/config/valuation_bands.yaml` |
| What fails a name automatically | `screener/config/hard_gates.yaml` |
| Sector factor importance | `screener/config/sector_weights.yaml` (standard) or `settings.yaml` → `composite_weights` (bank / IT / insurance) |
| BUY / SELL RS cuts, bank/IT soft SELL rules | `settings.yaml` → `action_book` |
| Who conservative clients can own | `screener/config/risk_profile_matrix.yaml` |
| Finance-sub D/E patches | `screener/config/debt_adjustments.yaml` |
| Bank / insurance statutory ratios | `banking_metrics.json` / `insurance_metrics.json` |

Code map for engineers: `pipeline.py` (QC) → `composite.py` / `generic.py` (scores) → `quality_grade.py` + `action_matrix.py` (labels) → `stock_analyst.py` (risk Qs) → `risk_matcher.py` (personalized picks).

---

## 17. Summary — grounds for selection

A company is **shown as a candidate** if:

1. A human put it on the NSE universe list, and  
2. Data QC did not drop it.

A company is **labelled BUY or STRONG BUY** if:

1. It did not fail a sector hard gate,  
2. Absolute quality is A or B,  
3. Absolute valuation is Under or Fair (STRONG BUY needs Grade A),  
4. Confidence / completeness is not so poor that the action was stepped down, and  
5. Over-valuation, red flags, or weak relative strength did not force HOLD / AVOID / SELL.

A company is **offered as a personalized pick** if, in addition:

6. It is not excluded by that investor’s risk, beta, cyclical, and valuation rules,  
7. Fit score is at least 45, and  
8. It survives the 20-name / 3-per-sector / banking+IT floor diversification.

That is the full selection algorithm: **curated universe → data fitness → sector-aware quality and growth → absolute valuation → safety gates → action → optional profile fit.**

---

*This note describes the production rules as implemented in the `screener/` package. For a more file-oriented map see `docs/SCORING_ARCHITECTURE.md`. Thresholds above are the defaults in YAML; if a config file was changed after this note, the YAML wins.*
