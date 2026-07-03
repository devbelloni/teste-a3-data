# Teste Técnico A3Data — Cientista de Dados (LLM/NLP)

Ferramenta de análise automatizada da base **Amazon Books Reviews**, para uma
editora que hoje leva 5 analistas × 3 dias por ciclo de análise manual. O
projeto cobre EDA, NLP clássico, RAG com LLM e uma API funcional (não só
notebooks), com métricas de qualidade objetivas e uma estimativa de impacto
financeiro.

Contexto completo do desafio, decisões de projeto e detalhamento de cada etapa:
[`docs/plano.md`](docs/plano.md). Apresentação executiva:
[`slides/A3Data_Desafio_Tecnico.pptx`](slides/A3Data_Desafio_Tecnico.pptx).

## O que tem aqui

- **EDA** (`notebooks/01_eda.ipynb`): distribuição de notas, performance por
  autor/gênero, evolução temporal, tamanho de review vs. nota.
- **NLP clássico** (`src/sentiment.py`, `src/reviewer_scoring.py`,
  `src/keywords.py`): sentimento (VADER) vs. nota real, heurística para achar
  "usuários com opiniões relevantes para entrevista", keywords por gênero (TF-IDF).
- **RAG** (`app/rag/`): embeddings locais (`all-MiniLM-L6-v2`) + ChromaDB +
  LangChain + Groq (Llama 3.3 70B) — busca semântica em linguagem natural sobre
  o catálogo, com reescrita de query para melhorar a recuperação.
- **API FastAPI** (`app/`): `POST /perguntar` (RAG), `GET /resumo/livro|autor/{nome}`
  (sumarização via LLM), `GET /reviewers-relevantes` (ranking heurístico).
- **Avaliação de qualidade** (`notebooks/02_avaliacao_qualidade.ipynb`): ROUGE
  da sumarização vs. resumo humano real, precisão@k do RAG, VADER vs. LLM em
  sentimento.
- **Impacto financeiro** (`src/financial_impact.py`): estimativa parametrizada
  de economia por ciclo de análise.

## Arquitetura

```
Books_rating.csv (2.8GB) ──┐
                            ├─→ DuckDB (amostragem estratificada, ~200k linhas)
books_data.csv (181MB) ────┘         │
                                      ▼
                        limpeza + junção (pandas)
                                      │
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                     ▼
         EDA (Jupyter)      NLP clássico (VADER,      Ingestão RAG
                             TF-IDF, heurística)    (embeddings + ChromaDB)
                                      │                     │
                                      └──────────┬──────────┘
                                                  ▼
                                     API FastAPI (LangChain + Groq/Llama 3.3 70B)
                                                  │
                                                  ▼
                                    /perguntar · /resumo · /reviewers-relevantes
```

## Como reproduzir

### 1. Setup

```bash
python -m venv .venv
.venv/Scripts/activate           # Windows
pip install -r requirements.txt
cp .env.example .env             # preencha GROQ_API_KEY (grátis em console.groq.com)
```

### 2. Dados

Baixe `Books_rating.csv` e `books_data.csv` do dataset
[Amazon Books Reviews (Kaggle)](https://www.kaggle.com/datasets/mohamedbakhet/amazon-books-reviews)
e coloque-os na raiz do projeto (não estão no repositório — 2.8GB e 181MB).

### 3. Pipeline (rodar nesta ordem, sempre como módulo a partir da raiz)

```bash
python -m src.data_sampling      # amostragem estratificada via DuckDB
python -m src.data_cleaning      # limpeza + junção com metadados
python -m src.sentiment          # sentimento VADER (gera sample_with_sentiment.parquet)
python -m src.reviewer_scoring   # smoke test da heurística de reviewer
python -m src.keywords           # smoke test de keywords por gênero
python -m app.rag.ingest         # embeddings + indexação no ChromaDB
```

### 4. API

```bash
uvicorn app.main:app --reload
```

Documentação interativa (Swagger): http://127.0.0.1:8000/docs

### 5. Notebooks

```bash
jupyter notebook notebooks/
```

`01_eda.ipynb` só precisa da amostra limpa. `02_avaliacao_qualidade.ipynb` faz
chamadas reais à API da Groq (usa `GROQ_API_KEY`) — leva alguns minutos.

## Hiperparâmetros

Todos os hiperparâmetros do projeto (tamanho de amostra, pesos da heurística de
reviewer, thresholds de sentimento, parâmetros de TF-IDF, modelo de embeddings,
modelo de LLM, tamanhos de amostra das métricas, premissas do impacto
financeiro) estão centralizados em [`config.yaml`](config.yaml), carregado por
`src/config.py` e usado por todos os módulos de `src/` e `app/`.

## Principais resultados

| Frente | Resultado |
|---|---|
| Amostra | 198.924 reviews (de ~3M), 87% com autor identificado, 82% com gênero |
| Sentimento (VADER) | 75,1% de acurácia geral vs. nota real; cai para 0% no recorte "difícil" (12,5% da amostra) |
| Sentimento (LLM) | 63,3% de acurácia no mesmo recorte "difícil" — ganho claro sobre NLP clássico |
| Sumarização (LLM) | ROUGE-1/2/L de 0,21 / 0,05 / 0,21 vs. resumo humano real |
| RAG | Precisão@5 média de 80% (7 queries de teste, 13.661 livros indexados) |
| Impacto financeiro | ~96,7% de redução de custo por ciclo de análise (premissas explícitas em `config.yaml`) |

## Limitações conhecidas / roadmap

- Busca semântica funciona melhor em inglês que em português (corpus majoritariamente
  em inglês) — mitigado com reescrita de query pelo LLM; produção usaria embeddings
  multilíngues nativos.
- Metadados de autor têm duplicidade por variação de nome (ex.: "J. R. R. Tolkien"
  vs. "John Ronald Reuel Tolkien") — bom caso de uso para normalização de entidades
  via LLM em uma próxima fase.
- RAG indexa livros com 3+ reviews na amostra (13.661 livros); produção cobriria o
  catálogo completo com ingestão incremental.

Mais detalhes de planejamento e roadmap completo: [`docs/plano.md`](docs/plano.md)
e o slide de roadmap na apresentação.
