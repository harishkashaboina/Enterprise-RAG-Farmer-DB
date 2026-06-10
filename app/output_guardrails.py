import re
from typing import Dict, Any, List
from loguru import logger

PII_COLUMN_NAMES = {"customer_first_name", "customer_last_name", "customer_zip",
                    "customer_zip_masked", "vendor_owner_first_name", "vendor_owner_last_name"}

def redact_row(row: Dict) -> Dict:
    out = {}
    for k, v in row.items():
        if k.lower() in PII_COLUMN_NAMES:
            out[k] = "[REDACTED]"
        elif isinstance(v, str) and re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", v):
            out[k] = "[EMAIL_REDACTED]"
        else:
            out[k] = v
    return out

def apply_output_guardrails(
    rows: List[Dict],
    sql: str,
    explanation: str
) -> Dict[str, Any]:
    redacted_rows = [redact_row(r) for r in rows]
    redactions = sum(
        1 for row in redacted_rows
        for v in row.values()
        if isinstance(v, str) and "REDACTED" in v
    )
    result = {
        "rows": redacted_rows,
        "row_count": len(redacted_rows),
        "columns": list(redacted_rows[0].keys()) if redacted_rows else [],
        "sql_used": sql,
        "explanation": explanation,
        "redactions_applied": redactions,
        "provenance": "Farmers Market DB via read-only views",
    }
    logger.info(f"Output guardrails | rows={len(rows)} redactions={redactions}")
    return result