# Plano — Teste Técnico A3Data (Cientista de Dados LLM/NLP)

## Contexto

O desafio (PDF em `desafio_tecnico_sr_a3data_-_llm_atualizado_(2) (1) (1).pdf`) pede uma
ferramenta que ajude uma editora a explorar avaliações de livros — entender performance
de autor/gênero e encontrar usuários com opiniões relevantes para entrevista — reduzindo
o tempo de análise manual (hoje: 5 analistas × 3 dias, salário R$5.000).

Dados disponíveis na raiz do projeto:
- `books_data.csv` (~181MB): metadados de livros — `Title, description, authors, image,
  previewLink, publisher, publishedDate, infoLink, categories, ratingsCount`.
- `Books_rating.csv` (~2.8GB, ~3M linhas): reviews — `Id, Title, Price, User_id,
  profileName, score, time, summary, text`. Importante: `summary` é um resumo humano
  real de cada review — serve como **referência gold para avaliar sumarização (ROUGE)**.

Decisões já confirmadas com o usuário:
- Volume: **amostra representativa** dos dados (não a base completa de 2.8GB).
- Stack: **Python**.
- Entregável de slides: **arquivo .pptx** gerado via `python-pptx`.
- **LLM/RAG**: reaproveitar a arquitetura do projeto pessoal do usuário
  [devbelloni/RAG-with-FastAPI](https://github.com/devbelloni/RAG-with-FastAPI) —
  LangChain + ChromaDB + embeddings locais (`sentence-transformers/all-MiniLM-L6-v2`) +
  **Groq (Llama 3.3 70B)** como LLM via API gratuita. O usuário forneceu a API key do
  Groq (guardada em `.env`, fora do git).
- **POC como API real**: o entregável de código não é só notebooks, é uma **API FastAPI**
  que a editora poderia efetivamente usar — atende diretamente ao pedido do desafio
  ("a editora gostaria de uma ferramenta que agilizasse este processo").

## Estrutura do projeto

```
Desafio A3/
  .venv/                          (não versionado)
  docs/
    plano.md                      # este documento
  data/
    raw/                          (CSVs originais, gitignored — grandes demais pro GitHub)
    processed/sample_reviews.parquet  (amostra tratada, versionada se < ~50MB, senão script p/ gerar)
  src/
    data_sampling.py              # lê os CSVs grandes via DuckDB, gera amostra estratificada
    data_cleaning.py              # parsing de listas (authors/categories), tipos, merge
    eda.py                        # gráficos e estatísticas descritivas
    sentiment.py                  # sentimento clássico (VADER) vs score numérico
    reviewer_scoring.py           # heurística p/ achar "usuários com opiniões relevantes"
    metrics.py                    # métricas de qualidade consolidadas (ROUGE, precisão@k, sentimento)
  app/                             # API FastAPI — a "ferramenta" pedida pelo desafio
    main.py                       # entrypoint FastAPI
    core/
      config.py                   # carrega GROQ_API_KEY do .env
      llm.py                      # wrapper do LLM (langchain-groq, Llama 3.3 70B)
    rag/
      ingest.py                   # embeddings (all-MiniLM-L6-v2) + indexação no ChromaDB
      chain.py                    # chain LangChain de RAG (retriever + prompt + LLM)
    routers/
      qa.py                       # POST /perguntar — pergunta em linguagem natural (RAG)
      summarization.py            # GET /resumo/{autor|livro} — sumarização via LLM
      reviewers.py                # GET /reviewers-relevantes — ranking p/ entrevista
  chroma_db/                      # índice vetorial gerado, gitignored
  notebooks/
    01_eda.ipynb                  # EDA interativa (exploração livre + gráficos)
    02_avaliacao_qualidade.ipynb  # ROUGE da sumarização, precisão@k do RAG
  outputs/figures/                # PNGs exportados dos gráficos p/ usar nos slides
  slides/
    build_deck.py                 # gera o .pptx programaticamente
    A3Data_Desafio_Tecnico.pptx   # entregável final
  requirements.txt
  .env.example                    # placeholder de GROQ_API_KEY (sem a key real)
  README.md
  .gitignore                      # .env, .venv/, chroma_db/, data/raw/*.csv
```

## Etapas de execução

### 1. Setup do ambiente ✅
- Criar venv em `.venv`.
- `requirements.txt` com: pandas, numpy, pyarrow, duckdb (leitura eficiente do CSV de
  2.8GB sem estourar RAM), matplotlib, seaborn, scikit-learn, nltk, vaderSentiment,
  keybert, rouge-score, python-pptx, wordcloud, jupyter, fastapi, uvicorn, langchain,
  langchain-groq, langchain-community, langchain-chroma, chromadb,
  sentence-transformers, python-dotenv.
- Instalar tudo e validar imports.

### 2. Amostragem e limpeza dos dados
- Usar **DuckDB** para consultar `Books_rating.csv` direto do disco (sem carregar 2.8GB
  em memória) e extrair uma amostra estratificada (~150k–250k reviews), balanceando por
  faixa de `score` e por presença de `categories` (via join com `books_data.csv`), para
  garantir diversidade de gêneros/autores na amostra.
- Parsing de `authors` e `categories` (strings tipo `['Nome']` → listas reais).
- Tratar nulos (`price`, `categories`, `ratingsCount`), duplicatas, datas.
- Salvar `data/processed/sample_reviews.parquet`.

### 3. Análise exploratória (EDA) — feita no Jupyter
- `notebooks/01_eda.ipynb`.
- Distribuição de notas (score), por ano, por gênero, por autor.
- Top autores/gêneros por volume e por nota média (com filtro de volume mínimo, pra
  evitar outliers de 1 review).
- Distribuição de tamanho de review, relação entre tamanho/sentimento e score.
- Tendência temporal de volume de reviews.
- Exporta gráficos para `outputs/figures/`.

### 4. NLP clássico
- **Sentimento** (VADER, leve e sem download de modelo pesado) comparado ao `score`
  numérico → identifica discrepâncias (texto muito negativo com nota alta e vice-versa),
  que é um insight de negócio (reviews "estranhas" valem investigação).
- **Reviewer scoring**: heurística combinando tamanho do texto, especificidade
  (diversidade lexical), intensidade de sentimento e discrepância vs. média do livro,
  para rankear "usuários com opiniões relevantes para entrevista" por autor/gênero —
  isso ataca diretamente um dos pedidos do problema de negócio.
- **Keywords por gênero/autor** via TF-IDF ou KeyBERT.

### 5. Ingestão para RAG (`app/rag/ingest.py`)
- Embeddings locais (`sentence-transformers/all-MiniLM-L6-v2`, mesma escolha do projeto
  RAG-with-FastAPI do usuário) sobre descrições de livros + reviews/resumos agregados por
  livro.
- Indexação no **ChromaDB** local (mesmo padrão do repo de referência).
- API key do Groq em `.env` (nunca commitada — `.env` entra no `.gitignore`; sobe só
  `.env.example`).

### 6. API FastAPI (a "ferramenta" pedida no desafio)
- `POST /perguntar`: pergunta em linguagem natural (ex. "quais livros de fantasia os
  leitores mais elogiaram?") → RAG com ChromaDB + **Groq/Llama 3.3 70B** via
  `langchain-groq`, no mesmo padrão do RAG-with-FastAPI.
- `GET /resumo/{autor|livro}`: agrega reviews de um autor/livro e usa o LLM (Groq) para
  gerar um "resumo do que os leitores estão dizendo" — sumarização real via LLM de API
  gratuita, não modelo local pequeno.
- `GET /reviewers-relevantes/{autor|genero}`: retorna o ranking de reviewers mais
  relevantes (heurística da etapa 4), atacando diretamente o pedido de "buscar usuários
  com opiniões relevantes para uma entrevista".
- Swagger automático do FastAPI serve como demo interativa na apresentação/entrevista.
- Nos slides, documento a arquitetura de produção (ingestão contínua, vector DB
  gerenciado, monitoramento de custo/latência do LLM) como roadmap além do POC.

### 7. Métricas de qualidade (item h) — `notebooks/02_avaliacao_qualidade.ipynb`
- Sentimento: acurácia do sentimento derivado do texto (VADER) vs. bucket de score real.
- Sumarização: ROUGE-1/2/L comparando o resumo gerado pelo LLM com o campo `summary`
  humano real do dataset (referência gold já existente nos dados).
- RAG: precisão@k em um pequeno conjunto de queries de teste feitas à mão contra
  respostas/documentos esperados.

### 8. Estimativa de impacto financeiro (item i)
- Custo atual: 5 analistas × 3 dias × taxa diária (a partir de R$5.000 — vou deixar a
  suposição explícita: se é salário mensal ou por ciclo de análise, pois o PDF é ambíguo;
  vou assumir R$5.000/mês por analista e derivar custo por ciclo de 3 dias, deixando a
  fórmula visível no slide para poder ajustar ao vivo na entrevista).
- Com a ferramenta: tempo de execução do pipeline (minutos/poucas horas) + tempo de
  revisão humana dos insights — estimo redução percentual de tempo/custo e valor
  economizado por ciclo/mês/ano, com analistas realocados para outras frentes.

### 9. Geração do PPTX
- `slides/build_deck.py` usa `python-pptx` para montar automaticamente o deck com os
  itens a–j pedidos no PDF (desafio, roadmap, processo, hipóteses, EDA, sumarização,
  RAG, métricas, impacto financeiro, POC), inserindo os gráficos gerados na etapa 3 e
  números calculados nas etapas anteriores.

### 10. Preparação do repositório GitHub
- `git init`, `.gitignore` (excluindo `data/raw/*.csv`, `.venv/`, checkpoints de modelo),
  README explicando o problema, como reproduzir, e estrutura do projeto.
- Criação do repositório remoto no GitHub e push serão feitos apenas com autorização
  explícita do usuário na hora.

## Verificação
- Cada script em `src/` roda de forma independente e imprime/loga métricas-chave.
- Notebooks reexecutáveis do zero (`Restart & Run All`) sem erro.
- API FastAPI sobe com `uvicorn app.main:app --reload` e responde nos 3 endpoints
  (`/perguntar`, `/resumo/...`, `/reviewers-relevantes/...`) via Swagger (`/docs`).
- `slides/A3Data_Desafio_Tecnico.pptx` abre corretamente e contém todas as seções a–j.
- Números do slide de impacto financeiro batem com os cálculos em `src/metrics.py`.
