# Phase 2: Embedding & Vector Store

Embed evidence from `data/schemes.json` and persist in Chroma for semantic retrieval in Phase 3.

## Contents

- `config.py` — schemes path, embedding model (sentence-transformers), vector store path, TOP_K.
- `indexer.py` — load schemes.json, build evidence chunks, embed with sentence-transformers, upsert into Chroma; exposes `query_store()` for Phase 3.
- Vector store is written to `data/vector_store/` (Chroma persistent client).

## Run

From project root (after Phase 1 has produced `data/schemes.json`):

```bash
pip install sentence-transformers chromadb  # or use project requirements.txt
python -m phase_2.indexer
```

Rebuilds the vector store from current `data/schemes.json` (full rebuild: deletes existing collection and re-indexes).

## For Phase 3

Use the query helper from Phase 3:

```python
from phase_2.indexer import query_store

chunks = query_store("What is the expense ratio of HDFC Flexi Cap?", top_k=5)
# Each chunk: evidence_text, source_url, scheme_name, field_name, scraped_at
```
