"""
api/models/patient.py

Pydantic schemas for patient data.
"""

from __future__ import annotations
from pydantic import BaseModel


class DrugInfo(BaseModel):
    name: str = ""
    dosage: str | None = None
    frequency: str | None = None


class ConditionInfo(BaseModel):
    name: str = ""
    severity: float | None = None
    since: str | None = None


class DrugInteraction(BaseModel):
    drug1: str = ""
    drug2: str = ""
    severity: float = 0.0
    mechanism: str = ""


class PatientSummary(BaseModel):
    patientID: str
    name: str = ""
    age: int | None = None
    gender: str | None = None
    drugCount: int | None = None
    conditions: list[str] = []
    drugs: list[str] = []
    interactions: list[DrugInteraction] = []
    risk_level: str = "low"  # low | medium | high


class PatientProfile(BaseModel):
    patientID: str
    name: str = ""
    age: int | None = None
    gender: str | None = None
    drugs: list[DrugInfo] = []
    conditions: list[ConditionInfo] = []
    providers: list[str] = []
    interactions: list[DrugInteraction] = []


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # Patient | Drug | Condition | Provider


class GraphEdge(BaseModel):
    from_: str = ""
    to: str = ""
    label: str = ""
    severity: float | None = None

    class Config:
        populate_by_name = True
        fields = {"from_": "from"}


class PatientGraphPath(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[dict] = []
