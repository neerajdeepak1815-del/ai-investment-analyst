# Deploy MERIDIAN on Render (least work)

## One click (recommended)

1. Open this link (sign in with GitHub if asked):

   **https://render.com/deploy?repo=https://github.com/neerajdeepak1815-del/ai-investment-analyst**

2. Confirm repo / branch **`main`**, then click **Apply**.
3. Wait 5–10 minutes for Docker build + Postgres.
4. Open your service URL → `/setup` → Database should be green.
5. Login: username **`admin`** / password **`MeridianStart99`**
6. On the dashboard, click **Run Full Analysis** once.

Done. That is all you must do.

### After it works (2 minutes, optional but recommended)

On **meridian-analyst** → **Environment**, change:

| Variable | Change to |
|----------|-----------|
| `AUTH_PASSWORD` | Your own strong password |
| `SEC_USER_AGENT` | `MERIDIAN/1.0 your-real-email@example.com` |
| `FINNHUB_API_KEY` | Free key from [finnhub.io](https://finnhub.io/register) |

Then **Manual Deploy** → Deploy latest.

### Pause Railway

When Render `/setup` is green, pause or delete the Railway web service so you are not billed twice.

---

## Manual path (if the deploy link fails)

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint**
2. Connect **`neerajdeepak1815-del/ai-investment-analyst`**, branch **`main`**
3. **Apply** (defaults are already in `render.yaml` — no secrets required)
4. Same verify steps as above

## Verify URLs

Replace with your real Render hostname:

| URL | Expected |
|-----|----------|
| `/setup` | Database connected ✓ |
| `/health/diagnostics` | `"database_ok": true` |
| `/login` | `admin` / `MeridianStart99` |
| `/dashboard` | UI loads |

## Cost

Blueprint uses **Starter** web + **Starter** Postgres (~$14/mo total). Always-on (no free-tier sleep).

## Troubleshooting

**Can't see the repo** — In Render, reconnect GitHub and grant access to `neerajdeepak1815-del/ai-investment-analyst`.

**Build fails** — Open service → Logs. Should build from root `Dockerfile` (`FROM python:3.11-slim-bookworm`).

**Database red on `/setup`** — Wait until `meridian-db` shows Available, then Manual Deploy the web service.

**Login fails** — Use `admin` / `MeridianStart99` (unless you already changed `AUTH_PASSWORD`).
