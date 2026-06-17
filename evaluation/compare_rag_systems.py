"""
evaluation/compare_rag_systems.py

Side-by-side comparison of Standard RAG (vector-only) vs GraphRAG.
"""

import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphrag.retrievers.vector_retriever import VectorRetriever
from src.graphrag.retrievers.graph_retriever import GraphRetriever
from src.graphrag.generator import GraphAwareGenerator


class StandardRAG:
    """Vector-only RAG baseline for comparison."""

    def __init__(self):
        self.vector = VectorRetriever()
        self.generator = GraphAwareGenerator()

    def query(self, natural_language_query: str) -> dict:
        start = time.perf_counter()

        patients   = self.vector.search_similar_patients(natural_language_query, top_k=5)
        drugs      = self.vector.search_drug_knowledge(natural_language_query, top_k=3)
        conditions = self.vector.search_condition_knowledge(natural_language_query, top_k=3)

        # Fake-fuse with no graph data
        fused = {
            "graph_facts":         [],
            "semantic_matches":    patients,
            "drug_knowledge":      drugs,
            "condition_knowledge": conditions,
            "confirmed_patients":  [],
            "provenance": {
                "graph_only": [],
                "vector_only": [p.get("patientID", "") for p in patients],
                "confirmed": [],
            },
            "confidence":          0.5,
        }

        result = self.generator.generate_answer(natural_language_query, fused)
        result["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
        result["system"] = "Standard RAG (Vector Only)"
        return result


class RAGComparison:
    """Run the same query through both systems and compare results."""

    def __init__(self):
        self.standard_rag = StandardRAG()
        self.graph_retriever = GraphRetriever()
        self.vector_retriever = VectorRetriever()
        self.generator = GraphAwareGenerator()

    def _run_graph_rag(self, query: str) -> dict:
        from src.graphrag.medical_graphrag import MedicalGraphRAG
        system = MedicalGraphRAG()
        result = system.query(query)
        result["system"] = "GraphRAG (Vector + Neo4j)"
        system.close()
        return result

    def run_comparison(self, query: str, verbose: bool = True) -> dict:
        """Run query through both systems and return combined results."""

        if verbose:
            print(f"\n{'='*60}")
            print(f"QUERY: {query}")
            print(f"{'='*60}")

        # Standard RAG
        if verbose:
            print("\n[Standard RAG] Running...")
        standard_result = self.standard_rag.query(query)

        # GraphRAG
        if verbose:
            print("\n[GraphRAG] Running...")
        graph_result = self._run_graph_rag(query)

        comparison = {
            "query": query,
            "standard_rag": {
                "answer":     standard_result.get("answer", ""),
                "latency_ms": standard_result.get("latency_ms", 0),
                "confidence": standard_result.get("confidence", 0),
                "system":     "Standard RAG (Vector Only)",
            },
            "graph_rag": {
                "answer":     graph_result.get("answer", ""),
                "latency_ms": graph_result.get("latency_ms", 0),
                "confidence": graph_result.get("confidence", 0),
                "provenance": graph_result.get("provenance", {}),
                "system":     "GraphRAG (Vector + Neo4j)",
            },
        }

        if verbose:
            self._print_comparison(comparison)

        return comparison

    def run_batch(self, queries: list[str]) -> list[dict]:
        """Run multiple comparisons and return all results."""
        return [self.run_comparison(q) for q in queries]

    @staticmethod
    def _print_comparison(c: dict) -> None:
        print(f"\n{'─'*60}")
        print("STANDARD RAG (Vector Only):")
        print(f"  Latency:    {c['standard_rag']['latency_ms']:.0f} ms")
        print(f"  Confidence: {c['standard_rag']['confidence']:.2%}")
        print(f"  Answer:\n{c['standard_rag']['answer'][:500]}...")

        print(f"\n{'─'*60}")
        print("GRAPHRAG (Vector + Neo4j):")
        print(f"  Latency:    {c['graph_rag']['latency_ms']:.0f} ms")
        print(f"  Confidence: {c['graph_rag']['confidence']:.2%}")
        print(f"  Provenance: {c['graph_rag']['provenance']}")
        print(f"  Answer:\n{c['graph_rag']['answer'][:500]}...")


def main():
    from demos.impossible_queries import DEMO_QUERIES

    comparison = RAGComparison()
    all_results = []

    for demo in DEMO_QUERIES[:3]:  # Run first 3 to avoid excessive API costs
        result = comparison.run_comparison(demo["query"])
        all_results.append(result)

    output_path = os.path.join(os.path.dirname(__file__), "comparison_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
