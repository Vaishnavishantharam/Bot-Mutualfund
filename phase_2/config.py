"""
Phase 2: Embedding and vector store config.
Uses ChromaDB + OpenAI embeddings (lightweight, Vercel-friendly).
"""

import os
from pathlib import Path

# Load .env from project root or phase_2
_root = Path(__file__).resolve().parent.parent
for _p in (_root / ".env", Path(__file__).resolve().parent / ".env"):
    if _p.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(_p)
        except ImportError:
            pass
        break

# Path to schemes.json (relative to project root)
SCHEMES_JSON_PATH = "data/schemes.json"

# Embedding: OpenAI API (no local model). Set OPENAI_API_KEY in env.
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Vector store: "chroma" (local persist) or "pinecone" (hosted, for Vercel)
VECTOR_STORE_TYPE = os.environ.get("VECTOR_STORE_TYPE", "chroma")

# ChromaDB: persist under project root
CHROMA_PERSIST_PATH = os.environ.get("CHROMA_PERSIST_PATH", "data/chroma")

# Pinecone (when VECTOR_STORE_TYPE=pinecone)
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "mutual-fund-faq")
PINECONE_ENV = os.environ.get("PINECONE_ENV", "")  # e.g. us-east-1-aws

# Top-k for retrieval (used by Phase 3)
TOP_K = 5
