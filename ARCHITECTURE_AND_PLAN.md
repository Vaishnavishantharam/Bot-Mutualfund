# Phase-wise Architecture & Implementation Plan: Facts-only Mutual Fund FAQ RAG Chatbot

**Scope:** Local prototype first; deployment/hosting later.  
**Data source (Phase 1):** INDMoney only — the 5 approved HDFC scheme pages listed below.

**Layout:** Each phase lives in its own folder (`phase_1/` through `phase_6/`). Phase 1 code lives only in `phase_1/`; Phase 2 only in `phase_2/`; and so on. No phase’s logic is implemented inside another phase’s folder. Shared assets (e.g. `data/schemes.json`) live at project root.

---

## Architecture principles (mandatory)

1. **Separate folders per phase** — All phases in their own folders (`phase_1/` … `phase_6/`). No phase's logic lives in another phase's folder. Shared data at project root.
2. **Correct URL for every answer** — Every response must include the **correct URL from which the information came** (`citation_url` = exact `source_url` of the scheme/chunk used; one of the 5 approved INDMoney pages).
3. **Phase 3: Groq as LLM** — Phase 3 uses **Groq** for response generation (config in `phase_3/config.py`).
4. **Answer only from embeddings** — The chatbot must **not** answer by itself. It must use **only** information stored in the embeddings (retrieved chunks). No answering from the LLM's general knowledge; if nothing relevant is retrieved, say the information is not in the corpus.
5. **Personal information out of scope** — Questions about personal information (PAN, Aadhaar, account, OTP, email, phone, etc.) must **not** be answered. Refuse politely; state that the chatbot only answers factual scheme details and does not handle personal information. Do not store or process PII.

---

## Return the correct source URL (every response)

For **every** user question, the system must return the **correct URL from which the information is coming**. That URL must be the exact `source_url` of the scheme (or evidence chunk) used to answer the question — i.e. one of the 5 approved INDMoney scheme pages. The response payload must include:

- **`citation_url`** — the scheme page URL that was the source for the answer (e.g. the `source_url` of the top-ranked retrieved evidence or the scheme that matched the query). Never return a generic or wrong URL; it must match the source of the facts in the answer.
- **`answer`** — the factual text (≤3 sentences).
- **`last_updated`** — ISO timestamp from that scheme’s `scraped_at`.

Refusals (e.g. for opinionated questions) must also include one `citation_url` from the 5 approved URLs (e.g. the scheme the user asked about, or the first scheme).

---

## Approved Data Sources (Phase 1)

| # | Scheme | URL |
|---|--------|-----|
| 1 | HDFC Large Cap Fund Direct Growth | https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989 |
| 2 | HDFC Flexi Cap Fund Direct Growth | https://www.indmoney.com/mutual-funds/hdfc-flexi-cap-fund-direct-plan-growth-option-3184 |
| 3 | HDFC Mid Cap Fund Direct Growth | https://www.indmoney.com/mutual-funds/hdfc-mid-cap-fund-direct-plan-growth-option-3097 |
| 4 | HDFC Small Cap Fund Direct Growth | https://www.indmoney.com/mutual-funds/hdfc-small-cap-fund-direct-growth-option-3580 |
| 5 | HDFC Nifty 100 Index Fund Direct Growth | https://www.indmoney.com/mutual-funds/hdfc-nifty-100-index-fund-direct-growth-1040567 |

No other INDMoney pages, blogs, or external sources in Phase 1.

---

## High-level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  phase_5: Scheduler (orchestrator — runs on a schedule)                          │
│  1. Update latest data → Phase 1 (scrape → data/schemes.json)                    │
│  2. Trigger Phase 2   → re-index vector store from fresh schemes.json            │
│  3. Trigger Phase 3/4 → reload / invalidate caches so queries use latest data    │
└───────────────────────────────────────────┬─────────────────────────────────────┘
                                             │ triggers (in order)
     ┌──────────────────────────────────────┼──────────────────────────────────────┐
     ↓                                      ↓                                       ↓
┌──────────────┐  ┌──────────────────────────────┐  ┌──────────────────────────────┐
│  phase_1     │  │  phase_2                     │  │  phase_3 & phase_4           │
│  Data        │→ │  Embedding & Vector Store    │→ │  (use updated store on next   │
│  Ingestion   │  │  (re-index from schemes.json) │  │   query or after reload)      │
│  Scraper →   │  │                              │  │  Retrieval & Gen + Chat API   │
│  schemes.json│  │                              │  │                              │
└──────────────┘  └──────────────────────────────┘  └──────────────────────────────┘

phase_6: Improvements and operations (later)
```

---

## Phase 1: Data Ingestion & Storage  
**Folder: `phase_1/`**

**Goal:** Scrape the 5 INDMoney scheme pages, extract only the required factual fields, store normalized records + evidence snippets in `data/schemes.json`.

### 1.1 Scraper design

- **Input:** Fixed list of 5 URLs (no discovery/crawling).
- **Output:** One normalized scheme record per URL + evidence list per scheme.
- **Where to scrape:** Visible “Fund Overview” / “Key Facts” / “Fund Details” sections (and FAQ section only for fact verification).
- **Method:** Label-based parsing: label → field mapping (e.g. `"Expense ratio"` → `expense_ratio`). Find element containing the label, read adjacent value. Log missing fields per scheme.

### 1.2 Required fields per scheme

| Field | Description | Example |
|-------|-------------|--------|
| `scheme_name` | Full scheme title | "HDFC Large Cap Fund - Direct Plan - Growth Option" |
| `amc_name` | AMC name | "HDFC" |
| `category` | Category if present | "Large Cap" / "Flexi Cap" / "Mid Cap" / "Small Cap" / "Index" |
| `plan_type` | Plan type | "Direct" |
| `option_type` | Option | "Growth" |
| `expense_ratio` | Value + units | "0.98%" |
| `exit_load` | Full text | "1% if redeemed in 0-1 Years" |
| `min_sip` / `min_sip_raw` | ₹ amount + raw | 100, "₹100" |
| `min_lumpsum` / `min_lumpsum_raw` | ₹ amount + raw | 100, "₹100" |
| `lock_in` | Text | "No Lock-in" |
| `risk_level` | Text | "Very High Risk" |
| `benchmark` | Index name | "Nifty 100 TR INR" |
| `aum` | Optional | "₹39621 Cr" |
| `inception_date` | Optional | "1 January, 2013" |
| `fund_manager` | Optional | "Rahul Baijal, Dhruv Muchhal" |
| `source_url` | One of the 5 URLs | (exact URL) |
| `scraped_at` | ISO timestamp | "2026-03-02T12:00:00Z" |

### 1.3 Evidence snippets (for citations)

Per extracted field: `field_name`, `field_value`, `evidence_text` (1–2 lines), `source_url`.

### 1.4 Storage

- **Path:** `data/schemes.json` (or `phase_1/output/schemes.json` if phase-local).
- See `docs/schema.md` for JSON schema.

### 1.5 Phase 1 folder contents

- `phase_1/scraper/` — config, field_mapping, parser, run script.
- `phase_1/README.md` — phase scope and how to run.
- Output written to shared `data/schemes.json` or phase_1 output dir.

---

## Phase 2: Embedding & Vector Store  
**Folder: `phase_2/`**

**Goal:** Embed scheme records and evidence text, persist in a vector store so Phase 3 can do semantic retrieval.

### 2.1 Inputs

- `data/schemes.json` (from Phase 1): `schemes` + `evidence`.

### 2.2 What to embed

- **Evidence chunks:** Each evidence item’s `evidence_text` (and optionally `field_name` + `field_value` concatenated) as one chunk. Attach metadata: `source_url`, `scheme_name`, `field_name`, `scraped_at`.
- **Optional:** Scheme-level summary text (e.g. key facts concatenated) for fallback retrieval.

### 2.3 Embedding model

- Use a local/small embedding model (e.g. `sentence-transformers`, or a small OpenAI-compatible embed API) so the prototype runs without mandatory cloud.
- Embedding dimension and model name should be configurable (e.g. in `phase_2/config.py` or env).

### 2.4 Vector store

- **Options:** Chroma, FAISS, or similar — store vectors + metadata (at least `source_url`, `scheme_name`, `field_name`, `scraped_at`).
- **Path:** e.g. `phase_2/vector_store/` or `data/vector_store/` (persistent across runs).
- **Indexing script:** Read `schemes.json` → build chunks from evidence (and optionally schemes) → embed → upsert into vector store. Support full rebuild (delete + re-index).

### 2.5 Phase 2 folder contents

- `phase_2/embed.py` or `phase_2/indexer.py` — load schemes.json, chunk evidence, embed, write to vector store.
- `phase_2/config.py` — embedding model name, dimension, vector store path.
- `phase_2/vector_store/` — persistent store (or path to `data/vector_store`).
- `phase_2/README.md` — how to run indexing.

### 2.6 Implementation steps

1. Load `data/schemes.json`; iterate over `evidence` (and optionally `schemes`).
2. Build text chunks + metadata per chunk.
3. Embed chunks (batch if needed); upsert into vector store with metadata.
4. Expose a minimal “query → top-k chunks” helper for Phase 3 to use (or Phase 3 calls the store directly).

---

## Phase 3: Retrieval & Generation (query side)  
**Folder: `phase_3/`**

**Goal:** Given a user query, classify intent, retrieve relevant evidence from the vector store, and generate a facts-only response (≤3 sentences, one citation, “Last updated” footer). Also handle refusals for opinionated questions.

### 3.0 LLM and answer policy

- **LLM:** Phase 3 uses **Groq** as the LLM for response generation (e.g. summarising retrieved evidence into ≤3 sentences). Configure Groq API endpoint and model in `phase_3` config; do not use the LLM to “answer from its own knowledge”.
- **Answer only from embeddings:** The chatbot must **not** answer any question by itself. It must use **only** information stored in the embeddings (vector store). Every answer must be grounded in retrieved chunks from the corpus (the 5 INDMoney scheme pages). If retrieval returns no relevant evidence, the bot must say the information is not in the corpus and may cite the closest scheme page — it must not invent or hallucinate answers from the LLM’s general knowledge.
- **Personal information out of scope:** If the user asks about **any personal information** (e.g. PAN, Aadhaar, account numbers, OTPs, emails, phone numbers, or any question about the user’s own personal data), the chatbot must **not** answer. Such questions are out of scope: respond with a polite message that the chatbot only answers factual scheme details from the corpus and does not handle personal information. Do not store or process PII.

### 3.1 Query classification (factual vs refusal)

- **Factual:** Expense ratio, exit load, min SIP/lumpsum, lock-in, riskometer, benchmark, AUM, inception, fund manager; “How to download statements / capital gains?” (answer or “not in corpus” + one URL). Answers must be generated only from retrieved evidence (see 3.0).
- **Refusal triggers:** “Should I invest?”, “Which is best?”, “Buy/sell?”, “Compare returns” — return a polite facts-only message + exactly one citation link (one of the 5 URLs).
- **Personal information / PII:** Questions asking for or about personal information (PAN, Aadhaar, accounts, OTPs, email, phone, or any user-specific data) are **out of scope**. Do not answer; respond that the chatbot only answers factual scheme details and does not handle personal information.
- **Implementation:** Rule-based or regex/keywords in `phase_3/classifier.py`; PII detection to reject or refuse personal-information questions.

### 3.2 Retrieval

- **Input:** User query (after PII check; reject if PII detected).
- **Flow:** Embed query with same model as Phase 2 → query vector store for top-k chunks (e.g. k=3–5) with metadata.
- **Constraint:** Results must be from the 5 approved URLs only; pick **one** `source_url` for the citation (e.g. from the top-ranked chunk).
- **Output:** List of chunks with `evidence_text`, `source_url`, `scheme_name`, `scraped_at`, etc.

### 3.3 Response generation (Groq LLM)

- **LLM:** Use **Groq** for generation (e.g. turning retrieved evidence into ≤3 sentences). The LLM must only reformat/summarise the retrieved text; it must not add facts from its own knowledge (answer only from embeddings).
- **Generator:** Use retrieved evidence to form ≤3 sentences. No returns computation or performance claims. If “statements / capital gains” not in corpus → reply not in corpus + closest scheme page URL. If retrieval returns nothing relevant, do not invent an answer; say the information is not in the corpus and cite one scheme page.
- **Return the correct source URL:** `citation_url` in the response must be the exact `source_url` of the evidence/scheme used to answer (the scheme page from which the fact was retrieved). Do not return a generic or different URL.
- **Constraints (enforce before return):**
  - Answer is grounded **only** in retrieved chunks; no answering by the chatbot from its own/LLM knowledge.
  - ≤ 3 sentences.
  - Exactly one citation link: the **correct** source URL (the scheme page that supplied the answer).
  - “Last updated from sources: &lt;ISO timestamp&gt;” (from cited chunk’s `scraped_at`).
  - No PII in response; personal-information questions are out of scope and are refused.

### 3.4 Phase 3 folder contents

- `phase_3/config.py` — Groq API endpoint/model; vector store path (or reuse phase_2 config).
- `phase_3/classifier.py` — factual vs refusal; personal-information (PII) detection → out of scope.
- `phase_3/retrieval.py` — embed query, query vector store, return top-k with metadata.
- `phase_3/generator.py` or `response.py` — call Groq with retrieved evidence only; build answer + citation + timestamp; validate answer is from embeddings only.
- `phase_3/query_pipeline.py` or `main.py` — PII/personal-info check → classify → retrieve → generate (only from embeddings).
- `phase_3/README.md` — how to run query pipeline (e.g. CLI); Groq setup.

### 3.5 Scheduler (Phase 5) trigger

Phase 5 will trigger a reload or cache invalidation after re-indexing (Phase 2). Phase 3 should either load the vector store on every request (so no explicit reload is needed) or support reload when the scheduler calls the backend or updates a sentinel file.

---

## Phase 4: Frontend & Backend (chat application)  
**Folder: `phase_4/`**

**Goal:** Chat application with a backend API and a frontend UI so users can ask questions in a browser (local prototype).

### 4.1 Backend

- **API:** e.g. FastAPI or Flask. Endpoints:
  - `POST /chat` or `POST /query` — body: `{ "query": "..." }`. Response: `{ "answer": "...", "citation_url": "...", "last_updated": "..." }` where **`citation_url` is the correct URL from which the information came** (the scheme page `source_url` used to generate the answer).
  - Optional: `GET /health` for readiness.
- **Logic:** Call Phase 3 query pipeline (classifier → retrieval → generator); return structured response. Ensure `citation_url` is always the exact source URL of the scheme/evidence used. Enforce no PII acceptance; reject requests that look like PII.

### 4.2 Frontend

- **Chat UI:** Simple web interface: input box, send button, display answer + citation link + “Last updated” line.
- **Tech:** Any lightweight stack (e.g. React, Vue, or plain HTML/JS) that can call the backend. Keep it in `phase_4/frontend/` or `phase_4/web/`.

### 4.3 Phase 4 folder contents

- `phase_4/backend/` — API server (e.g. FastAPI app), imports/invokes Phase 3 pipeline.
- `phase_4/frontend/` — chat UI source.
- `phase_4/README.md` — how to run backend and frontend locally.

### 4.4 Scheduler (Phase 5) trigger

After Phase 5 runs Phase 1 and Phase 2, it triggers Phase 4 so the chat app uses the latest data. The backend should either: (a) expose a reload endpoint (e.g. `POST /admin/reload`) that re-loads the vector store, or (b) check a sentinel file (e.g. `data/last_indexed_at`) on each request and reload the store when it changes.

---

## Phase 5: Scheduler (data refresh pipeline)  
**Folder: `phase_5/`**

**Goal:** A scheduler that runs on a schedule to (1) update the latest data into Phase 1, then (2) trigger all other phases in order so that the entire system uses the latest data every time a user asks a question.

### 5.1 Pipeline (run in order)

1. **Update latest data into Phase 1**  
   Run the Phase 1 scraper so that `data/schemes.json` is refreshed from the 5 INDMoney URLs. This is the single source of truth for scheme facts.

2. **Trigger Phase 2**  
   Run the Phase 2 indexer to re-build the vector store from the updated `schemes.json`. Retrieval (Phase 3) will then read from this updated store.

3. **Trigger Phase 3**  
   Ensure the query pipeline uses the new data: if Phase 3 (or the backend) caches the vector store client or in-memory index, the scheduler must trigger a **reload** or **cache invalidation** (e.g. call an internal endpoint or write a sentinel file that Phase 3/backend checks on each request). If Phase 3 loads the store on every request, no extra step is needed after Phase 2.

4. **Trigger Phase 4**  
   Ensure the chat application (backend) serves from the updated index. Options: backend reloads the vector store when it detects a new index (e.g. timestamp file written by Phase 5), or scheduler calls a backend **reload endpoint** (e.g. `POST /admin/reload`) so that the next user query uses the latest data.

### 5.2 Scheduling

- **Options:** Cron job, or in-process scheduler (e.g. APScheduler). Configurable interval (e.g. daily).
- **Script:** `phase_5/run_refresh.py` (or `phase_5/scheduler.py`) that:
  1. Invokes Phase 1 scraper → `data/schemes.json` updated.
  2. Invokes Phase 2 indexer → vector store updated.
  3. Triggers Phase 3/4 reload (e.g. HTTP call to backend reload endpoint, or write `data/last_indexed_at` that backend reads and reloads when changed).
- Log success/failure and timestamps for each step. On Phase 1 or Phase 2 failure, optionally skip the remaining steps and alert.

### 5.3 Phase 5 folder contents

- `phase_5/run_refresh.py` — entry point: run Phase 1 → Phase 2 → trigger Phase 3/4 reload.
- `phase_5/config.py` — schedule interval; command or path for each phase (phase_1 scraper, phase_2 indexer); optional backend reload URL or sentinel file path.
- `phase_5/README.md` — how to run manually and how to schedule (cron example); description of “trigger all phases” flow.

---

## Phase 6: Improvements and Operations (later)  
**Folder: `phase_6/`**

**Goal:** Reserved for future work — monitoring, logging, evaluation, model upgrades, deployment prep, etc.

### 6.1 Possible topics (later)

- Evaluation suite (factual accuracy, citation correctness).
- Logging and basic observability.
- Deployment and hosting (when required).
- Improved embedding model or reranking.
- Rate limiting, auth (if needed).

### 6.2 Phase 6 folder contents

- `phase_6/README.md` — placeholder describing “Improvements and operations (later)”.
- No implementation until later.

---

## File Layout (phase-based folders)

```
Mutual funds/
├── ARCHITECTURE_AND_PLAN.md
├── README.md
├── requirements.txt
├── .gitignore
├── data/                          # Shared data (Phase 1 output, optional Phase 2 store)
│   └── schemes.json
├── docs/
│   └── schema.md
│
├── phase_1/                       # Data ingestion & storage (all Phase 1 code only here)
│   ├── README.md
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── field_mapping.py
│   │   ├── parser.py
│   │   └── run.py
│   ├── html_fixtures/             # optional local HTML (2989.html, etc.)
│   ├── test_schemes_data.py       # validate data/schemes.json
│   └── (output → data/schemes.json)
│
├── phase_2/                       # Embedding & vector store
│   ├── README.md
│   ├── config.py
│   ├── indexer.py
│   ├── vector_store/              # or path to data/vector_store
│   └── (reads data/schemes.json)
│
├── phase_3/                       # Retrieval & generation (query side); LLM = Groq
│   ├── README.md
│   ├── config.py                  # Groq API/model; answer only from embeddings
│   ├── classifier.py             # factual vs refusal; PII/personal-info = out of scope
│   ├── retrieval.py
│   ├── generator.py              # Groq; answer only from retrieved evidence
│   └── query_pipeline.py
│
├── phase_4/                       # Frontend & backend (chat application)
│   ├── README.md
│   ├── backend/
│   │   ├── __init__.py
│   │   └── main.py
│   └── frontend/
│       └── (chat UI source)
│
├── phase_5/                       # Scheduler: update Phase 1 data, then trigger 2→3→4
│   ├── README.md
│   ├── config.py                  # interval; phase commands; reload URL or sentinel
│   └── run_refresh.py             # run Phase 1 → Phase 2 → trigger Phase 3/4 reload
│
└── phase_6/                       # Improvements and operations (later)
    └── README.md
```

---

## Response constraints (all phases)

Every answer from the chatbot MUST:

- Be ≤ 3 sentences.
- **Answer only from embeddings:** The chatbot must not answer any question by itself. It must use only information stored in the embeddings (retrieved chunks from the corpus). No answering from the LLM’s general knowledge; if nothing relevant is retrieved, say the information is not in the corpus and cite one scheme page.
- **Return the correct URL from which the information is coming:** exactly one citation link, which must be the **source_url** of the scheme/evidence used to generate the answer (one of the 5 approved INDMoney scheme pages). The `citation_url` in the API response must be this exact source URL.
- Include: “Last updated from sources: &lt;ISO timestamp&gt;” (from the cited scheme’s `scraped_at`).
- Not compute or compare returns; no performance claims.
- **Personal information out of scope:** Do not answer questions about personal information (PAN, Aadhaar, account numbers, OTPs, emails, phone numbers, or any user-specific data). Refuse politely and state that the chatbot only answers factual scheme details and does not handle personal information. Never accept or store PII.

Refusals for opinionated/portfolio questions with a polite facts-only message and one citation from the 5 URLs (still the correct scheme page URL, e.g. the one the user asked about).

---

## Label-to-field mapping (Phase 1 scraper)

| Page label (approximate) | Field(s) |
|--------------------------|----------|
| Expense ratio | `expense_ratio` |
| Benchmark | `benchmark` |
| Exit Load | `exit_load` |
| Min Lumpsum/SIP / Min SIP | `min_sip`, `min_lumpsum` |
| Lock In / Lock-in | `lock_in` |
| Risk | `risk_level` |
| AUM | `aum` |
| Inception Date | `inception_date` |
| Fund Manager(s) | `fund_manager` |

Scheme name, plan type, option type, category from page title/headings/breadcrumbs.

---

## Summary checklist

- [ ] **Phase 1** (`phase_1/`): Scraper → `data/schemes.json`; label-based parsing; log missing fields.
- [ ] **Phase 2** (`phase_2/`): Embed evidence (and optionally schemes); build and persist vector store.
- [ ] **Phase 3** (`phase_3/`): Groq as LLM; answer only from embeddings; PII/personal info out of scope. Classifier (fact vs refusal), retrieval, generator (≤3 sentences, 1 URL, last updated).
- [ ] **Phase 4** (`phase_4/`): Backend API + frontend chat UI.
- [ ] **Phase 5** (`phase_5/`): Scheduler: update latest data into Phase 1, then trigger Phase 2 (re-index), then Phase 3/4 (reload/cache invalidation) so the system uses latest data every time.
- [ ] **Phase 6** (`phase_6/`): Improvements and operations (later).

---

## Compliance: Are we following this?

| Requirement | Status | Where implemented |
|-------------|--------|--------------------|
| **All phases in separate folders** | Yes | `phase_1/`, `phase_2/`, `phase_3/`, `phase_4/`, `phase_5/`, `phase_6/` — each phase's code lives only in its folder. |
| **Return correct URL for every answer** | Yes | `phase_3/generator.py`: `citation_url` = top chunk's `source_url`; `phase_3/scheme_matching.py`: filter chunks by detected scheme so cited URL matches the fund asked about. API and frontend return/show `citation_url`. |
| **Phase 3 uses Groq as LLM** | Yes | `phase_3/config.py`: `GROQ_API_KEY`, `GROQ_MODEL`; `phase_3/generator.py`: Groq client for chat completion. |
| **Answer only from embeddings (no answering by itself)** | Yes | `phase_3/generator.py`: `SYSTEM_PROMPT` instructs "answer ONLY using the provided context"; context is retrieved chunks only. No context = "information is not available in our corpus". |
| **Personal information out of scope** | Yes | `phase_3/classifier.py`: `PII_PATTERNS` and `personal_info` label; `phase_3/query_pipeline.py`: if `personal_info` → `generate_refusal("personal_info", ...)` with message that the chatbot does not handle personal information. |
