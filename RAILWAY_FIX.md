# Railway setup — fix wrong service config

Railway support flagged three issues. **Items 1–2 are UI settings** (cannot be set in `railway.toml` for root directory).

## 1. Root Directory → empty (repo root) — RECOMMENDED

**Web service → Settings → Source → Root Directory**

| Wrong | Correct |
|-------|---------|
| `backend` | *(leave blank / empty)* |

Why: Root `Dockerfile` copies `backend/` into the image. If Root Directory is `backend`, Railway can't find the root Dockerfile and may fall back to Railpack.

**Fallback:** If you must keep Root Directory = `backend`, the repo now includes `backend/Dockerfile` + `backend/railway.toml` — still use Dockerfile builder, not Railpack.

---

## 2. Builder → Dockerfile (not Railpack)

**Web service → Settings → Build → Builder**

| Wrong | Correct |
|-------|---------|
| Railpack | **Dockerfile** |

**Dockerfile path:** `Dockerfile` (relative to root directory above)

Repo-root `railway.toml` and `railway.json` also set `builder = "DOCKERFILE"`. Redeploy after changing the UI — config-as-code overrides dashboard **on deploy**, but wrong Root Directory can prevent finding the file.

---

## 3. Postgres and web service — SAME REGION

**Problem:** Postgres in **EU West**, Meridian web service in **US East** → latency, connection issues, private networking may not work.

**Fix (pick one):**

### Option A — Move web service to EU West (easier)
1. Web service → **Settings** → **Regions**
2. Set region to **EU West** (same as Postgres)
3. Redeploy

### Option B — Recreate Postgres in US East
1. Add new **PostgreSQL** in **US East**
2. Update web service variable: `DATABASE_URL = ${{NewPostgresName.DATABASE_URL}}`
3. Remove old EU Postgres when confirmed working

---

## 4. Wire DATABASE_URL

**Web service → Variables → New Variable → Add Reference**

```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
```

Use your actual Postgres service name if not `Postgres`.

Also set:
- `SEC_USER_AGENT` = `MERIDIAN/1.0 your-email@example.com`
- `AUTH_ENABLED` = `true`
- `AUTH_PASSWORD` = your password
- `FINNHUB_API_KEY` = *(recommended)*

---

## 5. Verify after redeploy

```
GET https://<your-app>.up.railway.app/health
GET https://<your-app>.up.railway.app/health/ready
GET https://<your-app>.up.railway.app/health/diagnostics
```

Expect: `"database_ok": true`, `"database_type": "postgresql"`

Then: `/login` → `/dashboard` → **Run Full Analysis**

---

## Copy-paste for Railway agent

```
Please fix my Meridian web service config:

1. Root Directory: CLEAR (empty = repo root). Currently wrongly set to "backend".
2. Builder: Dockerfile (not Railpack). dockerfilePath = Dockerfile
3. Postgres (EU West) and web service (US East) are in different regions — move web service to EU West OR recreate Postgres in US East, then wire DATABASE_URL reference.
4. Confirm DATABASE_URL=${{Postgres.DATABASE_URL}} on web service.
5. Redeploy and verify /health/diagnostics database_ok:true

Repo: neerajdeepak1815-del/ai-investment-analyst branch main
```
