# AI Investment Analyst

This is a runnable AI investment analyst product that:
- Uses a multi-investor persona framework (Buffett/Ackman/Wood/Burry/Pelosi proxy + institutional overlay)
- Pulls last 3 years of 10-K filing metadata/text from SEC EDGAR
- Pulls annual financials from SEC Company Facts (XBRL)
- Produces scored stock recommendations and a dashboard with rationale

## Run the product (local)

1. Create a virtual environment and install deps:
   - `cd backend`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Set SEC user-agent (required by SEC):
   - `export SEC_USER_AGENT="AIInvestmentAnalyst/0.1 your-email@example.com"`
2. Run API:
   - `uvicorn app.main:app --reload`
3. Open dashboard:
   - `http://127.0.0.1:8000/dashboard`

## One-click workflow

- Open dashboard and click **Run Full Analysis**.
- The system will:
  - sync the stock universe
  - fetch SEC 10-K data + financial metrics
  - score each stock using persona framework
  - display **recommended and watchlist** names, each with **live trusted-outlet headlines** (last ~10 days; refreshes when you reload the dashboard)

## Notes

- **Verify your deploy:** open **`/health/features`** (no login). You should see `auto_block_critical_risk_gate: false` and `investor_news_on_recommendation_detail: true`.
- **Investor news:** optional **`NEWSAPI_KEY`** improves headline quality; outlet filtering uses **`CRITICAL_NEWS_ALLOWLIST`** / **`CRITICAL_NEWS_STRICT_OUTLETS`** (see `backend/.env.example`).
- Live **stock prices** are best-effort: Finnhub (if `FINNHUB_API_KEY`), Yahoo, yfinance, Stooq, Twelve Data, Alpha Vantage (context only; not for order execution). Use `/health/quote` to debug providers on deploy.
- Forward-looking narrative is **illustrative** and stored with each recommendation after analysis runs; it is not a price target or guarantee.
- Uses SQLite by default (`backend/investment_analyst.db`).
- Endpoints are still available at `http://127.0.0.1:8000/docs`.
- For production, add scheduler workers and persistent deployment.

## Operations Runbook

- See `runbook.md` for production operations, monitoring, incident response, and maintenance checklist.

## Cloud deploy (Render — recommended)

Railway Metal builders have had intermittent “scheduled but never runs” failures. **Render + Docker** is the supported path.

**Full guide:** see [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md)

1. Push `main` to GitHub.
2. [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint** → connect repo.
3. Render reads `render.yaml` (Dockerfile + Postgres).
4. When prompted, set:
   - `SEC_USER_AGENT` (e.g. `MERIDIAN/1.0 your-email@example.com`)
   - `AUTH_PASSWORD` (strong password)
   - `FINNHUB_API_KEY` (recommended — [free](https://finnhub.io/register))
5. Deploy (~$14/mo Starter web + DB).

After deploy:
- `https://<your-render-domain>/health` — liveness
- `https://<your-render-domain>/login` — username `admin`

## Cloud deploy (Railway — optional)

Only if Railway builders are healthy. Use root `Dockerfile` builder (see `railway.json`). If builds stall on Metal with zero execution, migrate to Render above.
