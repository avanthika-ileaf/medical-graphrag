"""
src/embeddings/embed_knowledge.py

Embeds drug and condition knowledge from data/*.json into Qdrant.
Sources the same static data used to populate Neo4j.
Uses Regolo API with Qwen3-Embedding-8B for semantic embeddings.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.config import config
from src.embeddings.embed_pipeline import create_embeddings_batch_with_embedder

DATA_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
BATCH_SIZE = 50


def load_json(filename: str) -> list[dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_drug_text(drug: dict) -> str:
    return (
        f"Drug Name: {drug['name']}. "
        f"Class: {drug['class']}. "
        f"FDA Approved: {drug.get('fda', True)}. "
        f"Indications: {drug.get('indications', 'Not specified')}. "
        f"Side Effects: {drug.get('side_effects', 'Not specified')}. "
        f"Contraindications: {drug.get('contraindications', 'Not specified')}."
    )


def build_condition_text(cond: dict) -> str:
    return (
        f"Condition: {cond['name']}. "
        f"ICD-10: {cond.get('icd10', 'N/A')}. "
        f"Category: {cond.get('category', 'N/A')}. "
        f"Symptoms: {cond.get('symptoms', 'Not specified')}. "
        f"Risk Factors: {cond.get('risk_factors', 'Not specified')}."
    )


# def embed_drugs(qdrant: QdrantClient, openai: OpenAI) -> None:  # OpenAI signature (commented)
def embed_drugs(qdrant: QdrantClient, embedder) -> None:
    """
    Embed drug knowledge into Qdrant.
    
    Parameters
    ----------
    qdrant : QdrantClient
        Qdrant vector database client
    embedder : RegloEmbedder
        Regolo embedder instance for generating embeddings
    """
    drugs = load_json("drugs.json")
    texts = [build_drug_text(d) for d in drugs]
    vectors = create_embeddings_batch_with_embedder(texts, embedder)

    points = [
        PointStruct(
            id=idx,
            vector=vectors[idx],
            payload={
                "drug_name":         drug["name"],
                "class":             drug["class"],
                "fda_approved":      drug.get("fda", True),
                "indications":       drug.get("indications", ""),
                "side_effects":      drug.get("side_effects", ""),
                "contraindications": drug.get("contraindications", ""),
                "description":       texts[idx],
            },
        )
        for idx, drug in enumerate(drugs)
    ]
    qdrant.upsert(collection_name=config.COLLECTION_DRUGS, points=points)
    print(f"  ✓ Embedded {len(drugs)} drugs into '{config.COLLECTION_DRUGS}'")


# def embed_conditions(qdrant: QdrantClient, openai: OpenAI) -> None:  # OpenAI signature (commented)
def embed_conditions(qdrant: QdrantClient, embedder) -> None:
    """
    Embed condition knowledge into Qdrant.
    
    Parameters
    ----------
    qdrant : QdrantClient
        Qdrant vector database client
    embedder : RegloEmbedder
        Regolo embedder instance for generating embeddings
    """
    conditions = load_json("conditions.json")
    texts = [build_condition_text(c) for c in conditions]
    vectors = create_embeddings_batch_with_embedder(texts, embedder)

    points = [
        PointStruct(
            id=idx,
            vector=vectors[idx],
            payload={
                "condition_name": cond["name"],
                "icd10":          cond.get("icd10", ""),
                "category":       cond.get("category", ""),
                "symptoms":       cond.get("symptoms", ""),
                "risk_factors":   cond.get("risk_factors", ""),
                "description":    texts[idx],
            },
        )
        for idx, cond in enumerate(conditions)
    ]
    qdrant.upsert(collection_name=config.COLLECTION_CONDITIONS, points=points)
    print(f"  ✓ Embedded {len(conditions)} conditions into '{config.COLLECTION_CONDITIONS}'")
