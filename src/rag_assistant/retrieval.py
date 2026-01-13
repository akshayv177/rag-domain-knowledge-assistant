from typing import List, Dict

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .config import settings

_COLLECTION_NAME = "documents"


def _get_client() -> chromadb.ClientAPI:
    """
    Return a persistent Chroma client pointing at the vector DB path.
    """
    return chromadb.PersistentClient(path=str(settings.vector_db_path))


def get_collection():
    """
    Open the persisted Chroma collection used for document retrieval.
    """
    client = _get_client()

    embedding_fn = OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name=settings.embedding_model,
    )

    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    return collection


def retrieve(query: str, k: int = 5) -> List[Dict]:
    """
    Retrieve the top-k most similar chunks for a given query string.

    Returns a list of dicts with:
      - text:   chunk text
      - source: original document path (if available)
      - score:  distance (lower is closer)

    If the index is empty or no results are found, returns an empty list.
    """
    if not query:
        return []

    collection = get_collection()

    raw = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    docs_lists = raw.get("documents", [[]])
    metas_lists = raw.get("metadatas", [[]])
    dists_lists = raw.get("distances", [[]])

    if not docs_lists or not docs_lists[0]:
        return []

    docs = docs_lists[0]
    metadatas = metas_lists[0] if metas_lists else [{}] * len(docs)
    distances = dists_lists[0] if dists_lists else [None] * len(docs)

    results: List[Dict] = []

    for text, meta, dist in zip(docs, metadatas, distances):
        source = meta.get("source") if isinstance(meta, dict) else None

        results.append(
            {
                "text": text,
                "source": source,
                "score": dist,
            }
        )

    return results
