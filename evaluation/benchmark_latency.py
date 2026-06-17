"""
evaluation/benchmark_latency.py

Latency benchmarking across different graph sizes and query types.
Produces a matplotlib chart of mean and P95 latency.
"""

import sys
import os
import time
import json
import statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt

BENCHMARK_QUERIES = [
    "Which patients with diabetes are on 3 or more interacting medications?",
    "Show drug interactions for patients with chronic kidney disease.",
    "Find patients with both hypertension and heart failure.",
    "Which medications are contraindicated for kidney disease patients?",
    "Show high-risk patients with dangerous drug combinations.",
]


def benchmark_single_query(system, query: str, trials: int = 5) -> dict:
    """Run a single query N times and return latency statistics."""
    latencies_ms = []
    for _ in range(trials):
        start = time.perf_counter()
        system.query(query)
        latencies_ms.append((time.perf_counter() - start) * 1000)

    return {
        "query":  query,
        "trials": trials,
        "mean":   round(statistics.mean(latencies_ms), 1),
        "median": round(statistics.median(latencies_ms), 1),
        "p95":    round(float(np.percentile(latencies_ms, 95)), 1),
        "min":    round(min(latencies_ms), 1),
        "max":    round(max(latencies_ms), 1),
    }


def benchmark_system(system_name: str, system, trials: int = 3) -> list[dict]:
    """Benchmark all queries against a system."""
    results = []
    for query in BENCHMARK_QUERIES:
        print(f"  Benchmarking: {query[:60]}...")
        result = benchmark_single_query(system, query, trials)
        result["system"] = system_name
        results.append(result)
        print(f"    Mean: {result['mean']:.0f}ms  P95: {result['p95']:.0f}ms")
    return results


def plot_results(standard_results: list[dict], graphrag_results: list[dict]) -> None:
    """Generate comparison bar chart."""
    query_labels = [r["query"][:40] + "..." for r in standard_results]
    x = range(len(query_labels))
    width = 0.35

    standard_means  = [r["mean"] for r in standard_results]
    graphrag_means  = [r["mean"] for r in graphrag_results]
    standard_p95    = [r["p95"] for r in standard_results]
    graphrag_p95    = [r["p95"] for r in graphrag_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Mean latency
    ax1.bar([i - width/2 for i in x], standard_means, width, label="Standard RAG", color="#e74c3c", alpha=0.85)
    ax1.bar([i + width/2 for i in x], graphrag_means, width, label="GraphRAG", color="#2ecc71", alpha=0.85)
    ax1.set_xlabel("Query")
    ax1.set_ylabel("Mean Latency (ms)")
    ax1.set_title("Mean Latency Comparison")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(query_labels, rotation=30, ha="right", fontsize=8)
    ax1.legend()
    ax1.axhline(y=2000, color="red", linestyle="--", alpha=0.5, label="2s target")

    # P95 latency
    ax2.bar([i - width/2 for i in x], standard_p95, width, label="Standard RAG P95", color="#c0392b", alpha=0.85)
    ax2.bar([i + width/2 for i in x], graphrag_p95, width, label="GraphRAG P95", color="#27ae60", alpha=0.85)
    ax2.set_xlabel("Query")
    ax2.set_ylabel("P95 Latency (ms)")
    ax2.set_title("P95 Latency Comparison")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(query_labels, rotation=30, ha="right", fontsize=8)
    ax2.legend()

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(__file__), "latency_benchmark.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\nChart saved to {output_path}")
    plt.show()


def run_benchmark(trials: int = 3) -> dict:
    """Run benchmarks for both systems."""
    from evaluation.compare_rag_systems import StandardRAG
    from src.graphrag.medical_graphrag import MedicalGraphRAG

    print("Benchmarking Standard RAG...")
    standard = StandardRAG()
    standard_results = benchmark_system("Standard RAG", standard, trials)

    print("\nBenchmarking GraphRAG...")
    graph_rag = MedicalGraphRAG()
    graphrag_results = benchmark_system("GraphRAG", graph_rag, trials)
    graph_rag.close()

    # Summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    overall_std  = statistics.mean(r["mean"] for r in standard_results)
    overall_grag = statistics.mean(r["mean"] for r in graphrag_results)
    print(f"Standard RAG avg mean latency: {overall_std:.0f} ms")
    print(f"GraphRAG avg mean latency:     {overall_grag:.0f} ms")

    # Save results
    all_results = {
        "standard_rag": standard_results,
        "graph_rag":    graphrag_results,
        "summary": {
            "standard_rag_avg_ms": round(overall_std, 1),
            "graph_rag_avg_ms":    round(overall_grag, 1),
        },
    }
    output_json = os.path.join(os.path.dirname(__file__), "latency_results.json")
    with open(output_json, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Results saved to {output_json}")

    # Plot
    try:
        plot_results(standard_results, graphrag_results)
    except Exception as e:
        print(f"Could not generate plot: {e}")

    return all_results


if __name__ == "__main__":
    run_benchmark(trials=3)
