from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import SAMPLE_PATH
from app.core.llm import get_llm
from src.config import CONFIG

router = APIRouter()

_CFG = CONFIG["summarization"]
MAX_REVIEWS_FOR_SUMMARY = _CFG["max_reviews_for_summary"]

SUMMARY_SYSTEM_PROMPT = (
    "Você resume opiniões de leitores para uma editora de livros. A partir das reviews "
    "fornecidas, escreva em português um resumo curto e objetivo com: (1) sentimento "
    "geral, (2) principais elogios, (3) principais críticas, (4) uma citação "
    "representativa. Baseie-se SOMENTE nas reviews fornecidas."
)


@lru_cache
def _load_reviews() -> pd.DataFrame:
    return pd.read_parquet(SAMPLE_PATH)


def _summarize_reviews(reviews: pd.DataFrame, label: str) -> dict:
    sample = reviews.sort_values("review_len", ascending=False).head(MAX_REVIEWS_FOR_SUMMARY)
    reviews_block = "\n\n".join(
        f"[nota {r.score:.0f}] {r.summary}: {str(r.text)[:600]}" for r in sample.itertuples()
    )

    llm = get_llm(temperature=_CFG["temperature"])
    messages = [
        SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
        HumanMessage(content=f"Reviews de {label}:\n\n{reviews_block}"),
    ]
    response = llm.invoke(messages)

    return {
        "resumo": response.content,
        "n_reviews_usadas": len(sample),
        "n_reviews_total": len(reviews),
        "nota_media": round(float(reviews["score"].mean()), 2),
    }


@router.get("/resumo/livro/{title}")
def resumo_livro(title: str):
    """Resumo (via LLM) do que os leitores dizem sobre um livro específico."""
    df = _load_reviews()
    matches = df[df["Title"].str.lower() == title.lower()]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Livro '{title}' não encontrado na amostra.")
    return {"title": matches.iloc[0]["Title"], **_summarize_reviews(matches, f"o livro '{title}'")}


@router.get("/resumo/autor/{author}")
def resumo_autor(author: str):
    """Resumo (via LLM) do que os leitores dizem sobre as obras de um autor."""
    df = _load_reviews()
    matches = df[df["primary_author"].str.lower() == author.lower()]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Autor '{author}' não encontrado na amostra.")
    return {"author": matches.iloc[0]["primary_author"], **_summarize_reviews(matches, f"o autor '{author}'")}
