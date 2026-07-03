from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.chain import answer_question
from src.config import CONFIG

router = APIRouter()


class PerguntaRequest(BaseModel):
    pergunta: str
    k: int = CONFIG["rag"]["default_k"]


@router.post("/perguntar")
def perguntar(body: PerguntaRequest):
    """Pergunta em linguagem natural sobre o catálogo de livros e reviews (RAG)."""
    return answer_question(body.pergunta, k=body.k)
