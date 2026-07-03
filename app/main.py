from fastapi import FastAPI

from app.routers import qa, reviewers, summarization

app = FastAPI(
    title="A3Data — Ferramenta de Análise de Reviews de Livros",
    description=(
        "POC para a editora: perguntas em linguagem natural sobre o catálogo (RAG), "
        "sumarização de reviews via LLM e ranking de usuários com opiniões relevantes "
        "para entrevista."
    ),
    version="0.1.0",
)

app.include_router(qa.router, tags=["Perguntas (RAG)"])
app.include_router(summarization.router, tags=["Sumarização"])
app.include_router(reviewers.router, tags=["Reviewers relevantes"])


@app.get("/")
def status():
    return {"status": "ok", "docs": "/docs"}
