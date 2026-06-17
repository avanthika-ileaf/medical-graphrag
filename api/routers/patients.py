"""
api/routers/patients.py

GET /api/patients                  — List high-risk patients (paginated)
GET /api/patients/high-risk        — Patients on 3+ interacting drugs
GET /api/patients/contraindicated  — Patients with contraindicated drugs
GET /api/patients/{id}             — Full patient profile
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Query
from api.models.patient import PatientSummary, PatientProfile, DrugInfo, ConditionInfo, DrugInteraction
from api.dependencies import get_graph_retriever

router = APIRouter(prefix="/patients", tags=["Patients"])


def _risk_level(drug_count: int, interaction_count: int) -> str:
    if interaction_count >= 2 or drug_count >= 5:
        return "high"
    elif interaction_count >= 1 or drug_count >= 3:
        return "medium"
    return "low"


def _to_patient_summary(raw: dict) -> PatientSummary:
    interactions = []
    for ix in raw.get("interactions", []):
        if isinstance(ix, dict) and ix.get("drug1") and ix.get("drug2"):
            interactions.append(DrugInteraction(
                drug1=ix.get("drug1", ""),
                drug2=ix.get("drug2", ""),
                severity=float(ix.get("severity") or 0),
                mechanism=ix.get("mechanism", ""),
            ))

    drug_count = int(raw.get("drugCount") or len(raw.get("drugs", [])))
    return PatientSummary(
        patientID=str(raw.get("patientID", "")),
        name=str(raw.get("name", "")),
        age=raw.get("age"),
        gender=raw.get("gender"),
        drugCount=drug_count,
        conditions=raw.get("conditions", []) or [],
        drugs=raw.get("drugs", []) or [],
        interactions=interactions,
        risk_level=_risk_level(drug_count, len(interactions)),
    )


@router.get("", response_model=list[PatientSummary])
def list_patients(
    limit: int = Query(20, ge=1, le=100),
    filter: str = Query("high-risk", description="Filter: high-risk | contraindicated | all"),
):
    """List patients, defaulting to high-risk patients ordered by interaction count."""
    try:
        gr = get_graph_retriever()
        if filter == "contraindicated":
            raw = gr.find_patients_with_contraindicated_drugs(limit=limit)
        else:
            raw = gr.find_high_risk_patients(limit=limit)
        return [_to_patient_summary(r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/high-risk", response_model=list[PatientSummary])
def high_risk_patients(
    limit: int = Query(20, ge=1, le=100),
    min_severity: float = Query(0.7, ge=0.0, le=1.0),
):
    """Return patients on 3+ drugs with dangerous interactions."""
    try:
        gr = get_graph_retriever()
        raw = gr.find_high_risk_patients(
            min_drug_count=3,
            min_interaction_severity=min_severity,
            limit=limit,
        )
        return [_to_patient_summary(r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/contraindicated", response_model=list[PatientSummary])
def contraindicated_patients(limit: int = Query(20, ge=1, le=100)):
    """Return patients taking drugs contraindicated for their conditions."""
    try:
        gr = get_graph_retriever()
        raw = gr.find_patients_with_contraindicated_drugs(limit=limit)
        return [_to_patient_summary(r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/condition/{condition_name}", response_model=list[PatientSummary])
def patients_by_condition(
    condition_name: str,
    limit: int = Query(20, ge=1, le=100),
):
    """Return patients who have the specified condition."""
    try:
        gr = get_graph_retriever()
        raw = gr.find_patients_with_conditions([condition_name], limit=limit)
        return [_to_patient_summary(r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {e}")


@router.get("/{patient_id}", response_model=PatientProfile)
def get_patient_profile(patient_id: str):
    """Return the full graph profile for a single patient."""
    try:
        gr = get_graph_retriever()
        raw = gr.get_patient_by_id(patient_id)
        if not raw:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        drugs = []
        for d in raw.get("drugs", []):
            if isinstance(d, dict) and d.get("name"):
                drugs.append(DrugInfo(
                    name=d.get("name", ""),
                    dosage=d.get("dosage"),
                    frequency=d.get("frequency"),
                ))

        conditions = []
        for c in raw.get("conditions", []):
            if isinstance(c, dict) and c.get("name"):
                conditions.append(ConditionInfo(
                    name=c.get("name", ""),
                    severity=c.get("severity"),
                    since=str(c.get("since", "")) if c.get("since") else None,
                ))

        # Fetch interaction data via patient path
        path_data = gr.get_patient_graph_paths(patient_id)
        interactions = []
        for edge in path_data.get("edges", []):
            if edge.get("severity") and edge.get("severity", 0) > 0:
                from_id = edge.get("from", "")
                to_id = edge.get("to", "")
                d1 = from_id.replace("drug::", "") if from_id.startswith("drug::") else from_id
                d2 = to_id.replace("drug::", "") if to_id.startswith("drug::") else to_id
                if d1 != d2:
                    interactions.append(DrugInteraction(
                        drug1=d1, drug2=d2,
                        severity=float(edge.get("severity", 0)),
                        mechanism="",
                    ))

        return PatientProfile(
            patientID=str(raw.get("patientID", patient_id)),
            name=str(raw.get("name", "")),
            age=raw.get("age"),
            gender=raw.get("gender"),
            drugs=drugs,
            conditions=conditions,
            providers=raw.get("providers", []) or [],
            interactions=interactions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Patient profile error: {e}")
