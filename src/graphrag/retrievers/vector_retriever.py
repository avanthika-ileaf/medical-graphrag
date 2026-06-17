"""
src/graphrag/retrievers/vector_retriever.py

Semantic search via Qdrant for patients, drugs, and conditions.
Complements graph traversal with fuzzy similarity matching.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.config import config
from src.embeddings.regolo_embedder import get_regolo_embedder


class VectorRetriever:
    """Semantic search over Qdrant collections."""

    def __init__(self, qdrant_client: QdrantClient | None = None):
        self.qdrant = qdrant_client or QdrantClient(
            host=config.QDRANT_HOST, port=config.QDRANT_PORT
        )
        self._ensure_required_collections()
        self.embedder = get_regolo_embedder()

    def _ensure_required_collections(self) -> None:
        """Fail fast with a setup error when required Qdrant collections are missing."""
        required = [
            config.COLLECTION_PATIENTS,
            config.COLLECTION_DRUGS,
            config.COLLECTION_CONDITIONS,
        ]
        existing = {c.name for c in self.qdrant.get_collections().collections}
        missing = [name for name in required if name not in existing]

        if missing:
            raise RuntimeError(
                "Qdrant is not initialized for semantic search. "
                f"Missing collections: {', '.join(missing)}. "
                "Run `python -c \"from src.embeddings.embed_pipeline import "
                "run_all_embeddings; run_all_embeddings()\"` "
                "after Neo4j and Qdrant are running."
            )

    def _embed(self, text: str) -> list[float]:
        return self.embedder.embed(text)

    # ─── Patient search ───────────────────────────────────────────────────────

    def search_similar_patients(
        self,
        query: str,
        top_k: int = 5,
        gender_filter: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[dict]:
        """Find patients whose profiles are semantically similar to the query."""
        query_vector = self._embed(query)

        qdrant_filter = None
        conditions = []

        if gender_filter:
            conditions.append(
                FieldCondition(key="gender", match=MatchValue(value=gender_filter))
            )

        if conditions:
            qdrant_filter = Filter(must=conditions)

        results = self.qdrant.query_points(
            collection_name=config.COLLECTION_PATIENTS,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            with_payload=True,
        ).points

        hits = []
        for r in results:
            p = r.payload
            # Apply age filter post-retrieval (Qdrant range filters require schema config)
            if min_age and p.get("age", 0) < min_age:
                continue
            if max_age and p.get("age", 0) > max_age:
                continue
            hits.append(
                {
                    "score":       r.score,
                    "patientID":   p["patientID"],
                    "name":        p["name"],
                    "age":         p["age"],
                    "gender":      p["gender"],
                    "conditions":  p.get("conditions", []),
                    "drugs":       p.get("drugs", []),
                    "profile_text": p.get("profile_text", ""),
                }
            )
        return hits

    # ─── Drug search ──────────────────────────────────────────────────────────

    def search_drug_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Find drug documents semantically matching the query."""
        query_vector = self._embed(query)

        results = self.qdrant.query_points(
            collection_name=config.COLLECTION_DRUGS,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points

        return [
            {
                "score":             r.score,
                "drug_name":         r.payload["drug_name"],
                "class":             r.payload.get("class", ""),
                "indications":       r.payload.get("indications", ""),
                "side_effects":      r.payload.get("side_effects", ""),
                "contraindications": r.payload.get("contraindications", ""),
                "description":       r.payload.get("description", ""),
            }
            for r in results
        ]

    # ─── Condition search ─────────────────────────────────────────────────────

    def search_condition_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Find medical condition documents semantically matching the query."""
        query_vector = self._embed(query)

        results = self.qdrant.query_points(
            collection_name=config.COLLECTION_CONDITIONS,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points

        return [
            {
                "score":          r.score,
                "condition_name": r.payload["condition_name"],
                "icd10":          r.payload.get("icd10", ""),
                "category":       r.payload.get("category", ""),
                "symptoms":       r.payload.get("symptoms", ""),
                "risk_factors":   r.payload.get("risk_factors", ""),
                "description":    r.payload.get("description", ""),
            }
            for r in results
        ]

    # ─── Combined search ──────────────────────────────────────────────────────

    def search_all(self, query: str, top_k: int = 3) -> dict:
        """Search all three collections and return combined results."""
        return {
            "patients":   self.search_similar_patients(query, top_k),
            "drugs":      self.search_drug_knowledge(query, top_k),
            "conditions": self.search_condition_knowledge(query, top_k),
        }
