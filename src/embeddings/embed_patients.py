"""
src/embeddings/embed_patients.py

Fetches all patient profiles from Neo4j (with their conditions and drugs),
builds a rich textual profile for each patient, generates an embedding,
and upserts into the Qdrant 'medical_patients' collection.
Uses Regolo API with Qwen3-Embedding-8B for semantic embeddings.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from neo4j import GraphDatabase

from src.config import config
from src.embeddings.embed_pipeline import create_embeddings_batch_with_embedder

BATCH_SIZE = 50

NEO4J_QUERY = """
MATCH (p:Patient)
OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
OPTIONAL MATCH (p)-[:TAKES_DRUG]->(d:Drug)
OPTIONAL MATCH (p)-[:TREATED_BY]->(hp:HealthcareProvider)
RETURN p.patientID      AS patientID,
       p.name           AS name,
       p.age            AS age,
       p.gender         AS gender,
       collect(DISTINCT c.name)  AS conditions,
       collect(DISTINCT d.name)  AS drugs,
       collect(DISTINCT hp.name) AS providers
ORDER BY p.patientID
"""


def build_profile_text(record: dict) -> str:
    conditions = ", ".join(record["conditions"]) if record["conditions"] else "None"
    drugs = ", ".join(record["drugs"]) if record["drugs"] else "None"
    providers = ", ".join(record["providers"]) if record["providers"] else "Unknown"
    gender_str = "male" if record["gender"] == "M" else "female"
    return (
        f"Patient {record['name']} is a {record['age']}-year-old {gender_str}. "
        f"Medical conditions: {conditions}. "
        f"Current medications: {drugs}. "
        f"Treated by: {providers}."
    )


# def embed_patients(qdrant: QdrantClient, openai: OpenAI) -> None:  # OpenAI signature (commented)
def embed_patients(qdrant: QdrantClient, embedder) -> None:
    """
    Embed patient profiles into Qdrant.
    
    Parameters
    ----------
    qdrant : QdrantClient
        Qdrant vector database client
    embedder : RegloEmbedder
        Regolo embedder instance for generating embeddings
    """
    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    )

    try:
        with driver.session() as session:
            records = list(session.run(NEO4J_QUERY))

        print(f"  Fetched {len(records)} patients from Neo4j")

        all_points: list[PointStruct] = []

        # Process in batches — one API call per batch (avoids rate limit)
        for batch_start in tqdm(range(0, len(records), BATCH_SIZE), desc="Embedding patients (batches)"):
            batch = records[batch_start: batch_start + BATCH_SIZE]
            texts = [build_profile_text(dict(r)) for r in batch]

            # One API call for the whole batch
            vectors = create_embeddings_batch_with_embedder(texts, embedder)

            for i, (record, vector, profile_text) in enumerate(zip(batch, vectors, texts)):
                all_points.append(
                    PointStruct(
                        id=batch_start + i,
                        vector=vector,
                        payload={
                            "patientID":    record["patientID"],
                            "name":         record["name"],
                            "age":          record["age"],
                            "gender":       record["gender"],
                            "conditions":   list(record["conditions"]),
                            "drugs":        list(record["drugs"]),
                            "providers":    list(record["providers"]),
                            "profile_text": profile_text,
                        },
                    )
                )

            # Upsert this batch to Qdrant
            qdrant.upsert(
                collection_name=config.COLLECTION_PATIENTS,
                points=all_points[-len(batch):],
            )

        print(f"  ✓ Embedded {len(records)} patients into '{config.COLLECTION_PATIENTS}'")

    finally:
        driver.close()
