"""Tests for the fail-closed PR gate classifier and aggregator."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.ci import pr_gate

from scripts.engineering.ci.pr_gate import (
    NOT_APPLICABLE,
    REQUIRED,
    CatalogError,
    _matches,
    _parse_name_status_paths,
    classify_changes,
    collect_changed_files,
    evaluate_results,
    load_catalog,
)


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

HEAD_SHA = "a" * 40


@pytest.mark.parametrize("github_actions", [False, True])
def test_classify_cli_preserves_artifact_and_optional_github_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, github_actions: bool
) -> None:
    artifact = tmp_path / "matrix.json"
    output = tmp_path / "github-output"
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    if github_actions:
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(pr_gate, "load_catalog", lambda _: _catalog())
    monkeypatch.setattr(pr_gate, "collect_changed_files", lambda **_: ["docs/guide.md"])
    args = argparse.Namespace(
        catalog=tmp_path / "catalog.yaml",
        artifact=artifact,
        event_name="pull_request",
        base_sha="b" * 40,
        before_sha="",
        head_sha=HEAD_SHA,
    )

    assert pr_gate._classify_command(args) == 0
    matrix = json.loads(artifact.read_text(encoding="utf-8"))
    assert matrix["head_sha"] == HEAD_SHA
    assert matrix["decisions"]["docs"]["decision"] == REQUIRED
    if github_actions:
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        assert json.loads(values["decision_matrix"]) == matrix
        assert values["docs"] == REQUIRED
    else:
        assert not output.exists()


def test_github_actions_requires_output_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_OUTPUT"):
        pr_gate._write_outputs(classify_changes(_catalog(), [], head_sha=HEAD_SHA))


def _catalog() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "version": 2,
        "aggregator": "pr-gate-complete",
        "gates": [
            {
                "id": "always",
                "owner_workflow": ".github/workflows/tests.yml",
                "owner_jobs": ["tests-complete"],
                "decision": "always_required",
                "paths": [],
                "allowed_results": ["success"],
                "not_applicable_allowed": False,
                "sha_binding": True,
            },
            {
                "id": "docs",
                "owner_workflow": ".github/workflows/docs.yml",
                "owner_jobs": ["docs-governance"],
                "decision": "path_scoped",
                "paths": {"include": ["docs/**", ".github/workflows/**"]},
                "allowed_results": ["success", "not_applicable"],
                "not_applicable_allowed": True,
                "not_applicable_reason_required": True,
                "sha_binding": True,
            },
            {
                "id": "docker",
                "owner_workflow": ".github/workflows/docker.yml",
                "owner_jobs": ["docker-complete"],
                "decision": "path_scoped",
                "paths": {"include": ["src/**", "Dockerfile.bioetl"]},
                "allowed_results": ["success", "not_applicable"],
                "not_applicable_allowed": True,
                "not_applicable_reason_required": True,
                "sha_binding": True,
            },
        ],
    }


def _matrix_and_results() -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = _catalog()
    matrix = classify_changes(catalog, ["docs/guide.md"], head_sha=HEAD_SHA)
    results = {
        "always": {"required": "success", "not_applicable": "skipped"},
        "docs": {"required": "success", "not_applicable": "skipped"},
        "docker": {
            "required": "skipped",
            "not_applicable": "success",
            "na_head_sha": HEAD_SHA,
            "na_reason": "no_path_match",
        },
    }
    return matrix, results


def test_classifier_materializes_required_and_not_applicable() -> None:
    matrix = classify_changes(_catalog(), ["docs/guide.md"], head_sha=HEAD_SHA)

    assert matrix["decisions"]["always"]["decision"] == REQUIRED
    assert matrix["decisions"]["docs"]["decision"] == REQUIRED
    assert matrix["decisions"]["docker"]["decision"] == NOT_APPLICABLE


def test_classifier_fails_closed_for_empty_or_unclassified_diff() -> None:
    empty = classify_changes(_catalog(), [], head_sha=HEAD_SHA)
    unknown = classify_changes(_catalog(), ["unowned.file"], head_sha=HEAD_SHA)

    for matrix in (empty, unknown):
        assert {value["decision"] for value in matrix["decisions"].values()} == {
            REQUIRED
        }


def test_path_globs_preserve_root_only_star_semantics() -> None:
    assert _matches("README.md", ["*.md"])
    assert not _matches("grafana/README.md", ["*.md"])
    assert _matches("grafana/README.md", ["**/*.md"])
    assert _matches("docs/guides/setup.md", ["docs/**"])
    assert not _matches("docs/guides/setup.md", ["docs/*.md"])


def test_name_status_parser_keeps_deletions_and_both_rename_paths() -> None:
    raw = (
        b"D\0docs/deleted.md\0"
        b"R100\0docs/old-name.md\0docs/new-name.md\0"
        b"M\0src/bioetl/module.py\0"
    )

    assert _parse_name_status_paths(raw) == [
        "docs/deleted.md",
        "docs/old-name.md",
        "docs/new-name.md",
        "src/bioetl/module.py",
    ]


def test_collect_changed_files_uses_nul_delimited_full_status_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def fake_run(args: list[str], **kwargs: Any) -> Any:
        observed["args"] = args
        observed["kwargs"] = kwargs
        return type(
            "Completed",
            (),
            {"stdout": b"D\0docs/deleted.md\0R100\0old.md\0new.md\0"},
        )()

    monkeypatch.setattr("scripts.engineering.ci.pr_gate.subprocess.run", fake_run)

    paths = collect_changed_files(
        event_name="pull_request",
        base_sha="b" * 40,
        before_sha="",
        head_sha=HEAD_SHA,
    )

    assert paths == ["docs/deleted.md", "old.md", "new.md"]
    assert "--name-status" in observed["args"]
    assert "-z" in observed["args"]
    assert "--diff-filter=ACDMRTUXB" in observed["args"]
    assert observed["kwargs"]["text"] is False


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", None])
def test_required_owner_non_success_blocks_aggregate(conclusion: str | None) -> None:
    matrix, results = _matrix_and_results()
    results["always"]["required"] = conclusion

    failures = evaluate_results(
        _catalog(),
        matrix,
        results,
        expected_head_sha=HEAD_SHA,
        observed_head_sha=HEAD_SHA,
    )

    assert any("always: required result=" in failure for failure in failures)


def test_missing_owner_result_blocks_aggregate() -> None:
    matrix, results = _matrix_and_results()
    del results["always"]

    failures = evaluate_results(
        _catalog(),
        matrix,
        results,
        expected_head_sha=HEAD_SHA,
        observed_head_sha=HEAD_SHA,
    )

    assert "result gate set does not match catalog" in failures
    assert "always: missing result" in failures


def test_sha_mismatch_blocks_aggregate() -> None:
    matrix, results = _matrix_and_results()

    failures = evaluate_results(
        _catalog(),
        matrix,
        results,
        expected_head_sha=HEAD_SHA,
        observed_head_sha="b" * 40,
    )

    assert any("SHA mismatch" in failure for failure in failures)


def test_invalid_not_applicable_evidence_blocks_aggregate() -> None:
    matrix, results = _matrix_and_results()
    results["docker"]["na_head_sha"] = "b" * 40
    results["docker"]["na_reason"] = ""

    failures = evaluate_results(
        _catalog(),
        matrix,
        results,
        expected_head_sha=HEAD_SHA,
        observed_head_sha=HEAD_SHA,
    )

    assert "docker: N/A SHA mismatch" in failures
    assert "docker: N/A reason mismatch" in failures


def test_catalog_rejects_not_applicable_for_always_required(tmp_path: Any) -> None:
    catalog = deepcopy(_catalog())
    catalog["gates"][0]["allowed_results"].append("not_applicable")
    catalog["gates"][0]["not_applicable_allowed"] = True
    path = tmp_path / "catalog.yaml"
    import yaml

    path.write_text(yaml.safe_dump(catalog), encoding="utf-8")

    with pytest.raises(CatalogError, match="always_required"):
        load_catalog(path)


def test_live_catalog_classifies_grafana_reports_and_test_fixtures() -> None:
    catalog = load_catalog(
        Path(__file__).resolve().parents[6]
        / "configs/quality/github_required_checks.yaml"
    )
    matrix = classify_changes(
        catalog,
        [
            "grafana/dashboards/bioetl-control-plane-v1.json",
            "grafana/plugins/bioetl-scenes-app/docs/scenes-parity-ledger.json",
            "reports/observability/scenes-parity-ledger.json",
            "tests/fixtures/grafana/run_explorer/valid_empty.json",
        ],
        head_sha=HEAD_SHA,
    )

    assert matrix["unclassified_files"] == []
    assert matrix["decisions"]["docs-governance"]["decision"] == REQUIRED
    assert matrix["decisions"]["docs-governance"]["reason"] == "path_match"
    assert matrix["decisions"]["docker"]["decision"] == NOT_APPLICABLE
