import os
from pathlib import Path

from dotenv import load_dotenv

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", CONFIG["llm"]["groq_model"])

CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = CONFIG["rag"]["collection_name"]
EMBEDDING_MODEL = CONFIG["rag"]["embedding_model"]

SAMPLE_WITH_SENTIMENT_PATH = ROOT / "data" / "processed" / "sample_with_sentiment.parquet"
SAMPLE_PATH = ROOT / "data" / "processed" / "sample_reviews.parquet"
