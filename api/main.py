"""
Vercel FastAPI entrypoint: expose /api/query using the existing query handler.

This satisfies the FastAPI integration's requirement for an `app` object while
reusing the Phase 3 pipeline and fallback logic from api/query.py.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .query import handle_query


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

