"""
src/graphrag/retrievers/graph_retriever.py

Cypher-based retrieval from the Neo4j knowledge graph.
Provides multi-hop traversal, drug interaction chains, and
patient cohort discovery — things impossible with vector search alone.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from neo4j import GraphDatabase, Driver as Neo4jDriver
from src.config import config


class GraphRetriever:
    """Execute Cypher queries for multi-hop graph traversal."""

    def __init__(self, driver: Neo4jDriver | None = None):
        self.driver = driver or GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
        )

    def close(self):
        self.driver.close()

    # ─── Patient queries ──────────────────────────────────────────────────────

    def find_high_risk_patients(
        self,
        min_drug_count: int = 3,
        min_interaction_severity: float = 0.7,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find patients on 3+ drugs where at least one pair interacts dangerously.
        This is the core 'impossible for vector search' query.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Patient)-[:TAKES_DRUG]->(d:Drug)
                WITH p, count(d) AS drugCount
                WHERE drugCount >= $minDrugs
                MATCH (p)-[:TAKES_DRUG]->(d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p)
                WHERE i.severity >= $minSeverity
                WITH p, drugCount,
                     collect(DISTINCT {drug1: d1.name, drug2: d2.name,
                         severity: i.severity, mechanism: i.mechanism}) AS interactions
                RETURN p.patientID   AS patientID,
                       p.name        AS name,
                       p.age         AS age,
                       p.gender      AS gender,
                       drugCount,
                       interactions
                ORDER BY size(interactions) DESC, drugCount DESC
                LIMIT $limit
                """,
                minDrugs=min_drug_count,
                minSeverity=min_interaction_severity,
                limit=limit,
            )
            return [dict(r) for r in result]

    def find_patients_with_conditions(
        self,
        condition_names: list[str],
        require_all: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Return patients who have any (or all) of the specified conditions."""
        if require_all:
            cypher = """
            MATCH (p:Patient)
            WHERE ALL(cname IN $conditions WHERE EXISTS {
                MATCH (p)-[:HAS_CONDITION]->(c:Condition {name: cname})
            })
            OPTIONAL MATCH (p)-[:TAKES_DRUG]->(d:Drug)
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c2:Condition)
            RETURN p.patientID AS patientID, p.name AS name, p.age AS age,
                   collect(DISTINCT c2.name) AS conditions,
                   collect(DISTINCT d.name)  AS drugs
            LIMIT $limit
            """
        else:
            cypher = """
            MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition)
            WHERE c.name IN $conditions
            WITH p, collect(DISTINCT c.name) AS matchedConditions
            OPTIONAL MATCH (p)-[:TAKES_DRUG]->(d:Drug)
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c2:Condition)
            RETURN p.patientID AS patientID, p.name AS name, p.age AS age,
                   collect(DISTINCT c2.name) AS conditions,
                   collect(DISTINCT d.name)  AS drugs,
                   matchedConditions
            LIMIT $limit
            """
        with self.driver.session() as session:
            result = session.run(cypher, conditions=condition_names, limit=limit)
            return [dict(r) for r in result]

    def find_patients_with_contraindicated_drugs(self, limit: int = 15) -> list[dict]:
        """
        Find patients taking a drug that is contraindicated for one of their conditions.
        Demonstrates CONTRAINDICATED_FOR relationship traversal.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition)<-[:CONTRAINDICATED_FOR]-(d:Drug)<-[:TAKES_DRUG]-(p)
                WITH p, d, c
                OPTIONAL MATCH (p)-[:TAKES_DRUG]->(allDrugs:Drug)
                OPTIONAL MATCH (p)-[:HAS_CONDITION]->(allConds:Condition)
                RETURN p.patientID  AS patientID,
                       p.name       AS name,
                       p.age        AS age,
                       p.gender     AS gender,
                       d.name       AS drug,
                       c.name       AS contraindicated_condition,
                       collect(DISTINCT allConds.name) AS conditions,
                       collect(DISTINCT allDrugs.name) AS drugs
                ORDER BY p.patientID
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(r) for r in result]

    def find_shared_doctor_cohorts(self, limit: int = 10) -> list[dict]:
        """
        Find pairs of patients sharing a doctor AND overlapping conditions AND interacting drugs.
        3-way graph join — only possible via graph traversal.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p1:Patient)-[:TREATED_BY]->(hp:HealthcareProvider)<-[:TREATED_BY]-(p2:Patient)
                WHERE id(p1) < id(p2)
                MATCH (p1)-[:HAS_CONDITION]->(c:Condition)<-[:HAS_CONDITION]-(p2)
                MATCH (p1)-[:TAKES_DRUG]->(d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p2)
                RETURN p1.patientID  AS patient1,
                       p2.patientID  AS patient2,
                       hp.name       AS sharedDoctor,
                       collect(DISTINCT c.name)                              AS sharedConditions,
                       collect(DISTINCT d1.name + ' ↔ ' + d2.name)          AS interactingDrugs,
                       collect(DISTINCT i.severity)                          AS severities
                ORDER BY size(interactingDrugs) DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(r) for r in result]

    # ─── Drug queries ─────────────────────────────────────────────────────────

    def k_hop_drug_interactions(self, drug_name: str, k: int = 2) -> list[dict]:
        """Find all drugs reachable via k-hop interaction chains from a given drug."""
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (d:Drug {{name: $drug}})-[:INTERACTS_WITH*1..{k}]-(d2:Drug)
                WHERE d <> d2
                RETURN [node IN nodes(path) | node.name]          AS chain,
                       length(path)                                AS hops,
                       [rel IN relationships(path) | rel.severity] AS severities
                ORDER BY hops, severities[-1] DESC
                LIMIT 30
                """,
                drug=drug_name,
            )
            return [dict(r) for r in result]

    def get_drug_interaction_network(self, min_severity: float = 0.7) -> list[dict]:
        """Return all high-severity drug interactions for network visualisation."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)
                WHERE i.severity >= $minSeverity
                RETURN d1.name AS drug1, d2.name AS drug2,
                       i.severity AS severity, i.mechanism AS mechanism
                ORDER BY i.severity DESC
                """,
                minSeverity=min_severity,
            )
            return [dict(r) for r in result]

    # ─── Analytics ────────────────────────────────────────────────────────────

    def get_graph_statistics(self) -> dict:
        """Return high-level graph counts."""
        with self.driver.session() as session:
            node_counts = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
            )
            rel_counts = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count"
            )
            return {
                "nodes": {r["label"]: r["count"] for r in node_counts},
                "relationships": {r["type"]: r["count"] for r in rel_counts},
            }

    def get_patient_by_id(self, patient_id: str) -> dict | None:
        """Fetch a single patient's full profile from the graph."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Patient {patientID: $pid})
                OPTIONAL MATCH (p)-[td:TAKES_DRUG]->(d:Drug)
                OPTIONAL MATCH (p)-[hc:HAS_CONDITION]->(c:Condition)
                OPTIONAL MATCH (p)-[:TREATED_BY]->(hp:HealthcareProvider)
                RETURN p.patientID AS patientID, p.name AS name,
                       p.age AS age, p.gender AS gender,
                       collect(DISTINCT {name: d.name, dosage: td.dosage, frequency: td.frequency}) AS drugs,
                       collect(DISTINCT {name: c.name, severity: hc.severity, since: hc.diagnosisDate}) AS conditions,
                       collect(DISTINCT hp.name) AS providers
                """,
                pid=patient_id,
            )
            record = result.single()
            return dict(record) if record else None

    def get_patient_graph_paths(self, patient_id: str) -> dict:
        """
        Return all relationship paths from a patient node for graph visualisation.

        Collects:
          - Patient → HAS_CONDITION → Condition
          - Patient → TAKES_DRUG   → Drug
          - Patient → TREATED_BY   → HealthcareProvider
          - Drug    → INTERACTS_WITH → Drug  (only drugs the patient takes)

        Returns a dict:
          {
            "nodes": [{"id": str, "label": str, "type": str}, ...],
            "edges": [{"from": str, "to": str, "label": str, "severity": float|None}, ...],
          }
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Patient {patientID: $pid})
                OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
                OPTIONAL MATCH (p)-[:TAKES_DRUG]->(d:Drug)
                OPTIONAL MATCH (p)-[:TREATED_BY]->(hp:HealthcareProvider)
                OPTIONAL MATCH (p)-[:UNDERWENT]->(proc:Procedure)
                OPTIONAL MATCH (p)-[:HAS_OBSERVATION]->(cf:ClinicalFinding)
                OPTIONAL MATCH (p)-[:TAKES_DRUG]->(d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p)
                OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c_t:Condition)-[:TREATED_BY]->(d_t:Drug)
                RETURN
                    p.patientID AS patientID,
                    p.name      AS patientName,
                    p.age       AS age,
                    p.gender    AS gender,
                    collect(DISTINCT c.name)                                           AS conditions,
                    collect(DISTINCT d.name)                                           AS drugs,
                    collect(DISTINCT hp.name)                                          AS providers,
                    collect(DISTINCT proc.name)                                        AS procedures,
                    collect(DISTINCT cf.name)                                          AS clinicalFindings,
                    collect(DISTINCT {
                        drug1:     d1.name,
                        drug2:     d2.name,
                        severity:  i.severity,
                        mechanism: i.mechanism
                    })                                                                 AS interactions,
                    collect(DISTINCT {
                        condition: c_t.name,
                        drug:      d_t.name
                    })                                                                 AS conditionTreatments                """,
                pid=patient_id,
            )
            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}

        nodes: list[dict] = []
        edges: list[dict] = []
        seen_node_ids: set = set()

        def add_node(node_id: str, label: str, node_type: str):
            if node_id not in seen_node_ids:
                nodes.append({"id": node_id, "label": label, "type": node_type})
                seen_node_ids.add(node_id)

        # Patient (root)
        add_node(patient_id, record["patientName"] or patient_id, "Patient")

        # Conditions
        for name in record["conditions"]:
            if name:
                nid = f"cond::{name}"
                add_node(nid, name, "Condition")
                edges.append({"from": patient_id, "to": nid, "label": "HAS_CONDITION", "severity": None})

        # Drugs
        for name in record["drugs"]:
            if name:
                nid = f"drug::{name}"
                add_node(nid, name, "Drug")
                edges.append({"from": patient_id, "to": nid, "label": "TAKES_DRUG", "severity": None})

        # Providers
        for name in record["providers"]:
            if name:
                nid = f"prov::{name}"
                add_node(nid, name, "Provider")
                edges.append({"from": patient_id, "to": nid, "label": "TREATED_BY", "severity": None})

        # Procedures
        for name in record["procedures"]:
            if name:
                nid = f"proc::{name}"
                add_node(nid, name, "Procedure")
                edges.append({"from": patient_id, "to": nid, "label": "UNDERWENT", "severity": None})

        # Clinical Findings
        for name in record["clinicalFindings"]:
            if name:
                nid = f"cf::{name}"
                add_node(nid, name, "ClinicalFinding")
                edges.append({"from": patient_id, "to": nid, "label": "HAS_OBSERVATION", "severity": None})

        # Drug–Drug interactions
        for inter in record["interactions"]:
            d1, d2 = inter.get("drug1"), inter.get("drug2")
            if d1 and d2:
                sev = inter.get("severity")
                edges.append({
                    "from":     f"drug::{d1}",
                    "to":       f"drug::{d2}",
                    "label":    f"INTERACTS (sev {sev:.2f})" if sev else "INTERACTS_WITH",
                    "severity": sev,
                })
        
        # Condition-Drug treatments
        for ct in record["conditionTreatments"]:
            c_name, d_name = ct.get("condition"), ct.get("drug")
            if c_name and d_name:
                edges.append({
                    "from": f"cond::{c_name}",
                    "to": f"drug::{d_name}",
                    "label": "TREATED_BY",
                    "severity": None
                })

        return {"nodes": nodes, "edges": edges}
