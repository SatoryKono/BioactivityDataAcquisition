import argparse
import json
import subprocess
import sys
from pathlib import Path
import yaml
from collections import defaultdict

def _load_test_matrix():
    with open("configs/quality/test_matrix.yaml") as f:
        return yaml.safe_load(f)

def run_all_collection():
    cmd = ["uv", "run", "pytest", "--collect-only", "-q", "-p", "pytest_nodeid_plugin", "--disable-warnings", "--nodeid-out", ".nodeid_inventory_all.json"]
    paths = ["tests/", ".github/workflows/", ".github/actions/", "scripts/", "configs/quality/"]
    for p in paths:
        if Path(p).exists():
            cmd.append(p)

    result = subprocess.run(cmd, capture_output=True, text=True)
    out_file = Path(".nodeid_inventory_all.json")
    if not out_file.exists():
        print(f"Failed to collect: {result.stderr}\n{result.stdout}", file=sys.stderr)
        return []

    with open(out_file) as f:
        collected = json.load(f)
    out_file.unlink()

    return collected

def match_marker_expr(markers, expr):
    if not expr:
        return True
    parts = expr.split(" and ")
    for part in parts:
        part = part.strip()
        if part.startswith("not "):
            m = part[4:]
            if m in markers:
                return False
        else:
            if part not in markers:
                return False
    return True

def get_canonical_owner(owners, file):
    path = file.lower()
    if "agentmemory" in path or "memory" in path:
        return "AgentMemory"
    if "agent" in path or "ai" in path or "codex" in path or "junie" in path:
        return "Agent"
    if "doc" in path or "markdown" in path:
        return "Docs"
    if "diagram" in path:
        return "Diagram"
    if "e2e" in path or "performance" in path or "smoke" in path or "integration" in path:
        return "FullOnly"
    return "Core"

def get_semantic_production_criticality(file, markers, canonical_owner):
    if canonical_owner in ("Core", "FullOnly"):
        return "critical"
    return "non-critical"

def get_workflow_job(canonical_owner):
    return "tests"

def main():
    parser = argparse.ArgumentParser(description="Build pytest nodeid inventory.")
    parser.add_argument("--output", default="reports/quality/pytest-nodeid-inventory.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    matrix = _load_test_matrix()
    lanes = matrix.get("test_lanes", {}).get("lanes", {})

    collected = run_all_collection()

    nodes_out = []

    for item in collected:
        nodeid = item["nodeid"]
        file = item["file"]
        type_ = item["type"]
        markers = item["markers"]
        fixtures = item["fixtures"]

        owners = []
        for lane_name, lane_info in lanes.items():
            lane_paths = lane_info.get("paths", [])
            in_path = False
            for p in lane_paths:
                if file.startswith(p):
                    in_path = True
                    break

            if not in_path:
                continue

            if match_marker_expr(markers, lane_info.get("marker_expression", "")):
                owners.append(lane_name)

        canonical_owner = get_canonical_owner(owners, file)

        overlap_rationale = None
        if len(owners) > 1:
            overlap_rationale = "intentional smoke execution"

        execution_policy = owners[0] if owners else "TBD"

        node_out = {
            "nodeid": nodeid,
            "file": file,
            "type": type_,
            "semantic_production_criticality": get_semantic_production_criticality(file, markers, canonical_owner),
            "canonical_owner": canonical_owner,
            "execution_policy": execution_policy,
            "fixtures": fixtures,
            "workflow_job": get_workflow_job(canonical_owner),
            "overlap_rationale": overlap_rationale
        }
        nodes_out.append(node_out)

    inventory = {
        "schema_version": 1,
        "nodes": sorted(nodes_out, key=lambda x: x["nodeid"]),
        "count": len(nodes_out)
    }

    output_path = Path(args.output)

    if args.check:
        if not output_path.exists():
            print(f"Inventory {output_path} does not exist for check.", file=sys.stderr)
            return 1
        with open(output_path) as f:
            existing = json.load(f)

        if existing.get("count") != inventory["count"]:
            print(f"Inventory count mismatch: existing={existing.get('count')}, new={inventory['count']}", file=sys.stderr)
            return 1
        print("Inventory matches.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, sort_keys=True)

    print(f"Wrote {len(nodes_out)} nodeids to {output_path}.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
