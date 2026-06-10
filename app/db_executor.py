from typing import Any, Dict, List, Tuple
from sqlalchemy import create_engine, text
from langchain_core.tools import tool
from loguru import logger
import json
import os
from urllib.parse import quote_plus

def _get_engine():
    # read env vars with safe defaults
    raw_user = os.getenv("MYSQL_USER", "")
    raw_password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "")

    # URL-encode user/password so special chars (like @ or :) don't break the URL
    user = quote_plus(raw_user)
    password = quote_plus(raw_password)

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    logger.debug(f"Creating DB engine with url host={host} db={database} (user redacted)")
    return create_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True)

ENGINE = _get_engine()

def execute_sql(sql: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Safe parameterized SQL executor (SELECT only, views only).
    """
    max_rows_env = os.getenv('MYSQL_MAX_ROWS')
    try:
        max_rows = int(max_rows_env) if max_rows_env is not None else None
    except (ValueError, TypeError):
        logger.warning("Invalid MYSQL_MAX_ROWS value, ignoring limit")
        max_rows = None

    params = params or {}

    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries permitted", "rows": [], "row_count": 0}

    try:
        with ENGINE.connect() as conn:
            print(sql)
            result = conn.execute(text(sql), params)
            print("result:", result)
            if max_rows:
                fetched = result.fetchmany(max_rows)
            else:
                fetched = result.fetchall()
            rows = [dict(r._mapping) for r in fetched]
            cols = list(rows[0].keys()) if rows else []
            logger.info(f"SQL executed | rows={len(rows)}")
            return {"rows": rows, "row_count": len(rows), "columns": cols, "error": None}
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        return {"error": str(e), "rows": [], "row_count": 0}
    
@tool
def farmers_market_sql_tool(sql: str, params: str = "{}") -> str:
    """
    Execute a read-only SQL SELECT query against Farmers Market database views.
    sql: parameterized SELECT using :param_name syntax
    params: JSON string of parameter key-value pairs
    """
    try:
        p = json.loads(params) if params else {}
    except Exception:
        p = {}
    result = execute_sql(sql, p)
    return json.dumps(result, default=str)