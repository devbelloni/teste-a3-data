"""
Orquestra o pipeline completo de pré-processamento, do zero, na ordem correta.
Rode este script sempre que Books_rating.csv e/ou books_data.csv mudarem
(nova exportação, atualização mensal, etc.) — ele regenera tudo que os outros
módulos (API, notebooks) consomem.

Uso:
    python -m scripts.run_pipeline              # roda tudo
    python -m scripts.run_pipeline --skip-rag    # pula a reindexação no ChromaDB
                                                  # (mais lenta; pule se só quer
                                                  # atualizar EDA/NLP clássico)

Pode ser agendado (Windows Task Scheduler, cron, Airflow, GitHub Actions) para
rodar automaticamente quando os CSVs de origem forem substituídos.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_step(name: str, fn) -> None:
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    start = time.time()
    fn()
    print(f"[OK] {name} — {time.time() - start:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-rag", action="store_true",
                         help="pula a reindexação no ChromaDB (etapa mais lenta)")
    args = parser.parse_args()

    for csv_name in ("Books_rating.csv", "books_data.csv"):
        if not (ROOT / csv_name).exists():
            print(f"ERRO: {csv_name} não encontrado na raiz do projeto ({ROOT}). "
                  f"Baixe o dataset e coloque os CSVs lá antes de rodar o pipeline.")
            sys.exit(1)

    from src import data_sampling, data_cleaning, sentiment

    _run_step("1/4 — Amostragem estratificada (DuckDB)", data_sampling.sample_ratings)
    _run_step("2/4 — Limpeza e junção com metadados", data_cleaning.build_clean_sample)
    _run_step("3/4 — Sentimento (VADER)", sentiment.run)

    if args.skip_rag:
        print("\n--skip-rag: pulando reindexação no ChromaDB.")
    else:
        from app.rag import ingest
        _run_step("4/4 — Reindexação RAG (embeddings + ChromaDB)", ingest.ingest)

    print("\nPipeline concluído. Reinicie a API (uvicorn app.main:app --reload) "
          "para servir os dados atualizados.")


if __name__ == "__main__":
    main()
