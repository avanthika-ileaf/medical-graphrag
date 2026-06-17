"""
evaluation/ragas_eval.py

RAGAS-based evaluation of faithfulness, answer relevancy, and context precision
for both Standard RAG and GraphRAG systems.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import Dataset


# ─── Ground-truth evaluation set ──────────────────────────────────────────────

EVAL_DATASET = [
    {
        "question": "Which patients with diabetes are on medications that interact dangerously?",
        "ground_truth": (
            "Patients with Type 2 Diabetes taking 3 or more medications with"
            " high-severity interactions (>0.7) represent the highest risk cohort."
            " Graph traversal is required to identify these patients."
        ),
    },
    {
        "question": "What drugs are contraindicated for patients with chronic kidney disease?",
        "ground_truth": (
            "Metformin, Lisinopril, Spironolactone, NSAIDs, and Allopurinol are contraindicated"
            " for patients with Chronic Kidney Disease due to risk of lactic acidosis,"
            " hyperkalemia, and further renal damage."
        ),
    },
    {
        "question": "Show the drug interaction chain from Warfarin up to 2 hops.",
        "ground_truth": (
            "Warfarin directly interacts with Aspirin (severity 0.9), Ciprofloxacin (0.85),"
            " Fluoxetine (0.8), Sertraline (0.75), Amoxicillin (0.7), and Azithromycin (0.72)."
            " At 2 hops, Ciprofloxacin also interacts with Azithromycin"
            " (additive QT prolongation)."
        ),
    },
    {
        "question": "Are there patients sharing the same doctor who also have overlapping conditions?",
        "ground_truth": (
            "Yes. Graph traversal of TREATED_BY and HAS_CONDITION relationships reveals"
            " patient pairs sharing providers and diagnoses."
            " This is only discoverable via graph join queries."
        ),
    },
    {
        "question": "Which medications should not be combined due to serotonin syndrome risk?",
        "ground_truth": (
            "SSRIs (Sertraline, Fluoxetine) combined with Tramadol carry the highest"
            " serotonin syndrome risk (severity 0.85-0.88)."
            " Duloxetine combined with either SSRI also poses significant risk (0.78-0.80)."
        ),
    },
]


def build_ragas_dataset(system_results: list[dict]) -> Dataset:
    """
    Format system results for RAGAS evaluation.

    system_results: list of dicts with keys 'question', 'answer', 'contexts', 'ground_truth'
    """
    return Dataset.from_dict(
        {
            "question":     [r["question"] for r in system_results],
            "answer":       [r["answer"] for r in system_results],
            "contexts":     [r.get("contexts", [""]) for r in system_results],
            "ground_truth": [r["ground_truth"] for r in system_results],
        }
    )


def evaluate_system(system_name: str, system_results: list[dict]) -> dict:
    """Run RAGAS evaluation on system output."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision

        dataset = build_ragas_dataset(system_results)

        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
        )

        print(f"\n{system_name} RAGAS Scores:")
        print(f"  Faithfulness:       {scores['faithfulness']:.3f}")
        print(f"  Answer Relevancy:   {scores['answer_relevancy']:.3f}")
        print(f"  Context Precision:  {scores['context_precision']:.3f}")

        return dict(scores)

    except ImportError:
        print("RAGAS not installed. Run: pip install ragas")
        return {}


def run_ragas_comparison() -> dict:
    """
    Query both systems with the evaluation set and compute RAGAS scores.
    """
    from evaluation.compare_rag_systems import StandardRAG
    from src.graphrag.medical_graphrag import MedicalGraphRAG

    standard = StandardRAG()
    graph_rag = MedicalGraphRAG()

    standard_results = []
    graphrag_results = []

    for example in EVAL_DATASET:
        q = example["question"]
        gt = example["ground_truth"]

        # Standard RAG
        sr = standard.query(q)
        standard_results.append(
            {
                "question":     q,
                "answer":       sr.get("answer", ""),
                "contexts": [
                    r.get("profile_text", "")
                    for r in sr.get("raw_context", {}).get("semantic_matches", [])[:2]
                ],
                "ground_truth": gt,
            }
        )

        # GraphRAG
        gr = graph_rag.query(q)
        graph_contexts = [str(f) for f in gr.get("graph_hits", [])[:2]]
        graphrag_results.append(
            {
                "question":     q,
                "answer":       gr.get("answer", ""),
                "contexts":     graph_contexts or ["No graph context available"],
                "ground_truth": gt,
            }
        )

    graph_rag.close()

    standard_scores = evaluate_system("Standard RAG", standard_results)
    graphrag_scores  = evaluate_system("GraphRAG",     graphrag_results)

    return {
        "standard_rag": standard_scores,
        "graph_rag":    graphrag_scores,
    }


if __name__ == "__main__":
    results = run_ragas_comparison()
    print("\nFinal comparison:", results)
