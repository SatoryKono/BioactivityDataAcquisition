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
"""Architecture guardrail for pipeline-level source pagination overrides."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"

_FORBIDDEN_PROVIDER_KEYS: tuple[str, ...] = (
    "batch_size",
    "page_size",
    "max_url_length",
    "cursor_pagination",
)
_FORBIDDEN_SOURCE_TRANSPORT_KEYS: tuple[str, ...] = (
    "rate_limit",
    "circuit_breaker",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _collect_forbidden_paths(path: Path) -> list[str]:
    payload = _load_yaml(path)
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return []

    source = pipeline.get("source")
    if not isinstance(source, dict):
        return []

    forbidden: list[str] = []
    if "batch_size" in source:
        forbidden.append("pipeline.source.batch_size")
    for key in _FORBIDDEN_SOURCE_TRANSPORT_KEYS:
        if key in source:
            forbidden.append(f"pipeline.source.{key}")
    provider_config = source.get("provider_config")
    if isinstance(provider_config, dict):
        if provider_config:
            forbidden.append("pipeline.source.provider_config")
        pagination = provider_config.get("pagination")
        if isinstance(pagination, dict) and pagination:
            forbidden.append("pipeline.source.provider_config.pagination")
        for key in _FORBIDDEN_PROVIDER_KEYS:
            if key in provider_config:
                forbidden.append(f"pipeline.source.provider_config.{key}")

    batch = source.get("batch")
    if isinstance(batch, dict) and batch:
        forbidden.append("pipeline.source.batch")

    return forbidden


def test_pipeline_configs_do_not_override_provider_transport_directly() -> None:
    """Unified entity configs cannot create a second transport authority."""
    violations: list[str] = []
    for path in sorted(ENTITIES_DIR.rglob("*.yaml")):
        forbidden = _collect_forbidden_paths(path)
        if forbidden:
            rel = path.relative_to(PROJECT_ROOT)
            violations.append(f"{rel}: {', '.join(forbidden)}")

    assert not violations, (
        "Pipeline configs must not override provider transport directly. "
        "Use configs/providers or page_size_override.\n" + "\n".join(violations)
    )
