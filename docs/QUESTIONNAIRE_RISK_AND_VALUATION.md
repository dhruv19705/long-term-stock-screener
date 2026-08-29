# Questionnaire, Beta, Risk Profiling, Matching & Valuation

**Audience:** investment, research, and product colleagues  
**Purpose:** explain how we turn a user’s answers into a risk profile, how we measure a stock’s beta and stock-level risk, how we match names to that profile, and how we decide Under / Fair / Over.  
**Companion:** [COMPANY_SELECTION_ALGORITHM.md](COMPANY_SELECTION_ALGORITHM.md) covers universe, scoring, and BUY/HOLD/SELL. This note is the investor-side and valuation-side detail.

There are **two questionnaires** in the product. Do not mix them up:

| Questionnaire | Who answers it | What it produces |
|---------------|----------------|------------------|
| **User questionnaire** (14 questions) | The investor | A risk profile: Conservative / Moderate / Growth / Aggressive, plus hard limits (max beta, max stock risk, sectors) |
| **Stock risk questions** (5 or 7 questions) | The model, automatically | A **stock risk score** 0–100 for that ticker |

Profile matching then asks: *does this stock’s risk, beta, valuation, and sector fit this investor?*

---

## 1. The user questionnaire

File: `screener/config/user_questionnaire.yaml`  
Logic: `screener/interpret/questionnaire.py`

Fourteen questions in three chapters. Each answer does one or both of:

- **Adds points** to the four profile buckets (this decides *which type of investor* they are)  
- **Sets a hard constraint** (this decides *what they are allowed to own*)

### 1.1 The four profiles

| ID | Label shown in UI | Default max stock risk | Default max beta | Cyclicals OK by default? |
|----|-------------------|------------------------|------------------|--------------------------|
| `conservative` | Capital Preservation | 40 | 1.15 | No |
| `moderate` | Balanced Growth | 55 | 1.35 | Yes |
| `growth` | Growth Oriented | 65 | 1.60 | Yes |
| `aggressive` | High Conviction | 80 | 2.00 | Yes |

Those defaults apply **only if the investor did not answer** the loss-tolerance or volatility questions. If they did, the answer **overrides** the default (see §1.4).

### 1.2 Chapter A — goals (4 questions)

These mostly add profile points. They do not set numeric caps.

| ID | Question | How answers lean |
|----|----------|------------------|
| `horizon` | Time horizon | &lt;1 year → conservative; 5+ years → growth / aggressive |
| `goal` | Primary goal | Preserve capital → conservative (3 pts); maximize returns → aggressive (3 pts) |
| `income_need` | Need for stable income | Critical → conservative; not needed → growth / aggressive |
| `experience` | Years investing | Beginner → conservative; 5+ years → growth / aggressive |

Example: “Preserve capital” gives **3 points to conservative and 0 to everyone else**. That is a strong pull.

### 1.3 Chapter B — risk tolerance (6 questions)

This chapter both scores the profile **and** writes the numbers we later enforce.

| ID | Question | Profile points | Constraint it writes |
|----|----------|----------------|----------------------|
| `drawdown` | Reaction to a 20% drop | Sell → conservative 3; buy more → aggressive 3 | none |
| `loss_tolerance` | Max acceptable 1-year loss on one stock | *(no profile points)* | **`max_stock_risk`**: 10%→35, 20%→50, 30%→65, 30%+→80 |
| `volatility` | Comfortable volatility | Low → conservative 3; high → aggressive 3 | **`max_beta`**: low→1.10, medium→1.35, high→1.80 |
| `valuation` | Sensitivity to price | Won’t buy expensive → conservative 3; will pay for quality → aggressive 3 | none (the *profile id* later decides whether Over is excluded) |
| `leverage` | Debt tolerance | Prefer low leverage → conservative 3 | none (used only for scoring the type) |
| `liquidity` | Might sell within 6 months? | *(no profile points)* | **`needs_liquidity`**: yes / no |

**Important:** `loss_tolerance` does **not** vote for a profile. It only sets the stock-risk cap. A long-horizon “maximize returns” person who also says “I can only lose 10% on one name” can still be classified Growth, but their **cap is 35** and many names will be excluded.

### 1.4 Chapter C — portfolio rules (4 questions)

These are almost all constraints, not personality scores.

| ID | Question | Constraint |
|----|----------|------------|
| `cyclical_pref` | Defensive vs cyclical | `cyclical_ok` true/false **and** a sector filter: `defensive` / `all` / `cyclical` |
| `concentration` | Max in one stock | 10% / 20% / 30% (`max_concentration_pct`) — stored on the profile; used as guidance, not as a position sizer in the matcher |
| `diversification` | Spread across sectors? | `diversify_sectors` true → max 3 per sector, reserved banking + IT slots; false → just the top fit scores |
| `sector_exposure` | Universe preference | `all` / exclude financials (`no_financials`) / financials + IT only (`both`) |

**Sector-filter tie-break:** if they pick a *restrictive* exposure (no financials, or financials+IT only), that **overrides** the cyclical-pref universe. If they pick “all sectors” on exposure, the cyclical-pref filter wins (defensive-only, cyclical-only, or all).

### 1.5 How we pick the winning profile

Every option that has a `scores:` block adds integer points to one or more of the four IDs. We **sum** all points, then:

```
winning profile = the ID with the highest total
```

There is no weighted “risk score 0–100” for the person. It is a **plurality vote**. Ties go to whichever ID `max()` returns first among equals (Python dict order: conservative, moderate, growth, aggressive — so a perfect tie prefers the *earlier* key, i.e. more conservative).

Worked example (abbreviated):

| Answer | Conservative | Moderate | Growth | Aggressive |
|--------|--------------|----------|--------|------------|
| Horizon 5+ years | 0 | 1 | 2 | 2 |
| Goal: grow wealth | 0 | 1 | 3 | 1 |
| Income: not needed | 0 | 0 | 2 | 2 |
| Experience: 5+ | 0 | 1 | 2 | 2 |
| Drawdown: hold | 1 | 3 | 1 | 0 |
| Volatility: medium | 0 | 3 | 1 | 0 |
| Valuation: fair is fine | 1 | 3 | 1 | 0 |
| Leverage: moderate OK | 0 | 3 | 1 | 0 |
| **Total** | **2** | **15** | **13** | **7** |

Winner: **Balanced Growth (moderate)**. Then constraints from the same answers are applied on top (e.g. if they also chose “max 10% loss,” `max_stock_risk` becomes 35 even though the profile default is 55).

### 1.6 Constraint vs default — which number wins?

| Field | If the user answered the related question | If they skipped it |
|-------|------------------------------------------|--------------------|
| `max_stock_risk` | From `loss_tolerance` (35 / 50 / 65 / 80) | Profile default (40 / 55 / 65 / 80) |
| `max_beta` | From `volatility` (1.10 / 1.35 / 1.80) | Profile default (1.15 / 1.35 / 1.60 / 2.00) |
| `cyclical_ok` | From `cyclical_pref` | True, except conservative default is False |
| `needs_liquidity` | From `liquidity` | False |
| `diversify_sectors` | From `diversification` | True |
| `sector_filter` | From cyclical_pref + sector_exposure | `all` |

The UI can preview a leading profile before all 14 are answered (`preview_from_answers`). The live recommend path uses `profile_from_answers` once answers are complete.

---

## 2. How beta is calculated

We **do not** use Yahoo’s published beta field. We compute it from daily prices against Nifty 50.

File: `screener/data/fetcher.py` → `_risk_from_close()`  
Benchmark: `^NSEI` (from `settings.yaml`)

### 2.1 Formula

Align the stock’s daily close and Nifty’s daily close on common dates. Take daily percentage returns. Then:

```
β = Cov(r_stock, r_nifty) / Var(r_nifty)
```

That is ordinary least-squares market beta: how many percent the stock typically moves when Nifty moves 1%.

- **β = 1.0** — moves with the market  
- **β = 1.4** — about 40% more volatile vs Nifty  
- **β = 0.7** — defensive vs the index  
- **β negative** — rare; usually a data quirk; we clamp it (below)

### 2.2 Minimum data

| Check | Rule | If failed |
|-------|------|-----------|
| Stock history | Need at least **60** daily closes | Beta = missing |
| Overlap with Nifty | Need at least **60** aligned closes | Beta = missing |
| Overlapping *returns* | Need at least **40** paired daily returns | Beta = missing |
| Nifty variance | Must be &gt; 0 | Beta = missing |

We use up to **5 years** of daily history (same window as the rest of the fetch).

### 2.3 After-compute cleanup

Beta is clamped to **[−1, +4]** (`normalize.py`). Extreme Yahoo/gap artifacts cannot become β = 12.

If beta is **missing**, the matcher does **not** treat that as a fail. The beta cap is only applied when a number exists. Conservative exclusion “beta too high” also requires a computed beta.

### 2.4 Related market-risk numbers (same function)

Computed in the same pass, used later for risk alignment and scoring:

| Metric | How |
|--------|-----|
| **Annualized volatility** | Daily return std × √252 |
| **Downside deviation** | Std of *negative* daily returns × √252 (need ≥ 20 down days) |
| **1-year max drawdown** | Worst peak-to-trough % over the last 252 closes |
| **RS vs Nifty** | Stock 6-month return − Nifty 6-month return (need ≥ 127 aligned days) |

`needs_liquidity = yes` penalizes a name if annualized volatility **&gt; 45%**.

### 2.5 How the questionnaire uses beta

The investor’s `max_beta` is a **ceiling**, not a target.

| Profile / answer | Typical ceiling | Meaning |
|------------------|-----------------|---------|
| Conservative default | 1.15 | Only near-market or quieter names |
| Volatility = Low | 1.10 | Slightly tighter than conservative default |
| Moderate / vol = Medium | 1.35 | Typical large-cap India range |
| Growth default | 1.60 | Mid-cap / cyclical OK |
| Volatility = High | 1.80 | High-beta names allowed |
| Aggressive default | 2.00 | Almost no beta veto |

If **stock β &gt; investor max_beta**:

- Fit score is cut by `min(20, (β − max_β) × 15)`  
- A reason line is added, e.g. `Beta 1.62 > 1.35 (−10)`  
- **Conservative only:** the name is **excluded** from picks (not just penalized)

---

## 3. How we risk-profile a *stock* (stock risk score)

This is independent of the user. Every scored ticker gets a **stock risk score from 0 to 100**. Higher = riskier.

File: `screener/interpret/stock_analyst.py`  
Questions: `banking_risk_questions.yaml`, `it_risk_questions.yaml`, `insurance_risk_questions.yaml`, `generic_risk_questions.yaml`

### 3.1 Which questions a stock gets

| Stock type | Count | Themes |
|------------|-------|--------|
| Banking | 7 | GNPA/NNPA, CAR, NIM/ROA, loan growth, valuation, distress flag, earnings trend |
| IT | 7 | Margins, margin trend, revenue growth, PEG, leverage, momentum vs Nifty, quality vs stretch |
| Insurance | 7 | Solvency, VNB, persistency, ROE, valuation, momentum, data quality |
| All other sectors | 5 | Balance sheet, valuation, earnings quality, momentum/tail risk, data sufficiency |

Generic bands are **softened for cyclicals** (auto, energy, metals, capital goods) via `sector_risk_overrides.yaml` — e.g. cyclical ROE “good” is &gt; 6%, not &gt; 10%. FMCG has its own ROE overlay.

### 3.2 How each question is graded

Each question has `good` / `warn` / `bad` rules. Evaluation order:

1. If **every** metric the question needs is missing → **unknown**  
2. Else if all `good` rules pass → **good**  
3. Else if all `warn` rules pass → **warn**  
4. Else → **bad**

Example (generic GQ1 — “Is the balance sheet safe?”):

- **Good:** D/E &lt; 0.8 **and** interest coverage &gt; 2.5  
- **Warn:** D/E &lt; 1.5  
- Otherwise **bad**

No LLM. A colleague can reproduce any signal from the YAML.

### 3.3 From signals to stock risk score

```
good     = 0 points
warn     = 1 point
unknown  = 1 point   ← missing data is treated as caution, not as safe
bad      = 2 points

stock_risk = 100 × Σ (weight × points) / Σ (weight × 2)
```

So 100 means every question was *bad*. 0 means every question was *good*. Unknown sits in the middle, which is why thin Yahoo data makes a name look riskier and also lowers confidence.

Worked example (5 generic questions, all weight 1.0 except GQ1 = 1.5 and GQ2/GQ3 = 1.2):

| Q | Signal | Weight | Points |
|---|--------|--------|--------|
| GQ1 | good | 1.5 | 0 |
| GQ2 | warn | 1.2 | 1.2 |
| GQ3 | good | 1.2 | 0 |
| GQ4 | bad | 1.0 | 2.0 |
| GQ5 | unknown | 1.0 | 1.0 |
| **Sum** | | **5.9** | **4.2** |

`stock_risk = 100 × 4.2 / (5.9 × 2) = 35.6`

That 35.6 is what we compare to the investor’s `max_stock_risk` (e.g. conservative 40, or 35 if they chose “max 10% loss”).

### 3.4 Confidence (used to step BUY down)

After stock risk is known:

```
confidence = 0.35 × data_completeness
           + 0.35 × (1 − stock_risk/100)
           + 0.30 × fundamental_strength
```

If confidence &lt; 0.35, or completeness &lt; 0.50 **and** ROE is missing, the action label is stepped one rung down (STRONG BUY → BUY → HOLD → …). Risk profiling can therefore change the *published rating*, not only the personalized list.

---

## 4. How profile matching works

File: `screener/interpret/risk_matcher.py`  
Policy table: `screener/config/risk_profile_matrix.yaml`

Matching is **not** “sort by composite and take the top 20.” It is: score every name for *this* investor → exclude the unfit → keep high-fit names → diversify.

```
For each stock that already has a score + interpretation:
    1. Apply exclusion rules  →  in or out
    2. Compute fit_score 0–100
    3. Attach reasons (why it fits / why it hurts)
Then:
    4. Drop excluded names into the “avoid” list
    5. Keep remaining names with fit ≥ 45
    6. Diversify (unless the user said “best ideas only”)
    7. Return up to 20 picks
```

The stock’s BUY/HOLD/SELL **does not change** in this step (except the conservative/aggressive tweaks already applied when `assign_action` was given a `profile_id`). Matching mainly **filters and ranks**.

### 4.1 Exclusion rules (hard outs)

| Rule | Conservative | Moderate | Growth | Aggressive |
|------|--------------|----------|--------|------------|
| Stock risk &gt; investor `max_stock_risk` | **Exclude** | Penalize only | Penalize only | Penalize only |
| Valuation on exclude list | **Over excluded** | none | none | none |
| Hard gate fail | **Exclude** (all profiles) | same | same | same |
| Red flag or fetch fail | Exclude if `require_hard_gates` | Exclude | Allowed (growth/aggressive have this off) | Allowed |
| Bad leverage / credit / solvency signal | Exclude if `require_hard_gates` | Exclude | Allowed | Allowed |
| Cyclical sector and `cyclical_ok` is false | **Exclude** | Penalize | Penalize | Penalize |
| Beta &gt; `max_beta` | **Exclude** | Penalize | Penalize | Penalize |

So a conservative client **never** sees: Over-valued names, hard-gate fails, high-beta names, cyclicals they opted out of, or names above their risk cap.

Growth and aggressive can still *see* a red-flagged name (it will score poorly). They cannot see a hard-gate fail.

### 4.2 Fit score (how we rank what remains)

```
fit = 0.27 × risk_alignment
    + 0.25 × quality          (absolute quality_score × 100)
    + 0.18 × valuation_fit
    + 0.10 × profile_bonus
    + 0.20 × composite_score
```

All five parts are 0–100 before blending.

**Risk alignment** starts at 100 and is cut:

- Stock risk above the cap: subtract `min(40, excess × 0.8)`  
- Beta above the cap: subtract `min(20, (β − max_β) × 15)`  
- Needs liquidity **and** annualized vol &gt; 45%: subtract 15  

**Valuation fit** (this is how the investor’s valuation preference shows up in ranking):

| Stock label | Conservative | Everyone else |
|-------------|--------------|---------------|
| Under | 100 | 100 |
| Fair | 70 | 70 |
| Over | 30 | 40 |
| Unknown | 50 | 50 |

Conservative already *excluded* Over, so the 30 is mostly for other profiles who can still own expensive names, just with a weaker fit.

**Profile bonus** (capped at 100, usually small):

- Conservative + FMCG or Pharma: +8  
- Growth + revenue growth &gt; 10%: half of the YAML `strong_growth` bonus  
- Low 1-year drawdown (better than −15%) if the profile has `low_drawdown`  
- Positive relative strength if the profile has `strong_momentum` (aggressive)  
- Deep-sector (bank/IT/insurance) bonus for moderate  

**Fit labels:** ≥80 Excellent, ≥60 Good, ≥40 Fair, else Poor. Excluded names are forced to **Poor** even if the numeric fit was high.

### 4.3 Diversification of the published 20

Only names with **fit ≥ 45**.

If the user said **do not diversify:** take the top 20 by fit (then composite as tie-break).

If they said **diversify** (default):

1. Reserve at least **2 banking** and **2 IT** (highest-fit names in those buckets).  
2. Then fill, **max 3 per sector**.  
3. Sort the combined list by fit, keep **20**.

That is why a conservative list is not “20 FMCG names.” Banking and IT seats are reserved even if raw fit would have filled with staples.

### 4.4 Reasons shown to the user

Up to 3 positives and 2 negatives (all negatives if excluded), for example:

- “Strong fundamental profile”  
- “Undervalued vs absolute bands”  
- “Stock risk 28 within your 40 limit”  
- “Beta 1.62 &gt; 1.35 (−10)”  
- “Valuation Over excluded (−25)”

Penalties in the text come from `risk_profile_matrix.yaml` (they describe *why*, they are not subtracted a second time from fit except via the formulas above).

---

## 5. How we calculate valuation

Valuation is a **label**: `Under` / `Fair` / `Over` / `Unknown`.  
It is **not** a DCF, not a target price, and (for most sectors) **not** “cheap vs the worst peer.”

Two different numbers exist. Do not confuse them:

| Output | What it is | Used for |
|--------|------------|----------|
| **Valuation label** | Under / Fair / Over | Action matrix (BUY vs HOLD), profile matching, risk questions |
| **Valuation *score* (0–1)** | A pillar inside the 0–100 composite | Ranking within the sector only |

### 5.1 Where the raw multiples come from

From yfinance `get_info()`:

| Field | Yahoo key | Cleanup |
|-------|-----------|---------|
| PE | `trailingPE`, else `forwardPE` | Dropped if ≤ 0 or &gt; 500 |
| PB | `priceToBook` | Dropped if ≤ 0 or &gt; 50 |
| PEG | `pegRatio`, else PE ÷ profit-growth % | Need PE &gt; 0 and growth &gt; 0 |
| EV/EBITDA | `enterpriseToEbitda` | Dropped if ≤ 0 or &gt; 100 |
| Earnings yield | **100 / PE** (we compute this) | Same as PE validity |
| FCF yield | From free cash flow / market cap in the fetcher | Used when present |

Zero, negative, or missing multiples **do not vote**. They are skipped, not treated as “cheap.”

### 5.2 Absolute bands (standard sectors, IT, insurance label)

File: `screener/config/valuation_bands.yaml`  
Code: `screener/scoring/absolute_valuation.py`

Each sector lists which metrics vote, and the cut-offs.

**Price multiples** (lower is cheaper):

```
value ≤ under_max  →  Under
value ≤ fair_max   →  Fair
value >  fair_max  →  Over
```

**Yields** (higher is cheaper):

```
value ≥ under_min  →  Under
value ≥ fair_min   →  Fair
value <  fair_min  →  Over
```

### 5.3 Sector bands (the actual numbers)

| Sector | Metrics that vote | Under | Fair (upper / lower) | Then Over |
|--------|-------------------|-------|----------------------|-----------|
| **Default** | PE, PB, EV/EBITDA | PE≤18, PB≤2.0, EV/EBITDA≤10 | PE≤28, PB≤3.5, EV/EBITDA≤16 | above those |
| **IT** | PE, PEG, earnings yield | PE≤22, PEG≤1.2, EY≥4.5% | PE≤32, PEG≤2.5, EY≥3.0% | above / below |
| **FMCG** | PE, EV/EBITDA | PE≤30, EV/EBITDA≤22 | PE≤45, EV/EBITDA≤32 | richer |
| **Pharma** | PE, EV/EBITDA | PE≤25, EV/EBITDA≤18 | PE≤38, EV/EBITDA≤28 | richer |
| **Auto** | PE, PB | PE≤18, PB≤3.0 | PE≤28, PB≤5.0 | richer |
| **Energy** | PE, EV/EBITDA | PE≤12, EV/EBITDA≤6 | PE≤18, EV/EBITDA≤10 | richer |
| **Metals** | PE, PB | PE≤10, PB≤1.5 | PE≤16, PB≤2.5 | richer |
| **Capital goods** | PE, EV/EBITDA | PE≤22, EV/EBITDA≤14 | PE≤35, EV/EBITDA≤22 | richer |
| **Banking (fallback)** | PB, earnings yield | PB≤2.0, EY≥4.5% | PB≤3.5, EY≥3.0% | richer |
| **Insurance** | PB, PE | PB≤3.0, PE≤25 | PB≤6.0, PE≤45 | richer |

That is why PE 24 can be **Fair for IT**, **Over for energy**, and **Under for FMCG**. The band *is* the investment belief about a normal multiple in that industry.

### 5.4 How votes become one label

Each available metric casts Under, Fair, or Over. Then:

1. If **no** metric could vote → **Unknown**  
2. If Under votes **strictly outnumber** Over **and** Under has a majority of all votes → **Under**  
3. Same rule for Over → **Over**  
4. If Under and Over are tied (and both &gt; 0) → **Fair**  
5. If every vote is the same → that label  
6. Otherwise → **Fair**

Majority for an odd count of votes is `n//2 + 1`. For 2 votes, you need both (or a tie → Fair). For 3 votes, you need at least 2 Unders to print Under.

**Cyclical cheap-trap rule:** auto / energy / metals / capital goods only. If the label came out **Under** but margins look peaky (operating margin &gt; 18% and/or margin trend &gt; +3 pp, penalty ≥ 0.4), we **lift Under → Fair**. Cheap P/E on peak-cycle earnings is not treated as a bargain.

### 5.5 Banking (and insurance composite score) — P/B vs ROE residual

Banks are valued on **how much P/B the market pays per unit of ROE**, inside the **private or PSU** cohort — not on a single PE.

File: `screener/scoring/banking_valuation.py`

1. Keep peers that have both P/B &gt; 0 and ROE.  
2. If at least **4** such names: ordinary least squares  
   `P/B ≈ a + b × ROE`  
   **Residual = actual P/B − fitted P/B**  
   - Residual **&lt; −0.25** → Under (cheaper than the ROE line)  
   - Residual **&gt; +0.55** → Over  
   - Else Fair  
3. If fewer than 4 names: residual ≈ `P/B ÷ median P/B − 1`  
   - Ratio &lt; 0.85 → Under; &gt; 1.15 → Over  
4. If that still cannot produce a label → fall back to the **absolute** banking PB / earnings-yield bands in §5.3.

The residual is also mapped into the 0–1 **valuation pillar** of the bank composite (`0.5 − residual × 0.4`, clipped to 0–1). Negative residual raises the composite; rich residual lowers it.

Insurance uses a similar residual for the *composite pillar*, but the **published label** is the absolute insurance PE/PB bands (life insurers normally trade richer P/B than banks, so the Fair ceiling is 6.0× book).

### 5.6 How valuation changes the recommendation and the pick list

| Valuation | Effect on action (quality A/B, no hard fail) | Effect on conservative picks | Effect on fit score |
|-----------|----------------------------------------------|------------------------------|---------------------|
| **Under** | BUY; Grade A → STRONG BUY | Eligible (best case) | 100 |
| **Fair** | BUY; Grade A + non-negative RS vs Nifty → STRONG BUY | Eligible | 70 |
| **Over** | Usually **HOLD** (no BUY path in production) | **Excluded** | 30 or 40 |
| **Unknown** | Treated like a non-Under path → typically HOLD | Not on the Over exclude list | 50 |

Over + Grade D/F, or Over + RS vs Nifty ≤ −10%, or Over + red flag, can become **SELL**. That is valuation *plus* quality/risk, not valuation alone.

The questionnaire answer “I won’t buy expensive stocks” does two things: it **adds conservative points** (more likely Capital Preservation) and, if they land conservative, **Over is excluded**. “I will pay for quality” adds aggressive/growth points; Over is then allowed but still scored as a weak valuation fit and still blocked from BUY by the action matrix.

---

## 6. End-to-end example

**Investor answers (short version):** 5+ year horizon, grow wealth, medium volatility, “fair valuation is fine,” max 20% single-stock loss, balanced sectors, please diversify.

1. Profile points peak on **moderate** → label **Balanced Growth**.  
2. Constraints: `max_stock_risk = 50` (from the 20% loss answer), `max_beta = 1.35` (from medium vol), `cyclical_ok = true`, `sector_filter = all`, `diversify_sectors = true`.  
3. Universe is scored as usual. Each stock gets quality, peer band, **valuation label**, and **stock risk**.  
4. A pharma name: Grade A, Fair valuation (PE 28 on pharma bands), β = 0.9, stock risk = 32.  
   - Not excluded.  
   - Risk alignment ≈ 100. Valuation fit = 70. Quality high.  
   - High fit → can enter the top 20 (max 3 pharma).  
5. A metal name: Grade B, PE 18 → **Over** on metals (Fair max 16).  
   - Moderate does *not* exclude Over.  
   - Action is HOLD. Valuation fit = 40. Fit may still clear 45, but it will rank below the Fair/Under names.  
6. A high-beta small-cap (β = 1.7): penalized on fit; not excluded (only conservative would hard-exclude). Unlikely to beat 3-per-sector names with better alignment.

**One-liner for colleagues:**

> “We classify the *person* by a 14-question vote plus explicit caps (beta, stock risk, sectors). We measure the *stock* with computed Nifty beta and a 5–7 question risk score. We value the *price* with sector multiple bands (banks: P/B vs ROE). Matching keeps names inside those caps, scores fit, and prints a diversified 20.”

---

## 7. What this is not

- Not a psychometric “risk score out of 100” for the human — it is a **winner-take-all profile** plus numeric ceilings.  
- Not Yahoo beta, not levered/unlevered beta, not beta vs a sector index (always **Nifty 50**).  
- Not a DCF or 12-month target. Under means “cheap vs our band,” not “must rise 20%.”  
- Not advice on position size. `max_concentration_pct` is stored but the matcher does not allocate rupees.  
- Stock risk **unknown** is not “safe”; it counts like a warning.

---

## 8. Where to change the philosophy

| Change this | File |
|-------------|------|
| Question wording, profile point tables, loss/beta ceilings on answers | `screener/config/user_questionnaire.yaml` |
| Profile defaults when a question is skipped | `screener/interpret/questionnaire.py` → `PROFILE_DEFAULTS` |
| Who is excluded, fit bonuses, 20 / 3 / floors | `screener/config/risk_profile_matrix.yaml` |
| What “cheap” means per sector | `screener/config/valuation_bands.yaml` |
| Stock risk question bands | `*_risk_questions.yaml` and `sector_risk_overrides.yaml` |
| Beta formula / Nifty symbol | `screener/data/fetcher.py`, `settings.yaml` → `benchmark_nifty` |
| Bank P/B–ROE residual cuts | `screener/scoring/banking_valuation.py` |

---

*Production rules as implemented in `screener/interpret/` and `screener/scoring/`. If a YAML file was edited after this note, the YAML wins.*
