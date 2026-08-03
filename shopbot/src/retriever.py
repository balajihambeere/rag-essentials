# src/retriever.py
# Source: Book 1, Chapter 6 (Appendix A — Code Wiring)
# Threshold-gated retrieval — the gatekeeper of the Grounding Layer.
# Embeds the customer's query, searches ChromaDB for nearest neighbours,
# and applies the similarity threshold. Chunks below 0.75 are withheld.
# If nothing passes, returns None — the API then routes to the deliberate fallback.
#
# Threshold 0.75 was calibrated by testing 20 queries: correct top results scored
# 0.78–0.94, incorrect (adjacent) results scored 0.48–0.68. The gap between
# 0.68 and 0.78 is where the threshold sits. (Ch. 6)

import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

SIMILARITY_THRESHOLD = 0.75
MAX_RESULTS = 3

embeddings_model = OpenAIEmbeddings()

# Initialized at module level so the ChromaDB client and collection are shared
# across every request — not recreated per call. (Ch. 8 lifespan pattern)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="zudyog_products",
    metadata={"hnsw:space": "cosine"},  # HNSW = Hierarchical Navigable Small World — the graph algorithm
                                        # ChromaDB uses for approximate nearest-neighbour search.
                                        # "cosine" sets the distance metric to cosine (not Euclidean).
                                        # Cosine measures angle between vectors, not magnitude —
                                        # correct for text embeddings where direction = meaning. (Ch. 3)
)


def retrieve(
    query: str,
    chunk_type: Optional[str] = None,
    product_id: Optional[str] = None,
) -> Optional[list[dict]]:
    """
    Retrieve relevant chunks for a query.

    Args:
        query:       the customer's question.
        chunk_type:  optional — restrict to one chunk type
                     ("identity", "variants", "policy", "care", "faq").
        product_id:  optional — restrict to a specific product ("p001"–"p005").

    Returns:
        A list of chunk dicts above the similarity threshold, or None
        if nothing qualifies. None means the Grounding Layer withholds.
    """
    query_vector = embeddings_model.embed_query(query)

    where: dict = {}
    if chunk_type:
        where["chunk_type"] = chunk_type
    if product_id:
        where["product_id"] = product_id

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=MAX_RESULTS,
        where=where if where else None,  # ChromaDB rejects an empty dict; must pass None
        include=["documents", "distances", "metadatas"],
    )

    retrieved = []
    for i, doc in enumerate(results["documents"][0]):
        distance   = results["distances"][0][i]
        similarity = 1 - distance  # ChromaDB returns cosine distance; convert to similarity
        if similarity >= SIMILARITY_THRESHOLD:
            retrieved.append({
                "text":       doc,
                "similarity": round(similarity, 4),
                "metadata":   results["metadatas"][0][i],
            })

    return retrieved if retrieved else None


def get_retriever(k: int = 3):
    """
    Return a LangChain-compatible retriever wrapping the ChromaDB collection.
    Used by src/chain.py to wire retrieval into the LangChain expression language.
    """
    vector_store = Chroma(
        client=client,
        collection_name="zudyog_products",
        embedding_function=embeddings_model,
    )
    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": k,
            "score_threshold": SIMILARITY_THRESHOLD,
        },
    )


