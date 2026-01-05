from rag_assistant.config import settings
from rag_assistant.ingest import load_docs, split_docs, build_vector_store


def main():
    print("Docs path:", settings.docs_path)
    print("Vector store path:", settings.vector_db_path)

    docs = load_docs()
    print(f"Loaded {len(docs)} raw docs")

    chunks = split_docs(docs)
    print(f"Split into {len(chunks)} chunks")

    build_vector_store(chunks)
    print("Vector store built & persisted at:", settings.vector_db_path)


if __name__ == "__main__":
    main()
