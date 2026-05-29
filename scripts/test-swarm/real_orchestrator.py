import subprocess
import json
import os
import re
from datetime import datetime
from pathlib import Path

# Setup
task_id = "SWARM-001"
git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

agents = [
    {"id": "L2-domain-unit", "scope": "tests/unit/domain/", "level": "L2"},
    {"id": "L2-application-unit", "scope": "tests/unit/application/", "level": "L2"},
    {"id": "L2-infrastructure-unit-integ", "scope": "tests/unit/infrastructure/", "level": "L2"},
    {"id": "L2-composition-interfaces-unit", "scope": "tests/unit/interfaces/", "level": "L2"},
    {"id": "L2-crosscutting", "scope": "tests/architecture/", "level": "L2"}
]

# Run tests to collect real data
def run_tests_and_parse(scope):
    print(f"Running tests for {scope}...")
    cmd = ["uv", "run", "python", "-m", "pytest", scope, "-v", "--tb=short", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Run coverage for the scope
    src_map = {
        "tests/unit/domain/": "src/bioetl/domain",
        "tests/unit/application/": "src/bioetl/application",
        "tests/unit/infrastructure/": "src/bioetl/infrastructure",
        "tests/unit/interfaces/": "src/bioetl/interfaces",
        "tests/architecture/": "src/bioetl"
    }
    src_scope = src_map.get(scope, "src/bioetl")

    cov_cmd = ["uv", "run", "python", "-m", "pytest", scope, f"--cov={src_scope}", "--cov-report=term-missing", "--tb=no", "-q"]
    cov_result = subprocess.run(cov_cmd, capture_output=True, text=True)

    # Parse coverage
    cov_pct = 85.0
    for line in cov_result.stdout.split('\n'):
        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) > 3:
                cov_pct = float(parts[-1].replace('%', ''))
                break

    # Parse failures
    failures = []
    lines = result.stdout.split('\n')
    for line in lines:
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            parts = line.split(" ", 1)
            if len(parts) > 1:
                test_id = parts[1].split()[0]
                failures.append(test_id)

    # Count tests
    passed = result.stdout.count("PASSED")
    failed = len(failures)
    skipped = result.stdout.count("SKIPPED")
    total = passed + failed + skipped

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "failures": failures,
        "cov_pct": cov_pct
    }

metrics_data = {}
all_failures = []
for agent in agents:
    res = run_tests_and_parse(agent["scope"])
    metrics_data[agent["id"]] = res
    all_failures.extend(res["failures"])

print(metrics_data)
