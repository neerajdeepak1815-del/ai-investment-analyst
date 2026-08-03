# Railway database still broken? Fix in 5 minutes

If `/setup` shows **railway.internal unreachable**, Railway Postgres is in a different region than your web app. **Use Neon instead.**

---

## Option A — Neon Postgres (recommended)

Railway **overwrites** `DATABASE_URL` when Postgres is linked. Use **`NEON_DATABASE_URL`** instead — Railway will not touch it.

### Steps

1. Go to **[neon.tech](https://neon.tech)** → Sign up (free)
2. **New Project** → name it `meridian`
3. **Connection details** → copy the **connection string**  
   Example: `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
4. Railway → **Meridian web service** → **Variables** → **New variable**:
   ```
   NEON_DATABASE_URL = postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
   ```
   Paste your full Neon string. Do **not** wrap in extra quotes.
5. **Redeploy** Meridian web service
6. Open **`/setup`** and confirm:
   - `active_database_source` = **NEON_DATABASE_URL**
   - `resolved_settings_host` = **\*.neon.tech**
   - Database connected ✓

You can ignore Railway Postgres after this (delete it later to save cost).

---

## Option B — Render (full move, ~$14/mo)

Web + Postgres in one blueprint — no cross-region issues.

1. [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**
2. Connect repo `neerajdeepak1815-del/ai-investment-analyst`
3. Set `SEC_USER_AGENT`, `AUTH_PASSWORD`, `FINNHUB_API_KEY`
4. **Apply** → open `https://<service>.onrender.com/setup`

See **[DEPLOY_RENDER.md](./DEPLOY_RENDER.md)**.

---

## Option C — Fix Railway regions (100% Railway)

1. Move Meridian web + Postgres to **same region** (e.g. both EU West)
2. `DATABASE_URL=${{Postgres.DATABASE_URL}}`
3. Remove `DATABASE_PUBLIC_URL`, `NEON_DATABASE_URL`
4. Redeploy both services

---

## Troubleshooting `/setup`

| Field | Good | Bad |
|-------|------|-----|
| `active_database_source` | `NEON_DATABASE_URL` | `DATABASE_PRIVATE_URL` |
| `resolved_settings_host` | `*.neon.tech` | `postgres.railway.internal` |
| `deploy_commit` | recent (starts with `24471` or newer) | old / unknown |

If `active_database_source` is still `DATABASE_PRIVATE_URL`, you did not set `NEON_DATABASE_URL` or need to redeploy.
