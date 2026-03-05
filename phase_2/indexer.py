"""
Phase 2: Load data/schemes.json, build evidence chunks, embed via OpenAI API,
store in ChromaDB (or Pinecone). Lightweight for Vercel. Exposes query_store() for Phase 3.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

from . import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "mutual_fund_evidence"


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


def _get_chroma_client():
    """Lazy ChromaDB client with OpenAI embedding function."""
    import chromadb
    from chromadb.utils import embedding_functions

    root = get_project_root()
    persist_path = root / cfg.CHROMA_PERSIST_PATH
    persist_path.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required for ChromaDB embeddings")

    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name=cfg.OPENAI_EMBEDDING_MODEL,
    )
    client = chromadb.PersistentClient(path=str(persist_path))
    return client, ef


def _chroma_rebuild(schemes_path: Optional[Path] = None) -> int:
    """Rebuild ChromaDB collection from schemes.json."""
    data = load_schemes_json(schemes_path)
    documents, metadatas, ids = build_chunks(data)
    if not documents:
        logger.warning("No evidence chunks to index")
        return 0

    client, ef = _get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "HDFC scheme evidence chunks"},
    )
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("ChromaDB indexed %d chunks", len(ids))
    return len(ids)


def _chroma_query_store(query: str, top_k: Optional[int] = None) -> List[dict[str, Any]]:
    """Query ChromaDB and return chunks in Phase 3 format."""
    k = top_k if top_k is not None else cfg.TOP_K
    client, ef = _get_chroma_client()
    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception as e:
        raise FileNotFoundError(
            f"ChromaDB collection not found. Run python -m phase_2.indexer first. {e}"
        )

    results = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    out: List[dict[str, Any]] = []
    if not results or not results["documents"] or not results["documents"][0]:
        return out
    docs = results["documents"][0]
    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        meta = meta or {}
        out.append({
            "evidence_text": doc or "",
            "source_url": meta.get("source_url", ""),
            "scheme_name": meta.get("scheme_name", ""),
            "field_name": meta.get("field_name", ""),
            "scraped_at": meta.get("scraped_at", ""),
        })
    return out


def _pinecone_rebuild(schemes_path: Optional[Path] = None) -> int:
    """Rebuild Pinecone index from schemes.json."""
    try:
        from pinecone import Pinecone, ServerlessSpec
    except ImportError:
        raise ImportError("pip install pinecone-client for VECTOR_STORE_TYPE=pinecone")

    if not cfg.PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY is required for Pinecone")

    data = load_schemes_json(schemes_path)
    documents, metadatas, ids = build_chunks(data)
    if not documents:
        logger.warning("No evidence chunks to index")
        return 0

    from openai import OpenAI
    client_openai = OpenAI()
    # Batch embed (OpenAI preserves order)
    vectors = []
    batch_size_embed = 100
    for i in range(0, len(documents), batch_size_embed):
        chunk = documents[i : i + batch_size_embed]
        embeds = client_openai.embeddings.create(
            input=chunk,
            model=cfg.OPENAI_EMBEDDING_MODEL,
        )
        vectors.extend(e.embedding for e in embeds.data)

    pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
    if cfg.PINECONE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
        pc.create_index(
            name=cfg.PINECONE_INDEX_NAME,
            dimension=len(vectors[0]),
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=cfg.PINECONE_ENV or "us-east-1"),
        )
    index = pc.Index(cfg.PINECONE_INDEX_NAME)
    # Upsert in batches; metadata must include "text" for retrieval
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch = []
        for j in range(i, min(i + batch_size, len(ids))):
            meta = dict(metadatas[j])
            meta["text"] = documents[j][:40000]  # Pinecone metadata size limit
            batch.append({
                "id": ids[j],
                "values": vectors[j],
                "metadata": meta,
            })
        index.upsert(vectors=batch)
    logger.info("Pinecone indexed %d chunks", len(ids))
    return len(ids)


def _pinecone_query_store(query: str, top_k: Optional[int] = None) -> List[dict[str, Any]]:
    """Query Pinecone and return chunks in Phase 3 format."""
    try:
        from pinecone import Pinecone
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install pinecone-client openai for Pinecone")

    k = top_k if top_k is not None else cfg.TOP_K
    openai_client = OpenAI()
    q_embed = openai_client.embeddings.create(
        input=[query],
        model=cfg.OPENAI_EMBEDDING_MODEL,
    ).data[0].embedding

    pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
    index = pc.Index(cfg.PINECONE_INDEX_NAME)
    res = index.query(vector=q_embed, top_k=k, include_metadata=True)
    out: List[dict[str, Any]] = []
    for match in (res.matches or []):
        meta = (match.metadata or {})
        out.append({
            "evidence_text": meta.get("text", ""),
            "source_url": meta.get("source_url", ""),
            "scheme_name": meta.get("scheme_name", ""),
            "field_name": meta.get("field_name", ""),
            "scraped_at": meta.get("scraped_at", ""),
        })
    return out


def rebuild_index(schemes_path: Optional[Path] = None) -> int:
    """Rebuild vector store (ChromaDB or Pinecone) from schemes.json. Returns chunk count."""
    if cfg.VECTOR_STORE_TYPE.lower() == "pinecone":
        return _pinecone_rebuild(schemes_path)
    return _chroma_rebuild(schemes_path)


def query_store(
    query: str,
    top_k: Optional[int] = None,
) -> List[dict[str, Any]]:
    """
    Embed query and return top-k chunks with metadata (for Phase 3).
    Returns list of dicts: evidence_text, source_url, scheme_name, field_name, scraped_at.
    """
    if cfg.VECTOR_STORE_TYPE.lower() == "pinecone":
        return _pinecone_query_store(query, top_k)
    return _chroma_query_store(query, top_k)


def main() -> None:
    """CLI: rebuild the vector store from data/schemes.json."""
    try:
        n = rebuild_index()
        logger.info("Done. %d chunks indexed (%s).", n, cfg.VECTOR_STORE_TYPE)
    except Exception as e:
        logger.exception("Indexing failed: %s", e)
        raise


if __name__ == "__main__":
    main()
