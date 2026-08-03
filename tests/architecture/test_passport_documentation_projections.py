"""Architecture and governance guards for passport projections."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.architecture


def test_runtime_does_not_import_passport_tooling() -> None:
    violations: list[str] = []
    for path in sorted((ROOT / "src/bioetl").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name.startswith("scripts.docs.passports") for name in names):
                violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []


def test_committed_passport_completeness_is_exact() -> None:
    report = json.loads(
        (ROOT / "docs/04-reference/passports/completeness-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["counts"] == {
        "composite": 5,
        "pipeline": 22,
        "total": 54,
        "workflow": 27,
    }
    assert report["orphan_passports"] == []
    assert report["duplicate_typed_identities"] == []
    assert report["unresolved_aliases"] == []
    assert report["registry_config_mismatches"] == []
    assert report["blocking_diagnostics"] == 0


def test_passport_cli_is_wired_into_docs_governance() -> None:
    docs_router = (ROOT / "scripts/docs/__main__.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert '"passports": "scripts.docs.passports.cli"' in docs_router
    assert "python -m scripts.docs passports check" in workflow
    assert "tests/architecture/test_passport_documentation_projections.py" in workflow
    for source_path in (
        "configs/entities/**",
        "configs/providers/**",
        "configs/composites/**",
        "configs/workflows/**",
        "configs/contracts/**",
    ):
        assert workflow.count(source_path) == 2


def test_passport_nightly_and_release_gates_are_blocking() -> None:
    nightly = (ROOT / ".github/workflows/architecture-docs-nightly.yml").read_text(
        encoding="utf-8"
    )
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "scripts.docs passports generate" in nightly
    assert "tests/unit/scripts/docs/passports" in nightly
    assert "scripts.docs passports check" in release
    assert "--require-clean-source" in release


def test_reconciliation_ownership_is_explicitly_decided() -> None:
    decision = (
        ROOT
        / "docs/02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md"
    ).read_text(encoding="utf-8")
    assert "**Status:** Accepted" in decision
    assert "data_plane_transformation" in decision
    assert "commit_pending_confirmation" in decision


def test_manual_rollout_covers_composites_and_multistep_workflows() -> None:
    manual_root = ROOT / "docs/04-reference/passports/manual"
    pipeline_sidecars = sorted((manual_root / "pipelines").glob("*.yaml"))
    workflow_sidecars = sorted((manual_root / "workflows").glob("*.yaml"))
    assert len(pipeline_sidecars) == 5
    assert len(workflow_sidecars) == 6
    for path in [*pipeline_sidecars, *workflow_sidecars]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert payload["owner"] == "BioETL Team"
        assert payload["owner_approved"] is True
        assert payload["purpose"]
        assert payload["rationale"]
