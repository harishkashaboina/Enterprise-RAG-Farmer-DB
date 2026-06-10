from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from loguru import logger
import json
import os
llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))


def rewrite_query(query: str, error: str, context: str) -> dict:

    REWRITE_PROMPT = PromptTemplate.from_template("""
    You are a query rewriter for a Farmers Market database. Understand the error {error} which is caused by original query {query}, 
    and rewrite a query that addresses this error using context. 
    Given the user's natural language query, rewrite it to be:
    1. More specific and unambiguous
    2. Use correct column/view names from the schema
    3. Expand abbreviations (e.g. "last year" → specific year)
    4. Remove filler words

    Original query: {query}

    Error: {error}

    Context: {context}

    Respond with JSON only:
    {{"rewritten_query": "...", "extracted_constraints": {{"date_range": null, "views": [], "aggregation": null}}, "confidence": 0.0}}
    """)
    chain = REWRITE_PROMPT | llm
    try:
        response = chain.invoke({"query": query, "schema": context})
        result = json.loads(response.content.strip())
        logger.info(f"Query rewritten | confidence={result.get('confidence', 0)}")
        return result
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}")
        return {"rewritten_query": query, "extracted_constraints": {}, "confidence": 0.5}