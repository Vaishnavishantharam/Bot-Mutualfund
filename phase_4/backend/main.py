"""
Phase 4: Backend API — POST /query calls Phase 3 pipeline.
Every response includes citation_url (exact source URL of the scheme used).
Falls back to corpus (schemes.json) when the pipeline fails so the chat still returns answers.
Preloads the pipeline in a background thread at startup so the first request can complete
within Render's ~15s request timeout (free tier).
"""
from __future__ import annotations

import logging
import sys
import threading
import traceback
from pathlib import Path

# Ensure project root is on path when running as uvicorn phase_4.backend.main:app
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("phase_4")

# Set when background preload has finished (success or failure). Until then, /api/query returns 503.
_pipeline_ready = False


def _preload_pipeline() -> None:
    """Load Phase 3 pipeline (embeddings, FAISS, etc.) so first request is fast. Runs in background at startup."""
    global _pipeline_ready
    try:
        from phase_3.query_pipeline import run_pipeline
        run_pipeline("expense ratio")
        logger.info("Pipeline preload completed")
    except Exception as e:
        logger.warning("Pipeline preload failed (first request may be slow or use fallback): %s", e)
    finally:
        _pipeline_ready = True


app = FastAPI(
    title="Mutual Fund FAQ API",
    description="Facts-only HDFC scheme FAQ — answer, citation_url, last_updated",
)


@app.on_event("startup")
def startup_preload() -> None:
    """Start listening immediately; preload pipeline in background so first /api/query can finish within ~15s (Render timeout)."""
    t = threading.Thread(target=_preload_pipeline, daemon=True)
    t.start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    citation_url: str
    last_updated: str
    source: str = "llm"  # "llm" = Phase 3 pipeline (Groq); "fallback" = corpus only, no API call


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/ready")
def ready() -> dict:
    """Let frontend poll until pipeline is ready so we don't hit 503 or timeout on first query."""
    return {"pipeline_ready": _pipeline_ready}


@app.get("/api/last-updated")
def last_updated() -> dict:
    """Return last_updated from data/schemes.json (meta.last_scraped) or data/last_indexed_at for frontend display."""
    # Prefer schemes.json meta (source of truth after Phase 1)
    schemes_path = _root / "data" / "schemes.json"
    if schemes_path.exists():
        try:
            import json
            with open(schemes_path, encoding="utf-8") as f:
                meta = json.load(f).get("meta", {})
            lu = meta.get("last_scraped") or ""
            if lu:
                return {"last_updated": lu}
        except Exception:
            pass
    # Fallback: sentinel written by Phase 5 scheduler
    sentinel = _root / "data" / "last_indexed_at"
    if sentinel.exists():
        try:
            return {"last_updated": sentinel.read_text(encoding="utf-8").strip()}
        except Exception:
            pass
    return {"last_updated": ""}


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """Run Phase 3 pipeline; on failure use corpus fallback so the chat still returns answers."""
    if not _pipeline_ready:
        raise HTTPException(
            status_code=503,
            detail="Service is warming up. Please retry in 30 seconds.",
            headers={"Retry-After": "30"},
        )
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        from phase_3.query_pipeline import run_pipeline
        out = run_pipeline(q)
        logger.info("Query answered by LLM (Phase 3 pipeline)")
        return QueryResponse(
            answer=out.get("answer", ""),
            citation_url=out.get("citation_url", ""),
            last_updated=out.get("last_updated", ""),
            source="llm",
        )
    except Exception as e:
        logger.warning("Phase 3 pipeline failed, using corpus fallback (no LLM call): %s\n%s", e, traceback.format_exc())
        from .fallback import answer_from_corpus
        out = answer_from_corpus(q, _root)
        return QueryResponse(
            answer=out.get("answer", ""),
            citation_url=out.get("citation_url", ""),
            last_updated=out.get("last_updated", ""),
            source="fallback",
        )


# Serve frontend at / (API is under /api so routes take precedence)
_frontend = _root / "phase_4" / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
