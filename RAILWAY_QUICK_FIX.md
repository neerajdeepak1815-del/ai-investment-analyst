# Railway database still broken? Fix in 5 minutes

If `/setup` shows **railway.internal unreachable** (cross-region), Railway support may take days. Use one of these **proven workarounds**:

---

## Option A — Neon Postgres (fastest, keep Railway web)

External Postgres works from **any** Railway region. Free tier is enough to start.

### Steps

1. Go to **[neon.tech](https://neon.tech)** → Sign up (free)
2. **New Project** → name it `meridian` → pick a region close to you
3. Dashboard → **Connection details** → copy the **connection string**  
   Looks like: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`
4. Railway → **Meridian web service** → **Variables**:
   - **Replace** `DATABASE_URL` with the Neon connection string (paste full URL)
   - **Delete** `DATABASE_PRIVATE_URL` if present
   - **Delete** `DATABASE_PUBLIC_URL` if present
   - Keep: `SEC_USER_AGENT`, `AUTH_ENABLED`, `AUTH_PASSWORD`, `FINNHUB_API_KEY`
5. **Redeploy** Meridian web service
6. Open **`/setup`** → should show Database connected ✓, host `*.neon.tech`

You can delete or ignore the old Railway Postgres service to save cost once Neon works.

---

## Option B — Render (full move, ~$14/mo, most reliable)

Web + Postgres in one blueprint, same network, no cross-region issues.

1. Push `main` to GitHub (already done)
2. [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**
3. Connect repo `neerajdeepak1815-del/ai-investment-analyst`
4. Set secrets when prompted: `SEC_USER_AGENT`, `AUTH_PASSWORD`, `FINNHUB_API_KEY`
5. **Apply** → wait ~5 min
6. Open `https://<service>.onrender.com/setup`

See **[DEPLOY_RENDER.md](./DEPLOY_RENDER.md)** for details.

---

## Option C — Nuclear Railway reset (stay 100% on Railway)

If you want Railway-only and can delete/recreate services:

1. Note Postgres **region** (e.g. EU West)
2. **Delete** the current Meridian **web** service (not Postgres yet)
3. **+ New** → **GitHub Repo** → same repo
4. When creating, pick **same region as Postgres**
5. Settings: Root Directory = **empty**, Builder = **Dockerfile**
6. Variables:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SEC_USER_AGENT=MERIDIAN/1.0 your@email.com
   AUTH_ENABLED=true
   AUTH_PASSWORD=your-password
   FINNHUB_API_KEY=your-key
   ```
7. Generate domain → Redeploy Postgres → Redeploy web
8. Verify `/setup`

---

## Which to pick?

| Option | Time | Cost | Best when |
|--------|------|------|-----------|
| **A Neon** | 5 min | Free tier | Want app live today on Railway |
| **B Render** | 15 min | ~$14/mo | Tired of Railway infra issues |
| **C Nuclear** | 20 min | Railway pricing | Must stay on Railway, can recreate services |

**Recommended right now: Option A (Neon).**
