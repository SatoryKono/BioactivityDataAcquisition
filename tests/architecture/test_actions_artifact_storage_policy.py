"""Architecture guardrails for bounded GitHub Actions artifact storage."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

_UPLOAD_ARTIFACT_PREFIX = "actions/upload-artifact@"
_MAX_RETENTION_DAYS = 30


def _iter_upload_steps(node: object) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str) and uses.startswith(_UPLOAD_ARTIFACT_PREFIX):
            yield node
        for value in node.values():
            yield from _iter_upload_steps(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_upload_steps(value)


def test_actions_upload_artifacts_have_bounded_explicit_retention(
    workflow_yaml_cache: dict[Path, object],
) -> None:
    violations: list[str] = []

    for workflow_path, payload in workflow_yaml_cache.items():
        for step in _iter_upload_steps(payload):
            step_name = str(step.get("name", "unnamed upload-artifact step"))
            with_config = step.get("with")
            retention = (
                with_config.get("retention-days")
                if isinstance(with_config, dict)
                else None
            )
            if (
                not isinstance(retention, int)
                or not 1 <= retention <= _MAX_RETENTION_DAYS
            ):
                violations.append(
                    f"{workflow_path.as_posix()}::{step_name}: retention-days must "
                    f"be an integer from 1 to {_MAX_RETENTION_DAYS}, got {retention!r}"
                )

    assert not violations, "\n".join(violations)


def test_always_uploads_skip_cancelled_runs(
    workflow_yaml_cache: dict[Path, object],
) -> None:
    violations: list[str] = []

    for workflow_path, payload in workflow_yaml_cache.items():
        for step in _iter_upload_steps(payload):
            condition = step.get("if")
            if isinstance(condition, str) and "always()" in condition:
                if "!cancelled()" not in condition:
                    violations.append(
                        f"{workflow_path.as_posix()}::{step.get('name', 'unnamed')}: "
                        "always() artifact upload must include !cancelled()"
                    )

    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    ("workflow_name", "artifact_name"),
    [
        ("duplication-complexity.yml", "duplication-complexity-reports"),
        ("type-checking.yml", "type-checking-reports"),
    ],
)
def test_actions_heavy_diagnostics_are_failure_only_and_path_scoped(
    workflow_yaml_cache: dict[Path, object],
    workflow_name: str,
    artifact_name: str,
) -> None:
    workflow_path = next(
        path for path in workflow_yaml_cache if path.name == workflow_name
    )
    matching_steps = [
        step
        for step in _iter_upload_steps(workflow_yaml_cache[workflow_path])
        if isinstance(step.get("with"), dict)
        and step["with"].get("name") == artifact_name
    ]

    assert len(matching_steps) == 1
    step = matching_steps[0]
    assert "failure()" in str(step.get("if", ""))
    assert "!cancelled()" in str(step.get("if", ""))

    artifact_path = str(step["with"].get("path", "")).strip()
    assert artifact_path not in {"reports", "reports/"}
