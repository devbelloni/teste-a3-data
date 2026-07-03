from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import GROQ_API_KEY, GROQ_MODEL


@lru_cache
def get_llm(temperature: float = 0.2) -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. Defina-a em um arquivo .env na raiz do projeto."
        )
    return ChatGroq(model=GROQ_MODEL, temperature=temperature, api_key=GROQ_API_KEY)
