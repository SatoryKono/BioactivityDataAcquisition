"""Seal independently checked coverage and native browser capture evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

root = Path.cwd()
proof = root / "reports/quality/proof-or-stop/grafana-11874-11844"
capture = root / "reports/observability/grafana/screenshots-final-91a1443"
def read(path): return json.loads(path.read_text(encoding="utf-8"))
verification = read(proof / "r11-independent-verification.json")
subprocess.run(["git", "diff", "--quiet", verification["verification_head_sha"], "HEAD", "--", "src/bioetl", "tests", "scripts/engineering/qa"], check=True)
manifest = read(capture / "render-manifest.json")
assert manifest["terminal_state_validation"]["status"] == "ok"
expected = {read(path)["uid"] for path in (root / "grafana/dashboards").glob("*.json")}
assert set(manifest["terminal_state_validation"]["dashboards"]) == expected
preflight = read(proof / "screenshot-preflight-final.json")
checks = {row["name"]:row["status"] for row in preflight["checks"]}
assert checks["screenshots"] == checks["bioetl-control-plane-source"] == "ok"
totals = dict(tests=0, failures=0, errors=0, skipped=0)
for suite in ET.parse(proof / "final-owning-acceptance.xml").getroot().iter("testsuite"):
    for key in totals: totals[key] += int(suite.get(key, 0))
assert totals == dict(tests=141, failures=0, errors=0, skipped=0)
ci = read(proof / "github-ci-11898-final.json")
assert ci["all_failures_billing_blocked"]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert head == ci["head"] == "91a1443fe81dd5706d21c7fe0a5ae4b42741be42"
assert manifest["source"]["commit_sha"] == head
assert manifest["source"]["working_tree_dirty"] is False
target = proof / "five-dashboard-final-native"
files = []
for path in capture.rglob("*"):
    if not path.is_file() or "render-api" in path.relative_to(capture).parts or path.suffix not in {".json", ".png"}: continue
    if path.suffix == ".png": assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    copied = target / path.relative_to(capture)
    copied.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, copied)
    assert copied.read_bytes() == path.read_bytes()
    files.append(copied)
files += [path for path in (proof / "verified-r11-coverage").rglob("*") if path.is_file() and (path.suffix in {".json", ".xml", ".log"})]
for run in ["full-coverage-cee1fbb-r3", "full-coverage-6a4aa1b-final"]:
    files += [path for path in (proof / run).rglob("*") if path.is_file() and path.suffix in {".json", ".xml", ".log"}]
names = ["r11-independent-verification.json", "verify_r11_evidence.py", "final-owning-acceptance.xml", "final-owning-acceptance.log", "inventory-adoption-ledger.json", "module-inventory-r11-measured-candidate.json", "module-coverage-r11-direct-candidate.log", "module-coverage-main-guard.log", "github-ci-11898-final.json", "ci-family-final-check.log", "ci-family-merged-final-refresh.log", "nav-main-final.log", "nav-direct-entrypoint-failed.log", "docs-links-main.log", "docs-drift-main.log", "docs-cleanup-final.log", "screenshot-preflight-final.json", "audit-cycle-final-91a1443.log", "domain-worker-retry-diagnosis.json", "domain-worker-24508-stack.log", "domain-worker-30140-stack.log", "domain-controller-stack.log", "full-coverage-cee1fbb-r3.log", "full-coverage-6a4aa1b-final.log", "coverage-execution-context-final.json", "run_current_main_coverage_final.py", "prepare_final_evidence.py", "publish_final_evidence.py"]
files += [proof / name for name in names]
inventory_snapshot = proof / "final-module-coverage-inventory.json"
shutil.copyfile(root / "reports/quality/module-coverage-inventory.json", inventory_snapshot)
files.append(inventory_snapshot)
summary = {"issues": [11874,11844], "final_pr_head_sha": head, "coverage": verification, "supplemental_owning_tests": totals, "screenshots": {"uids": sorted(expected), "preflight": checks, "capture_head_sha": head}, "ci": "BLOCKED_EXTERNAL_PERMANENT", "full_live_visual_release_acceptance": False, "followups": ["https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11895", "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11899"], "inventory_adoption": read(proof / "inventory-adoption-ledger.json"), "failed_or_interrupted_runs_are_excluded_from_measured_xml": True, "files": {path.relative_to(root).as_posix(): {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size} for path in files}}
summary_path = proof / "acceptance-main.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
files.append(summary_path)
(proof / "final-artifact-files.json").write_text(json.dumps(sorted({path.relative_to(root).as_posix() for path in files}), indent=2), encoding="utf-8")
print({"files": len(files), "source": verification["source_tree_sha256"], "head": head})
