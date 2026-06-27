# Message for Railway support / agent

Copy everything inside the block below and send it to Railway support or your Railway agent.

---

```
Subject: Meridian web app cannot connect to Postgres — cross-region networking

Hi Railway team,

My MERIDIAN web service cannot connect to PostgreSQL. The app deploys but /setup shows:

"Private Postgres (railway.internal) is unreachable — your web service and Postgres are in different Railway regions."

Previously we also saw public proxy failures:
hopper.proxy.rlwy.net — "server closed the connection unexpectedly"

Please apply the following fixes to my project:

---

PROJECT
- GitHub repo: neerajdeepak1815-del/ai-investment-analyst
- Branch: main
- App: MERIDIAN (FastAPI / Python 3.11, Dockerfile deploy)

---

REQUIRED FIXES

1) SAME REGION (critical)
   - Postgres and the Meridian WEB service must be in the SAME region.
   - Likely current state: Postgres in EU West, web service in US East (or similar mismatch).
   - Preferred fix: Move the Meridian WEB service to EU West (same region as Postgres).
   - Alternative: Create new Postgres in the web service's region and rewire DATABASE_URL.

2) WEB SERVICE BUILD SETTINGS
   - Root Directory: EMPTY (repo root — NOT "backend")
   - Builder: Dockerfile (NOT Railpack)
   - Dockerfile path: Dockerfile (repo root)
   - railway.toml at repo root sets builder = "DOCKERFILE"

3) WEB SERVICE VARIABLES (Meridian only — not on Postgres service)
   Set:
     DATABASE_URL = ${{Postgres.DATABASE_URL}}

   Remove if present:
     DATABASE_PUBLIC_URL

   Do NOT set DATABASE_URL to DATABASE_PUBLIC_URL — public proxy is unreliable cross-region.

   Other recommended variables:
     SEC_USER_AGENT = MERIDIAN/1.0 <email>
     AUTH_ENABLED = true
     AUTH_PASSWORD = <set>
     FINNHUB_API_KEY = <set>

4) REDEPLOY ORDER
   a) Redeploy Postgres — wait until healthy
   b) Redeploy Meridian web service
   c) Confirm new deployment is in the same region as Postgres

5) VERIFICATION
   After redeploy, these must succeed:
     GET https://<meridian-domain>/setup
       → "Database connected" ✓
       → host should be postgres.railway.internal (NOT hopper.proxy.rlwy.net)

     GET https://<meridian-domain>/health/diagnostics
       → "database_ok": true

---

WHAT WE'VE ALREADY TRIED (app-side, on main branch)
- Prefer private DATABASE_URL over public proxy
- SSL/keepalive for public proxy fallback
- Connection retries and clearer /setup diagnostics
- Code is deployed; failure is Railway networking / region mismatch

---

Please confirm:
1. Current region of Postgres service
2. Current region of Meridian web service
3. That DATABASE_URL on web service references private Postgres URL (railway.internal)
4. After your changes, /setup shows database connected

Thank you.
```
