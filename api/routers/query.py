"""
api/routers/query.py

POST /api/query          — Full agentic GraphRAG query (orchestrator)
POST /api/query/simple   — Direct pipeline query (no agent loop)
POST /api/query/compare  — Side-by-side Standard RAG vs GraphRAG
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException
from api.models.query import (
    QueryRequest, QueryResponse, CompareQueryResponse,
    StandardRAGResult, GraphRAGResult, ProvenanceInfo, ArxivPaper
)
from api.dependencies import get_orchestrator, get_medical_graphrag

router = APIRouter(prefix="/query", tags=["Query"])

PRESET_QUERIES = [
    "Which patients with Type 2 Diabetes are on 3+ medications that interact dangerously?",
    "Which patients with Chronic Kidney Disease are taking contraindicated drugs?",
    "Show the drug interaction chain from Warfarin (2 hops).",
    "Find patients sharing a doctor who have overlapping conditions and interacting drugs.",
    "Which patients are at risk for serotonin syndrome from their medications?",
]


@router.get("/presets")
def get_preset_queries():
    """Return preset query suggestions."""
    return {"presets": PRESET_QUERIES}


@router.post("", response_model=QueryResponse)
def run_query(body: QueryRequest):
    """
    Run the full agentic Medical GraphRAG pipeline.
    Uses MedicalGraphRAGOrchestrator (LiteLLM tool-calling loop).
    """
    t0 = time.perf_counter()
    try:
        orch = get_orchestrator()
        result = orch.query(body.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query pipeline error: {e}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    provenance_raw = result.get("provenance", {})
    provenance = ProvenanceInfo(
        graph_only=provenance_raw.get("graph_only", []),
        vector_only=provenance_raw.get("vector_only", []),
        confirmed=provenance_raw.get("confirmed", []),
    )

    arxiv_papers = [
        ArxivPaper(**p) for p in result.get("arxiv_papers", [])
        if isinstance(p, dict)
    ]

    return QueryResponse(
        query=body.query,
        answer=result.get("answer", ""),
        confidence=float(result.get("confidence", 0.0)),
        provenance=provenance,
        graph_hits=result.get("graph_hits", []) or [],
        vector_hits=result.get("vector_hits", []) or [],
        arxiv_papers=arxiv_papers,
        agent_output=result.get("agent_output"),
        latency_ms=latency_ms,
        model=result.get("model", ""),
    )


@router.post("/simple", response_model=QueryResponse)
def run_simple_query(body: QueryRequest):
    """
    Run the direct pipeline (no agent loop) — faster, less reasoning.
    Uses MedicalGraphRAG (graph + vector + fusion + generation).
    """
    t0 = time.perf_counter()
    try:
        mg = get_medical_graphrag()
        result = mg.query(body.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simple query error: {e}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    provenance_raw = result.get("provenance", {})
    provenance = ProvenanceInfo(
        graph_only=provenance_raw.get("graph_only", []),
        vector_only=provenance_raw.get("vector_only", []),
        confirmed=provenance_raw.get("confirmed", []),
    )

    return QueryResponse(
        query=body.query,
        answer=result.get("answer", ""),
        confidence=float(result.get("confidence", 0.0)),
        provenance=provenance,
        graph_hits=result.get("graph_hits", []) or [],
        vector_hits=result.get("vector_hits", []) or [],
        arxiv_papers=[],
        latency_ms=latency_ms,
        model=result.get("model", ""),
    )


@router.post("/compare", response_model=CompareQueryResponse)
def compare_rag_systems(body: QueryRequest):
    """
    Side-by-side Standard RAG vs GraphRAG comparison.
    Runs both pipelines and returns latency + answers for both.
    """
    from src.graphrag.retrievers.vector_retriever import VectorRetriever
    from src.graphrag.generator import GraphAwareGenerator

    try:
        # ── Standard RAG (vector-only) ───────────────────────────────────────
        t0 = time.perf_counter()
        vr = VectorRetriever()
        gen = GraphAwareGenerator()
        vector_results = vr.search_all(body.query, top_k=5)
        std_fused = {
            "graph_facts": [],
            "semantic_matches": vector_results.get("patients", []),
            "confirmed_patients": [],
            "provenance": {"graph_only": [], "vector_only": [], "confirmed": []},
            "confidence": 0.5,
        }
        std_gen = gen.generate_answer(body.query, std_fused)
        std_latency = round((time.perf_counter() - t0) * 1000, 1)

        standard = StandardRAGResult(
            answer=std_gen.get("answer", ""),
            confidence=float(std_gen.get("confidence", 0.0)),
            latency_ms=std_latency,
        )

        # ── GraphRAG ─────────────────────────────────────────────────────────
        t1 = time.perf_counter()
        mg = get_medical_graphrag()
        gr_result = mg.query(body.query)
        gr_latency = round((time.perf_counter() - t1) * 1000, 1)

        prov_raw = gr_result.get("provenance", {})
        graph_rag = GraphRAGResult(
            answer=gr_result.get("answer", ""),
            confidence=float(gr_result.get("confidence", 0.0)),
            latency_ms=gr_latency,
            provenance=ProvenanceInfo(
                graph_only=prov_raw.get("graph_only", []),
                vector_only=prov_raw.get("vector_only", []),
                confirmed=prov_raw.get("confirmed", []),
            ),
        )

        # ── arXiv papers ─────────────────────────────────────────────────────
        from api.dependencies import get_arxiv_retriever
        arxiv_papers = []
        try:
            arxiv_r = get_arxiv_retriever()
            raw_papers = arxiv_r.search(body.query)
            arxiv_papers = [ArxivPaper(**p) for p in raw_papers if isinstance(p, dict)]
        except Exception:
            pass

        return CompareQueryResponse(
            query=body.query,
            standard_rag=standard,
            graph_rag=graph_rag,
            graph_hits=gr_result.get("graph_hits", []) or [],
            arxiv_papers=arxiv_papers,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison query error: {e}")
