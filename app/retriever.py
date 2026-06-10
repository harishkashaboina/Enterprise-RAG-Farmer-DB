from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from app.cache import get_cached_embedding, set_cached_embedding
from loguru import logger
import os 

from dotenv import load_dotenv
load_dotenv()

embeddings_model = OpenAIEmbeddings(
    model=os.getenv("OPENAI_EMBEDDING_MODEL"),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def get_embedding(text: str) -> List[float]:
    cached = get_cached_embedding(text)
    if cached:
        return cached
    emb = embeddings_model.embed_query(text)
    set_cached_embedding(text, emb)
    return emb

def retrieve_context(
    query: str,
    top_k: int = 8
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval from Pinecone: vector search + metadata filter.
    """
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

    embedding = get_embedding(query)

    filter_dict = {}

    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True
    )

    contexts = []
    for match in results.matches:
        contexts.append({
            "id": match.id,
            "score": match.score,
            "text": match.metadata.get("text", ""),
            "view_name": match.metadata.get("view_name", ""),
            "type": match.metadata.get("type", "schema"),
        })
    logger.info(f"Retrieved {len(contexts)} contexts from Pinecone")
    return contexts