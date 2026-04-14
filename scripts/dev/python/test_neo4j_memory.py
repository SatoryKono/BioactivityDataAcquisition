#!/usr/bin/env python3
"""Test Neo4j memory instances connectivity."""

from neo4j import GraphDatabase
import os

def test_instance(name: str, uri: str, auth: tuple, expected: str) -> bool:
    """Test a single Neo4j instance."""
    print(f"\n=== Testing {name} ({uri}) ===")
    try:
        driver = GraphDatabase.driver(uri, auth=auth, encrypted=False)
        with driver.session() as session:
            result = session.run('RETURN $msg AS msg', msg=expected)
            msg = result.single()['msg']
            print(f"[OK] Connected: {msg}")
            driver.close()
            return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

# Test both instances
results = []

results.append(test_instance(
    "MCP Instance",
    "bolt://localhost:7687",
    ("neo4j", "bioetl_secure_password"),
    "MCP OK"
))

results.append(test_instance(
    "Audit Instance",
    "bolt://localhost:7688",
    ("neo4j", "audit_secure_password"),
    "Audit OK"
))

# Summary
print("\n" + "="*50)
if all(results):
    print("[OK] Both Neo4j instances are operational and responding")
else:
    print("[ERROR] One or more instances failed to connect")
    exit(1)
