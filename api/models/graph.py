"""
api/models/graph.py

Pydantic schemas for graph / analytics data.
"""

from __future__ import annotations
from pydantic import BaseModel


class GraphStatistics(BaseModel):
    nodes: dict[str, int] = {}
    relationships: dict[str, int] = {}
    total_nodes: int = 0
    total_relationships: int = 0


class DrugInteractionEdge(BaseModel):
    drug1: str
    drug2: str
    severity: float
    mechanism: str = ""


class KHopChain(BaseModel):
    chain: list[str]
    hops: int
    severities: list[float]
