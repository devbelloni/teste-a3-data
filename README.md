# LLM/NLP Analytics for Book Reviews: EDA, RAG, FastAPI

A technical case study (Senior Data Scientist, LLM/NLP) built on the **Amazon Books
Reviews** dataset. The scenario is a publisher that spends about 5 analysts x 3 days per
manual analysis cycle. The project replaces that with a reproducible pipeline and a
working API (not just notebooks), with objective quality metrics and a parameterized
cost-impact estimate.

> Portuguese version: [README.pt-BR.md](README.pt-BR.md) · Full design notes:
> [docs/plano.md](docs/plano.md)

## What is inside

- **EDA** (`notebooks/01_eda.ipynb`): rating distribution, performance by author and genre,
  time trends, review length vs. rating.
- **Classic NLP** (`src/`): VADER sentiment vs. true rating, a heuristic to find
  "relevant reviewers worth interviewing", TF-IDF keywords per genre.
- **RAG** (`app/rag/`): local embeddings (`all-MiniLM-L6-v2`) + ChromaDB + LangChain +
  Groq (Llama 3.3 70B), with LLM query rewriting to improve retrieval.
- **FastAPI service** (`app/`): `POST /perguntar` (RAG Q&A), `GET /resumo/livro|autor/{name}`
  (LLM summarization), `GET /reviewers-relevantes` (reviewer ranking).
- **Quality evaluation** (`notebooks/02_avaliacao_qualidade.ipynb`): ROUGE for
  summarization against a real human summary, precision@k for RAG, VADER vs. LLM sentiment.
- **Financial impact** (`src/financial_impact.py`): parameterized savings per analysis cycle.
- **Engineering**: single `config.yaml` for all hyperparameters, Docker and Docker Compose,
  a Postman collection (runnable with newman) covering success and error cases.

## Architecture

```
Books_rating.csv (2.8 GB) ──┐
                             ├─► DuckDB (stratified sampling, ~200k rows)
books_data.csv (181 MB) ────┘            │
                                          ▼
                              cleaning + join (pandas)
                                          │
                  ┌───────────────────────┼────────────────────┐
                  ▼                       ▼                    ▼
          EDA (Jupyter)        Classic NLP (VADER,        RAG ingestion
                               TF-IDF, heuristics)     (embeddings + ChromaDB)
                                          │                    │
                                          └─────────┬──────────┘
                                                    ▼
                                  FastAPI (LangChain + Groq / Llama 3.3 70B)
```

## Key results

| Area | Result |
|---|---|
| Sample | 198,924 reviews (of ~3M); 87% with identified author, 82% with genre |
| Sentiment (VADER) | 75.1% accuracy vs. true rating overall; 0% on the "hard" slice (12.5% of the sample) |
| Sentiment (LLM) | 60% accuracy on that same hard slice: a real gain over classic NLP |
| RAG | Mean precision@5 of 80% (7 test queries, 13,661 books indexed) |
| Cost impact | About 96.7% reduction per analysis cycle (assumptions in `config.yaml`) |

Summarization is reported with ROUGE and embedding similarity in the evaluation notebook.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # set GROQ_API_KEY
```

Download `Books_rating.csv` and `books_data.csv` from the
[Amazon Books Reviews dataset on Kaggle](https://www.kaggle.com/datasets/mohamedbakhet/amazon-books-reviews)
into the project root (not included: 2.8 GB and 181 MB).

```bash
python -m scripts.run_pipeline        # sampling, cleaning, sentiment, RAG indexing
uvicorn app.main:app --reload         # Swagger UI at http://127.0.0.1:8000/docs
# or
docker compose up -d api
```

## Known limitations and roadmap

- Semantic search works better in English than Portuguese (the corpus is mostly English);
  mitigated by LLM query rewriting. Production would use multilingual embeddings.
- Author metadata has duplicates caused by name variants (for example "J. R. R. Tolkien"
  vs. "John Ronald Reuel Tolkien"); a good candidate for LLM-based entity normalization.
- The RAG index covers books with 3+ reviews in the sample; production would index the
  full catalog with incremental ingestion.

## Author

**Márcio Belloni**, AI/ML Engineer.
[LinkedIn](https://www.linkedin.com/in/marcio-belloni/) · [GitHub](https://github.com/devbelloni)
