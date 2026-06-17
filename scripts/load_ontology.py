"""
scripts/load_ontology.py

Parses the OWL ontology (ontology/medical_ontology.owl) and creates
corresponding Neo4j schema constraints and ontology metadata nodes.
"""

import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rdflib import Graph, RDF, RDFS, OWL, Namespace
from neo4j import GraphDatabase
from src.config import config

ONTOLOGY_NS = Namespace("http://medical-graphrag.org/ontology#")
ONTOLOGY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ontology", "medical_ontology.owl")

NEO4J_URI  = config.NEO4J_URI
NEO4J_USER = config.NEO4J_USER
NEO4J_PASS = config.NEO4J_PASSWORD


def parse_ontology(path: str) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    print(f"Parsed ontology: {len(g)} triples from {path}")
    return g


def extract_classes(g: Graph) -> list[dict]:
    classes = []
    for cls in g.subjects(RDF.type, OWL.Class):
        label = str(g.value(cls, RDFS.label) or cls.split("#")[-1])
        comment = str(g.value(cls, RDFS.comment) or "")
        parent_uri = g.value(cls, RDFS.subClassOf)
        parent = str(parent_uri).split("#")[-1] if parent_uri else None
        classes.append({"iri": str(cls), "label": label, "comment": comment, "parent": parent})
    return classes


def extract_object_properties(g: Graph) -> list[dict]:
    props = []
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        label = str(g.value(p, RDFS.label) or p.split("#")[-1])
        domain = g.value(p, RDFS.domain)
        range_ = g.value(p, RDFS.range)
        symmetric = (p, RDF.type, OWL.SymmetricProperty) in g
        props.append({
            "iri": str(p),
            "label": label,
            "domain": str(domain).split("#")[-1] if domain else None,
            "range": str(range_).split("#")[-1] if range_ else None,
            "symmetric": symmetric,
        })
    return props


def load_schema_to_neo4j(driver, classes: list[dict], properties: list[dict]) -> None:
    with driver.session() as session:
        # Create uniqueness constraints for main node types
        constraints = [
            "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patientID IS UNIQUE",
            "CREATE CONSTRAINT drug_name IF NOT EXISTS FOR (d:Drug) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT condition_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT provider_name IF NOT EXISTS FOR (hp:HealthcareProvider) REQUIRE hp.name IS UNIQUE",
        ]
        for cypher in constraints:
            session.run(cypher)
        print("  ✓ Neo4j constraints created")

        # Store OWL class hierarchy as OntologyClass nodes
        for cls in classes:
            session.run(
                """
                MERGE (o:OntologyClass {iri: $iri})
                SET o.label = $label,
                    o.comment = $comment,
                    o.parent = $parent
                """,
                iri=cls["iri"],
                label=cls["label"],
                comment=cls["comment"],
                parent=cls["parent"],
            )

        # Store object properties as OntologyProperty nodes
        for prop in properties:
            session.run(
                """
                MERGE (p:OntologyProperty {iri: $iri})
                SET p.label = $label,
                    p.domain = $domain,
                    p.range = $range,
                    p.symmetric = $symmetric
                """,
                iri=prop["iri"],
                label=prop["label"],
                domain=prop["domain"],
                range=prop["range"],
                symmetric=prop["symmetric"],
            )

        print(f"  ✓ {len(classes)} OWL classes stored as OntologyClass nodes")
        print(f"  ✓ {len(properties)} object properties stored as OntologyProperty nodes")


def main():
    print("Loading OWL ontology into Neo4j...")
    g = parse_ontology(ONTOLOGY_PATH)
    classes = extract_classes(g)
    properties = extract_object_properties(g)

    print(f"  Found {len(classes)} classes, {len(properties)} object properties")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    try:
        load_schema_to_neo4j(driver, classes, properties)
    finally:
        driver.close()

    print("Ontology loading complete.")


if __name__ == "__main__":
    main()
