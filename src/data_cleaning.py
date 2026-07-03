"""
Limpeza da amostra de reviews e junção com os metadados dos livros
(books_data.csv): parsing de listas (authors/categories), tratamento de nulos,
conversão de datas e deduplicação.
"""

import ast
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RAW_PATH = ROOT / "data" / "processed" / "sample_raw.parquet"
BOOKS_DATA_CSV = ROOT / "books_data.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "sample_reviews.parquet"


def _parse_list_literal(value):
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
        return list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]
    except (ValueError, SyntaxError):
        return []


def load_books_data(path: Path = BOOKS_DATA_CSV) -> pd.DataFrame:
    books = pd.read_csv(path)
    books["authors"] = books["authors"].apply(_parse_list_literal)
    books["categories"] = books["categories"].apply(_parse_list_literal)
    books["primary_category"] = books["categories"].apply(lambda c: c[0] if c else None)
    books["primary_author"] = books["authors"].apply(lambda a: a[0] if a else None)
    # Um mesmo título pode aparecer mais de uma vez (reedições); mantém o registro
    # com descrição mais completa.
    books["_desc_len"] = books["description"].fillna("").str.len()
    books = (
        books.sort_values("_desc_len", ascending=False)
        .drop_duplicates(subset="Title", keep="first")
        .drop(columns="_desc_len")
    )
    return books


def build_clean_sample(
    sample_raw_path: Path = SAMPLE_RAW_PATH,
    books_data_csv: Path = BOOKS_DATA_CSV,
    output_path: Path = OUTPUT_PATH,
) -> Path:
    print("Carregando amostra de reviews...")
    reviews = pd.read_parquet(sample_raw_path)
    print(f"  {len(reviews):,} linhas antes da limpeza")

    # `Id` identifica o livro (ASIN/ISBN), não a review — várias reviews
    # compartilham o mesmo Id. A chave de review única é (Id, User_id, time).
    reviews = reviews.drop_duplicates(subset=["Id", "User_id", "time"])
    reviews = reviews.dropna(subset=["Title", "score", "text"])

    reviews["review_date"] = pd.to_datetime(reviews["time"], unit="s", errors="coerce")
    reviews["review_year"] = reviews["review_date"].dt.year
    reviews["review_len"] = reviews["text"].str.len()

    print("Carregando e limpando metadados dos livros...")
    books = load_books_data(books_data_csv)
    print(f"  {len(books):,} títulos únicos em books_data.csv")

    merged = reviews.merge(books, on="Title", how="left", suffixes=("", "_book"))

    matched = merged["authors"].apply(lambda a: isinstance(a, list) and len(a) > 0).sum()
    print(f"  {matched:,} / {len(merged):,} reviews casaram com metadados de autor/gênero")

    merged["price"] = pd.to_numeric(merged["Price"], errors="coerce")
    merged["ratingsCount"] = pd.to_numeric(merged["ratingsCount"], errors="coerce")

    keep_cols = [
        "Id", "Title", "primary_author", "authors", "primary_category", "categories",
        "publisher", "publishedDate", "description", "price", "ratingsCount",
        "User_id", "profileName", "score", "review_date", "review_year",
        "summary", "text", "review_len",
    ]
    merged = merged[keep_cols]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output_path, index=False)
    print(f"\nAmostra limpa salva em {output_path} com {len(merged):,} linhas.")
    return output_path


if __name__ == "__main__":
    build_clean_sample()
