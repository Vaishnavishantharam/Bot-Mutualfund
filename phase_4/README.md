# Phase 4: Chat application (backend + frontend)

Chat UI for the facts-only HDFC scheme FAQ. Backend calls the Phase 3 pipeline; frontend is a single-page app (welcome + chat) styled like the reference UI (purple/white, rounded corners).

## Contents

- **backend/** — FastAPI app: `POST /api/query`, `GET /api/health`; serves frontend at `/`.
- **frontend/** — Static UI: `index.html`, `styles.css`, `app.js` (welcome screen, chat with assistant bubbles and source link).

## Run (single command)

From the **project root**:

```bash
uvicorn phase_4.backend.main:app --reload
```

Then open **http://127.0.0.1:8000** in a browser. The same server serves the API and the static frontend.

- **API:** `POST /api/query` with body `{"query": "What is the expense ratio of HDFC Nifty 100?"}` → returns `{ "answer", "citation_url", "last_updated" }`.
- **Health:** `GET /api/health` → `{"status": "ok"}`.

## Requirements

- Python 3.9+
- Phase 2 vector store built (`data/vector_store/`)
- `.env` with `GROQ_API_KEY` (or set in environment) for LLM answers

Install deps: `pip install -r requirements.txt` (includes `fastapi`, `uvicorn`).
