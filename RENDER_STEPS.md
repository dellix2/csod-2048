# Step-by-step: Git → Render → “Is it working?”

Use this checklist in order. Your **local** project is already a Git repo and matches GitHub (see Part 1). **Render** must be checked **in your browser** — it cannot be verified from this machine alone.

---

## Part 1 — Is my application on Git?

### 1.1 On your PC (already verified for this folder)

Open PowerShell in the project folder and run:

```powershell
cd c:\Users\Admin\Desktop\eC_scripts\MicroApps\2048
git remote -v
git status
```

You should see:

- `origin` pointing to `https://github.com/dellix2/csod-2048.git`
- `On branch main` and **up to date** with `origin/main` (or `git push` if you have local commits to upload)

### 1.2 On the web

1. Open: **https://github.com/dellix2/csod-2048**
2. Confirm you see your files: `app/`, `static/`, `requirements.txt`, etc.

If the repo opens and files are there, **your application code is on Git**.

---

## Part 2 — Is my application connected to Render?

You have to **log in** at [dashboard.render.com](https://dashboard.render.com) and look for a **Web Service** that uses this repo.

### 2.1 If you already created a service

1. Go to **Render Dashboard**.
2. Find a service whose name you chose (e.g. `csod-2048`).
3. Open it → **Settings** (or the service overview).
4. Under **Build & Deploy** / **Source**, check:
   - **Repository** = `dellix2/csod-2048` (or your fork path)
   - **Branch** = `main`

If that matches, **Render is connected to your Git repo**.

### 2.2 If you do **not** see any service yet — create it (first-time setup)

1. Push your latest code to GitHub (if needed):

   ```powershell
   cd c:\Users\Admin\Desktop\eC_scripts\MicroApps\2048
   git status
   git push origin main
   ```

2. Open [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**.

3. **Connect** GitHub and authorize Render if asked.

4. Select repository **`dellix2/csod-2048`**, branch **`main`**.

5. Configure:

   | Setting | Value |
   |---------|--------|
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

6. **Environment** → **Add Environment Variable** for each line your app needs (same names as `.env`):

   - `CSOD_CORP`
   - `CSOD_CLIENT_ID`
   - `CSOD_CLIENT_SECRET`
   - `CSOD_SCOPES`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - (optional) `LEADERBOARD_LIMIT`

   Paste **real values** from your local `.env` file (not from `.env.example`).

   **Alternative — Secret Files:** You can upload a single file named **`.env`** (same `KEY=value` lines) under **Environment → Secret Files** instead of pasting each variable. This app loads it from **`/etc/secrets/.env`** on Render.

7. Click **Create Web Service** and wait until the first deploy finishes.

After this, your app **is** connected to Render.

---

## Part 3 — Is the application working?

### 3.1 On Render: deploy succeeded

1. Open your **Web Service** on Render.
2. Check the top: status should be **Live** (green) after deploy.
3. Open the **Logs** tab: look for **Uvicorn running** and no repeated crash errors.

### 3.2 Health check URL

1. On the service page, copy the **URL** (e.g. `https://something.onrender.com`).
2. In a browser, open:

   `https://YOUR-URL/healthz`

   You should see JSON: `{"ok":true}`

If you see that, the **server is running**.

### 3.3 Full app

Open:

`https://YOUR-URL/`

You should see the 2048 page. (Sign-in via Cornerstone only works when opened from CSOD with `code` and `state`; locally you may see the “authorization required” message — that is normal.)

### 3.4 If something fails

| Symptom | What to check |
|--------|----------------|
| Build failed | Logs → fix Python errors; confirm `requirements.txt` exists at repo root. |
| Deploy failed / crash loop | Logs → often missing **environment variables** or wrong `CSOD_*` / `SUPABASE_*` values. |
| 502 / “Application failed to respond” | Service sleeping (free tier: wait ~1 min after idle); or process crashed — read **Logs**. |
| `/healthz` works, leaderboard errors | Supabase URL/key and table from `supabase_schema.sql`. |

---

## Quick summary

| Question | How you know |
|----------|----------------|
| **On Git?** | Repo visible at `https://github.com/dellix2/csod-2048` with your files. |
| **On Render?** | Dashboard shows a Web Service linked to `dellix2/csod-2048` / `main`. |
| **Working?** | `https://YOUR-RENDER-URL/healthz` returns `{"ok":true}` and Logs show no crash loop. |

For more deployment detail, see **`DEPLOY.md`**.
