# Enterprise RAG — Farmers Market Text-to-SQL

This project is an enterprise-style Retrieval-Augmented Generation (RAG) application for a Farmers Market dataset.
It converts natural language queries into read-only SQL against MySQL views, using semantic retrieval, LLM-driven context optimization, SQL generation, validation, and safe execution.

## Summary

Enterprise RAG pipeline built for secure natural-language query answering over a MySQL-backed Farmers Market dataset.

Key capabilities:
- Natural language to parameterized read-only SQL conversion
- Schema grounding with `app/schema.get_schema_prompt()` during SQL generation
- Pinecone retrieval with OpenAI embeddings for relevant schema/context
- Anthropic LLM for SQL synthesis and OpenAI for retrieval/context optimization
- Redis caching for query results and embedding lookups
- Streamlit UI for query entry, result display, and debugging insights

## Features

- Streamlit UI for entering natural language queries and reviewing results
- Input sanitization and guardrails against SQL injection, prompt injection, and destructive intent
- Vector retrieval from Pinecone using OpenAI embeddings
- LLM-based schema/context optimization and SQL generation
- Redis caching for query results and embeddings
- Secure MySQL execution of SELECT-only queries through SQLAlchemy
- Output redaction for sensitive fields and provenance tracking

## Repository Structure

- `streamlit_app.py` — user interface and pipeline invocation
- `app/graph.py` — pipeline orchestration and state graph definition
- `app/sanitizer.py` — input normalization and threat detection
- `app/input_guardrail.py` — intent and schema-level guardrails
- `app/cache.py` — Redis-backed semantic and embedding cache
- `app/retriever.py` — Pinecone retrieval using OpenAI embeddings
- `app/context_manager.py` — LLM context optimization
- `app/sql_generator.py` — Anthropic-based SQL generation
- `app/sql_validator.py` — SQL safety enforcement
- `app/db_executor.py` — database execution tool for safe SELECT queries
- `app/output_guardrails.py` — result redaction and response formatting
- `app/schema.py` — schema definitions for allowed views
- `scripts/load_pinecone_data_index_schema.py` — schema indexing for Pinecone

## Setup

1. Create a `.env` file with required credentials and configuration values.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

> If you are using Poetry, run `poetry install` instead.

3. Index schema data into Pinecone:

```bash
python scripts/load_pinecone_data_index_schema.py
```

4. Launch the Streamlit app:

```bash
streamlit run streamlit_app.py
```

## Environment Variables

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

## Deployment Guide

1. Create `.env` in the repository root with the required credentials and configuration values.
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

If using Poetry:

```bash
poetry install
```

3. Build the Pinecone index from schema data:

```bash
python scripts/load_pinecone_data_index_schema.py
```

4. Start the Streamlit app:

```bash
streamlit run streamlit_app.py
```

5. Open the Streamlit URL shown in the terminal (typically `http://localhost:8501`).

6. Monitor API usage and logs during execution, especially for OpenAI/Anthropic/Redis/Pinecone connectivity.

For production deployment, containerize the app or host it on a managed service with secure environment variables and network access to MySQL, Redis, and Pinecone.

## Design Notes

The application uses a multi-stage pipeline:

1. Sanitize user text and detect threats
2. Enforce guardrails for destructive intent and allowed views
3. Check Redis semantic cache for prior results
4. Retrieve schema/context from Pinecone
5. Optimize relevant context with an LLM
6. Generate parameterized SQL with Anthropic
7. Validate SQL for safety and add limits
8. Execute safely against MySQL views
9. Apply output redaction and return structured results

## Additional Documentation

See `DESIGN.md` for a more detailed architecture and workflow design document.
