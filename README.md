# RAG Domain Knowledge Assistant (UAV Manuals / SOPs)

A small, systems-minded **RAG** project that answers questions over UAV/drone manuals & SOP-style docs with **grounded answers + sources**.

## Current status (v0 working)
- ✅ Ingestion pipeline: `data/raw/` → chunk → embed → **persistent Chroma** store (`data/vector_store/`)
- ✅ Retrieval: top-k chunks with `source + score`
- ✅ `answer(query)`: returns `{ answer, sources }` (grounding: answer only from provided context)
- ✅ CLI dev scripts: `dev_ingest.py`, `dev_query.py`, `dev_answer.py`
- ✅ Eval harness: JSONL logs + manual labeling loop (`eval_run.py`, `eval_label.py`)

## Quick run (local)
```bash
# set env vars in .env (ignored by git)
OPENAI_API_KEY=...
DOCS_PATH=data/raw
VECTOR_DB_PATH=data/vector_store

PYTHONPATH=src python scripts/dev_ingest.py
PYTHONPATH=src python scripts/dev_answer.py "What pre-flight checks are required before take-off?"
```


## Next milestone:
- Minimal FastAPI wrapper: POST /ask → {answer, sources} + GET /health
- eval_report.py to summarize labeled runs
- Docker for reproducible demo

## Notes: raw docs, vector store, logs, and .env are intentionally gitignored.