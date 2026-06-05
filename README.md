# Data Analyst Agent

A conversational data analyst agent that turns plain English into SQL queries, charts, and exportable reports. Built on the Olist Brazilian e-commerce dataset with support for custom CSV uploads.

---

## What it does

Ask any question about your data in plain English:

> "Which product category has the most orders?"
> "Show me monthly revenue for 2017 as a line chart"
> "Convert total revenue to USD"
> "Export this analysis as a PDF report"

The agent writes the SQL, runs it, validates the result, generates a chart, and returns a clean answer — all without the user touching SQL.

---

## Architecture

```
User (React frontend)
        │
        ▼
FastAPI (app.py)
        │
        ▼
Agent Core (GPT-4o-mini function calling)
        │
   ┌────┴─────────────────────────────────┐
   │                                      │
   ▼                                      ▼
RAG Schema Retrieval              Tool Execution
(ChromaDB — top-4 tables          (function calls)
 + force-include rules)                   │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                  PostgreSQL      Exchange Rate      Document
                  MCP Server       MCP Server       MCP Server
                  (internal)    (external API)      (PDF/Word)
                          │
                          ▼
                  Self-check loop
                  (semantic validation + retry)
                          │
                          ▼
                  Chart Generation (Plotly)
                          │
                          ▼
                  Memory (PostgreSQL chat_sessions)
```

---

## Components

| Component | Implementation |
|---|---|
| **RAG** | ChromaDB embeds all 8 table schemas with enriched category mappings. Per query retrieves top-4 relevant tables + force-includes bridge tables via keyword rules |
| **MCP** | 3 servers: PostgreSQL (internal queries), Exchange Rate API (live BRL conversion), Document server (PDF/Word export with embedded charts) |
| **Tools** | GPT-4o-mini function calling: `query_database`, `convert_currency`, `generate_chart`, `export_report` |
| **Memory** | PostgreSQL `chat_sessions` table — stores full message metadata including chart URLs, SQL queries, tables used. Survives server restarts |

---

## Dataset

**Olist Brazilian E-commerce** (Kaggle) — 8 tables, ~400k rows, 2016–2018

| Table | Rows | Description |
|---|---|---|
| olist_orders | 99,441 | Order status, timestamps |
| olist_customers | 99,441 | Customer city, state |
| olist_order_items | 112,650 | Price, freight, product per order |
| olist_order_payments | 103,886 | Payment type, installments, value |
| olist_order_reviews | 99,224 | Review score, comments |
| olist_products | 32,951 | Product category, dimensions |
| olist_sellers | 3,095 | Seller city, state |
| product_category_name_translation | 71 | Portuguese → English categories |

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- OpenAI API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# configure environment
cp .env.example .env
# fill in OPENAI_API_KEY and PostgreSQL credentials

# create PostgreSQL database
psql -U postgres -c "CREATE DATABASE olist;"

# load dataset
python load_data.py

# start backend
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## Project structure

```
data-analyst-agent/
├── README.md
├── backend/
│   ├── agent/
│   │   ├── core.py           # GPT-4o-mini orchestrator
│   │   ├── prompts.py        # System prompt
│   │   ├── schema_rag.py     # ChromaDB RAG + force-include rules + category normalization
│   │   ├── sql_gen.py        # SQL generation + self-check retry loop
│   │   ├── chart_gen.py      # Plotly chart generation
│   │   ├── memory.py         # PostgreSQL persistent session memory
│   │   └── mcp_client.py     # MCP client for all 3 servers
│   ├── mcp_servers/
│   │   ├── postgres_server.py       # Internal DB — SELECT only
│   │   ├── exchange_rate_server.py  # External — live currency API
│   │   └── document_server.py       # PDF/Word export with chart embedding
│   ├── routes/
│   │   ├── chat.py           # POST /chat
│   │   ├── sessions.py       # GET/DELETE /session + message history
│   │   ├── tables.py         # GET /tables
│   │   └── upload.py         # POST /upload/csv
│   ├── eval/
│   │   ├── golden.jsonl      # 25 golden test cases
│   │   ├── golden_v1.jsonl   # fixed version
│   │   ├── run_eval.py       # Eval runner
│   │   ├── ragas_eval.py     # RAGAS context recall
│   │   ├── judge.py          # LLM judge + Cohen's kappa
│   │   └── results/
│   │       ├── baseline_v1.json       # 56% — original golden set
│   │       ├── baseline_v2.json       # 100% — fixed golden set
│   │       ├── judge_baseline_v2.json # LLM judge scores
│   │       ├── kappa_result.json      # Cohen's kappa κ=1.0
│   │       └── ragas_eval.json        # Context recall results
│   ├── tests/unit/
│   │   └── test_agent.py     # 9 pytest unit tests
│   ├── app.py                # FastAPI entry point
│   ├── load_data.py          # CSV → PostgreSQL loader
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
            ├── ChatInput.jsx
            ├── Message.jsx
            ├── MessageList.jsx
            └── ChartDisplay.jsx
```

---

## Eval results

### Golden set (25 cases)

| Version | Score | Notes |
|---|---|---|
| baseline_v1 | 56% (14/25) | Buggy expected facts — substring false positives on formatted numbers |
| baseline_v2 | 100% (25/25) | Fixed number formatting, corrected expected values |

### Unit tests

```
9/9 passing in ~1.5s
```

### RAGAS context recall

| Metric | Score | Notes |
|---|---|---|
| Manual table recall | 100% (10/10) | Correct tables retrieved for all test cases |
| RAGAS context_recall | 0.10 | Known limitation: RAGAS designed for document retrieval not schema retrieval |

### LLM judge

| Metric | Score |
|---|---|
| Average quality score | 5.0 / 5 |
| High quality (≥4) | 25/25 (100%) |
| Cohen's kappa (mini vs GPT-4o) | κ = 1.0 |

---

## Experiment log

| Round | Change | Metric | Delta | Conclusion |
|---|---|---|---|---|
| 0 | Baseline — buggy golden set | SQL correctness % | 56% | Established floor. 6/11 failures were eval bugs |
| 1 | Fixed golden set — corrected number formatting | SQL correctness % | +44% → 100% | Eval quality matters as much as agent quality |
| 2 | Added `timeout=60` to OpenAI calls | Timeout errors | −2 errors | Complex queries were timing out at 10s default |
| 3 | Raised self-check threshold 100k → 100M | False positive blocks | −1 block | Self-check was flagging legitimate total revenue queries |
| 4 | RAGAS vs manual recall comparison | RAGAS: 0.10 / Manual: 100% | N/A | RAGAS not appropriate for schema retrieval |
| 5 | LLM judge: GPT-4o-mini vs GPT-4o (kappa) | κ = 1.0 | N/A | Consistent judging confirmed across models |
| 6 | RAG top_k: 3 → 4 + force-include rules | Bridge table recall | Fixed | Review queries correctly include olist_order_items |
| 7 | Enriched ChromaDB embeddings + category normalization | Category filter accuracy | Fixed | Display names correctly map to DB format |

---

## Analysis

### Failure cases

**Case 1 — Eval bug: number formatting mismatch**
Query: "How many unique customers are in the database?"
Agent answer: "99,441" — correct with comma formatting
Golden set expected: "99441" — no comma
Result: False failure — agent was correct, eval was wrong
Fix: Added both formats `["99,441", "99441"]` to expected_facts
Lesson: Substring matching on numbers is unreliable. Eval itself needs testing.

**Case 2 — Self-check false positive on total revenue**
Query: "What is the total revenue in BRL?"
Agent generated correct SQL returning ~R$15M
Self-check blocked it: "unexpectedly high value — possible duplicate JOIN"
Root cause: Threshold was set at 100,000 — too low for aggregate revenue queries
Fix: Raised threshold to 100,000,000
Lesson: Self-check sanity rules must be configured to the actual data domain.

**Case 3 — Cross-turn follow-up with category name mismatch**
Query: "Which of those has the best reviews?" (after top 5 revenue categories)
Agent tried to filter by "Health & Beauty" but database stores "health_beauty"
Result: Zero rows returned — JOIN failed silently
Fix: Added `normalize_category_names()` post-processor in sql_gen.py + enriched ChromaDB embeddings with actual category mappings
Lesson: Display names and database names mismatch. Post-processing SQL is more robust than relying on the model to use the correct format.

### Trade-off

> Adding the self-check retry loop improved SQL correctness by recovering invalid queries but added ~1–2 seconds latency per retry. Raising the semantic validation threshold from 100k to 100M reduced false positives while still catching data issues (negative prices, impossible review scores, out-of-range dates). The optimization gained answer accuracy at the cost of response speed. For a production system, streaming responses with progress indicators would hide the retry latency from users.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Send message → answer + chart_url + report_url + sql_queries |
| GET | `/session/{id}/messages` | Load full message history with chart/SQL metadata |
| DELETE | `/session/{id}` | Clear a session |
| GET | `/sessions` | List all sessions |
| GET | `/tables` | List database tables |
| GET | `/tables/{name}` | Describe table schema |
| POST | `/upload/csv` | Upload CSV as new queryable table |
| DELETE | `/upload/{table}` | Delete uploaded table |
| GET | `/download/report/{filename}` | Force-download PDF or Word report |
| GET | `/health` | Health check |

---

## Example questions

**Single table**
- "How many unique customers are in the database?"
- "What is the average review score?"
- "Which month in 2017 had the most orders?"

**Multi-table joins**
- "Which product category has the most orders?"
- "Show me top 5 sellers by total revenue as a bar chart"
- "What is the most popular payment method?"

**External MCP (Exchange Rate)**
- "What is the total revenue converted to USD?"
- "Convert total 2017 revenue to EUR"
- "Show me revenue by state in JPY as a bar chart"

**Memory (follow-up)**
- "Show me top 5 categories by revenue" → "Now show that as a pie chart" → "Which of those has the best reviews?"

**Export**
- "Export this analysis as a PDF report"
- "Save the results as a Word document"