import re
import sqlparse
from typing import Dict, Any
from loguru import logger

FORBIDDEN_STATEMENTS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE
)

def validate_sql(sql: str, params: Dict = None) -> Dict[str, Any]:
    issues = []

    if not sql or not sql.strip():
        return {"ok": False, "issues": ["Empty SQL"]}

    # 1. only SELECT
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        issues.append("SQL must start with SELECT.")

    # 2. no forbidden statements
    if FORBIDDEN_STATEMENTS.search(stripped):
        issues.append("Forbidden SQL statement detected.")

    # 3. no multiple statements
    parsed = sqlparse.parse(stripped)
    if len(parsed) > 1:
        issues.append("Multiple SQL statements are not allowed.")

    # # 4. must reference at least one allowed view
    # sql_upper = stripped.upper()
    # used_views = [v for v in ALLOWED_VIEWS if v.upper() in sql_upper]
    # if not used_views:
    #     issues.append("Query must reference at least one allowed view.")

    sql_upper = stripped.upper()
    # 5. must have LIMIT
    if "LIMIT" not in sql_upper:
        sql = stripped.rstrip(";") + " LIMIT 500"
        logger.warning("LIMIT clause added automatically")

    # 6. no subquery injection
    if stripped.count("(") > 5:
        issues.append("Query too complex - too many nested subqueries.")

    result = {
        "ok": len(issues) == 0,
        "sql": sql,
        "issues": issues
    }
    logger.info(f"SQL validated | ok={result['ok']}")
    return result