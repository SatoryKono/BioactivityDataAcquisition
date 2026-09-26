# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integrity guard for pipeline-config-contract ownership map rows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = (
    PROJECT_ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)


def _load_payload() -> dict[str, object]:
    payload = json.loads(JSON_ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_rows() -> list[dict[str, object]]:
    payload = _load_payload()
    rows = payload.get("rows")
    assert isinstance(rows, list)
    normalized: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        normalized.append(row)
    return normalized


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_rows_reference_existing_artifacts() -> (
    None
):
    """Ownership map rows must point at committed config, contract, and code owners."""
    assert JSON_ARTIFACT.exists(), (
        "Missing pipeline-config-contract ownership map artifact; regenerate with "
        "python -m scripts.engineering.qa report-pipeline-config-contract-ownership-map"
    )

    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        assert isinstance(pipeline_name, str)

        for field in (
            "config_path",
            "contract_config_path",
            "pipeline_code_owner",
            "published_artifact_path",
            "registry_source_path",
        ):
            rel_path = row.get(field)
            if not isinstance(rel_path, str) or not rel_path:
                violations.append(f"{pipeline_name}: missing {field}")
                continue
            if not (PROJECT_ROOT / rel_path).is_file():
                violations.append(
                    f"{pipeline_name}: missing file for {field}={rel_path}"
                )

        provider = row.get("provider")
        if provider == "composite":
            composite_path = row.get("composite_runtime_config_path")
            if not isinstance(composite_path, str) or not composite_path:
                violations.append(
                    f"{pipeline_name}: composite rows require composite_runtime_config_path"
                )
            elif not (PROJECT_ROOT / composite_path).is_file():
                violations.append(
                    f"{pipeline_name}: missing composite runtime config {composite_path}"
                )

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_has_full_gold_coverage() -> None:
    """Gold-enabled rows must link config, registry, contract YAML, JSON, and schema."""
    payload = _load_payload()
    explicit_exclusions = payload.get("explicit_exclusions")
    assert isinstance(explicit_exclusions, list)

    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        contract_ref = row.get("contract_ref")
        gold_enabled = row.get("gold_enabled")
        coverage_status = row.get("coverage_status")
        registry_status = row.get("registry_status")
        gold_schema_title = row.get("gold_schema_title")
        registry_contract_version = row.get("registry_contract_version")

        if gold_enabled is False:
            reason = row.get("gold_exclusion_reason")
            if not isinstance(reason, str) or not reason:
                violations.append(
                    f"{pipeline_name}: non-Gold exclusions require an explicit reason"
                )
            policy = row.get("gold_exclusion_policy")
            if not isinstance(policy, dict) or not policy:
                violations.append(
                    f"{pipeline_name}: non-Gold exclusions require governance policy"
                )
            else:
                expected_reason = policy.get("expected_reason")
                if expected_reason != reason:
                    violations.append(
                        f"{pipeline_name}: exclusion policy reason mismatch "
                        f"policy={expected_reason!r} row={reason!r}"
                    )
                for field in (
                    "owner",
                    "linked_issue",
                    "decision",
                    "rationale",
                    "reentry_condition",
                ):
                    value = policy.get(field)
                    if not isinstance(value, str) or not value.strip():
                        violations.append(
                            f"{pipeline_name}: exclusion policy missing {field}"
                        )
                linked_issue = policy.get("linked_issue")
                if isinstance(linked_issue, str) and not linked_issue.startswith("#"):
                    violations.append(
                        f"{pipeline_name}: exclusion linked_issue must start with #"
                    )
            continue

        if coverage_status != "covered":
            violations.append(
                f"{pipeline_name}: coverage_status={coverage_status!r} "
                f"for {contract_ref!r}"
            )
        if registry_status != "active":
            violations.append(f"{pipeline_name}: registry_status={registry_status!r}")
        if (
            not isinstance(registry_contract_version, str)
            or not registry_contract_version
        ):
            violations.append(f"{pipeline_name}: missing registry_contract_version")
        if not isinstance(gold_schema_title, str) or not gold_schema_title.endswith(
            " Contract"
        ):
            violations.append(f"{pipeline_name}: missing Gold schema title")

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_contract_refs_match_contract_yaml() -> (
    None
):
    """Each ownership row contract_ref must match the committed contract YAML."""
    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        contract_ref = row.get("contract_ref")
        contract_path = row.get("contract_config_path")
        if (
            not isinstance(pipeline_name, str)
            or not isinstance(contract_ref, str)
            or not isinstance(contract_path, str)
            or not contract_path
        ):
            continue

        payload = yaml.safe_load(
            (PROJECT_ROOT / contract_path).read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            violations.append(f"{pipeline_name}: contract payload is not a mapping")
            continue
        declared_ref = payload.get("contract_ref")
        if declared_ref != contract_ref:
            violations.append(
                f"{pipeline_name}: contract_ref mismatch "
                f"row={contract_ref!r} yaml={declared_ref!r}"
            )

    assert not violations, "\n".join(violations)
