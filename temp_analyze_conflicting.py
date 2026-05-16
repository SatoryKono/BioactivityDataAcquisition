#!/usr/bin/env python3
"""Analyze CONFLICTING fields in semantic pair matrix."""

import csv
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[0]
MATRIX_PATH = REPO_ROOT / "reports" / "semantic_pipeline_audit" / "semantic_pair_matrix_2026-05-16.csv"

with open(MATRIX_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

conflicting = [r for r in rows if r["Semantic Status"] == "CONFLICTING"]

print(f"Total CONFLICTING rows: {len(conflicting)}")
print()

# Count by cluster
clusters = Counter(r["Cluster ID"] for r in conflicting)
print("Rows per cluster:")
for cluster, count in clusters.most_common():
    print(f"  {cluster}: {count}")
print()

# Group by cluster and show details
for cluster in sorted(clusters.keys()):
    cluster_rows = [r for r in conflicting if r["Cluster ID"] == cluster]
    print(f"\n{cluster.upper()}:")
    print(f"  Total rows: {len(cluster_rows)}")

    # Unique fields
    fields = set()
    for r in cluster_rows:
        fields.add(r["Field A"])
        fields.add(r["Field B"])
    print(f"  Fields: {sorted(fields)}")

    # Unique pipelines
    pipelines = set()
    for r in cluster_rows:
        pipelines.add(r["Pipeline A"])
        pipelines.add(r["Pipeline B"])
    print(f"  Pipelines: {sorted(pipelines)}")

    # Show all pairs
    print(f"  Pairs:")
    for r in cluster_rows:
        print(f"    {r['Pipeline A']}.{r['Field A']} <-> {r['Pipeline B']}.{r['Field B']}")
