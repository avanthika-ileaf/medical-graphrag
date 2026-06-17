"""
tests/test_connections.py

Verify Neo4j and Qdrant are reachable and properly initialized.
Run: python tests/test_connections.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from src.config import config


def test_neo4j_connection() -> bool:
    print("Testing Neo4j connection...")
    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
        )
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j Connected!' AS message, datetime() AS ts")
            record = result.single()
            print(f"  [OK] {record['message']} at {record['ts']}")

        # Check node counts
        with driver.session() as session:
            counts = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
            for r in counts:
                if r["label"]:
                    print(f"  [OK] {r['label']}: {r['count']} nodes")

        driver.close()
        return True
    except Exception as e:
        print(f"  [FAIL] Neo4j connection failed: {e}")
        return False


def test_qdrant_connection() -> bool:
    print("\nTesting Qdrant connection...")
    try:
        client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        print(f"  [OK] Qdrant connected. Collections: {collection_names or '(none yet)'}")

        for name in collection_names:
            info = client.get_collection(name)
            print(f"  [OK] {name}: {info.points_count} vectors ({info.config.params.vectors.size}-dim)")

        return True
    except Exception as e:
        print(f"  [FAIL] Qdrant connection failed: {e}")
        return False


# def test_openai_config() -> bool:  # OpenAI test (commented, preserved for reference)
#     print("\nTesting OpenAI configuration...")
#     if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-your"):
#         print("  ✗ OPENAI_API_KEY not set in .env")
#         return False
#     print(f"  ✓ OPENAI_API_KEY is set (model: {config.EMBEDDING_MODEL}, LLM: {config.LLM_MODEL})")
#     print(f"  [OK] OPENAI_API_KEY is set (model: {config.EMBEDDING_MODEL}, LLM: {config.LLM_MODEL})")
#     return True


def test_regolo_config() -> bool:
    print("\nTesting Regolo configuration...")
    if not config.REGOLO_API_KEY or config.REGOLO_API_KEY.startswith("sk-your"):
        print("  [FAIL] REGOLO_API_KEY not set in .env")
        return False
    print(
        f"  [OK] REGOLO_API_KEY is set  "
        f"(embedding: {config.EMBEDDING_MODEL}, LLM: {config.LITELLM_MODEL})"
    )
    return True


def main():
    print("=" * 50)
    print("Medical GraphRAG — Connection Tests")
    print("=" * 50)

    results = {
        "neo4j":  test_neo4j_connection(),
        "qdrant": test_qdrant_connection(),
        "regolo": test_regolo_config(),
    }

    print("\n" + "=" * 50)
    print("Summary:")
    all_passed = True
    for name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"  {name:10s}: {status}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("All connections OK. Ready to populate and query.")
    else:
        print("Some connections failed. Check Docker status and .env settings.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
