import sys

from rag_assistant.retrieval import answer


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        query = input("Enter your question: ").strip()

    if not query:
        print("No query provided.")
        return
    
    print(f"\nRunning RAG answer() for query: {query!r}\n")

    result = answer(query, k_ctx=5)

    ans = result.get("answer", "")
    sources = result.get("sources", [])

    print("=== ANSWER ===")
    print(ans or "[No answer generated]")
    print("\n=== SOURCES ===")

    if not sources:
        print("[No sources available]")
        return
    
    for i, src in enumerate(sources, start=1):
        source_path = src.get("source", "unknown")
        score = src.get("score")
        snippet = src.get("snippet", "")

        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else str(score)

        print(f"\n[{i}] source={source_path} score={score_str}")
        print(f"    {snippet}")


if __name__ == "__main__":
    main()

