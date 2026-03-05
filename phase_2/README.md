# Phase 2: Embedding & Vector Store

Embed evidence from `data/schemes.json` and persist in Chroma for semantic retrieval in Phase 3.

## Contents

- `config.py` — schemes path, OpenAI embedding model, vector store type/path, TOP_K.
- `indexer.py` — load schemes.json, build evidence chunks, embed with OpenAI API, upsert into Chroma (or Pinecone); exposes `query_store()` for Phase 3.
- Vector store is written to `data/chroma/` by default (or Pinecone when `VECTOR_STORE_TYPE=pinecone`).

## Run

From project root (after Phase 1 has produced `data/schemes.json`):

```bash
pip install -r requirements.txt  # installs chromadb, openai, pinecone-client, etc.
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
