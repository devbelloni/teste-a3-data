"""
Palavras-chave características de cada gênero, via TF-IDF: o que os leitores
mencionam mais nas reviews de um gênero comparado ao corpus geral (não é só
frequência absoluta, é o que *distingue* aquele gênero dos demais).
"""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "sample_reviews.parquet"

_CFG = CONFIG["keywords"]
MIN_REVIEWS_PER_GENRE = _CFG["min_reviews_per_genre"]
TOP_N_GENRES = _CFG["top_n_genres"]
TOP_N_KEYWORDS = _CFG["top_n_keywords"]


def top_keywords_by_genre(
    df: pd.DataFrame,
    min_reviews: int = MIN_REVIEWS_PER_GENRE,
    top_n_genres: int = TOP_N_GENRES,
    top_n_keywords: int = TOP_N_KEYWORDS,
) -> dict[str, list[str]]:
    genre_counts = df["primary_category"].value_counts()
    genres = genre_counts[genre_counts >= min_reviews].head(top_n_genres).index.tolist()

    corpus = (
        df[df["primary_category"].isin(genres)]
        .groupby("primary_category")["text"]
        .apply(lambda texts: " ".join(texts.fillna("").str.slice(0, 500)))
    )
    corpus = corpus.reindex(genres)

    tfidf_cfg = _CFG["tfidf"]
    vectorizer = TfidfVectorizer(
        max_df=tfidf_cfg["max_df"],
        min_df=tfidf_cfg["min_df"],
        stop_words="english",
        max_features=tfidf_cfg["max_features"],
        ngram_range=tuple(tfidf_cfg["ngram_range"]),
    )
    tfidf = vectorizer.fit_transform(corpus.values)
    terms = vectorizer.get_feature_names_out()

    result = {}
    for i, genre in enumerate(genres):
        row = tfidf[i].toarray().ravel()
        top_idx = row.argsort()[::-1][:top_n_keywords]
        result[genre] = [terms[j] for j in top_idx]
    return result


if __name__ == "__main__":
    print("Carregando amostra...")
    data = pd.read_parquet(INPUT_PATH)

    print(f"Extraindo keywords TF-IDF para os {TOP_N_GENRES} gêneros com mais reviews "
          f"(mín. {MIN_REVIEWS_PER_GENRE} reviews)...\n")
    keywords = top_keywords_by_genre(data)
    for genre, kws in keywords.items():
        print(f"{genre}: {', '.join(kws)}")
