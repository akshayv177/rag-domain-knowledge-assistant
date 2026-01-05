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
