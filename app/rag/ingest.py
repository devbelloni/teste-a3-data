"""
Ingestão para RAG: agrega reviews por livro (descrição + resumos de reviews reais)
em um documento por livro, gera embeddings locais (all-MiniLM-L6-v2) e indexa no
ChromaDB. Mesmo padrão de app/rag do projeto RAG-with-FastAPI de referência.

Escopo do POC: livros com pelo menos MIN_REVIEWS reviews na amostra (conteúdo
suficiente para um documento significativo). Em produção, a ingestão cobriria o
catálogo completo, de forma incremental.
"""

from pathlib import Path

import pandas as pd
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "processed" / "sample_reviews.parquet"
CHROMA_DIR = ROOT / "chroma_db"

_CFG = CONFIG["rag"]
COLLECTION_NAME = _CFG["collection_name"]
EMBEDDING_MODEL = _CFG["embedding_model"]

MIN_REVIEWS = _CFG["min_reviews_per_book"]
MAX_REVIEW_SNIPPETS_PER_BOOK = _CFG["max_review_snippets_per_book"]
BATCH_SIZE = _CFG["batch_size"]


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def _clean_str(value, default: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return str(value).strip()


def build_book_documents(df: pd.DataFrame, min_reviews: int = MIN_REVIEWS) -> list[Document]:
    counts = df.groupby("Title").size()
    eligible_titles = counts[counts >= min_reviews].index

    docs: list[Document] = []
    for title, group in df[df["Title"].isin(eligible_titles)].groupby("Title"):
        first = group.iloc[0]
        author = _clean_str(first.get("primary_author"), "autor desconhecido")
        category = _clean_str(first.get("primary_category"), "gênero não identificado")
        description = _clean_str(first.get("description"))

        snippets = (
            group.sort_values("review_len", ascending=False)
            .head(MAX_REVIEW_SNIPPETS_PER_BOOK)["summary"]
            .dropna()
            .tolist()
        )
        reader_says = "; ".join(snippets)

        page_content = (
            f"Título: {title}\n"
            f"Autor: {author}\n"
            f"Gênero: {category}\n"
            f"Descrição: {description[:500]}\n"
            f"O que os leitores dizem: {reader_says}"
        )

        docs.append(
            Document(
                page_content=page_content,
                metadata={
                    "title": str(title),
                    "author": str(author),
                    "category": str(category),
                    "avg_score": float(group["score"].mean()),
                    "n_reviews_sample": int(len(group)),
                },
            )
        )
    return docs


def ingest(
    input_path: Path = INPUT_PATH,
    chroma_dir: Path = CHROMA_DIR,
    min_reviews: int = MIN_REVIEWS,
) -> Chroma:
    print("Carregando amostra de reviews...")
    df = pd.read_parquet(input_path)

    print(f"Montando documentos por livro (mín. {min_reviews} reviews)...")
    docs = build_book_documents(df, min_reviews=min_reviews)
    print(f"  {len(docs):,} livros elegíveis para indexação")

    print(f"Carregando modelo de embeddings local ({EMBEDDING_MODEL})...")
    embeddings = _get_embeddings()

    chroma_dir.mkdir(parents=True, exist_ok=True)
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(chroma_dir),
    )

    print(f"Indexando {len(docs):,} documentos em lotes de {BATCH_SIZE}...")
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        vectorstore.add_documents(batch)
        print(f"  {min(i + BATCH_SIZE, len(docs)):,} / {len(docs):,}")

    print(f"\nÍndice ChromaDB salvo em {chroma_dir}")
    return vectorstore


if __name__ == "__main__":
    ingest()
