"""
Cadeia de RAG: reescreve a pergunta do usuário (normaliza para inglês, já que o
corpus de reviews é majoritariamente em inglês — melhora bastante a qualidade da
busca semântica), recupera os livros mais relevantes no ChromaDB e gera uma
resposta em português com o LLM (Groq/Llama 3.3 70B), citando as fontes.
"""

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from app.core.llm import get_llm
from src.config import CONFIG

_LLM_CFG = CONFIG["llm"]
_RAG_CFG = CONFIG["rag"]

REWRITE_PROMPT = (
    "Reescreva a pergunta do usuário como uma consulta de busca concisa em INGLÊS, "
    "focada em gênero, autor, tema ou características do livro. Responda só com a "
    "consulta reescrita, sem explicações.\n\nPergunta: {question}"
)

ANSWER_SYSTEM_PROMPT = (
    "Você é um assistente de análise de dados para uma editora de livros. Responda em "
    "português, de forma objetiva, usando SOMENTE as informações dos livros fornecidos "
    "no contexto (título, autor, gênero, descrição e o que os leitores dizem). Se o "
    "contexto não tiver informação suficiente, diga isso claramente. Sempre cite os "
    "títulos dos livros usados na resposta."
)


@lru_cache
def get_vectorstore() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def rewrite_query(question: str) -> str:
    llm = get_llm(temperature=_LLM_CFG["rewrite_temperature"])
    response = llm.invoke([HumanMessage(content=REWRITE_PROMPT.format(question=question))])
    return response.content.strip()


def answer_question(question: str, k: int = _RAG_CFG["default_k"]) -> dict:
    vectorstore = get_vectorstore()
    search_query = rewrite_query(question)
    docs = vectorstore.similarity_search(search_query, k=k)

    context = "\n\n---\n\n".join(d.page_content for d in docs)
    llm = get_llm(temperature=_LLM_CFG["answer_temperature"])
    messages = [
        SystemMessage(content=ANSWER_SYSTEM_PROMPT),
        HumanMessage(content=f"Contexto:\n{context}\n\nPergunta: {question}"),
    ]
    response = llm.invoke(messages)

    return {
        "answer": response.content,
        "search_query_used": search_query,
        "sources": [
            {
                "title": d.metadata["title"],
                "author": d.metadata["author"],
                "category": d.metadata["category"],
                "avg_score": d.metadata["avg_score"],
            }
            for d in docs
        ],
    }
