# How to deploy the chatbot

You deploy **two parts**:

1. **Backend** (FastAPI + data) → Railway, Render, or Fly.io  
2. **Frontend + API proxy** → Vercel (with `BACKEND_URL` pointing to the backend)

Then the scheduler (GitHub Actions) can keep `data/schemes.json` updated; you redeploy the backend when you want it to use new data.

---

## Part 1: Deploy the backend (Railway or Render)

The backend needs:

- `data/schemes.json`
- `data/vector_store/` (FAISS index + metadata)
- `GROQ_API_KEY` in the environment

**Option A: Railway**

1. **Push your project to GitHub** (if not already).
2. Go to [railway.app](https://railway.app) and sign in (e.g. with GitHub).
3. **New Project** → **Deploy from GitHub repo** → select your Mutual Funds repo.
4. **Settings** for the service:
   - **Root Directory:** leave empty (repo root).
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn phase_4.backend.main:app --host 0.0.0.0 --port $PORT`  
     (Railway sets `PORT` automatically.)
5. **Variables** (Environment):
   - `GROQ_API_KEY` = your Groq API key (same as in `phase_3/.env`).
6. **Include data in the repo** (so the backend has data on deploy):
   - Commit `data/schemes.json` and `data/last_indexed_at`.
   - For the vector store you have two choices:
     - **Option (i):** Run Phase 2 locally, then commit the contents of `data/vector_store/` (e.g. `index.faiss`, `metadata.pkl`) and push. Then the backend can start without building the index.
     - **Option (ii):** Do **not** commit the vector store; add a **build step** that runs Phase 1 + Phase 2 before start (e.g. in a custom start script: `python -m phase_5.run_refresh` then `uvicorn ...`). That’s slower on each deploy but doesn’t require committing binaries.
7. Deploy. Railway will build and run the start command.
8. Open the **generated URL** (e.g. `https://your-app.railway.app`). Test:
   - `https://your-app.railway.app/api/health` → `{"status":"ok"}`
9. **Copy this URL** — you’ll use it as `BACKEND_URL` on Vercel (no trailing slash).

**Option B: Render**

1. Go to [render.com](https://render.com) and sign in (e.g. with GitHub).
2. **New** → **Web Service** → connect your GitHub repo.
3. **Settings:**
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn phase_4.backend.main:app --host 0.0.0.0 --port $PORT`  
     (Render sets `PORT`.)
4. **Environment** (Environment Variables):
   - `GROQ_API_KEY` = your Groq API key.
5. Same as Railway: ensure `data/schemes.json` (and optionally `data/vector_store/` or a build that runs Phase 1+2) is available in the repo or built at deploy.
6. **Create Web Service**. After deploy, open the URL (e.g. `https://your-app.onrender.com`).
7. Test: `https://your-app.onrender.com/api/health` → `{"status":"ok"}`.
8. **Copy this URL** for Vercel’s `BACKEND_URL`.

**If you don’t commit the vector store**

- Backend will fail when Phase 3 tries to load FAISS until you either:
  - Commit `data/vector_store/` (run `python -m phase_2.indexer` locally, then commit and push), or
  - Use a start script that runs `python -m phase_2.indexer` once before starting uvicorn (slower cold start).

---

## Part 2: Deploy frontend to Vercel and connect the backend

1. Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).
2. **Add New** → **Project** → import the **same GitHub repo** (Mutual Funds).
3. **Configure:**
   - **Root Directory:** leave as **.** (repo root).
   - **Framework Preset:** Other (or leave as detected).
   - **Build Command / Output:** Vercel will use `vercel.json` in the repo (`buildCommand` copies the frontend to `public`, `outputDirectory` is `public`). You don’t need to change this unless you edited `vercel.json`.
4. **Environment variables:**
   - Name: `BACKEND_URL`  
   - Value: your backend URL from Part 1, **no trailing slash**  
     Examples:  
     - Railway: `https://your-app.railway.app`  
     - Render: `https://your-app.onrender.com`
5. Click **Deploy**. Wait for the build to finish.
6. Open the Vercel URL (e.g. `https://your-project.vercel.app`). You should see the Emily welcome screen.
7. Ask a question in the chat. The frontend calls `/api/query` on Vercel; Vercel’s serverless functions (in `api/`) proxy to `BACKEND_URL`. So the bot should respond using your deployed backend.

**If the bot doesn’t respond**

- In Vercel → your project → **Settings** → **Environment Variables**: confirm `BACKEND_URL` is set and has no trailing slash.
- Open `https://your-project.vercel.app/api/health` — it should proxy to the backend and return `{"status":"ok"}`.
- If you see “Backend not configured”, `BACKEND_URL` is missing or wrong; fix it and redeploy.

---

## Summary checklist

| Step | Where | What to do |
|------|--------|------------|
| 1 | Repo | Commit `data/schemes.json` (and optionally `data/vector_store/` or document a build that runs Phase 2). |
| 2 | Railway or Render | Create project from repo, set build/start and `GROQ_API_KEY`, deploy. |
| 3 | Railway/Render | Copy the backend URL (e.g. `https://xxx.railway.app`). |
| 4 | Vercel | Import same repo, set `BACKEND_URL` = backend URL, deploy. |
| 5 | Browser | Open Vercel URL and test the chat. |

After this, the **scheduler** (GitHub Actions) can run daily; when it updates `data/schemes.json` and you redeploy the backend, the bot will use the new data.
