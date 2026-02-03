#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
PYTHONPATH=src uvicorn rag_assistant.app:app --reload --host 0.0.0.0 --port 8000
