import sys

from rag_assistant.retrieval import retrieve



def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        query = input("Enter query: ").strip()

    if not query:
        print("No query provided")
        return
    
    results = retrieve(query, k=3)
    print(f"DEBUG raw results: {results}")
    
    if not results:
        print("No results found (index empty or query unmatched).")
        return
    
    print(f"Top {len(results)} results:")
    for i, r in enumerate(results, start=1):
        text = r.get("text", "") or ""
        source = r.get("source", "unknown")
        score = r.get("score", None)

        snippet = text.replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."

        score_str = f"{score:.4f}" if isinstance(score, (int,float)) else str(score)

        print(f"\n[{i}] score={score_str} source={source}")
        print(f"    {snippet}")
        

if __name__ == "__main__":
    main()