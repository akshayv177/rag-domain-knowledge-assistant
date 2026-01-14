from typing import List, Dict

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .config import settings
from openai import OpenAI

_COLLECTION_NAME = "documents"


def _get_llm_client() -> OpenAI:
    """
    Return an OpenAI client configured with the API key from settings
    """
    return OpenAI(api_key=settings.openai_api_key)


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


def _build_context(chunks: List[Dict]) -> str:
    """
    Build a context string from retrieved chunks for the LLM prompt.
    Each chunk is numbered and includes source info.
    """
    lines: List[str] = []
    for idx, ch in enumerate(chunks, start=1):
        source = ch.get("source", "unknown")
        text = ch.get("text","")
        lines.append(f"[{idx}] Source: {source}\n{text}\n")

    return "\n\n".join(lines)


def answer(query: str, k_ctx: int = 5, max_output_tokens: int = 400) -> Dict:
    """
    High-level QA function for the RAG assistant.

        - Uses 'retrieve' to get top-k_ctx chunks.
        - Builds a grounded prompt instructing the model to answer ONLY from context.
        - Calls the LLM specified in the settings.llm_model
        - Returns a dict with:
            {
                "answer": str,
                "sources": List[Dict]    # each with source, score, snippet
            }
    """
    query = (query or "").strip()
    if not query:
        return {"answer": "No query provided.", "sources": []}
    
    # 1. Retrive context chunks
    chunks = retrieve(query, k=k_ctx)

    if not chunks:
        return {
            "answer": "I could not find any relevant information in the current document set for this query.",
            "sources": [],
        }
    
    # 2. Build context string for the prompt
    context = _build_context(chunks)

    system_msg = (
        "You are a domain knowledge assistant."
        "Answer the user's question ONLY using the provided context"
        "If the answer is not in the context, say you don't know and do not fabricate details"
    )

    user_msg = (
        f"User question:\n{query}\n\n"
        f"Context documents:\n{context}\n\n"
        "Answer concisely and, where useful, reference which source number used."
    )

    # 3. Call the LLM via chat completions
    client = _get_llm_client()

    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=max_output_tokens,
            temperature=0.1,
        )

        answer_text = resp.choices[0].message.content or ""
        answer_text = answer_text.strip()
        if not answer_text:
            answer_text = "I could not generate an answer."
    except Exception as e:
        answer_text = f"Error calling LLM: {e}"

    # 4. Shape sources paylod (trim text to short snippet)
    sources: List[Dict] = []
    for ch in chunks:
        text = (ch.get("text") or "").replace("\n", " ")
        snippet = text[:200] + "..." if len(text) > 200 else text
        sources.append(
            {
                "source": ch.get("source", "unknown"),
                "score": ch.get("score"),
                "snippet": snippet,
            }
        )

    return {
        "answer": answer_text,
        "sources": sources,
    }
