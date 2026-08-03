# Deploy MERIDIAN on Render

## Fix for: `databases[0].plan` / legacy `starter` not supported

Old `render.yaml` used `plan: starter` for Postgres — Render no longer allows that for **new** databases.

Fixed Blueprint on `main`:
- **No Render Postgres** in the Blueprint
- **Free web** service
- You paste a free **Neon** connection string as `NEON_DATABASE_URL`

---

## What to do now

### 1. Wait ~1 minute for GitHub `main` to update
(after we push the fixed `render.yaml`)

### 2. Create free Neon DB
1. https://neon.tech → New project `meridian`
2. Copy connection string  
   `postgresql://...@ep-xxx.neon.tech/neondb?sslmode=require`

### 3. Re-run Blueprint on Render
1. Cancel the failed Blueprint if needed
2. **New +** → **Blueprint**
3. Repo: `neerajdeepak1815-del/ai-investment-analyst`
4. Branch: **`main`**
5. Blueprint name: anything (e.g. `meridian`)
6. When asked for **`NEON_DATABASE_URL`**, paste the Neon string
7. **Apply**

No Render Postgres → no legacy `starter` error. Free web may still ask you to verify account, but not for a paid DB plan.

### 4. After deploy
- Open `https://meridian-analyst.onrender.com/setup` (or your Render URL)
- Login: `admin` / `MeridianStart99`
- Run **Full Analysis**

---

## If you prefer paid Render Postgres instead

Change `render.yaml` databases to:

```yaml
databases:
  - name: meridian-db
    plan: basic-256mb
```

(`basic-256mb` is the current lowest paid plan — requires a card.)

---

## Login defaults

| Field | Value |
|-------|--------|
| Username | `admin` |
| Password | `MeridianStart99` |
