"""
Sentimento clássico (VADER) sobre o texto das reviews, comparado à nota (score)
numérica. Serve para dois fins de negócio:
  1. Encontrar reviews "discrepantes" (texto e nota não combinam) — sinal de
     opiniões mais nuançadas, que vale a pena um analista olhar de perto.
  2. Métrica de qualidade: quão bem o sentimento do texto prevê a nota dada
     (usado depois em notebooks/02_avaliacao_qualidade.ipynb).
"""

from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "sample_reviews.parquet"
OUTPUT_PATH = ROOT / "data" / "processed" / "sample_with_sentiment.parquet"

_CFG = CONFIG["sentiment"]
_analyzer = SentimentIntensityAnalyzer()


def score_to_label(score: float) -> str:
    if score <= 2:
        return "negative"
    if score == 3:
        return "neutral"
    return "positive"


def compound_to_label(compound: float) -> str:
    if compound <= _CFG["vader_negative_threshold"]:
        return "negative"
    if compound < _CFG["vader_positive_threshold"]:
        return "neutral"
    return "positive"


def add_sentiment(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    df = df.copy()
    compounds = []
    for text in df[text_col].fillna(""):
        compounds.append(_analyzer.polarity_scores(text[:5000])["compound"])
    df["sentiment_compound"] = compounds
    df["sentiment_label"] = df["sentiment_compound"].apply(compound_to_label)
    df["score_label"] = df["score"].apply(score_to_label)
    df["sentiment_mismatch"] = df["sentiment_label"] != df["score_label"]
    return df


def run(input_path: Path = INPUT_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    print("Carregando amostra...")
    df = pd.read_parquet(input_path)

    print(f"Calculando sentimento (VADER) para {len(df):,} reviews...")
    df = add_sentiment(df)

    accuracy = (df["sentiment_label"] == df["score_label"]).mean()
    print(f"\nAcurácia sentimento-do-texto vs. nota-numérica: {accuracy:.1%}")
    print("\nMatriz nota_label x sentimento_label:")
    print(pd.crosstab(df["score_label"], df["sentiment_label"]))

    mismatch_extreme = df[
        (df["score"] >= 4) & (df["sentiment_compound"] <= -0.3)
        | (df["score"] <= 2) & (df["sentiment_compound"] >= 0.3)
    ]
    print(f"\nReviews com discrepância extrema texto x nota: {len(mismatch_extreme):,} "
          f"({len(mismatch_extreme) / len(df):.1%} da amostra)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"\nResultado salvo em {output_path}")
    return output_path


if __name__ == "__main__":
    run()
