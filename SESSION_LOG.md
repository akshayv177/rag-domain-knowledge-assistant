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


## W4D2 – Block B (P3 RAG) – Retrieval skeleton - 13.01.26

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
