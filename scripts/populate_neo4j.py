"""
scripts/populate_neo4j.py

Copies CSV files to the Neo4j Docker import directory and executes
the Cypher import script to populate the graph.

Prerequisites:
  - Docker container 'medical-neo4j' must be running
  - data/ CSVs must exist (run generate_medical_data.py first)
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from src.config import config

NEO4J_URI       = config.NEO4J_URI
NEO4J_USER      = config.NEO4J_USER
NEO4J_PASSWORD  = config.NEO4J_PASSWORD
CONTAINER_NAME  = "medical-neo4j"
DATA_DIR        = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CYPHER_SCRIPT   = os.path.join(os.path.dirname(__file__), "import_data.cypher")

CSV_FILES = [
    "patients.csv",
    "drugs.csv",
    "conditions.csv",
    "providers.csv",
    "interactions.csv",
    "contraindications.csv",
    "patient_drugs.csv",
    "patient_conditions.csv",
    "patient_providers.csv",
    "procedures.csv",
    "clinical_findings.csv",
    "condition_treatments.csv",
    "patient_procedures.csv",
    "patient_observations.csv",
]


def copy_csvs_to_neo4j():
    """Copy CSV files into the Neo4j Docker container's import directory."""
    print("Copying CSV files to Neo4j import directory...")
    for csv_file in CSV_FILES:
        src = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(src):
            print(f"  WARNING: {src} not found — run generate_medical_data.py first")
            continue
        cmd = ["docker", "cp", src, f"{CONTAINER_NAME}:/var/lib/neo4j/import/{csv_file}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Copied {csv_file}")
        else:
            print(f"  ✗ Failed to copy {csv_file}: {result.stderr.strip()}")


def wait_for_neo4j(driver, retries: int = 10, delay: int = 5):
    """Wait until Neo4j is ready to accept connections."""
    for attempt in range(1, retries + 1):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            print("  ✓ Neo4j is ready")
            return
        except Exception as e:
            print(f"  Attempt {attempt}/{retries}: Neo4j not ready yet ({e})")
            time.sleep(delay)
    raise RuntimeError("Neo4j did not become ready in time.")


def run_cypher_script(driver):
    """Execute the Cypher import script statement by statement."""
    print(f"\nExecuting Cypher script: {CYPHER_SCRIPT}")
    with open(CYPHER_SCRIPT, "r", encoding="utf-8") as f:
        raw = f.read()

    # Strip comment lines and split on semicolons
    statements = []
    for stmt in raw.split(";"):
        lines = [line for line in stmt.splitlines() if not line.strip().startswith("//")]
        cleaned = "\n".join(lines).strip()
        if cleaned:
            statements.append(cleaned)

    with driver.session() as session:
        for i, stmt in enumerate(statements, 1):
            try:
                result = session.run(stmt)
                result.consume()  # Drain result
                print(f"  ✓ Statement {i}/{len(statements)} executed")
            except Exception as e:
                print(f"  ✗ Statement {i} failed: {e}")
                print(f"    Statement was: {stmt[:120]}...")


def print_summary(driver):
    """Print node and relationship counts."""
    print("\nGraph population summary:")
    with driver.session() as session:
        counts = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
        for record in counts:
            print(f"  {record['label']}: {record['count']} nodes")

        rel_counts = session.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC")
        print()
        for record in rel_counts:
            print(f"  [{record['rel']}]: {record['count']} relationships")


def main():
    # Step 1: Copy CSV data
    copy_csvs_to_neo4j()

    # Step 2: Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        wait_for_neo4j(driver)

        # Step 3: Run Cypher import
        run_cypher_script(driver)

        # Step 4: Print summary
        print_summary(driver)

    finally:
        driver.close()

    print("\nNeo4j population complete.")


if __name__ == "__main__":
    main()
