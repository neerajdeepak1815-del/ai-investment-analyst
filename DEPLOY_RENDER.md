# Deploy MERIDIAN on Render (Railway alternative)

Use this when Railway Metal builders are stuck or you want predictable hosting (~$14/mo web + Postgres).

## One-click path

1. Push `main` to GitHub.
2. Open [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**.
3. Connect the `ai-investment-analyst` repository.
4. Render reads `render.yaml` and creates:
   - **meridian-analyst** (Docker web service)
   - **meridian-db** (PostgreSQL)
5. When prompted, set these secrets:
   - `SEC_USER_AGENT` — e.g. `MERIDIAN/1.0 you@yourdomain.com` (SEC requires contact email)
   - `AUTH_PASSWORD` — strong password for `/login`
   - `FINNHUB_API_KEY` — optional but recommended ([free key](https://finnhub.io/register)); cloud IPs often block Yahoo quotes
6. Click **Apply** and wait for the Docker build (~3–5 min first time).

## After deploy

| URL | Purpose |
|-----|---------|
| `https://<service>.onrender.com/health` | Liveness (no login) |
| `https://<service>.onrender.com/health/features` | Confirm build version |
| `https://<service>.onrender.com/login` | Dashboard login (`admin` + your password) |
| `https://<service>.onrender.com/dashboard` | MERIDIAN UI |

Run **Full Analysis** once from the dashboard to populate recommendations (fresh Postgres).

## Environment variables

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | Auto | Linked from `meridian-db` via Blueprint |
| `SEC_USER_AGENT` | Yes | SEC EDGAR user-agent string |
| `AUTH_ENABLED` | Auto | `true` in blueprint |
| `AUTH_PASSWORD` | Yes | Set in Render dashboard |
| `FINNHUB_API_KEY` | Recommended | Live stock prices |
| `NEWSAPI_KEY` | Optional | Better headline coverage |

## Troubleshooting

**Build fails** — Check Render build logs. The app builds via root `Dockerfile` (Python 3.11, no mise/Railpack).

**Login fails** — Confirm `AUTH_PASSWORD` in Environment, redeploy, try incognito.

**No quotes** — Set `FINNHUB_API_KEY`, open `/health/quote?ticker=AAPL`.

**Empty dashboard** — Click **Run Full Analysis**; check `/health/freshness`.

**Database errors** — `DATABASE_URL` is auto-normalized (`postgres://` → `postgresql+psycopg2://`).

## Local fallback (free)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SEC_USER_AGENT="MERIDIAN/1.0 you@email.com"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/dashboard` (uses SQLite by default).
