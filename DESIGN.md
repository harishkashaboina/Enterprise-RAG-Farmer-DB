# Enterprise RAG — Technical Design Document

## 1. Overview

This repository implements an enterprise-ready Retrieval-Augmented Generation (RAG) pipeline for a Farmers Market dataset, focused on converting natural language questions into read-only SQL queries and returning structured results.

The system stitches together:
- Streamlit UI for query entry and result display
- Input sanitization and security guardrails
- Semantic retrieval using Pinecone + OpenAI embeddings
- LLM-powered context optimization and SQL generation
- SQL validation and safe execution against MySQL views
- Redis caching for result reuse
- Output redaction guardrails for PII protection

## 2. Architecture

### 2.1 Key components

- `streamlit_app.py`
  - User-facing web application
  - Collects natural language query
  - Triggers pipeline execution via `GRAPH.invoke(...)`
  - Displays results, SQL, pipeline internals, and provenance

- `app/graph.py`
  - Defines the pipeline as a state graph using `langgraph`
  - Orchestrates node execution order and conditional routing
  - Uses `langsmith.traceable` for observability

- `app/sanitizer.py`
  - Normalizes user input
  - Detects prompt injection, SQL-injection patterns, and PII candidates
  - Computes query hash for caching

- `app/input_guardrail.py`
  - Applies restricted intent rules
  - Blocks destructive SQL intent
  - Maps recognized table names to allowed read-only views

- `app/cache.py`
  - Redis-backed cache for semantics and embeddings
  - Stores query results and embedding lookups

- `app/retriever.py`
  - Computes embeddings with OpenAI
  - Retrieves top schema/context entries from Pinecone

- `app/context_manager.py`
  - Uses OpenAI chat completion to prune and optimize retrieved context
  - Returns concise schema/context relevant to the query

- `app/sql_generator.py`
  - Uses Anthropic chat model to generate parameterized MySQL SELECT SQL
  - Requires only allowed views, JSON output, `:param_name` placeholders, and a LIMIT clause

- `app/sql_validator.py`
  - Validates generated SQL
  - Enforces SELECT-only semantics and disallows dangerous statements
  - Auto-appends `LIMIT 500` when missing

- `app/db_executor.py`
  - Executes SQL safely against MySQL using SQLAlchemy
  - Only allows SELECT queries
  - Returns rows and metadata

- `app/output_guardrails.py`
  - Redacts sensitive fields in returned rows
  - Adds provenance metadata and row counts

- `scripts/load_pinecone_data_index_schema.py`
  - One-time schema indexing script for Pinecone
  - Uploads view docs, columns, and sample questions into the vector index

## 3. Data Model and Schema

The system is centered around read-only views defined in `app/schema.py`.

Views include:
- `vw_booth`
- `vw_customer`
- `vw_customer_purchases`
- `vw_market_date_info`
- `vw_product`
- `vw_product_category`
- `vw_vendor`
- `vw_vendor_booth_assignments`
- `vw_vendor_inventory`
- `vw_vendor_market`
- `vw_zip_data`

Each view includes:
- `description`
- `columns`
- sample questions for retrieval relevance

This schema is used for:
- retrieval metadata
- prompt grounding
- query guardrails

## 4. Pipeline Workflow

The runtime workflow is defined in `app/graph.py`.

### 4.1 End-to-end flow

1. **User submits query** from `streamlit_app.py`
2. **Sanitize input** (`app/sanitizer.py`)
   - Normalize text
   - Remove control chars
   - Detect PII, prompt injection, SQL injection
   - Generate stable `query_hash`
3. **Apply guardrails** (`app/input_guardrail.py`)
   - Block destructive intent
   - Collect mentioned views
4. **Semantic cache check** (`app/cache.py`)
   - If cache hit: return cached response immediately
5. **Retrieve context** (`app/retriever.py`)
   - Embed query with OpenAI
   - Query Pinecone for top matched schema/context entries
6. **Optimize context** (`app/context_manager.py`)
   - Use OpenAI to prune and keep only relevant schema/context
7. **Generate SQL** (`app/sql_generator.py`)
   - Use Anthropic to emit JSON with SQL, params, explanation, and confidence
8. **Validate SQL** (`app/sql_validator.py`)
   - Confirm SELECT-only semantics
   - Prevent dangerous statements and multiple queries
   - Ensure LIMIT is present
9. **Execute SQL** (`app/db_executor.py`)
   - Run query against MySQL database views
   - Fetch row set and row metadata
10. **Apply output guardrails** (`app/output_guardrails.py`)
   - Redact PII fields
   - Build final structured response
   - Store response in Redis semantic cache
11. **Return response**
   - UI displays rows, SQL, explanation, provenance, and optional pipeline debugging

### 4.2 Conditional behavior

- If sanitization or guardrail checks fail, the pipeline stops early and returns an error.
- If semantic cache contains the query result, the pipeline bypasses retrieval, generation, validation, and execution.
- If SQL execution fails, the graph attempts a rewrite via `app/query_rewriter.py`.


## 5. Integration Points

### External services

- OpenAI
  - Text embeddings for retrieval (`OPENAI_EMBEDDING_MODEL`)
  - Context optimization (`OPENAI_MODEL`)
  - Query rewriting (`OPENAI_MODEL`)

- Anthropic
  - SQL generation (`ANTHROPIC_MODEL`)

- Pinecone
  - Schema/context vector store for retrieval
  - Index name configured via `PINECONE_INDEX_NAME`

- Redis
  - Caches embeddings and query results
  - Configured via `REDIS_URL`

- MySQL
  - Executes generated SQL
  - Configured via `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`

### Environment variables

The repository expects runtime configuration from `.env` or environment:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`
- `REDIS_URL`
- `REDIS_TTL_SECONDS`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_MAX_ROWS`

## 6. Security and Safety Controls

The system includes multiple protection layers:

- **Input Sanitization**
  - Normalizes and trims user text
  - Detects SQL injection patterns
  - Detects prompt injection phrases
- **Guardrails**
  - Disallows destructive intent
  - Restricts operations to read-only views
- **SQL Validation**
  - Allows only `SELECT`
  - Disallows dangerous statements and multi-statement payloads
  - Automatically enforces `LIMIT`
- **Output Redaction**
  - Masks PII-like fields such as names and email addresses
  - Tracks number of redacted values
- **Caching**
  - Uses query hash for deterministic cache lookups
  - Ensures identical queries reuse safe cached results

## 7. Deployment and Usage

Run the app with Streamlit using the workspace root:

```bash
streamlit run streamlit_app.py
```

Before running:
- populate `.env` with required API keys and DB/Redis connection info
- create and populate the Pinecone index via the script in `scripts/load_pinecone_data_index_schema.py`
- ensure the MySQL database is reachable and contains the read-only views described in `app/schema.py`

## 8. Component Workflow Diagram (Text)

```
User query
   ↓
Sanitizer → Guardrails → Cache check
                    ↘ cache hit → Return cached response
                    ↘ cache miss → Retriever → Context optimizer → SQL generator → SQL validator → DB executor
                                                                                 ↘ execute error → Query rewriter → SQL validator
                                                                                 ↘ success → Output guardrails → Return response
```
