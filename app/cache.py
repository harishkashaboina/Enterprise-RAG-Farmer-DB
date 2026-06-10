import json
import hashlib
import redis
from typing import Dict, Optional, Any, List
from loguru import logger
from dotenv import load_dotenv
import os


load_dotenv()

redis_url = os.getenv("REDIS_URL")
redis_ttl_seconds = int(os.getenv("REDIS_TTL_SECONDS", "3600"))

_redis: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(redis_url, decode_responses=True)
    return _redis

# ── Embedding cache ───────────────────────────────────────────────────────────
def get_cached_embedding(text: str) -> Optional[List[float]]:
    key = f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
    val = get_redis().get(key)
    if val:
        logger.debug("Embedding cache HIT")
        return json.loads(val)
    return None

def set_cached_embedding(text: str, embedding: List[float]) -> None:
    key = f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
    get_redis().setex(key, redis_ttl_seconds * 4, json.dumps(embedding))

# ── Semantic query result cache ───────────────────────────────────────────────
def _sem_key(query_hash: str) -> str:
    return f"semcache:{query_hash}"

def get_cached_result(query_hash: str) -> Optional[Dict[str, Any]]:
    key = _sem_key(query_hash)
    val = get_redis().get(key)
    print('val:', val)
    if val:
        logger.info(f"Semantic cache HIT | key={key[:20]}")
        return json.loads(val)
    logger.debug("Semantic cache MISS")
    return None

def set_cached_result(query_hash: str, result: Dict[str, Any]) -> None:
    key = _sem_key(query_hash)
    get_redis().setex(key, redis_ttl_seconds, json.dumps(result, default=str))
    logger.info(f"Semantic cache SET | key={key[:20]}")

def invalidate_cache(pattern: str = "semcache:*") -> int:
    r = get_redis()
    keys = r.keys(pattern)
    if keys:
        return r.delete(*keys)
    return 0