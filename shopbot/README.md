# ShopBot — RAG Product Assistant for zUdyog Fashion

A production-ready RAG chatbot built from Book 1 of *RAG Essentials* using the Pramana Framework.
Two applications work together: a **Python FastAPI backend** (ShopBot) and a **Next.js frontend** (zUdyog Fashion store).

---

## Architecture

```
zudyog-fashion/   ← Next.js storefront + chat widget  (port 3000)
shopbot/          ← FastAPI RAG backend               (port 8000)
```

The Next.js app proxies chat requests to the FastAPI backend at `http://localhost:8000`.
The backend can also be called directly via its REST API.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key (`sk-...`)

---

## 1 — Python Backend (ShopBot API)

### First-time setup

```bash
# from the shopbot/ directory
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set: OPENAI_API_KEY=sk-...

# Verify setup (expect: "Embedding dimensions: 1536")
python test_setup.py

# delet if exits
rm -rf chroma_db/

# Build the vector database (run once; re-run if products.py changes)
python shopbot-ingest/ingest.py
```

### Start the API server

```bash
source venv/bin/activate        # if not already active
python shopbot-agent/api.py
# API running at http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### Quick test

```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Does the anarkali suit come with a dupatta?"}'
```

---

## 2 — Next.js Frontend (zUdyog Fashion)

### First-time setup

```bash
cd zudyog-fashion
npm install
```

### Start the dev server

```bash
cd zudyog-fashion
npm run dev
# Store running at http://localhost:3000
```

The frontend reads `SHOPBOT_API_URL` from the environment (defaults to `http://localhost:8000`).
To point at a different backend, create `zudyog-fashion/.env.local`:

```
SHOPBOT_API_URL=http://localhost:8000
```

---

## 3 — Running Both Together

Open two terminal windows:

**Terminal 1 — backend**

```bash
cd shopbot
source venv/bin/activate
python shopbot-agent/api.py
```

**Terminal 2 — frontend**

```bash
cd shopbot/zudyog-fashion
npm run dev
```

Then open `http://localhost:3000` in your browser. The chat widget in the store calls the backend automatically.

---

## Evaluation (optional)

```bash
source venv/bin/activate
python -m evaluation.evaluate
# Results written to evaluation/results/<run_id>.json
# Approximate cost per run: ~$0.005
```

---

## Deploy

**Backend (Railway):**

```bash
npm install -g @railway/cli
railway login
railway up
# Set OPENAI_API_KEY in Railway's environment variables dashboard
```

Railway reads `Procfile`: `web: cd shopbot-agent && uvicorn api:app --host 0.0.0.0 --port $PORT`

**Frontend:** Deploy `zudyog-fashion/` to Vercel. Set `SHOPBOT_API_URL` to your Railway backend URL.

---

## 4 — MLflow Experiment Tracking (optional)

Requires Docker. Logs eval metrics and live API traces to a local MLflow server.

```bash
# Add to shopbot/.env
MLFLOW_TRACKING_URI=http://localhost:5001

# Start PostgreSQL + MLflow (first run pulls images and initialises schema)
cd shopbot && docker compose up -d

# Open dashboard
open http://localhost:5001
```

After `docker compose up -d`, every `python evaluation/evaluate.py` run logs metrics to
the **shopbot-eval** experiment ("Evaluation runs" in the left sidebar). Every live API
query from the frontend logs a trace ("Traces" in the left sidebar).

---

## Frontend Testing Plan

This plan maps each test scenario to the book chapter that built the behaviour being tested.
Run all three services before starting: backend (port 8000), frontend (port 3000), MLflow (port 5001).

### Start all three services

```bash
# Terminal 1 — MLflow (optional but recommended)
cd shopbot && docker compose up -d

# Terminal 2 — Python backend
cd shopbot
source venv/bin/activate
python shopbot-agent/api.py
# Expect: "MLflow tracing → http://localhost:5001" then "ShopBot ready."

# Terminal 3 — Next.js frontend
cd shopbot/zudyog-fashion
npm run dev
# Expect: "Ready on http://localhost:3000"
```

---

### Test 1 — Backend contract via Swagger UI (Ch. 8)

**What Ch. 8 built:** `shopbot-agent/api.py` — FastAPI with Pydantic validation and auto-generated `/docs`.

1. Open `http://localhost:8000/docs`
2. Expand `POST /ask`
3. Click **Try it out** → paste:

   ```json
   { "question": "Does the anarkali suit come with a dupatta?" }
   ```

4. Click **Execute**

**Expected:** HTTP 200, `answer` field confirms the dupatta is included, `session_id` echoed back.
This confirms the backend is live and the Pydantic schema (`question` required, max 500 chars) is enforced.

---

### Test 2 — Chat widget: grounded product question (Ch. 6 + Ch. 7)

**What Ch. 6 built:** `shopbot-agent/retriever.py` — similarity threshold 0.75, max 3 chunks returned.
**What Ch. 7 built:** `shopbot-agent/prompt.py` — temperature 0, honest system prompt.

1. Open `http://localhost:3000`
2. Click the 💬 button (bottom-right corner) to open the chat drawer
3. Type: `Is the linen co-ord set suitable for summer?`

**Expected:** A specific answer about the linen co-ord set (breathable, lightweight). The retriever
found chunks above the 0.75 threshold; the prompt instructed the LLM to answer only from those chunks.

1. Send the same question a second time.

**Expected:** Identical answer — `temperature=0` guarantees deterministic output (Ch. 7).

---

### Test 3 — Chat widget: out-of-scope question triggers honest response (Ch. 6)

**What Ch. 6 built:** Chunks scoring below `SIMILARITY_THRESHOLD = 0.75` are withheld entirely.
When no chunks pass the threshold, the LLM has no context and must say so honestly.

1. In the chat drawer, type: `Do you sell men's sherwanis?`

**Expected:** ShopBot says it doesn't carry men's clothing (or similar honest deflection). It does
**not** hallucinate a product. The retriever returned nothing above threshold; the prompt's
"do not make up products" constraint held.

1. Type: `Do you offer cash on delivery?`

**Expected:** ShopBot says it doesn't have information about payment methods and directs the customer
to `support@example.com`. The catalog has no payment or shipping data — no chunks pass the 0.75
threshold, so the prompt's honesty constraint kicks in.

Note: return policy questions ₹(e.g., "What is your return policy for the silk saree?")₹ are **in scope** —
every product in `shopbot-ingest/data/products.py` has `return_policy` and `exchange_policy` fields that are chunked
and indexed. ShopBot will answer those correctly from the retrieved chunks.

---

### Test 4 — AskAI button on a product page (Ch. 8 frontend integration)

**What Ch. 8 built:** The FastAPI endpoint any frontend can call. The Next.js store proxies
`/api/chat` → `http://localhost:8000/ask` via `SHOPBOT_API_URL`.

1. Open `http://localhost:3000/products`
2. Click on any product (e.g., Breathable Cotton Kurta)
3. On the product detail page, click **Ask AI**

**Expected:** The chat drawer opens with a prefilled question: `Tell me more about the Breathable Cotton Kurta`.
ShopBot answers with details from the product data — fabric, occasions, care — without hallucinating.

1. While the drawer is open, ask a follow-up: `Does the Breathable Cotton Kurta come in blue?`

**Expected:** ShopBot confirms it is available in sky blue (along with white and mint green), retrieved
from the variants chunk.

**Important — include the product name in every follow-up.** Book 1 has no session memory. Each
query is independent: the retriever does not know the previous question was about the Breathable Cotton
Kurta. If you ask `Does it come in blue?` without naming the product, the retriever interprets it as
a fresh colour query and returns whichever catalog products mention blue — in testing this returned
suit chunks (Rayon Printed Suit, Cotton Straight Suit, Straight Cut Palazzo Suit), not the kurta.
Conversational memory is a Book 2 topic.

---

### Test 5 — Verify live API trace in MLflow (Ch. 8 + MLflow tracing)

**What Ch. 8 built:** `mlflow.langchain.autolog()` in the FastAPI lifespan patches LangChain to
record every chain call as a nested trace (VectorStoreRetriever span + ChatOpenAI span).

1. Send at least one question via the chat widget (Test 2 or 4 above)
2. Open `http://localhost:5001`
3. In the left sidebar, click **Traces**
4. Find the trace for your question

**Expected:** One trace entry per question. Expanding it shows two child spans:

- `VectorStoreRetriever` — time taken to retrieve chunks from ChromaDB
- `ChatOpenAI` — time taken for gpt-4o-mini to generate the answer

Token counts and latency are visible per span. A question that returns no chunks
(e.g., men's sherwanis) will show the retriever span with zero documents.

---

### Test 6 — Verify evaluation run in MLflow (Ch. 9)

**What Ch. 9 built:** `evaluation/evaluate.py` — RAGAS faithfulness + context precision over
20 labelled queries, logged as a named run in MLflow.

1. Run the evaluator (costs ~$0.002):

   ```bash
   cd shopbot
   source venv/bin/activate
   python evaluation/evaluate.py
   ```

2. Open `http://localhost:5001`
3. In the left sidebar, click **Evaluation runs**
4. Click the most recent run under **shopbot-eval**

**Expected:** Run shows these metrics (values are from Book 1 baseline runs):

| Metric | Expected range |
| --- | --- |
| `faithfulness` | 0.69 – 0.75 |
| `context_precision` | 0.64 – 0.66 |
| `queries_retrieved` | 19 – 20 |
| `total_cost_usd` | 0.0019 – 0.0021 |

Parameters logged: `model_embed`, `model_llm`, `ragas_version`, `similarity_threshold`, `max_results`, `total_queries`.

---

### What each test verifies

| Test | Chapter | Component tested |
| --- | --- | --- |
| 1 — Swagger UI | Ch. 8 | FastAPI schema, Pydantic validation |
| 2 — Grounded answer | Ch. 6 + Ch. 7 | Retriever threshold 0.75, temperature=0 |
| 3 — Honest deflection | Ch. 6 + Ch. 7 | Below-threshold withheld, honest prompt |
| 4 — AskAI button | Ch. 8 | Next.js proxy, prefill flow |
| 5 — Live traces | Ch. 8 | `mlflow.langchain.autolog()` |
| 6 — Eval run | Ch. 9 | RAGAS scores logged to MLflow |
