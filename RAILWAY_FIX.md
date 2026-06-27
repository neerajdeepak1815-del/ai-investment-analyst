# Railway setup — fix deploy & database

**Symptom:** `/setup` shows *"Private Postgres (railway.internal) is unreachable"* or *hopper.proxy.rlwy.net connection closed*.

**Root cause:** Meridian web service and Postgres are in **different regions**. Private networking only works same-region. Public proxy is flaky cross-region.

---

## What Railway must fix (you cannot fix this in code)

| # | Setting | Correct value |
|---|---------|---------------|
| 1 | **Regions** | Postgres + Meridian web = **same region** (e.g. both EU West) |
| 2 | **Root Directory** | **Empty** (repo root) — NOT `backend` |
| 3 | **Builder** | **Dockerfile** — NOT Railpack |
| 4 | **DATABASE_URL** | `${{Postgres.DATABASE_URL}}` on web service only |
| 5 | **DATABASE_PUBLIC_URL** | **Delete** — do not use |

---

## Step-by-step (Railway dashboard)

### 1. Same region
- Postgres → Settings → note **Region**
- Meridian web → Settings → **Region** → match Postgres
- If region cannot be changed: create **new web service** in Postgres's region, copy variables, delete old service

### 2. Build settings (Meridian web)
- Root Directory: *(blank)*
- Builder: Dockerfile
- Dockerfile path: `Dockerfile`

### 3. Variables (Meridian web only)
```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
SEC_USER_AGENT = MERIDIAN/1.0 your-email@example.com
AUTH_ENABLED = true
AUTH_PASSWORD = your-password
FINNHUB_API_KEY = your-key
```

### 4. Redeploy
1. Postgres → Redeploy → wait healthy
2. Meridian web → Redeploy

### 5. Verify
```
https://<your-app>.up.railway.app/setup
https://<your-app>.up.railway.app/health/diagnostics
```
Expect: Database connected ✓, host `postgres.railway.internal`, `"database_ok": true`

---

## Alternative: keep web in US, move Postgres
1. Add PostgreSQL in **US East** (same as web)
2. `DATABASE_URL = ${{NewPostgres.DATABASE_URL}}`
3. Redeploy, verify `/setup`, remove old EU Postgres

---

## Message for Railway agent

Full copy-paste message: **[RAILWAY_AGENT_MESSAGE.md](./RAILWAY_AGENT_MESSAGE.md)**

---

## Repo deploy config (already correct on `main`)

- `Dockerfile` at repo root (Python 3.11, uvicorn)
- `railway.toml` → `builder = "DOCKERFILE"`, healthcheck `/health`
- Fallback: `backend/Dockerfile` if Root Directory stuck on `backend`
