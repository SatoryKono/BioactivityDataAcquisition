"""Independently verify and preserve existing canonical R11 coverage receipts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

root = Path.cwd()
proof = root / "reports/quality/proof-or-stop/grafana-11874-11844"
original = Path("C:/Users/Fedor/.codex/worktrees/audit-p2-11856-11859/BioactivityDataAcquisition/reports/quality/proof-or-stop/audit-11859-coverage-20261002-r11")
manifest = json.loads((original / "manifest.json").read_text())
assert manifest["complete"] and len(manifest["shards"]) == 17
assert manifest["line_gate_exit_code"] == manifest["branch_gate_exit_code"] == 0
assert manifest["source_tree_sha256"] == "5115449e8c670f5393a58c7009693f666f0eff818fbaa80e0e9ea63f9827ae0f"
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(original / "coverage.xml") == manifest["coverage_xml_sha256"]
assert manifest["coverage_xml_sha256"] == "95b05f4e02569d9439dc6e629b9c3f979490baef1c0f827da3e65f5ca91ce451"
assert subprocess.check_output(["git", "diff", "--name-only", manifest["head"], "HEAD", "--", "src/bioetl", "scripts/engineering/qa"], text=True).strip() == ""
totals = dict(tests=0, failures=0, errors=0, skipped=0)
hashes = {"manifest.json": sha(original / "manifest.json"), "coverage.xml": sha(original / "coverage.xml")}
for row in manifest["shards"]:
    assert row["exit_code"] == 0
    coverage = Path(row["coverage_file"])
    assert coverage.is_relative_to(original) and sha(coverage) == row["coverage_sha256"]
    hashes[coverage.relative_to(original).as_posix()] = sha(coverage)
    junit = Path(row["junit_file"])
    log = Path(row["log_file"])
    assert junit.is_relative_to(original) and log.is_relative_to(original)
    hashes[junit.relative_to(original).as_posix()] = sha(junit)
    hashes[log.relative_to(original).as_posix()] = sha(log)
    for suite in ET.parse(junit).getroot().iter("testsuite"):
        for key in totals: totals[key] += int(suite.get(key, 0))
assert totals == dict(tests=32437, failures=0, errors=0, skipped=181), totals
destination = proof / "verified-r11-coverage"
destination.mkdir(exist_ok=False)
for relative, digest in hashes.items():
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original / relative, target)
    assert sha(target) == digest
changed_tests = subprocess.check_output(["git", "diff", "--name-only", manifest["head"], "HEAD", "--", "tests"], text=True).splitlines()
receipt = {"producer_head_sha": manifest["head"], "verification_head_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "source_tree_sha256": manifest["source_tree_sha256"], "complete_shards": 17, "line_percent": manifest["line_percent"], "branch_percent": manifest["branch_percent"], "junit": totals, "verified_file_sha256": hashes, "source_and_qa_changes_after_measurement": [], "tests_changed_after_measurement": changed_tests, "limit": "R11 measurement remains bound to its producer commit. Later test fixture/marker/docstring differences require supplemental owning tests and do not constitute a new full coverage run."}
(proof / "r11-independent-verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({key:value for key,value in receipt.items() if key != "verified_file_sha256"}))
