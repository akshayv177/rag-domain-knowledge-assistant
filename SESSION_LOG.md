# Date: 17.12.25 P3 RAG Setup

## Context
Light Block B session focused on getting started with the RAG project (P3) and understanding the system design, not heavy coding.

## What I did
- Confirmed `rag-agents` conda environment is working and used it for P3.
- Created base package structure for the RAG project:
  - `src/rag_assistant/`
    - `__init__.py`
    - `config.py`
    - `ingest.py` (initial stub)
    - `retrieval.py` (placeholder)
    - `app.py` (placeholder)
- Implemented `config.py` using **pydantic-settings** (Pydantic v2 style):
  - Centralised settings for:
    - `OPENAI_API_KEY`
    - `llm_model`, `embedding_model`
    - `docs_path` (`data/raw`)
    - `vector_db_path` (`data/vector_store`)
  - Learned why config sits in its own module from a systems design POV.
- Understood the **architectural separation** for the RAG system:
  - `config.py` – environment + knobs.
  - `ingest.py` – offline pipeline: docs → chunks → embeddings → vector store.
  - `retrieval.py` – online path: query → retrieve chunks → call LLM → answer.
  - `app.py` – API / UI layer over the retrieval logic.
- Wired up a first version of `ingest.py` conceptually:
  - `load_docs()` – load raw `.txt` docs into `Document` objects.
  - `split_docs()` – chunk docs with `RecursiveCharacterTextSplitter`.
  - `build_vector_store()` – planned to build a Chroma index using OpenAI embeddings.
- Created `scripts/dev_ingest.py` as the offline entrypoint:
  - Calls `load_docs()`, `split_docs()`, `build_vector_store()`.
  - Clarified how `PYTHONPATH=src` is used so `rag_assistant` can be imported from `src/`.

## Issues / Decisions
- Hit a `ModuleNotFoundError: rag_assistant` when running `dev_ingest.py`:
  - Fixed by running from project root with `PYTHONPATH=src`.
- Hit a **Pydantic v2 migration issue** (`BaseSettings` moved):
  - Resolved by switching to `pydantic-settings` and `SettingsConfigDict`.
- Tried to install `langchain-community`, but ran into dependency conflicts around `aiohttp`:
  - Decided not to fight this during a light session.
  - Chose to refactor ingestion in the next session to avoid `langchain_community` entirely and instead:
    - Use `pathlib` + `Document` for loading.
    - Use `chromadb.PersistentClient` + `OpenAIEmbeddingFunction` directly for the vector store.

## Next (for future Block B session)
- Implement the revised `ingest.py` **without** `langchain_community`:
  - `load_docs()` using `pathlib` and `Document`.
  - `split_docs()` using `RecursiveCharacterTextSplitter`.
  - `build_vector_store()` using `chromadb.PersistentClient` and OpenAI embeddings.
- Ensure `.env` is set up with:
  - `OPENAI_API_KEY`
  - `DOCS_PATH=data/raw`
  - `VECTOR_DB_PATH=data/vector_store`
- Create a small dummy doc in `data/raw/` and run:
  - `PYTHONPATH=src python scripts/dev_ingest.py`
  - Verify that a Chroma index is persisted under `data/vector_store/`.
- Then move on to designing `retrieval.py`:
  - `get_collection()`, `retrieve(query, k)`, and `answer(query)` using the stored index and LLM.


# W3D1 – Block B (P3 RAG) – 05.01.26

## Energy / Time
- Energy: ~5/10
- Time: ~90–120 min
- Scope: Get ingestion working, confirm vector DB persistence, push repo.

## What I did
- Verified `rag-agents` env and project imports:
  - `config.py` loads correctly and picks up `.env` (`docs_path`, `vector_db_path`, `OPENAI_API_KEY`).
  - `ingest.py` imports cleanly after removing `langchain_community` and using `chromadb` directly.
- Implemented and understood ingestion pipeline:
  - `load_docs()` → walks `data/raw/` and loads `.txt` into `Document` objects with `metadata["source"]`.
  - `split_docs()` → uses `RecursiveCharacterTextSplitter` to create overlapping chunks.
  - `build_vector_store()` → uses `chromadb.PersistentClient` + `OpenAIEmbeddingFunction` to build a persistent Chroma collection under `data/vector_store/`.
- Created a dummy doc (`data/raw/sample.txt`) and ran:
  - `PYTHONPATH=src python scripts/dev_ingest.py`
  - Output: `Loaded 1 raw docs`, `Split into 1 chunks`, `Vector store built & persisted at: data/vector_store`.
  - Confirmed Chroma index files are present in `data/vector_store/`.
- Added a minimal `.gitignore` to avoid committing:
  - `.env` and other secrets.
  - `data/raw/` (raw documents).
  - `data/vector_store/` (vector DB artifacts).

## Repo status
- Initialised git repo at `~/dev/block-b/p3_rag_assistant`.
- Created GitHub repo: `rag-domain-knowledge-assistant`.
- Pushed initial commit with:
  - `src/rag_assistant/config.py`, `ingest.py`
  - `scripts/dev_ingest.py`
  - `SESSION_LOG.md`, `.gitignore`, etc.
- Verified that `.env`, raw docs, and vector DB files are NOT committed.

## Next 2–3 steps (for next Block B)
1. Implement `retrieval.py`:
   - `get_collection()` → open Chroma collection from `data/vector_store/`.
   - `retrieve(query, k=5)` → return top-k chunks with source + score.
   - `answer(query)` → build prompt with retrieved chunks and call LLM.
2. Add `scripts/dev_query.py`:
   - Simple CLI to enter a query, print answer + sources.
3. Start sketching `app.py` (FastAPI) interface:
   - `POST /ask` → `{ query }` → `{ answer, sources }`.


## W4D2 - 13.01.26 – Block B (P3 RAG) – Retrieval skeleton 

### Energy / Time
- Energy: ~5/10
- Time: ~90–120 min
- Scope: Retrieval skeleton + sanity script, no answer()/FastAPI yet.

### What I did
- Confirmed ingestion + Chroma index still working (`dev_ingest.py` on dummy UAV doc).
- Implemented `retrieval.py`:
  - `get_collection()` opens the persisted Chroma collection from `data/vector_store/` using `chromadb.PersistentClient` and `OpenAIEmbeddingFunction` (same embedding model as ingestion).
  - `retrieve(query, k)`:
    - Calls `collection.query` with `include=["documents", "metadatas", "distances"]`.
    - Returns a list of dicts: `{ "text", "source", "score" }`.
- Added `scripts/dev_query.py`:
  - Takes a query from CLI or `input()`.
  - Calls `retrieve(query, k=3)` and prints:
    - raw results (debug line),
    - formatted top-k list with score, source path, and snippet.
- Sanity check:
  - Ran `PYTHONPATH=src python scripts/dev_query.py "pre-flight checks"`.
  - Got 1 result:
    - `source = data/raw/sample.txt`
    - `text = "This is a dummy UAV manual line about battery safety and pre-flight checks."`
    - `score ≈ 0.9584`

### Next steps (future Block B)
1. Implement `answer(query)` in `retrieval.py`:
   - Build prompt from retrieved chunks + query.
   - Call LLM (`settings.llm_model` via OpenAI client).
   - Return `{ "answer", "sources" }`.
2. Add `scripts/dev_answer.py`:
   - CLI that prints the final answer + cited sources.
3. Start FastAPI `app.py` skeleton:
   - `POST /ask` → `{ query }` → `{ answer, sources }`.


## W4D3 - 14.01.26 – Block B (P3 RAG) – End-to-end answer() 

### What I did
- Updated ingestion to be compatible with latest Chroma (`delete(ids=...)` instead of `where={}`).
- Created richer dummy UAV manual in `data/raw/sample.txt`.
- Implemented `answer(query)` on top of `retrieve()`:
  - Builds grounded prompt from top-k chunks.
  - Uses OpenAI chat completions via `settings.llm_model`.
  - Returns `{ answer, sources }` with snippets and scores.
- Added `scripts/dev_answer.py` CLI:
  - Runs a query, prints answer + sources.

### Sanity check
- Ran:

  ```bash
  PYTHONPATH=src python scripts/dev_ingest.py
  PYTHONPATH=src python scripts/dev_answer.py "What pre-flight checks and battery safety steps are required before take-off?"


## W5D1 – 19.01.26 – Block B (P3 RAG) – Eval/Logging Harness v0
What I did:
- Created scripts/eval_run.py as a v0 eval harness that:
  - Iterates over a 10-question UAV pre-flight eval set (EVAL_ITEMS with id, query, expected_answer).
  - Calls answer(query, k_ctx=top_k, max_output_tokens=...) for each question.
  - Measures latency per query and normalises retrieved chunks into [{rank, source, score, snippet}, ...].
  - Writes one JSON object per query to data/logs/eval_runs/YYYY-MM-DD.jsonl.
- Added helper functions:
  - _utc_iso_now() to generate UTC ISO timestamps for runs and per-query events.
  - _get_log_path() to create/resolve the daily log file under data/logs/eval_runs/.
- Logged per-query fields:
- run_date, run_id, eval_id, index, query, timestamp, top_k, latency_s,
  answer, expected_answer, retrieved, answer_label, retrieval_label.
- Initialised simple label counters for:
  - answer_label_counts = {correct, partial, wrong, oos, unlabeled}.
  - retrieval_label_counts = {ok, bad, unlabeled}.
- Wired in the real 10-question UAV pre-flight eval set from Block A:
  - Direct fact, paraphrased fact, procedural how-to, multi-hop, definition + example,
    out-of-scope, ambiguous order, shorthand/typo, tricky negative.
- Fixed small issues while wiring it up:
  - datetime.now(time.utc) → datetime.now(timezone.utc).
  - Typing bug (Dict[...] = {...}) → proper annotated dicts (var: Dict[...] = {...}).
  - Made expected_answer access robust via item.get("expected_answer", "") to avoid KeyError.
- Ran:
    PYTHONPATH=src python scripts/eval_run.py
- Observed console output:

    Running eval run with 10 questions...Logging to: data/logs/eval_runs/2026-01-19.jsonl
    === Eval summary (labels may be placeholders) ===
    Total questions: 10
    Answers – correct: 0, partial: 0, wrong: 0, oos: 0, unlabeled: 10
    Retrieval – ok: 0, bad: 0, unlabeled: 10
    Log file: data/logs/eval_runs/2026-01-19.jsonl
    Verified that data/logs/eval_runs/2026-01-19.jsonl exists and contains valid JSONL records with:
    eval_id, query, expected_answer, answer,
    retrieved (rank, source, score, snippet),
    placeholder labels (answer_label = "unlabeled", retrieval_label = "unlabeled").


### W6D3 - 28.01.26 Failure buckets v0 
Buckets:
- retrieval_miss: relevant chunk not retrieved
- chunking_issue: doc exists but split/snippets miss key info
- grounding_failure: hallucination / uses info not in context
- instruction_following: fails OOS behavior or constraints
- ambiguity_handling: ambiguous Q interpreted wrongly
- formatting: correct but messy/unusable
- other: misc

Today: labeled 5 eval items using scripts/eval_label.py → output JSONL in data/logs/eval_runs_labeled/
Next: label remaining 5; then pick top 1–2 buckets to address (likely retrieval_miss/chunking_issue first).
