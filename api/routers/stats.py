"""
api/routers/stats.py

GET /api/stats — Returns graph statistics (node/relationship counts).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException
from api.models.graph import GraphStatistics
from api.dependencies import get_graph_retriever

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("", response_model=GraphStatistics)
def get_statistics():
    """Return Neo4j graph node and relationship counts."""
    try:
        gr = get_graph_retriever()
        raw = gr.get_graph_statistics()
        total_nodes = sum(raw.get("nodes", {}).values())
        total_rels = sum(raw.get("relationships", {}).values())
        return GraphStatistics(
            nodes=raw.get("nodes", {}),
            relationships=raw.get("relationships", {}),
            total_nodes=total_nodes,
            total_relationships=total_rels,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")
