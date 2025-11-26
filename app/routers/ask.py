from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import search 
from app.services.llm import ask_llm

router = APIRouter(
    prefix="/ask",
    tags=["ask"]
)

class AskRequest(BaseModel):
    prompt: str

class AskResponse(BaseModel):
    llm_answer: str | None = None

ROLE_PROMPTS = {
    "children": "Ты помощник для детей. Объясняй всё простыми, дружелюбными словами. Вот контекст, на который можешь опираться, но не обязан:",
    "parent": "Ты помощник для взрослых. Отвечай строго, по сути, с аргументами. Вот контекст, на который можешь опираться, но не обязан:"
}

def generate_role_answer(role: str, query: str, top_k: int = 5):
    context_chunks = search.search(query, top_k=top_k)
    context_text = "\n\n".join([c["text"] for c in context_chunks])

    prompt = (
        f"{ROLE_PROMPTS[role]}\n\n"
        f"Контекст:\n{context_text}\n\n"
        f"Вопрос: {query}\nОтвет:"
    )

    llm_answer = ask_llm(prompt)
    return llm_answer


@router.post("/children", response_model=AskResponse)
def ask_children(request: AskRequest):
    try:
        llm_answer = generate_role_answer("children", request.prompt)
        return AskResponse(llm_answer=llm_answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parent", response_model=AskResponse)
def ask_parent(request: AskRequest):
    try:
        llm_answer = generate_role_answer("parent", request.prompt)
        return AskResponse(llm_answer=llm_answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
