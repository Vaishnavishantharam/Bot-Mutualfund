"""
Phase 4: Backend API — POST /query calls Phase 3 pipeline.
Uses ChromaDB/Pinecone + OpenAI embeddings (no heavy local models). Vercel-friendly.
Falls back to corpus (schemes.json) when the pipeline fails.
"""
from __future__ import annotations

import logging
import sys
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

app = FastAPI(
    title="Mutual Fund FAQ API",
    description="Facts-only HDFC scheme FAQ — answer, citation_url, last_updated",
)

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
    """No warmup needed with ChromaDB/Pinecone; always ready."""
    return {"pipeline_ready": True}


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
    """Run Phase 3 pipeline; on failure use corpus fallback."""
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
