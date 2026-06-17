"""
api/routers/arxiv.py

GET /api/arxiv/search?q=... — Hybrid arXiv + Qdrant cache search
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Query
from api.models.query import ArxivPaper
from api.dependencies import get_arxiv_retriever

router = APIRouter(prefix="/arxiv", tags=["ArXiv"])


@router.get("/search", response_model=list[ArxivPaper])
def search_arxiv(
    q: str = Query(..., min_length=3, description="Medical topic search query"),
):
    """Search arXiv (live API + Qdrant cache) for medical research papers."""
    try:
        retriever = get_arxiv_retriever()
        papers = retriever.search(q)
        return [ArxivPaper(**p) for p in papers if isinstance(p, dict)]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ArXiv search error: {e}")
