from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .config import settings


def load_docs(path: Path | None = None) -> Sequence[Document]:
    """
    Load raw documents from a directory into LangChain Document objects.
    For now: plain .txt files under docs_path (default: data/raw).
    """
    docs_dir = Path(path or settings.docs_path)
    docs_dir.mkdir(parents=True, exist_ok=True)

    docs: list[Document] = []

    for txt_path in docs_dir.rglob("*.txt"):
        try:
            text = txt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = txt_path.read_text(errors="ignore")

        docs.append(
            Document(
                page_content=text,
                metadata={"source": str(txt_path)},
            )
        )

    return docs


def split_docs(
    docs: Sequence[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 200,
) -> Sequence[Document]:
    """
    Chunk documents into overlapping pieces suitable for embeddings.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(docs)


def build_vector_store(
    chunks: Sequence[Document],
    persist_dir: Path | None = None,
):
    """
    Create or overwrite a local Chroma vector store from chunks.
    Persists it to disk so the query path can open it later.
    """
    persist_dir = Path(persist_dir or settings.vector_db_path)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Local persistent Chroma client
    client = chromadb.PersistentClient(path=str(persist_dir))

    embedding_fn = OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name=settings.embedding_model,
    )

    collection = client.get_or_create_collection(
        name="documents",
        embedding_function=embedding_fn,
    )

    # --- CLEAR EXISTING ENTRIES (Chroma 0.5+ compatible) ---
    existing_count = collection.count()
    if existing_count:
        # Fetch only IDs to avoid pulling full docs/embeddings
        existing = collection.get(include=[])
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for i, doc in enumerate(chunks):
        ids.append(f"chunk-{i}")
        texts.append(doc.page_content)
        metadatas.append(doc.metadata)

    if ids:
        collection.add(ids=ids, documents=texts, metadatas=metadatas)

    return collection

