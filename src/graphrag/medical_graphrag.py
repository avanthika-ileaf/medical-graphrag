"""
src/graphrag/medical_graphrag.py

Top-level MedicalGraphRAG class that provides a simple unified API
over the full pipeline (graph + vector + fusion + generation).

For direct non-agent use; prefer MedicalGraphRAGOrchestrator for the
full LangChain ReAct agent experience.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from qdrant_client import QdrantClient
from neo4j import GraphDatabase

from src.config import config
from src.graphrag.retrievers.graph_retriever import GraphRetriever
from src.graphrag.retrievers.vector_retriever import VectorRetriever
from src.graphrag.fusion import ResultFusion
from src.graphrag.generator import GraphAwareGenerator


class MedicalGraphRAG:
    """
    Hybrid retrieval system combining Neo4j graph traversal,
    Qdrant vector search, and GPT-4 generation.

    Provides the core query pipeline without the LangChain agent wrapper.
    """

    def __init__(self):
        self.qdrant_client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        self.neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
        )

        self.graph_retriever = GraphRetriever(driver=self.neo4j_driver)
        self.vector_retriever = VectorRetriever(qdrant_client=self.qdrant_client)
        self.generator = GraphAwareGenerator()

    def close(self):
        self.neo4j_driver.close()

    # ─── Main query pipeline ──────────────────────────────────────────────────

    def query(self, natural_language_query: str) -> dict:
        """
        Execute parallel graph + vector retrieval, fuse results,
        and generate a grounded answer.

        Returns a dict with:
            query, answer, provenance, confidence, latency_ms,
            graph_hits, vector_hits, raw_context
        """
        start = time.perf_counter()

        # 1. Parallel retrieval (graph + vector)
        graph_results  = self._run_graph_retrieval(natural_language_query)
        vector_results = self.vector_retriever.search_similar_patients(
            natural_language_query, top_k=5
        )
        drug_results       = self.vector_retriever.search_drug_knowledge(natural_language_query, top_k=3)
        condition_results  = self.vector_retriever.search_condition_knowledge(natural_language_query, top_k=3)

        # 2. Fuse
        fused = ResultFusion.fuse(graph_results, vector_results)
        fused["drug_knowledge"]      = drug_results
        fused["condition_knowledge"] = condition_results

        # 3. Generate grounded answer
        result = self.generator.generate_answer(natural_language_query, fused)

        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        result["latency_ms"]    = latency_ms
        result["graph_hits"]    = graph_results
        result["vector_hits"]   = vector_results

        return result

    def _run_graph_retrieval(self, query: str) -> list[dict]:
        """Route query to appropriate graph retrieval method(s)."""
        q = query.lower()

        results: list[dict] = []

        if any(kw in q for kw in ["interact", "high risk", "dangerous", "3+"]):
            results += self.graph_retriever.find_high_risk_patients(limit=10)

        if any(kw in q for kw in ["contraindic"]):
            results += self.graph_retriever.find_patients_with_contraindicated_drugs(limit=10)

        if any(kw in q for kw in ["shared doctor", "cohort", "same provider"]):
            results += self.graph_retriever.find_shared_doctor_cohorts(limit=5)

        if any(kw in q for kw in ["diabetes"]):
            results += self.graph_retriever.find_patients_with_conditions(
                ["Type 2 Diabetes", "Type 1 Diabetes"], limit=8
            )

        if any(kw in q for kw in ["hypertension", "blood pressure"]):
            results += self.graph_retriever.find_patients_with_conditions(
                ["Hypertension"], limit=8
            )

        if any(kw in q for kw in ["kidney"]):
            results += self.graph_retriever.find_patients_with_conditions(
                ["Chronic Kidney Disease"], limit=8
            )

        # Default: return high-risk patients if no specific intent detected
        if not results:
            results = self.graph_retriever.find_high_risk_patients(limit=10)

        return results

    # ─── Utility methods ──────────────────────────────────────────────────────

    def get_graph_stats(self) -> dict:
        return self.graph_retriever.get_graph_statistics()

    def get_patient_profile(self, patient_id: str) -> dict | None:
        graph_data   = self.graph_retriever.get_patient_by_id(patient_id)
        if not graph_data:
            return None
        vector_data = self.vector_retriever.search_similar_patients(
            f"Patient ID {patient_id}", top_k=1
        )
        return {
            "graph":  graph_data,
            "vector": vector_data[0] if vector_data else None,
        }
