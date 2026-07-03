from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.config import SAMPLE_WITH_SENTIMENT_PATH
from src.reviewer_scoring import rank_reviewers

router = APIRouter()


@lru_cache
def _load_reviews() -> pd.DataFrame:
    return pd.read_parquet(SAMPLE_WITH_SENTIMENT_PATH)


@router.get("/reviewers-relevantes")
def reviewers_relevantes(
    autor: str | None = None,
    genero: str | None = None,
    top_n: int = 10,
    min_reviews: int = 1,
):
    """Ranking de usuários com opiniões mais relevantes (heurística), filtrável por
    autor e/ou gênero — insumo direto para selecionar entrevistados."""
    df = _load_reviews()
    ranking = rank_reviewers(
        df, author=autor, category=genero, top_n=top_n, min_reviews=min_reviews
    )
    if ranking.empty:
        raise HTTPException(
            status_code=404,
            detail="Nenhum reviewer encontrado para os filtros informados.",
        )
    return {
        "filtros": {"autor": autor, "genero": genero},
        "resultados": ranking.to_dict(orient="records"),
    }
