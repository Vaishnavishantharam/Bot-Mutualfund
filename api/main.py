"""
Vercel FastAPI entrypoint: expose /api/query using the existing query handler.

This satisfies the FastAPI integration's requirement for an `app` object while
reusing the Phase 3 pipeline and fallback logic from api/query.py.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .query import handle_query
from .query import ROOT as _ROOT  # project root (parent of api/)


class QueryBody(BaseModel):
    query: str


app = FastAPI(title="Mutual Fund FAQ API (Vercel)")


@app.post("/api/query")
async def query_endpoint(body: QueryBody):
    out = handle_query(body.query or "")
    return {
        "answer": out.get("answer", ""),
        "citation_url": out.get("citation_url", ""),
        "last_updated": out.get("last_updated", ""),
        "source": out.get("source", "llm"),
    }


# Serve the existing Phase 4 frontend at `/`
_frontend = _ROOT / "phase_4" / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")


