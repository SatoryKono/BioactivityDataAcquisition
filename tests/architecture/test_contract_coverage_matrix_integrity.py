"""Integrity guard for contract coverage matrix rows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.json"


def _load_payload() -> dict[str, object]:
    payload = json.loads(JSON_ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_rows() -> list[dict[str, object]]:
    rows = _load_payload().get("rows")
    assert isinstance(rows, list)
    normalized: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        normalized.append(row)
    return normalized


@pytest.mark.architecture
def test_contract_coverage_matrix_rows_cover_all_entity_configs() -> None:
    """Each tracked entity config must have exactly one coverage-matrix row."""
    assert JSON_ARTIFACT.exists(), (
        "Missing contract coverage matrix artifact; regenerate with "
        "python -m scripts.engineering.qa report-contract-coverage-matrix"
    )
    expected = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "configs" / "entities").glob("*/*.yaml")
    )
    actual = sorted(
        row["config_path"]
        for row in _load_rows()
        if isinstance(row.get("config_path"), str)
    )
    assert actual == expected


@pytest.mark.architecture
def test_contract_coverage_matrix_declares_gold_enabled_semantics() -> None:
    """The public metric must not conflate runtime state with schema availability."""
    payload = _load_payload()
    assert payload.get("schema_version") == "contract-coverage-matrix-v2"
    semantics = payload.get("semantics")
    assert isinstance(semantics, dict)
    gold_enabled = semantics.get("gold_enabled")
    assert isinstance(gold_enabled, str)
    assert "effective runtime state" in gold_enabled.lower()
    assert "hierarchical config resolution" in gold_enabled
    gold_contract_available = semantics.get("gold_contract_available")
    assert isinstance(gold_contract_available, str)
    assert "independent" in gold_contract_available.lower()
    assert payload.get("gold_contract_available_count") == sum(
        1 for row in _load_rows() if row.get("gold_contract_available") is True
    )


@pytest.mark.architecture
def test_contract_coverage_matrix_gold_enabled_rows_have_full_governance_surfaces() -> (
    None
):
    """Gold-enabled rows must remain covered without hidden missing surfaces."""
    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        gold_enabled = row.get("gold_enabled")
        parity_status = row.get("parity_status")
        missing_surfaces = row.get("missing_surfaces")
        if not isinstance(pipeline_name, str) or gold_enabled is not True:
            continue
        if parity_status != "covered":
            violations.append(
                f"{pipeline_name}: expected parity_status='covered', got {parity_status!r}"
            )
        if missing_surfaces != []:
            violations.append(
                f"{pipeline_name}: expected no missing_surfaces, got {missing_surfaces!r}"
            )
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_contract_coverage_matrix_gold_enabled_rows_have_layer_pandera_details() -> (
    None
):
    """Dataset-layer rows must expose machine-readable Pandera contract evidence."""
    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        if not isinstance(pipeline_name, str) or row.get("gold_enabled") is not True:
            continue
        if row.get("dataset_layer") != "gold":
            violations.append(f"{pipeline_name}: expected dataset_layer='gold'")
        if row.get("pandera_contract_declared") is not True:
            violations.append(f"{pipeline_name}: missing Pandera contract source")
        if row.get("gold_strict_validation_declared") is not True:
            violations.append(f"{pipeline_name}: missing strict Gold validation")
        if not isinstance(row.get("primary_key_fields"), list) or not row.get(
            "primary_key_fields"
        ):
            violations.append(f"{pipeline_name}: missing primary_key_fields")
        if row.get("primary_key_required_in_published_contract") is not True:
            violations.append(
                f"{pipeline_name}: primary keys are not required in published contract"
            )
        if not isinstance(row.get("contract_test_paths"), list) or not row.get(
            "contract_test_paths"
        ):
            violations.append(f"{pipeline_name}: missing contract_test_paths")
        for count_field in (
            "published_contract_property_count",
            "published_contract_required_count",
            "published_contract_non_nullable_count",
            "pandera_field_count_in_source",
        ):
            value = row.get(count_field)
            if not isinstance(value, int) or value <= 0:
                violations.append(f"{pipeline_name}: invalid {count_field}={value!r}")
        check_count = row.get("published_contract_check_constraint_count")
        if not isinstance(check_count, int):
            violations.append(
                f"{pipeline_name}: invalid published_contract_check_constraint_count"
            )
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_contract_coverage_matrix_tracks_constraint_and_golden_evidence() -> None:
    """Gold-enabled rows must expose constraint completeness and golden-test evidence."""
    payload = _load_payload()
    rows = _load_rows()
    gold_rows = [row for row in rows if row.get("gold_enabled") is True]

    assert payload.get("constraint_completeness_review_count") == len(gold_rows)
    assert payload.get("constraint_completeness_missing_count") == 0

    violations: list[str] = []
    for row in gold_rows:
        pipeline_name = row.get("pipeline_name")
        assert isinstance(pipeline_name, str)
        if row.get("constraint_completeness_status") != "covered":
            violations.append(
                f"{pipeline_name}: constraint completeness is not covered"
            )
        if row.get("missing_constraint_surfaces") != []:
            violations.append(
                f"{pipeline_name}: unexpected missing constraints "
                f"{row.get('missing_constraint_surfaces')!r}"
            )
        surfaces = row.get("constraint_completeness_surfaces")
        if not isinstance(surfaces, list):
            violations.append(f"{pipeline_name}: missing completeness surfaces")
            continue
        for required_surface in (
            "pandera_fields",
            "nullable_policy",
            "required_fields",
            "primary_key_required_fields",
            "contract_tests",
            "golden_tests",
        ):
            if required_surface not in surfaces:
                violations.append(
                    f"{pipeline_name}: missing {required_surface} evidence"
                )
        if row.get("published_contract_nullable_policy_declared") is not True:
            violations.append(f"{pipeline_name}: nullable policy not declared")
        if row.get("golden_test_evidence_declared") is not True:
            violations.append(f"{pipeline_name}: golden test evidence not declared")
        golden_paths = row.get("golden_test_paths")
        if not isinstance(golden_paths, list) or not golden_paths:
            violations.append(f"{pipeline_name}: missing golden_test_paths")
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_contract_coverage_matrix_exclusions_are_explicit() -> None:
    """Excluded rows must carry an explicit justification and payload summary parity."""
    payload = _load_payload()
    rows = _load_rows()
    excluded_rows = [row for row in rows if row.get("parity_status") == "excluded"]
    assert payload.get("excluded_count") == len(excluded_rows)

    exclusions = payload.get("exclusions")
    assert isinstance(exclusions, list)
    assert len(exclusions) == len(excluded_rows)

    violations: list[str] = []
    for row in excluded_rows:
        pipeline_name = row.get("pipeline_name")
        reason = row.get("exclusion_reason")
        if not isinstance(reason, str) or not reason:
            violations.append(f"{pipeline_name}: excluded row missing exclusion_reason")
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_contract_coverage_matrix_covered_rows_reference_existing_governance_files() -> (
    None
):
    """Covered rows must resolve their contract YAML, Gold source, and published artifacts."""
    violations: list[str] = []
    for row in _load_rows():
        if row.get("parity_status") != "covered":
            continue
        pipeline_name = row.get("pipeline_name")
        assert isinstance(pipeline_name, str)

        contract_yaml_path = row.get("contract_yaml_path")
        if not isinstance(contract_yaml_path, str) or not contract_yaml_path:
            violations.append(f"{pipeline_name}: missing contract_yaml_path")
        elif not (PROJECT_ROOT / contract_yaml_path).is_file():
            violations.append(
                f"{pipeline_name}: missing contract YAML file {contract_yaml_path}"
            )

        source_path = row.get("gold_schema_source_path")
        if not isinstance(source_path, str) or not source_path:
            violations.append(f"{pipeline_name}: missing gold_schema_source_path")
        elif not (
            (PROJECT_ROOT / "configs" / "base")
            .joinpath(source_path)
            .resolve()
            .is_file()
        ):
            violations.append(
                f"{pipeline_name}: missing Gold schema source file {source_path}"
            )

        artifact_paths = row.get("published_artifact_paths")
        if not isinstance(artifact_paths, list) or not artifact_paths:
            violations.append(f"{pipeline_name}: missing published_artifact_paths")
            continue
        for artifact_path in artifact_paths:
            if not isinstance(artifact_path, str):
                violations.append(
                    f"{pipeline_name}: non-string published artifact path {artifact_path!r}"
                )
                continue
            artifact_file = (
                (PROJECT_ROOT / "configs" / "base").joinpath(artifact_path).resolve()
            )
            if not artifact_file.is_file():
                violations.append(
                    f"{pipeline_name}: missing published artifact file {artifact_path}"
                )

    assert not violations, "\n".join(violations)
