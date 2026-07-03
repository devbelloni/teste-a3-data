"""
Métricas de qualidade para as três frentes de NLP/LLM do projeto:
  1. Sumarização: ROUGE-1/2/L do resumo gerado pelo LLM vs. o resumo humano real
     (campo `summary` do dataset — referência gold já existente nos dados).
  2. RAG: precisão@k de recuperação, em queries de teste com gênero-alvo conhecido.
  3. Sentimento: acurácia comparando o sentimento derivado do texto (VADER, NLP
     clássico) contra o LLM, nos casos onde os dois discordam da nota numérica —
     mostra o ganho de qualidade de usar LLM sobre um léxico fixo.

Faz chamadas ao LLM (Groq) — mantém as amostras pequenas por padrão para não
estourar limites de taxa do tier gratuito.
"""

import time

import pandas as pd
from langchain_core.messages import HumanMessage
from rouge_score import rouge_scorer

from app.core.llm import get_llm
from src.config import CONFIG

_CFG = CONFIG["metrics"]

ONE_LINE_SUMMARY_PROMPT = (
    "Resuma esta review de livro em UMA frase curta em inglês, no estilo de um "
    "título de review (como '{example}'). Responda só com a frase, sem aspas.\n\n"
    "Review: {text}"
)

SENTIMENT_LABEL_PROMPT = (
    "Classifique o sentimento desta review de livro como exatamente uma palavra: "
    "positive, neutral ou negative. Responda só com a palavra.\n\nReview: {text}"
)


def evaluate_summarization_rouge(
    df: pd.DataFrame, n_samples: int = _CFG["rouge_n_samples"], seed: int = 42
) -> dict:
    sample = df.sample(n=min(n_samples, len(df)), random_state=seed)
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    llm = get_llm(temperature=0.0)

    rows = []
    for r in sample.itertuples():
        prompt = ONE_LINE_SUMMARY_PROMPT.format(example=r.summary, text=str(r.text)[:1500])
        generated = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        scores = scorer.score(str(r.summary), generated)
        rows.append(
            {
                "real_summary": r.summary,
                "generated_summary": generated,
                "rouge1_f": scores["rouge1"].fmeasure,
                "rouge2_f": scores["rouge2"].fmeasure,
                "rougeL_f": scores["rougeL"].fmeasure,
            }
        )
        time.sleep(0.3)

    results = pd.DataFrame(rows)
    summary = {
        "n_samples": len(results),
        "rouge1_f_mean": results["rouge1_f"].mean(),
        "rouge2_f_mean": results["rouge2_f"].mean(),
        "rougeL_f_mean": results["rougeL_f"].mean(),
    }
    return {"summary": summary, "details": results}


def evaluate_rag_precision_at_k(
    vectorstore, test_queries: list[dict], k: int = _CFG["rag_precision_k"]
) -> pd.DataFrame:
    """test_queries: [{"query": str, "expected_categories": set[str]}, ...]"""
    rows = []
    for tq in test_queries:
        docs = vectorstore.similarity_search(tq["query"], k=k)
        hits = sum(1 for d in docs if d.metadata.get("category") in tq["expected_categories"])
        rows.append(
            {
                "query": tq["query"],
                "expected_categories": ", ".join(tq["expected_categories"]),
                "retrieved_categories": ", ".join(d.metadata.get("category", "?") for d in docs),
                f"precision_at_{k}": hits / k,
            }
        )
    return pd.DataFrame(rows)


def evaluate_sentiment_vader_vs_llm(
    df: pd.DataFrame, n_samples: int = _CFG["sentiment_eval_n_samples"], seed: int = 42
) -> dict:
    """Compara VADER vs. LLM nos casos onde o sentimento VADER discorda fortemente
    da nota numérica — é justamente onde o léxico fixo tende a errar (sarcasmo,
    elogios pontuais dentro de crítica negativa etc.)."""
    mismatches = df[df["sentiment_mismatch"]].sample(n=min(n_samples, df["sentiment_mismatch"].sum()), random_state=seed)
    llm = get_llm(temperature=0.0)

    rows = []
    for r in mismatches.itertuples():
        prompt = SENTIMENT_LABEL_PROMPT.format(text=str(r.text)[:1500])
        llm_label = llm.invoke([HumanMessage(content=prompt)]).content.strip().lower()
        rows.append(
            {
                "score": r.score,
                "score_label": r.score_label,
                "vader_label": r.sentiment_label,
                "llm_label": llm_label,
                "vader_correct": r.sentiment_label == r.score_label,
                "llm_correct": llm_label == r.score_label,
            }
        )
        time.sleep(0.3)

    results = pd.DataFrame(rows)
    summary = {
        "n_samples": len(results),
        "vader_accuracy_on_mismatches": results["vader_correct"].mean(),
        "llm_accuracy_on_mismatches": results["llm_correct"].mean(),
    }
    return {"summary": summary, "details": results}
