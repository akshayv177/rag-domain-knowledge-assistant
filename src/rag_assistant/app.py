from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag_assistant.retrieval import answer

app = FastAPI(title="RAG Domain Knowledge Assistant", version="0.1.0")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question")
    top_k: int = Field(5, ge=1, le=20, description="How many chunks to retrieve")


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]


@app.get("/health")
def health():
    return {"status": "ok"}



@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query must be non-empty")
    
    try:
        result = answer(q, k_ctx=req.top_k)
    except Exception as e:
        # Keep errors readable during development; tighten later
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"answer": result.get("answer", ""), "sources": result.get("sources", [])}