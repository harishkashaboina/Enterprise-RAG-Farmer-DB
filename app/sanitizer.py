import re
import unicodedata
import hashlib
from typing import Dict, Any
from loguru import logger

PII_PATTERNS = {
    "email":       re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone":       re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn":         re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

SQL_INJECTION_PATTERNS = re.compile(
    r"(--|;|/\*|\*/|xp_|EXEC\s+|UNION\s+SELECT|DROP\s+TABLE|INSERT\s+INTO|"
    r"DELETE\s+FROM|UPDATE\s+\w+\s+SET|ALTER\s+TABLE|CREATE\s+TABLE|"
    r"\bor\b\s+\d+=\d+|#|\bdrop\b\s+\btable\b|\btruncate\b\s+\btable\b)",
    re.IGNORECASE
)


PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|previous) instructions", re.IGNORECASE),
    re.compile(r"you are now (a|an) sql", re.IGNORECASE),
    re.compile(r"reveal (system|prompt|schema)", re.IGNORECASE),
    re.compile(r"bypass (restrictions|rules|filters)", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 2000

def sanitize_input(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {"ok": False, "error": "Empty input", "text": ""}

    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
        logger.warning("Input truncated to max length")

    # unicode normalize + strip control chars
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"[\x00-\x1f\x7f]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # detect PII
    pii_flags = {k: bool(p.search(t)) for k, p in PII_PATTERNS.items()}
    pii_detected = any(pii_flags.values())

    # detect SQL injection
    injection_detected = bool(SQL_INJECTION_PATTERNS.search(t))

    prompt_injection_detected = any(p.search(t) for p in PROMPT_INJECTION_PATTERNS)

    query_hash = hashlib.sha256(t.lower().encode("utf-8")).hexdigest()

    result = {
        "ok": not injection_detected and not prompt_injection_detected,
        "text": t,
        "pii": pii_flags,
        "pii_detected": pii_detected,
        "injection_detected": injection_detected,
        "query_hash": query_hash,
        "length": len(t),
        "error": "SQL injection pattern detected" if injection_detected else None,
    }
    print(f"Sanitized input: {result}")
    logger.info(f"Sanitized input | hash={query_hash[:8]} pii={pii_detected} injection={injection_detected}")
    return result