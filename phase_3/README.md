# Phase 3: Retrieval & Generation (query side)

Classify user query (factual vs refusal), retrieve relevant evidence from the vector store, and generate a facts-only response using **Groq** as the LLM (≤3 sentences, one citation, “Last updated” footer).

**Policies:** (1) The chatbot must **not** answer any question by itself — it uses **only** information stored in the embeddings (retrieved chunks). (2) Questions about **personal information** (PAN, Aadhaar, accounts, OTPs, email, phone, etc.) are **out of scope**; do not answer, refuse politely.

## Contents

- `config.py` — Groq API endpoint/model.
- `classifier.py` — factual vs opinionated/portfolio (refusal); PII/personal-info → out of scope.
- `retrieval.py` — embed query, query vector store, return top-k chunks with metadata.
- `generator.py` — Groq; build answer from retrieved evidence only + citation + timestamp.
- `query_pipeline.py` — PII/personal-info check → classify → retrieve → generate (only from embeddings).

## Run

From project root (after Phase 2 has built the vector store):

```bash
# Groq API key: put it in project root .env (copy .env.example to .env)
# Get a key at https://console.groq.com
# .env should contain: GROQ_API_KEY=your_key_here

python -m phase_3.query_pipeline --query "Expense ratio of HDFC Flexi Cap?"
```

REPL mode (prompt for multiple queries):

```bash
python -m phase_3.query_pipeline --repl
```

## Tests (integration with Phase 2 + LLM)

From project root, with Phase 2 vector store built (`python -m phase_2.indexer`):

```bash
pytest phase_3/tests/ -v
```

Tests include: expense ratio HDFC Large Cap (example from spec), other factual queries, refusal, personal-info out of scope, and classifier unit checks. Integration tests are skipped if the vector store is missing.

Without `GROQ_API_KEY`, the generator falls back to returning the top retrieved chunk’s evidence text (no LLM).
