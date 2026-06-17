"""
demos/impossible_queries.py

Demonstrates queries that are impossible (or unreliable) for vector-only RAG
but trivially handled by GraphRAG via graph traversal.

Run: python demos/impossible_queries.py
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_QUERIES = [
    {
        "id": 1,
        "category": "multi_hop_interaction",
        "query": (
            "Which patients with Type 2 Diabetes are taking 3 or more medications"
            " that interact dangerously with each other?"
        ),
        "why_vector_fails": (
            "Vector search can retrieve documents mentioning 'diabetes' and 'drug interactions', "
            "but cannot traverse the graph path: "
            "Patient → HAS_CONDITION → Diabetes AND Patient → TAKES_DRUG → Drug1"
            " → INTERACTS_WITH → Drug2 ← TAKES_DRUG ← Patient. "
            "It will return text fragments without linking the actual patient-drug-interaction chain."
        ),
        "graph_cypher": """
MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition {name: 'Type 2 Diabetes'})
MATCH (p)-[:TAKES_DRUG]->(d:Drug)
WITH p, count(d) AS drugCount
WHERE drugCount >= 3
MATCH (p)-[:TAKES_DRUG]->(d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p)
WHERE i.severity > 0.7
RETURN p.patientID, p.name, drugCount, collect(DISTINCT d1.name + ' ↔ ' + d2.name) AS interactions
ORDER BY size(interactions) DESC
        """,
    },
    {
        "id": 2,
        "category": "contraindication_check",
        "query": (
            "Which patients with Chronic Kidney Disease are currently taking drugs"
            " that are contraindicated for their condition?"
        ),
        "why_vector_fails": (
            "Vector RAG may find text about CKD drug contraindications generically, "
            "but cannot check each individual patient's drug list against their specific conditions "
            "without traversing the CONTRAINDICATED_FOR relationship: "
            "Drug → CONTRAINDICATED_FOR → Condition ← HAS_CONDITION ← Patient → TAKES_DRUG → Drug."
        ),
        "graph_cypher": """
MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition {name: 'Chronic Kidney Disease'})
MATCH (p)-[:TAKES_DRUG]->(d:Drug)-[:CONTRAINDICATED_FOR]->(c)
RETURN p.patientID AS patient, p.name AS name, d.name AS contraindicatedDrug, c.name AS condition
ORDER BY p.patientID
        """,
    },
    {
        "id": 3,
        "category": "k_hop_chain",
        "query": (
            "Show me the drug interaction chain starting from Warfarin"
            " — what drugs interact with Warfarin and what do those drugs interact with?"
        ),
        "why_vector_fails": (
            "Variable-length path matching (INTERACTS_WITH*1..2) is structurally impossible "
            "in vector space. A vector search for 'Warfarin interactions' returns documents "
            "about Warfarin but cannot enumerate the 2-hop chain of interacting drug pairs."
        ),
        "graph_cypher": """
MATCH path = (d:Drug {name: 'Warfarin'})-[:INTERACTS_WITH*1..2]-(d2:Drug)
WHERE d <> d2
RETURN [node IN nodes(path) | node.name] AS chain,
       length(path) AS hops,
       [rel IN relationships(path) | rel.severity] AS severities
ORDER BY hops, severities[-1] DESC
LIMIT 20
        """,
    },
    {
        "id": 4,
        "category": "shared_provider_cohort",
        "query": (
            "Are there patients who share the same doctor, have overlapping diagnoses,"
            " AND are on medications that interact with each other?"
        ),
        "why_vector_fails": (
            "This requires a 3-way graph join across three relationship types simultaneously: "
            "Patient → TREATED_BY → HealthcareProvider, "
            "Patient → HAS_CONDITION → Condition, "
            "Patient → TAKES_DRUG → Drug → INTERACTS_WITH → Drug. "
            "No vector similarity measure can discover this structural pattern."
        ),
        "graph_cypher": """
MATCH (p1:Patient)-[:TREATED_BY]->(hp:HealthcareProvider)<-[:TREATED_BY]-(p2:Patient)
WHERE id(p1) < id(p2)
MATCH (p1)-[:HAS_CONDITION]->(c:Condition)<-[:HAS_CONDITION]-(p2)
MATCH (p1)-[:TAKES_DRUG]->(d1:Drug)-[:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p2)
RETURN p1.patientID, p2.patientID, hp.name,
       collect(DISTINCT c.name) AS sharedConditions,
       collect(DISTINCT d1.name + ' ↔ ' + d2.name) AS interactions
        """,
    },
    {
        "id": 5,
        "category": "serotonin_syndrome_risk",
        "query": "Which patients are at risk for serotonin syndrome based on their current medications?",
        "why_vector_fails": (
            "Vector RAG can retrieve generic information about serotonin syndrome but cannot "
            "identify which specific patients in the database take two or more serotonergic drugs. "
            "This requires: Patient → TAKES_DRUG → SSRI AND Patient → TAKES_DRUG → Tramadol/SNRI "
            "with INTERACTS_WITH.mechanism containing 'serotonin'."
        ),
        "graph_cypher": """
MATCH (p:Patient)-[:TAKES_DRUG]->(d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)<-[:TAKES_DRUG]-(p)
WHERE i.severity >= 0.75
  AND (toLower(i.mechanism) CONTAINS 'serotonin')
RETURN p.patientID, p.name, d1.name AS drug1, d2.name AS drug2,
       i.severity AS severity, i.mechanism AS mechanism
ORDER BY i.severity DESC
        """,
    },
]


def run_graph_demos(verbose: bool = True) -> None:
    """Execute each demo query against the graph and display results."""
    from src.graphrag.retrievers.graph_retriever import GraphRetriever
    from src.graphrag.retrievers.vector_retriever import VectorRetriever

    graph   = GraphRetriever()
    vector  = VectorRetriever()

    for demo in DEMO_QUERIES:
        print(f"\n{'='*70}")
        print(f"DEMO {demo['id']}: {demo['category'].upper()}")
        print(f"Query: {demo['query']}")
        print("\nWhy Vector-Only RAG Fails:")
        print(f"  {demo['why_vector_fails']}")

        # Graph result
        print("\n[GRAPH RESULT]")
        try:
            if demo["id"] == 1:
                results = graph.find_high_risk_patients(limit=5)
            elif demo["id"] == 2:
                results = graph.find_patients_with_contraindicated_drugs(limit=5)
            elif demo["id"] == 3:
                results = graph.k_hop_drug_interactions("Warfarin", k=2)
            elif demo["id"] == 4:
                results = graph.find_shared_doctor_cohorts(limit=5)
            elif demo["id"] == 5:
                results = graph.find_high_risk_patients(
                    min_drug_count=2, min_interaction_severity=0.75, limit=5
                )
            else:
                results = []

            if results:
                for r in results[:3]:
                    print(f"  {json.dumps(r, indent=4, default=str)}")
            else:
                print("  No results (graph may not be populated yet)")
        except Exception as e:
            print(f"  Graph error: {e}")

        # Vector result (to demonstrate limitation)
        print("\n[VECTOR-ONLY RESULT] (limited — no graph traversal)")
        try:
            vector_hits = vector.search_similar_patients(demo["query"], top_k=2)
            for h in vector_hits:
                print(f"  Score {h['score']:.3f}: {h['name']} — conditions: {h['conditions']}, drugs: {h['drugs']}")
        except Exception as e:
            print(f"  Vector error: {e}")

    graph.close()


if __name__ == "__main__":
    run_graph_demos()
