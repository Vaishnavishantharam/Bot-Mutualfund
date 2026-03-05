"""
Phase 2: Load data/schemes.json, build evidence chunks, embed with sentence-transformers,
and persist with FAISS (no sqlite). Supports full rebuild. Exposes query_store() for Phase 3.
"""
from __future__ import annotations

import hashlib
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

from . import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# FAISS index and metadata filenames under VECTOR_STORE_PATH
FAISS_INDEX_FILE = "index.faiss"
METADATA_FILE = "metadata.pkl"


def get_project_root() -> Path:
    """Project root = parent of phase_2."""
    return Path(__file__).resolve().parent.parent


def load_schemes_json(path: Optional[Path] = None) -> dict[str, Any]:
    """Load schemes.json; return dict with 'schemes' and 'evidence' keys."""
    root = get_project_root()
    file_path = path or root / cfg.SCHEMES_JSON_PATH
    if not file_path.exists():
        raise FileNotFoundError(f"Schemes file not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def build_chunks(data: dict[str, Any]) -> tuple[List[str], List[dict[str, str]], List[str]]:
    """
    Build (documents, metadatas, ids) from evidence. Each evidence item becomes one chunk.
    Metadata: source_url, scheme_name, field_name, scraped_at (all strings).
    """
    schemes = data.get("schemes", [])
    evidence = data.get("evidence", [])

    scraped_at_map: dict[str, str] = {}
    for s in schemes:
        url = s.get("source_url")
        if url:
            scraped_at_map[url] = s.get("scraped_at") or ""

    documents: List[str] = []
    metadatas: List[dict[str, str]] = []
    ids: List[str] = []

    for i, ev in enumerate(evidence):
        evidence_text = ev.get("evidence_text") or ""
        field_name = ev.get("field_name") or ""
        field_value = ev.get("field_value")
        if field_value is not None and not isinstance(field_value, str):
            field_value = str(field_value)
        else:
            field_value = str(field_value) if field_value else ""
        source_url = ev.get("source_url") or ""
        scheme_name = ev.get("scheme_name") or ""

        if field_name and field_value:
            doc_text = f"{evidence_text} {field_name} {field_value}".strip()
        else:
            doc_text = evidence_text.strip()

        if not doc_text:
            continue

        scraped_at = scraped_at_map.get(source_url, "")
        meta = {
            "source_url": source_url,
            "scheme_name": scheme_name,
            "field_name": field_name,
            "scraped_at": scraped_at,
        }
        uid = hashlib.sha256(f"{source_url}{field_name}{i}".encode()).hexdigest()[:16]
        documents.append(doc_text)
        metadatas.append(meta)
        ids.append(uid)

    return documents, metadatas, ids


def get_vector_store_path() -> Path:
    """Resolve vector store path (project root / VECTOR_STORE_PATH)."""
    return get_project_root() / cfg.VECTOR_STORE_PATH


def _normalize_l2(x: np.ndarray) -> np.ndarray:
    """L2-normalize rows. For cosine similarity with FAISS IndexFlatIP."""
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return x.astype(np.float32) / norms


def rebuild_index(schemes_path: Optional[Path] = None) -> int:
    """
    Load schemes.json, embed evidence chunks, build FAISS index, save index + metadata.
    Returns number of chunks indexed.
    """
    import faiss
    from sentence_transformers import SentenceTransformer

    data = load_schemes_json(schemes_path)
    documents, metadatas, ids = build_chunks(data)
    if not documents:
        logger.warning("No evidence chunks to index")
        return 0

    vector_store_path = get_vector_store_path()
    vector_store_path.mkdir(parents=True, exist_ok=True)

    logger.info("Loading embedding model: %s", cfg.EMBEDDING_MODEL)
    model = SentenceTransformer(cfg.EMBEDDING_MODEL)
    logger.info("Embedding %d chunks...", len(documents))
    embeddings = model.encode(documents, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype=np.float32)
    embeddings = _normalize_l2(embeddings)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    index_path = vector_store_path / FAISS_INDEX_FILE
    meta_path = vector_store_path / METADATA_FILE
    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump({"documents": documents, "metadatas": metadatas, "ids": ids}, f)
    logger.info("Indexed %d chunks to %s", len(ids), vector_store_path)
    return len(ids)


def query_store(
    query: str,
    top_k: Optional[int] = None,
) -> List[dict[str, Any]]:
    """
    Embed query and return top-k chunks with metadata (for Phase 3).
    Returns list of dicts with keys: evidence_text, source_url, scheme_name, field_name, scraped_at.
    """
    import faiss
    from sentence_transformers import SentenceTransformer

    k = top_k if top_k is not None else cfg.TOP_K
    vector_store_path = get_vector_store_path()
    index_path = vector_store_path / FAISS_INDEX_FILE
    meta_path = vector_store_path / METADATA_FILE
    if not index_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Vector store not found at {vector_store_path}. Run python -m phase_2.indexer first."
        )

    model = SentenceTransformer(cfg.EMBEDDING_MODEL)
    q = model.encode([query])
    q = np.asarray(q, dtype=np.float32)
    q = _normalize_l2(q)

    index = faiss.read_index(str(index_path))
    with open(meta_path, "rb") as f:
        stored = pickle.load(f)
    documents = stored["documents"]
    metadatas = stored["metadatas"]

    scores, indices = index.search(q, min(k, index.ntotal))
    out: List[dict[str, Any]] = []
    for idx in indices[0]:
        if idx < 0:
            continue
        meta = metadatas[idx] if idx < len(metadatas) else {}
        out.append({
            "evidence_text": documents[idx] if idx < len(documents) else "",
            "source_url": meta.get("source_url", ""),
            "scheme_name": meta.get("scheme_name", ""),
            "field_name": meta.get("field_name", ""),
            "scraped_at": meta.get("scraped_at", ""),
        })
    return out


def main() -> None:
    """CLI: rebuild the vector store from data/schemes.json."""
    try:
        n = rebuild_index()
        logger.info("Done. %d chunks indexed.", n)
    except Exception as e:
        logger.exception("Indexing failed: %s", e)
        raise


if __name__ == "__main__":
    main()
