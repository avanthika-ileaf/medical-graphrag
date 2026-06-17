"""
api/models/query.py

Pydantic request/response schemas for the query endpoints.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ── Requests ────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language medical query")
    use_agent: bool = Field(True, description="Use full agentic orchestrator (slower, richer)")


# ── Sub-models ───────────────────────────────────────────────────────────────

class ArxivPaper(BaseModel):
    arxiv_id: str = ""
    title: str = ""
    authors: list[str] = []
    summary: str = ""
    published: str = ""
    url: str = ""
    topics: list[str] = []
    source: str = ""
    score: float | None = None


class ProvenanceInfo(BaseModel):
    graph_only: list[str] = []
    vector_only: list[str] = []
    confirmed: list[str] = []


class StandardRAGResult(BaseModel):
    answer: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    sources: str = "Qdrant semantic search only"


class GraphRAGResult(BaseModel):
    answer: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    provenance: ProvenanceInfo = ProvenanceInfo()
    agent_output: str | None = None


# ── Responses ────────────────────────────────────────────────────────────────

class QueryResponse(BaseModel):
    query: str
    answer: str
    confidence: float = 0.0
    provenance: ProvenanceInfo = ProvenanceInfo()
    graph_hits: list[dict[str, Any]] = []
    vector_hits: list[dict[str, Any]] = []
    arxiv_papers: list[ArxivPaper] = []
    agent_output: str | None = None
    latency_ms: float = 0.0
    model: str = ""


class CompareQueryResponse(BaseModel):
    query: str
    standard_rag: StandardRAGResult
    graph_rag: GraphRAGResult
    graph_hits: list[dict[str, Any]] = []
    arxiv_papers: list[ArxivPaper] = []
