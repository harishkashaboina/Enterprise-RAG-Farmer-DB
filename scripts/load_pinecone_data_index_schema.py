"""
Run once to index the Farmers Market schema into Pinecone.
Usage: uv run python scripts/index_schema.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from app.schema import VIEWS

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
embed = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL"), openai_api_key=os.getenv("OPENAI_API_KEY"))
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
# create index if needed
existing = [i.name for i in pc.list_indexes()]
if pinecone_index_name not in existing:
    pc.create_index(
        name=pinecone_index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("Index created, waiting 30s...")
    time.sleep(30)

index = pc.Index(pinecone_index_name)

docs = []
for view_name, meta in VIEWS.items():
    # schema doc
    text = (
        f"View: {view_name}\n"
        f"Description: {meta['description']}\n"
        f"Columns: {', '.join(meta['columns'])}\n"
        f"Sample questions: {'; '.join(meta.get('sample_questions', []))}"
    )
    docs.append({"id": f"schema_{view_name}", "text": text, "view_name": view_name, "type": "schema"})

    # per-column docs
    for col in meta["columns"]:
        col_text = f"Column '{col}' in view '{view_name}': {meta['description']}"
        docs.append({"id": f"col_{view_name}_{col}", "text": col_text, "view_name": view_name, "type": "column"})

    # sample question docs
    for i, q in enumerate(meta.get("sample_questions", [])):
        docs.append({"id": f"qa_{view_name}_{i}", "text": q, "view_name": view_name, "type": "sample_question"})

print(f"Indexing {len(docs)} documents...")
print(docs)
batch_size = 50
for i in range(0, len(docs), batch_size):
    batch = docs[i:i + batch_size]
    texts = [d["text"] for d in batch]
    embeddings = embed.embed_documents(texts)
    vectors = [(d["id"], e, {"text": d["text"], "view_name": d["view_name"], "type": d["type"]})
               for d, e in zip(batch, embeddings)]
    index.upsert(vectors=vectors)
    print(f"  Upserted {i+len(batch)}/{len(docs)}")

print("✅ Schema indexed successfully.")