# src/ingest.py
# Source: Book 1, Chapter 4 + Chapter 5 (Appendix A — Code Wiring)
# Reads the product catalog, converts each product into chunks,
# embeds all chunks in a single API call, and stores them in ChromaDB.
# Run once to build the Grounding Layer.
# Re-run whenever the catalog changes — get_or_create_collection is safe to repeat.

import sys
import chromadb
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

from data.products import PRODUCTS
from src.chunker import product_to_chunks

load_dotenv()

force = "--force" in sys.argv

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="zudyog_products",
    metadata={"hnsw:space": "cosine"},  # HNSW = Hierarchical Navigable Small World — the graph algorithm
                                        # ChromaDB uses for approximate nearest-neighbour search.
                                        # "cosine" sets the distance metric to cosine (not Euclidean).
                                        # Cosine measures angle between vectors, not magnitude —
                                        # correct for text embeddings where direction = meaning. (Ch. 3)
)

existing = collection.count()
if existing > 0 and not force:
    print(f"Collection already has {existing} chunks — skipping embed (no API cost).")
    print("Run with --force to re-embed from scratch.")
    sys.exit(0)

if force and existing > 0:
    # Delete and recreate — collection.add() fails on duplicate IDs, so upsert
    # is not an option here; we need a clean slate before re-embedding.
    client.delete_collection("zudyog_products")
    collection = client.get_or_create_collection(
        name="zudyog_products",
        metadata={"hnsw:space": "cosine"},
    )
    print("Existing collection cleared.")

# OpenAI client created here, after the skip check, so a no-op run (already
# ingested, no --force) never initializes the API client at all.
embeddings_model = OpenAIEmbeddings()

# Build all chunks from the catalog
all_chunks = []
for product in PRODUCTS:
    chunks = product_to_chunks(product)
    all_chunks.extend(chunks)
    print(f"  {product['name']}: {len(chunks)} chunks")

print(f"\nTotal chunks to embed: {len(all_chunks)}")

# Embed all chunk texts in a single API call
texts = [c["text"] for c in all_chunks]
vectors = embeddings_model.embed_documents(texts)

# Store in ChromaDB.
# embeddings = the 1536-number vectors — used by HNSW for similarity search.
# documents  = the original text — returned with every result so the LLM can
#              read it. Without this, a query returns only IDs; the text is lost.
# Both are required: vectors find the chunk, documents are what the LLM reads.
collection.add(
    ids=[c["id"] for c in all_chunks],
    embeddings=vectors,
    documents=texts,
    metadatas=[c["metadata"] for c in all_chunks],
)

print(f"Ingested {collection.count()} chunks into ChromaDB.")
print("Grounding Layer ready.")
