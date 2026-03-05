# Facts-only Mutual Fund FAQ RAG Chatbot (Local Prototype)

RAG-style chatbot that answers **factual** mutual fund scheme questions from 5 INDMoney HDFC scheme pages only. Each phase lives in its own folder.

## Data source (Phase 1)

- **INDMoney only.** Exactly 5 approved scheme URLs (see [ARCHITECTURE_AND_PLAN.md](ARCHITECTURE_AND_PLAN.md)).
- Scraped data is stored in `data/schemes.json` (schemes + evidence for citations).

## What it answers

- Expense ratio, exit load, min SIP/lumpsum, lock-in, riskometer, benchmark, AUM, inception, fund manager.
- “How to download statements / capital gains?” — if not in corpus: says so and cites the closest scheme page (one of the 5 URLs); does not invent steps.

## Refusals and out of scope

- Opinionated questions (“Should I invest?”, “Which is best?”, “Buy/sell?”, “Compare returns”) are refused with a polite facts-only message and one citation link.
- **Personal information:** Questions about PAN, Aadhaar, accounts, OTPs, email, phone, or any user-specific data are out of scope; the chatbot does not answer them and states it only answers factual scheme details.

## Response rules

- Every answer: ≤ 3 sentences, **and the correct URL from which the information is coming** (exactly one citation link — the scheme page URL that was the source for the answer).
- “Last updated from sources: &lt;ISO timestamp&gt;” on every response.
- No returns computation or performance claims. No PII accepted or stored.

## Project layout (phase-based folders)

Each phase lives only in its own folder; no phase’s code is in another phase’s folder.

| Folder | Purpose |
|--------|---------|
| **phase_1/** | Data ingestion only — scraper, fixtures, tests → `data/schemes.json` |
| **phase_2/** | Embedding & vector store only — index evidence for retrieval |
| **phase_3/** | Retrieval & generation only — Groq LLM; answer only from embeddings; PII/personal info out of scope |
| **phase_4/** | Frontend & backend only — chat API + UI |
| **phase_5/** | Scheduler only — data refresh (re-run Phase 1 + Phase 2) |
| **phase_6/** | Improvements and operations (later) |
| **data/** | Shared: `schemes.json`, optional `vector_store/` |
| **docs/** | Schema and docs |

See [ARCHITECTURE_AND_PLAN.md](ARCHITECTURE_AND_PLAN.md) for the full plan and file layout.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Implementation order

1. **Phase 1** (`phase_1/`): Scraper → `data/schemes.json`.
2. **Phase 2** (`phase_2/`): Embed evidence → vector store.
3. **Phase 3** (`phase_3/`): Retrieval & generation (classifier, retrieval, generator).
4. **Phase 4** (`phase_4/`): Backend API + frontend chat UI.
5. **Phase 5** (`phase_5/`): Scheduler for data refresh.
6. **Phase 6** (`phase_6/`): Improvements and operations (later).

Each phase has its own `README.md` with run instructions.
