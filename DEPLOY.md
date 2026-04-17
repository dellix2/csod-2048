# Deploying the 2048 CSOD widget

This guide walks through **Supabase** (database), **HTTPS hosting** for the Python app, and how it connects to **Cornerstone OnDemand**.

---

## Part 1 — Supabase setup

### 1. Create a project

1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. **New project** → choose organization, name, database password (save it somewhere safe), region close to your users.
3. Wait until the project finishes provisioning.

### 2. Create the leaderboard table

1. In the Supabase dashboard, open **SQL Editor**.
2. Click **New query**, paste the full contents of `supabase_schema.sql` from this repository, and run it.
3. Confirm there are no errors. You should see table `public.leaderboard_scores`.

### 3. Get `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

Supabase split things across a few screens. You need **two** values for `.env`:

| Env variable | What it is |
|--------------|------------|
| `SUPABASE_URL` | Your project’s HTTPS API URL (ends with `.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | A **secret** key used **only on the server** (FastAPI). It must be able to read/write tables with RLS enabled. |

#### A) Project URL (`SUPABASE_URL`)

The **API Keys** page does **not** show the URL. Get it from one of these:

1. **Project Settings → General** (gear icon in the left sidebar) → look for **Project URL** or **Reference URL** (format `https://<project-ref>.supabase.co`).
2. Or from the project **home**: click **Connect** (top of the dashboard) — the connection dialog includes the same URL.

Copy that full `https://…supabase.co` value into `SUPABASE_URL`.

#### B) Secret key for the Python app (`SUPABASE_SERVICE_KEY`)

You are on **Project Settings → API Keys**. Two kinds of keys appear:

- **Publishable** (`sb_publishable_…`) — public, browser-safe. **Do not** use this for the leaderboard backend.
- **Secret** (`sb_secret_…`) — privileged, backend-only. This is the *new* format.

This app uses the official Python client (`supabase-py`). To avoid compatibility issues, use the **legacy JWT** secret (most reliable today):

1. Stay on **Project Settings → API Keys**.
2. Open the tab named **`Legacy anon, service_role API keys`** (or similar wording at the top of the page).
3. Find **`service_role`** (labeled secret / never expose in the browser).
4. Click **Reveal** and copy the **long** key that starts with **`eyJ`**.
5. Put that into **`SUPABASE_SERVICE_KEY`** in your `.env` or hosting secrets.

**If you prefer the new secret key** (`sb_secret_…` under **Secret keys**): use only a **recent** `supabase` Python package; if database calls fail, switch to the **Legacy `service_role`** key above.

Official reference: [Understanding API keys](https://supabase.com/docs/guides/api/api-keys).

**Security:** `SUPABASE_SERVICE_KEY` bypasses Row Level Security. Use it **only** in the FastAPI server environment, never in frontend code or public repositories.

---

## Part 2 — Prepare the application

### 1. Environment variables

On your machine (or in your host’s dashboard later), set these:

| Variable | Description |
|----------|-------------|
| `CSOD_CORP` | Tenant slug, e.g. `acme` for `https://acme.csod.com` |
| `CSOD_CLIENT_ID` | From your CSOD OAuth application |
| `CSOD_CLIENT_SECRET` | From your CSOD OAuth application |
| `CSOD_SCOPES` | Usually `all` or the exact scopes registered (space-separated if multiple) |
| `SUPABASE_URL` | From Supabase **Settings → API** |
| `SUPABASE_SERVICE_KEY` | Supabase **service_role** key |
| `LEADERBOARD_LIMIT` | Optional; default `50` |

Copy `.env.example` to `.env` locally and fill values for testing. Production hosts use the same variables in their **environment / secrets** UI.

### 2. Test locally (optional)

```powershell
cd path\to\2048
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/healthz` — you should see `{"ok":true}`.

---

## Part 3 — HTTPS application hosting

The Cornerstone **Custom External Widget** iframe URL **must be HTTPS** and the hostname must be allowed in your OAuth app’s **sanctioned domain(s)**. Pick one deployment style below.

### Option A — Platform with built-in HTTPS (simplest)

Examples: **Railway**, **Render**, **Fly.io**, **Google Cloud Run**, **Azure App Service**. Pattern is the same:

1. **Push code** to GitHub/GitLab (or use the platform’s CLI).
2. **Create a new Web Service** pointing at this repo; set:
   - **Build**: N/A or `pip install -r requirements.txt`
   - **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
     (Some platforms use `PORT` automatically; Render/Railway document the exact variable name.)
3. Add **all environment variables** from Part 2 (never commit `.env`).
4. Deploy and note the **public HTTPS URL**, e.g. `https://your-app.onrender.com`.

**Render example (typical):**

- Environment: **Python 3**
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Deploy on Render (step by step)

1. **Put the code on GitHub** (or GitLab / Bitbucket). Render deploys from a Git remote. Commit everything **except** `.env` (keep secrets out of the repo; `.gitignore` should list `.env`).

2. **Sign in** at [render.com](https://render.com) and click **New +** → **Web Service**.

3. **Connect** the repository that contains this project. Authorize Render if prompted.

4. **Configure the service** (adjust names as you like):

   | Field | Value |
   |--------|--------|
   | **Name** | e.g. `csod-2048` |
   | **Region** | Closest to your users |
   | **Branch** | `main` (or your default branch) |
   | **Root directory** | Leave empty if the repo root *is* this app (where `requirements.txt` lives). |
   | **Runtime** | **Python 3** |
   | **Build command** | `pip install -r requirements.txt` |
   | **Start command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

   Render sets **`PORT`** automatically; do not hard-code a port.

5. **Environment variables** — open **Environment** and add each variable (same names as your local `.env`):

   - `CSOD_CORP`
   - `CSOD_CLIENT_ID`
   - `CSOD_CLIENT_SECRET`
   - `CSOD_SCOPES` (e.g. `all`)
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - Optional: `LEADERBOARD_LIMIT` (default `50` if omitted)

   Use **Secret** / masked entries for anything sensitive.

6. **Create Web Service** and wait for the first deploy. When it succeeds, open the **URL** Render shows (e.g. `https://csod-2048.onrender.com`).

7. **Smoke test:** visit `https://<your-service>.onrender.com/healthz` — you should see `{"ok":true}`.

8. **Cornerstone:** In your CSOD OAuth app, add the **sanctioned domain** for that hostname (e.g. `csod-2048.onrender.com`). Set the Custom External Widget iframe URL to `https://<your-service>.onrender.com/` (with or without trailing slash, consistently).

**Notes:**

- **Free tier:** The service **spins down** after idle time; the first request after sleep can take **~30–60 seconds**. For production or demos, consider a paid instance or another host if that latency is unacceptable.
- **Python version:** If you need a specific version, add a `runtime.txt` in the repo root with one line, e.g. `python-3.12.8`, and redeploy.
- **Custom domain:** In the Render service → **Settings** → **Custom Domain**, add your domain and follow DNS instructions if you use something other than `*.onrender.com`.

**Railway / Fly:** Set the same start command; bind `0.0.0.0` and use the platform’s `$PORT` or equivalent.

### Deploy without pushing code to Git

Render’s usual **Web Service from a repo** expects GitHub/GitLab/Bitbucket. If you **do not** want your app in a Git remote at all, use one of these:

#### A) Render + Docker image (no app source in Git)

1. Install [Docker](https://docs.docker.com/get-docker/) on your machine.
2. In the project folder (where the `Dockerfile` is), build and push to [Docker Hub](https://hub.docker.com/) (create a free account and `docker login`):

   ```bash
   docker build -t YOUR_DOCKERHUB_USER/csod-2048:latest .
   docker push YOUR_DOCKERHUB_USER/csod-2048:latest
   ```

3. In Render: **New +** → **Web Service** → choose **Deploy an existing image from a registry** (wording may be “Existing Image”).
4. Enter your image, e.g. `YOUR_DOCKERHUB_USER/csod-2048:latest`.
5. Add the same **environment variables** as in Part 2 (Render does not read a `.env` file from the image for secrets—set them in the dashboard).
6. Deploy. Update the image later with `docker build` + `docker push` and trigger a **manual deploy** on Render if it does not auto-pull.

Your **application code** never has to live in GitHub; only the **built image** is on Docker Hub (you can keep the repo private or not use Git at all for deployment).

#### B) Your own server (no Git, no Docker)

Copy the project folder to a VPS with **SCP**, **WinSCP**, **rsync**, or a ZIP upload (e.g. DigitalOcean, Linode, AWS EC2). Install Python, `pip install -r requirements.txt`, run `uvicorn` behind **Caddy** or **nginx** for HTTPS—see **Option B** below. No Git required.

### Option B — Your own Linux VPS + reverse proxy (HTTPS)

1. **Server**: Ubuntu LTS VM with a public IP and DNS name (e.g. `2048.yourcompany.com` → server IP).
2. **DNS**: Create an **A record** for your subdomain pointing to the server.
3. **App on the server** (example with systemd + gunicorn):

   ```bash
   sudo apt update && sudo apt install -y python3-venv nginx
   cd /opt/2048
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

   Run with Gunicorn + Uvicorn workers:

   ```bash
   gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8765
   ```

   Put that behind **systemd** with `Environment=` lines for all variables, or an `EnvironmentFile=/opt/2048/.env` (chmod 600, not world-readable).

4. **HTTPS with Caddy** (automatic Let’s Encrypt):

   Install [Caddy](https://caddyserver.com/docs/install), then a minimal `Caddyfile`:

   ```text
   2048.yourcompany.com {
       reverse_proxy 127.0.0.1:8765
   }
   ```

   Reload Caddy; it obtains and renews TLS certificates.

   **Alternative:** **nginx** + **Certbot** (`certbot --nginx`) with `proxy_pass` to `127.0.0.1:8765`.

5. **Firewall**: Allow **80** and **443** only from the internet; keep **8765** bound to localhost.

---

## Part 4 — Cornerstone OnDemand configuration

1. **OAuth application** (already registered): ensure **sanctioned domain(s)** include the **exact host** you deploy to, e.g. `your-app.onrender.com` or `2048.yourcompany.com` (no path; domain-level allowlist depends on CSOD UI—match what your admin console asks for).
2. **Custom page** → add **Custom External Widget**:
   - Select your OAuth application.
   - **Iframe URL** = your **HTTPS root**, e.g. `https://2048.yourcompany.com/`  
     (Trailing slash optional; use the same URL you tested.)
3. Save and open the page **inside CSOD** so the LMS can append `?code=...&state=...` to the iframe. The app exchanges the code server-side and stores the token in `sessionStorage`.

---

## Part 5 — Verification checklist

| Step | Check |
|------|--------|
| Supabase | Table exists; service role key works (app can start and hit DB). |
| HTTPS | Browser shows padlock; `https://your-host/healthz` returns `{"ok":true}`. |
| CSOD | Widget loads in iframe; no “invalid redirect/domain” errors. |
| Auth | After load, UI shows “Signed in as …” when code exchange succeeds. |
| Leaderboard | Play a game; score appears in list after a qualifying move / game over. |

---

## Troubleshooting

- **Token exchange fails:** Wrong `CSOD_CORP`, client id/secret, or `CSOD_SCOPES`; or code expired—reload from the custom page again.
- **Leaderboard empty / errors:** Wrong `SUPABASE_URL` or `SUPABASE_SERVICE_KEY`; confirm `supabase_schema.sql` ran successfully.
- **Iframe blocked or OAuth domain error:** Sanctioned domain in CSOD must match deployment hostname exactly (including subdomain).
- **User name wrong:** Adjust `parse_csod_user` in `app/csod.py` after inspecting real `/userinfo` JSON from your tenant.

---

## Security reminders

- Rotate **client secret** and **service_role** key if they leak.
- Do not commit `.env` or keys to git.
- The Python app must be the only component that calls CSOD’s token endpoint with the **client secret**.
