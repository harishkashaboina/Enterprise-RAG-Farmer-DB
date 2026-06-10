from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from loguru import logger
import json
import os

from app.schema import get_schema_prompt

llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL"),
    temperature=0,
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


SYSTEM_PROMPT = """You are an expert MySQL SQL generator for the Farmers Market database.
RULES:
- Generate ONLY SELECT queries
- Use ONLY Views
- Use parameterized placeholders with :param_name syntax
- Always add LIMIT clause (max 500 rows)
- Return valid JSON only
- Return optimized SQL only in terms of memory usage and performance

Output format:
{{"sql": "SELECT ...", "params": {{}}, "explanation": "...", "views_used": [], "confidence": 0.0}}
"""

HUMAN_PROMPT = """Schema:
{schema}

Context:
{context}

User query: {query}

Generate the MySQL SELECT query."""

def generate_sql(query: str, context: str) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT)
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({
            "schema": get_schema_prompt(),
            "context": context,
            "query": query
        })
        logger.info(f"SQL generated | views={result.get('views_used')} confidence={result.get('confidence')}")
        return result
    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        return {"sql": "", "params": {}, "explanation": str(e), "views_used": [], "confidence": 0.0}