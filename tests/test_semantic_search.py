"""
tests/test_semantic_search.py

Verify that Qdrant collections are populated and semantic search
returns meaningful results.

Run: python tests/test_semantic_search.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphrag.retrievers.vector_retriever import VectorRetriever


def test_patient_search() -> bool:
    print("Testing patient semantic search...")
    retriever = VectorRetriever()
    try:
        results = retriever.search_similar_patients(
            "elderly patient with diabetes and heart disease on multiple medications",
            top_k=3,
        )
        if not results:
            print("  ✗ No results — is Qdrant populated? (run embed_pipeline.py)")
            return False
        for r in results:
            print(
                f"  \u2713 Score {r['score']:.3f}: {r['name']}"
                f" | conditions: {r['conditions'][:2]} | drugs: {r['drugs'][:3]}"
            )
        return True
    except Exception as e:
        print(f"  ✗ Patient search failed: {e}")
        return False


def test_drug_search() -> bool:
    print("\nTesting drug knowledge search...")
    retriever = VectorRetriever()
    try:
        results = retriever.search_drug_knowledge(
            "anticoagulant blood thinner interactions bleeding risk",
            top_k=3,
        )
        if not results:
            print("  ✗ No results — is Qdrant drug collection populated?")
            return False
        for r in results:
            print(f"  ✓ Score {r['score']:.3f}: {r['drug_name']} ({r['class']})")
        return True
    except Exception as e:
        print(f"  ✗ Drug search failed: {e}")
        return False


def test_condition_search() -> bool:
    print("\nTesting condition knowledge search...")
    retriever = VectorRetriever()
    try:
        results = retriever.search_condition_knowledge(
            "chronic progressive kidney disease renal failure",
            top_k=3,
        )
        if not results:
            print("  ✗ No results — is Qdrant condition collection populated?")
            return False
        for r in results:
            print(f"  ✓ Score {r['score']:.3f}: {r['condition_name']} (ICD-10: {r['icd10']})")
        return True
    except Exception as e:
        print(f"  ✗ Condition search failed: {e}")
        return False


def test_combined_search() -> bool:
    print("\nTesting combined search (all collections)...")
    retriever = VectorRetriever()
    try:
        results = retriever.search_all("diabetes hypertension elderly patient", top_k=2)
        patients   = results.get("patients", [])
        drugs      = results.get("drugs", [])
        conditions = results.get("conditions", [])
        print(f"  ✓ Patients: {len(patients)}, Drugs: {len(drugs)}, Conditions: {len(conditions)}")
        return len(patients) > 0 or len(drugs) > 0
    except Exception as e:
        print(f"  ✗ Combined search failed: {e}")
        return False


def main():
    print("=" * 50)
    print("Medical GraphRAG — Semantic Search Tests")
    print("=" * 50)

    results = {
        "patient_search":   test_patient_search(),
        "drug_search":      test_drug_search(),
        "condition_search": test_condition_search(),
        "combined_search":  test_combined_search(),
    }

    print("\n" + "=" * 50)
    print("Summary:")
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name:20s}: {status}")

    passed_count = sum(results.values())
    print(f"\n{passed_count}/{len(results)} tests passed.")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
