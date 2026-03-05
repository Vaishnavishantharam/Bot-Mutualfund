"""
Vercel serverless: run Phase 3 pipeline (Pinecone + Groq) or proxy to BACKEND_URL.
Set OPENAI_API_KEY, GROQ_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, VECTOR_STORE_TYPE=pinecone
to run on Vercel. If BACKEND_URL is set, the JS proxy (api/query.js) is used to forward to that backend.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Project root (parent of api/)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_pipeline_local(query: str):
    from phase_3.query_pipeline import run_pipeline
    return run_pipeline(query)


def fallback_answer(query: str):
    from phase_4.backend.fallback import answer_from_corpus
    return answer_from_corpus(query, ROOT)


def handle_query(q: str):
    backend_url = os.environ.get("BACKEND_URL", "").strip().rstrip("/")
    if backend_url:
        import urllib.request
        req = urllib.request.Request(
            backend_url + "/api/query",
            data=json.dumps({"query": q}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode())
    try:
        out = run_pipeline_local(q)
        return {
            "answer": out.get("answer", ""),
            "citation_url": out.get("citation_url", ""),
            "last_updated": out.get("last_updated", ""),
            "source": "llm",
        }
    except Exception:
        out = fallback_answer(q)
        return {
            "answer": out.get("answer", ""),
            "citation_url": out.get("citation_url", ""),
            "last_updated": out.get("last_updated", ""),
            "source": "fallback",
        }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            data = json.loads(body or "{}")
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "Invalid JSON"}).encode())
            return
        q = (data.get("query") or "").strip()
        if not q:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "query is required"}).encode())
            return
        try:
            out = handle_query(q)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(out).encode())
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.end_headers()
