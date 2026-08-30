# PRISM — Portfolio Risk & Investment Screening Model

Code-first India equity screener across the full configured NSE universe (banking, insurance, IT, FMCG, pharma, auto, energy, metals, capital goods):

- Sector-aware composites (deep models for banking / IT / insurance; standard model elsewhere)
- Peer bands, quality grades, and STRONG BUY / BUY / HOLD / AVOID / SELL actions
- Risk questionnaire → personalized recommendations
- Stock analysis: risk checklist, bull/bear case, plus live quote (price, day & 52-week range, volume) and a 6-month chart
- FastAPI backend + React frontend

## Setup

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
```

## CLI

```bash
# Screen universe (JSON cache under .cache/screener, ~24h TTL)
python cli.py screen --sector all
python cli.py screen --sector banking --top 10 --export results.csv

# Explain one ticker
python cli.py explain HDFCBANK.NS

# Recommendations for a profile
python cli.py recommend --profile moderate --sector all
```

`--sector` accepts `all`, `both` (banking+IT), a bucket (`banking`, `it`, `fmcg`, …), or a group (`defensive`, `cyclical`, `no_financials`).

Legacy shim still works:

```bash
python stock_sector_screener.py 8 summary
```

## API

Run the API and UI together. First screen after startup can take a minute.

```bash
uvicorn api.main:app --reload --port 8000
```

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| GET | `/api/questionnaire` | Risk questions |
| POST | `/api/questionnaire/preview` | Live profile preview |
| POST | `/api/questionnaire/submit` | Save profile |
| POST | `/api/recommend` | Personalized picks |
| GET | `/api/screen?sector=all` | Ranked universe |
| GET | `/api/sectors` | Buckets + filters |
| GET | `/api/sectors/{sector}/summary` | Sector rollup |
| GET | `/api/stock/{ticker}/interpret` | Analysis + quote snapshot |
| GET | `/api/quote?t=TCS.NS` | Live quote + 6-month history (preferred; dotted tickers) |
| GET | `/api/stock/{ticker}/quote` | Same payload via path |

Quote payload includes last price, change, day high/low, 52-week high/low, volume, market cap, PE/PB, and `history: [{date, close}, ...]`. yfinance is primary; NSE is the fallback. Cached fundamentals (PE, ROE, 1Y return) fill gaps when the live feed is slow.

## React UI

```bash
cd web
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` → `:8000`.

| Path | Page |
| --- | --- |
| `/` | Risk questionnaire |
| `/universe` | Full rankings (click a ticker) |
| `/stock/:ticker` | Analysis + quote strip and 6-month chart |
| `/recommendations` | Profile-matched picks |
| `/sectors` | All-sector dashboard |
| `/sectors/:sector` | Single-sector view |

## Tests

```bash
pytest -q
```

## Layout

```
screener/          # engine (data, scoring, interpret)
  data/quote.py    # live quote + history
  config/          # universe, scoring, risk questions
api/               # FastAPI
web/               # React SPA
cli.py
tests/
docs/              # scoring and questionnaire notes
```
