"""
src/graphrag/fusion.py

Result fusion layer: merges graph traversal and vector search outputs,
cross-validates them, and scores overall confidence.
"""

from __future__ import annotations


class ResultFusion:
    """
    Merge and rerank results from the graph (structured) and
    vector (semantic) retrieval paths.

    Patients appearing in both paths are treated as high-confidence
    findings.  The fused context dict is passed to the generator.
    """

    @staticmethod
    def fuse(graph_results: list[dict], vector_results: list[dict]) -> dict:
        """
        Parameters
        ----------
        graph_results:
            Output from GraphRetriever — list of dicts with at least
            a 'patientID' key.
        vector_results:
            Output from VectorRetriever.search_similar_patients() —
            list of dicts with a 'patientID' key.

        Returns
        -------
        dict with keys:
            graph_facts       – raw graph records
            semantic_matches  – raw vector hits
            confirmed_patients – IDs appearing in both
            provenance        – breakdown by source
            confidence        – float [0, 1]
        """
        graph_ids  = {r["patientID"] for r in graph_results if "patientID" in r}
        vector_ids = {r["patientID"] for r in vector_results if "patientID" in r}

        confirmed   = graph_ids & vector_ids
        graph_only  = graph_ids - vector_ids
        vector_only = vector_ids - graph_ids

        if len(graph_ids) > 0:
            # High confidence because graph traversal found exact relationship paths
            base = 0.8
            # Add bonus up to 0.2 if vector search semantically confirms those patients
            bonus = 0.2 * (len(confirmed) / len(graph_ids))
            confidence = base + bonus
        elif len(vector_ids) > 0:
            # Only vector semantic matches found, probabilistic confidence
            confidence = 0.5
        else:
            confidence = 0.0

        return {
            "graph_facts":         graph_results,
            "semantic_matches":    vector_results,
            "confirmed_patients":  list(confirmed),
            "provenance": {
                "graph_only":  list(graph_only),
                "vector_only": list(vector_only),
                "confirmed":   list(confirmed),
            },
            "confidence": round(confidence, 4),
        }

    @staticmethod
    def fuse_knowledge(
        graph_results: list[dict],
        drug_hits: list[dict],
        condition_hits: list[dict],
    ) -> dict:
        """
        Merge graph results with drug/condition knowledge hits for
        knowledge-base queries (not patient-centric).
        """
        return {
            "graph_facts":      graph_results,
            "drug_knowledge":   drug_hits,
            "condition_knowledge": condition_hits,
            "confidence": 1.0 if graph_results else 0.5,
        }

    @staticmethod
    def build_context_string(fused: dict) -> str:
        """
        Convert the fused context dict into a readable string
        suitable for inclusion in the LLM prompt.
        """
        lines: list[str] = []

        if fused.get("graph_facts"):
            lines.append("=== GRAPH DATABASE FACTS ===")
            for i, fact in enumerate(fused["graph_facts"], 1):
                lines.append(f"[{i}] {fact}")

        if fused.get("semantic_matches"):
            lines.append("\n=== SEMANTIC SIMILARITY MATCHES ===")
            for i, match in enumerate(fused["semantic_matches"], 1):
                lines.append(
                    f"[{i}] {match.get('name', 'Unknown')} "
                    f"(score {match.get('score', 0):.3f}) — "
                    f"conditions: {match.get('conditions', [])}; "
                    f"drugs: {match.get('drugs', [])}"
                )

        if fused.get("drug_knowledge"):
            lines.append("\n=== DRUG KNOWLEDGE BASE ===")
            for entry in fused["drug_knowledge"]:
                lines.append(f"- {entry.get('drug_name')}: {entry.get('description', '')[:200]}")

        if fused.get("condition_knowledge"):
            lines.append("\n=== CONDITION KNOWLEDGE BASE ===")
            for entry in fused["condition_knowledge"]:
                lines.append(f"- {entry.get('condition_name')}: {entry.get('description', '')[:200]}")

        if fused.get("confirmed_patients"):
            lines.append("\n=== CONFIRMED BY BOTH PATHS ===")
            lines.append(f"Patient IDs: {', '.join(fused['confirmed_patients'])}")

        lines.append(f"\nConfidence: {fused.get('confidence', 0):.2%}")
        return "\n".join(lines)
