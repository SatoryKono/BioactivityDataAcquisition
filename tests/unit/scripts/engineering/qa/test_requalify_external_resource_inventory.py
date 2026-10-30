"""Real Git source changes must be reviewed before the canonical writer can run."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.engineering.qa import external_resource_inventory as inventory
from scripts.engineering.qa import requalify_external_resource_inventory as producer
from scripts.engineering.qa.__main__ import main as qa_main

pytestmark = pytest.mark.unit
SOURCE = "src/bioetl/fixture.py"
REVIEW = "configs/quality/requalification-review.json"
TEXT = "def read_file():\n    with open('fixture') as stream:\n        return stream.read()\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def commit_source(root: Path, content: str) -> str:
    (root / SOURCE).write_text(content, encoding="utf-8", newline="\n")
    git(root, "add", "--", SOURCE)
    git(root, "commit", "-qm", "fixture source")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict, dict]:
    root = tmp_path / "repo"
    (root / SOURCE).parent.mkdir(parents=True)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "core.autocrlf", "false")
    first = commit_source(root, TEXT)
    ref = {
        "file": SOURCE,
        "line": 2,
        "expression": "open('fixture')",
        "source_commit": first,
        "source_blob": git(root, "rev-parse", f"HEAD:{SOURCE}"),
        "content_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
    }
    record = {
        "identity": "fixture.file",
        "type": "file",
        "creator": ["read_file"],
        "owner": "read_file operation",
        "closer": "with exit",
        "lifetime": "one read",
        "shutdown_contract": "file context exits",
        "production_entrypoint": "fixture.read_file",
        "call_path": ["read_file", "open"],
        "creation_sites": [deepcopy(ref)],
        "production_binding": [deepcopy(ref)],
        "qualification": "SOURCE_QUALIFIED_NOT_RUNTIME_VERIFIED",
        "scenarios": {
            name: {
                "applicability": "owning operation",
                "expected": "close stream",
                "observation": "observe actual stream",
                "runtime_result": "NOT_RUN_12553",
            }
            for name in inventory.SCENARIOS
        },
    }
    original = {
        "schema_version": 1,
        "source_commit": first,
        "source_tree": git(root, "rev-parse", "HEAD^{tree}"),
        "source_files": {SOURCE: ref["source_blob"]},
        "resources": [record],
        "accepted_site_keys": [[SOURCE, 2, "open('fixture')"]],
        "delegations_and_exclusions": [],
        "prior_candidates_input": {"count": 1},
        "prior_candidate_dispositions": [
            {
                "candidate_id": "old-1",
                "object": "file",
                "file": SOURCE,
                "disposition": "retained",
                "resource_definitions": ["fixture.file"],
            }
        ],
        "scope_statement": "fixture",
        "completeness_method": "independent AST census",
        "history_statement": "retain history",
        "reuse_statement": "reuse old source",
    }
    inventory.write_catalog(original, root)
    (root / inventory.REPORT).parent.mkdir(parents=True)
    (root / inventory.REPORT).write_text(
        inventory.render(original), encoding="utf-8", newline="\n"
    )
    git(
        root,
        "add",
        "--",
        inventory.CATALOG.as_posix(),
        "configs/quality/external_resource_inventory/part-01.json",
        inventory.REPORT.as_posix(),
    )
    git(root, "commit", "-qm", "fixture catalog")
    base = git(root, "rev-parse", "HEAD")
    target = commit_source(root, "\n\n" + TEXT)
    review = {
        "schema_version": 1,
        "catalog_ref": base,
        "source_ref": target,
        "source_reviews": {
            SOURCE: "Only source location changed; context ownership unchanged."
        },
    }
    monkeypatch.setattr(inventory, "ROOT", root)
    return root, review, original


def invoke(root: Path, review: dict, mode: str) -> int:
    (root / REVIEW).write_text(json.dumps(review), encoding="utf-8")
    return qa_main(["requalify-external-resource-inventory", "--review", REVIEW, mode])


def outputs(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in [
            root / inventory.CATALOG,
            root / inventory.REPORT,
            *sorted((root / inventory.CATALOG.with_suffix("")).glob("part-*.json")),
        ]
    }


def test_check_update_check_is_readonly_idempotent_and_preserves_history(
    candidate: tuple,
) -> None:
    root, review, original = candidate
    before = outputs(root)
    assert invoke(root, review, "--check") == 1
    assert outputs(root) == before
    assert invoke(root, review, "--update") == 0
    after = outputs(root)
    assert invoke(root, review, "--check") == 0
    assert invoke(root, review, "--update") == 0
    assert outputs(root) == after
    current = inventory.load_catalog(root)
    assert (
        current["prior_candidate_dispositions"]
        == original["prior_candidate_dispositions"]
    )
    assert current["resources"][0]["creation_sites"][0]["line"] == 4
    assert current["source_commit"] == review["source_ref"]
    assert current["source_requalification"]["runtime_result"] == "NOT_RUN_12553"


@pytest.mark.parametrize(
    "fault",
    [
        "missing-review",
        "extra-review",
        "identity-update",
        "runtime-pass",
        "unknown-field",
        "symbolic-ref",
        "dirty-source",
        "extra-tracked-source",
        "unreviewed-acquisition",
        "ambiguous-reference",
    ],
)
def test_invalid_delta_never_changes_outputs(candidate: tuple, fault: str) -> None:
    root, review, original = candidate
    if fault == "missing-review":
        review["source_reviews"] = {}
    elif fault == "extra-review":
        review["source_reviews"]["src/bioetl/extra.py"] = "not part of this revision"
    elif fault == "identity-update":
        review["resource_updates"] = {"fixture.file": {"identity": "replacement"}}
    elif fault == "runtime-pass":
        scenarios = deepcopy(original["resources"][0]["scenarios"])
        scenarios["normal"]["runtime_result"] = "PASS"
        review["resource_updates"] = {"fixture.file": {"scenarios": scenarios}}
    elif fault == "unknown-field":
        review["prior_candidate_dispositions"] = []
    elif fault == "symbolic-ref":
        review["source_ref"] = "HEAD"
    elif fault == "dirty-source":
        (root / SOURCE).write_text("\n\n\n" + TEXT, encoding="utf-8")
    elif fault == "extra-tracked-source":
        (root / "src/bioetl/extra.py").write_text(
            "open('unreviewed')\n", encoding="utf-8"
        )
        git(root, "add", "--", "src/bioetl/extra.py")
    elif fault == "unreviewed-acquisition":
        review["source_ref"] = commit_source(
            root, "\n\n" + TEXT + "\nopen('unreviewed')\n"
        )
    else:
        review["source_ref"] = commit_source(
            root, "def read_file():\n    open('fixture')\n    open('fixture')\n"
        )
    before = outputs(root)
    assert invoke(root, review, "--update") == 1
    assert outputs(root) == before


def test_new_resource_must_cover_the_actual_new_acquisition(candidate: tuple) -> None:
    root, review, original = candidate
    review["source_ref"] = commit_source(
        root,
        "\n\n"
        + TEXT
        + "\ndef read_second():\n    with open('second') as stream:\n        return stream.read()\n",
    )
    resource = deepcopy(original["resources"][0])
    for field in ("creation_sites", "production_binding"):
        resource.pop(field)
    resource.update(
        identity="fixture.second",
        creator=["read_second"],
        site_selectors=[
            {
                "file": SOURCE,
                "scope": "read_second",
                "call": "open",
                "expression": "open('second')",
            }
        ],
    )
    review["new_resources"] = [resource]
    assert invoke(root, review, "--update") == 0
    current = inventory.load_catalog(root)
    assert {r["identity"] for r in current["resources"]} == {
        "fixture.file",
        "fixture.second",
    }
    assert len(current["accepted_site_keys"]) == 2
    assert invoke(root, review, "--check") == 0


def test_review_path_cannot_escape_quality_inputs(candidate: tuple) -> None:
    root, review, _ = candidate
    outside = root.parent / "outside.json"
    outside.write_text(json.dumps(review), encoding="utf-8")
    before = outputs(root)
    assert producer.main(["--review", str(outside), "--update"]) == 1
    assert outputs(root) == before


def test_native_validator_rejects_forged_review_counts(candidate: tuple) -> None:
    root, review, _ = candidate
    assert invoke(root, review, "--update") == 0
    payload = inventory.load_catalog(root)
    payload["source_requalification"]["definition_count"] += 1
    snapshot = producer._snapshot(root, review["source_ref"])
    errors = inventory.validate_inventory(payload, snapshot.sources, snapshot.blobs)
    assert any(
        "source review identity/counts/runtime claim" in error for error in errors
    )
