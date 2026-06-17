"""
src/embeddings/embed_pipeline.py

Creates Qdrant collections and orchestrates embedding of all data.
Uses Regolo API with Qwen3-Embedding-8B for semantic embeddings.

Run directly:  python -c "from src.embeddings.embed_pipeline import run_all_embeddings; run_all_embeddings()"
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.config import config
from src.embeddings.regolo_embedder import get_regolo_embedder, create_embeddings_batch


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)


def get_regolo_client():
    """Get Regolo embedder instance."""
    return get_regolo_embedder()


def create_embedding(text: str, embedder=None) -> list[float]:
    """
    Generate a single embedding vector using Regolo.
    
    Parameters
    ----------
    text : str
        Text to embed
    embedder : RegloEmbedder, optional
        Regolo embedder instance. If None, creates a new one.
        
    Returns
    -------
    list[float]
        Embedding vector
    """
    if embedder is None:
        embedder = get_regolo_client()
        return embedder.embed(text)
    return embedder.embed(text)


def create_embeddings_batch_with_embedder(
    texts: list[str],
    embedder=None,
    max_retries: int = 5,
) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using Regolo.
    
    Parameters
    ----------
    texts : list[str]
        Batch of texts to embed
    embedder : RegloEmbedder, optional
        Regolo embedder instance. If None, creates a new one.
    max_retries : int
        Maximum number of retries on rate limit (429)
        
    Returns
    -------
    list[list[float]]
        List of embedding vectors
    """
    if embedder is None:
        embedder = get_regolo_client()
        return embedder.embed_batch(texts, max_retries=max_retries)
    return embedder.embed_batch(texts, max_retries=max_retries)


def create_collections(qdrant: QdrantClient) -> None:
    """Create (or recreate) the three Qdrant collections."""
    collections = [
        config.COLLECTION_PATIENTS,
        config.COLLECTION_DRUGS,
        config.COLLECTION_CONDITIONS,
    ]
    for name in collections:
        existing = [c.name for c in qdrant.get_collections().collections]
        if name not in existing:
            qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=config.EMBEDDING_DIM, distance=Distance.COSINE),
            )
            print(f"  ✓ Created collection: {name}")
        else:
            print(f"  - Collection already exists: {name}")


def run_all_embeddings() -> None:
    """Full pipeline: create collections → embed patients → embed drugs + conditions."""
    from src.embeddings.embed_patients import embed_patients
    from src.embeddings.embed_knowledge import embed_drugs, embed_conditions

    qdrant = get_qdrant_client()

    # --- Regolo embedder setup ---
    print("🔌 Initializing Regolo embedder with Qwen3-Embedding-8B...")
    embedder = get_regolo_client()

    try:
        print("Step 1: Creating Qdrant collections...")
        create_collections(qdrant)

        print("\nStep 2: Embedding patient profiles...")
        embed_patients(qdrant, embedder)

        print("\nStep 3: Embedding drug knowledge base...")
        embed_drugs(qdrant, embedder)

        print("\nStep 4: Embedding condition knowledge base...")
        embed_conditions(qdrant, embedder)

        print("\n✅ All embeddings complete.")
    finally:
        embedder.close()


if __name__ == "__main__":
    run_all_embeddings()
