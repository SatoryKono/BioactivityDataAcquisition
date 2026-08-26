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
"""Governance checks for domain aggregate invariant coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.architecture.quality_artifacts import (
    quality_artifact_path,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = quality_artifact_path("domain-aggregate-invariant-registry.json")
PUBLIC_AGGREGATE_ROOTS = frozenset({"Batch", "PipelineRun", "QuarantineEntry"})


def _registry_payload() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _registry_aggregate_rows() -> list[dict[str, Any]]:
    return list(_registry_payload()["aggregates"])


def test_domain_aggregate_invariant_registry_is_committed_and_complete() -> None:
    """Public aggregate roots must have explicit invariant evidence rows."""
    payload = _registry_payload()
    aggregate_names = {row["aggregate"] for row in payload["aggregates"]}

    assert payload["schema_version"] == 1
    assert payload["aggregate_root_count"] == len(PUBLIC_AGGREGATE_ROOTS)
    assert aggregate_names == PUBLIC_AGGREGATE_ROOTS
    assert payload["summary"]["aggregates_with_invariant_tests"] == len(
        PUBLIC_AGGREGATE_ROOTS
    )
    assert payload["summary"]["missing_source_paths"] == []
    assert payload["summary"]["missing_test_paths"] == []


def test_domain_aggregate_roots_match_public_exports() -> None:
    """The registry must stay aligned with domain aggregate facade exports."""
    aggregate_init = (
        PROJECT_ROOT / "src/bioetl/domain/aggregates/__init__.py"
    ).read_text(encoding="utf-8")

    for aggregate_name in PUBLIC_AGGREGATE_ROOTS:
        assert f'"{aggregate_name}"' in aggregate_init


def test_domain_aggregate_invariant_rows_reference_existing_sources() -> None:
    """Every invariant row must point to real source modules and test evidence."""
    for row in _registry_aggregate_rows():
        source_paths = [row["root_module"], *row["implementation_modules"]]
        test_paths = row["test_paths"]

        assert len(row["invariants"]) >= 3, row["aggregate"]
        assert test_paths, row["aggregate"]

        for relative_path in [*source_paths, *test_paths]:
            assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_domain_aggregate_invariant_rows_have_direct_test_envelopes() -> None:
    """Each aggregate must have at least one invariant-focused test module."""
    for row in _registry_aggregate_rows():
        invariant_tests = [
            path for path in row["test_paths"] if "invariant" in Path(path).stem
        ]
        assert invariant_tests, row["aggregate"]
