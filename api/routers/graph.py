"""
api/routers/graph.py

GET /api/graph/stats                  — Graph node/relationship counts
GET /api/graph/drug-interactions      — Drug interaction network edges
GET /api/graph/patient/{id}/path      — Patient relationship paths
GET /api/graph/khop                   — k-hop drug chain
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Query
from api.models.graph import GraphStatistics, DrugInteractionEdge, KHopChain
from api.models.patient import PatientGraphPath
from api.dependencies import get_graph_retriever

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/stats", response_model=GraphStatistics)
def graph_stats():
    """Return Neo4j node and relationship counts."""
    try:
        gr = get_graph_retriever()
        raw = gr.get_graph_statistics()
        return GraphStatistics(
            nodes=raw.get("nodes", {}),
            relationships=raw.get("relationships", {}),
            total_nodes=sum(raw.get("nodes", {}).values()),
            total_relationships=sum(raw.get("relationships", {}).values()),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/drug-interactions", response_model=list[DrugInteractionEdge])
def drug_interactions(
    min_severity: float = Query(0.6, ge=0.0, le=1.0, description="Minimum severity filter")
):
    """Return all drug interaction edges above the given severity threshold."""
    try:
        gr = get_graph_retriever()
        raw = gr.get_drug_interaction_network(min_severity=min_severity)
        return [
            DrugInteractionEdge(
                drug1=r.get("drug1", ""),
                drug2=r.get("drug2", ""),
                severity=float(r.get("severity", 0)),
                mechanism=r.get("mechanism", ""),
            )
            for r in raw
        ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/patient/{patient_id}/path", response_model=PatientGraphPath)
def patient_graph_path(patient_id: str):
    """Return all graph relationships for a specific patient (for visualisation)."""
    try:
        gr = get_graph_retriever()
        path_data = gr.get_patient_graph_paths(patient_id)
        return PatientGraphPath(
            nodes=path_data.get("nodes", []),
            edges=path_data.get("edges", []),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Graph path error: {e}")


@router.get("/khop", response_model=list[KHopChain])
def khop_drug_chain(
    drug: str = Query(..., description="Drug name to start from (e.g. Warfarin)"),
    k: int = Query(2, ge=1, le=4, description="Number of hops"),
):
    """Return k-hop drug interaction chains starting from a given drug."""
    try:
        gr = get_graph_retriever()
        raw = gr.k_hop_drug_interactions(drug_name=drug, k=k)
        return [
            KHopChain(
                chain=r.get("chain", []),
                hops=int(r.get("hops", 0)),
                severities=[float(s) for s in r.get("severities", []) if s is not None],
            )
            for r in raw
        ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"k-hop query error: {e}")
