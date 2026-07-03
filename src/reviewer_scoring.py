"""
Heurística para encontrar "usuários com opiniões relevantes para uma entrevista"
(pedido explícito do desafio), por autor ou por gênero.

Relevância combina 4 sinais, cada um normalizado (z-score) dentro do recorte
(autor/gênero) analisado, para não misturar escalas de reviewers muito diferentes:

  - especificidade (tamanho da review — mais detalhe, mais substância)
  - diversidade lexical (vocabulário variado — indica opinião elaborada, não genérica)
  - intensidade de sentimento (opinião forte, não morna)
  - discrepância vs. nota média do livro (opinião contrária ao consenso — interessante
    para entender pontos de vista minoritários / possíveis problemas não óbvios)
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "sample_with_sentiment.parquet"

WEIGHTS = CONFIG["reviewer_scoring"]["weights"]


def _lexical_diversity(text: str) -> float:
    words = text.lower().split()
    if len(words) < 5:
        return 0.0
    return len(set(words)) / len(words)


def _zscore(s: pd.Series) -> pd.Series:
    std = s.std()
    if not std or np.isnan(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


def _prepare_reviewer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["lexical_diversity"] = df["text"].fillna("").apply(_lexical_diversity)

    book_avg = df.groupby("Title")["score"].transform("mean")
    df["discrepancy"] = (df["score"] - book_avg).abs()
    df["sentiment_intensity"] = df["sentiment_compound"].abs()

    agg = (
        df.groupby(["User_id", "profileName"])
        .agg(
            n_reviews=("Id", "count"),
            specificity=("review_len", "mean"),
            lexical_diversity=("lexical_diversity", "mean"),
            sentiment_intensity=("sentiment_intensity", "mean"),
            discrepancy=("discrepancy", "mean"),
            avg_score_given=("score", "mean"),
        )
        .reset_index()
    )
    return agg


def rank_reviewers(
    df: pd.DataFrame,
    author: str | None = None,
    category: str | None = None,
    top_n: int = 10,
    min_reviews: int = 1,
) -> pd.DataFrame:
    """Rankeia reviewers dentro de um recorte (autor e/ou gênero). Sem filtro, rankeia
    globalmente."""
    scoped = df
    if author:
        scoped = scoped[scoped["primary_author"] == author]
    if category:
        scoped = scoped[scoped["primary_category"] == category]

    if scoped.empty:
        return pd.DataFrame(columns=list(WEIGHTS) + ["relevance_score"])

    agg = _prepare_reviewer_features(scoped)
    agg = agg[agg["n_reviews"] >= min_reviews]
    if agg.empty:
        return agg

    for col in WEIGHTS:
        agg[f"z_{col}"] = _zscore(agg[col])

    agg["relevance_score"] = sum(WEIGHTS[c] * agg[f"z_{c}"] for c in WEIGHTS)
    agg = agg.sort_values("relevance_score", ascending=False).head(top_n)

    return agg[
        ["User_id", "profileName", "n_reviews", "specificity", "lexical_diversity",
         "sentiment_intensity", "discrepancy", "avg_score_given", "relevance_score"]
    ].reset_index(drop=True)


def top_review_snippet(df: pd.DataFrame, user_id: str, author=None, category=None) -> str:
    scoped = df[df["User_id"] == user_id]
    if author:
        scoped = scoped[scoped["primary_author"] == author]
    if category:
        scoped = scoped[scoped["primary_category"] == category]
    if scoped.empty:
        return ""
    longest = scoped.loc[scoped["review_len"].idxmax()]
    return f"[{longest['Title']} — nota {longest['score']:.0f}] {longest['summary']}"


if __name__ == "__main__":
    print("Carregando amostra com sentimento...")
    data = pd.read_parquet(INPUT_PATH)

    print("\nTop 10 reviewers mais relevantes (global, min. 3 reviews na amostra):")
    top_global = rank_reviewers(data, top_n=10, min_reviews=3)
    print(top_global[["profileName", "n_reviews", "specificity", "discrepancy", "relevance_score"]])

    example_author = data["primary_author"].value_counts().index[0]
    print(f"\nTop 5 reviewers mais relevantes para o autor '{example_author}':")
    top_author = rank_reviewers(data, author=example_author, top_n=5)
    print(top_author[["profileName", "n_reviews", "specificity", "discrepancy", "relevance_score"]])
