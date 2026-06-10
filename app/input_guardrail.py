import re
from typing import Dict, Any, List
from app.schema import ALLOWED_VIEWS, VIEWS
from loguru import logger

DESTRUCTIVE_PATTERN = re.compile(
    r"\b(delete|drop|truncate|update|insert|alter|create|shutdown|grant|revoke)\b", re.IGNORECASE
)


def check_guardrails(sanitized_text: str) -> Dict[str, Any]:
    issues: List[str] = []

    # 1. destructive intent
    if DESTRUCTIVE_PATTERN.search(sanitized_text):
        issues.append("Destructive SQL intent detected. Read-only access only.")

    # 2. check which views are mentioned
    mentioned_views = [v for v in ALLOWED_VIEWS if re.search(rf"\b{re.escape(v)}\b", sanitized_text, re.IGNORECASE)]

    # 3. table name mentions (map to views)
    TABLE_TO_VIEW = {
        "customer_purchases": "vw_customer_purchases",
        "customer":           "vw_customer",
        "vendor_inventory":   "vw_vendor_inventory",
        "vendor_market":      "vw_vendor_market",
        "vendor_booth":       "vw_vendor_booth_assignments",
        "zip_data":           "vw_zip_data",
        "product":            "vw_product",
        "vendor":             "vw_vendor",
        "booth":              "vw_booth",
        "market_date_info":   "vw_market_date_info",
    }
    for tbl, view in TABLE_TO_VIEW.items():
        if re.search(rf"\b{re.escape(tbl)}\b", sanitized_text, re.I):
            if view not in mentioned_views:
                mentioned_views.append(view)


    result = {
        "ok": len(issues) == 0,
        "mentioned_views": mentioned_views,
        "issues": issues
    }
    print(f"Guardrail check: {result}")
    logger.info(f"Guardrails | ok={result['ok']} issues={len(issues)}")
    return result