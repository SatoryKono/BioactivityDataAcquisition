"""Unit tests for composite control-plane builder helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    _build_composite_manifest_create_request,
    _normalize_object,
)
from bioetl.domain.control_plane import RunArtifactRef, RunSourceRef

_VALID_RUN_ID = "12345678-1234-5678-1234-567812345678"


class _MockCompositeConfig:
    def __init__(self) -> None:
        self.name = "composite_publication"
        self.version = "1.0.0"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "seed": {"pipeline": "pubmed_publication"},
        }


def test_build_composite_manifest_create_request_wires_control_plane_payloads() -> None:
    config = cast(Any, _MockCompositeConfig())
    runtime = CompositeRuntimeConfig(resume=True)
    infra_context = cast(
        Any,
        SimpleNamespace(run_id=_VALID_RUN_ID),
    )
    source_refs = (
        RunSourceRef(
            provider="pubmed",
            entity="publication",
            pipeline_name="pubmed_publication",
        ),
    )
    planned_artifacts = (
        RunArtifactRef(layer="silver", path="data/output/silver/composite/publication"),
    )

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.build_composite_launch_context_snapshot",
            return_value={"resume": True},
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.build_composite_source_refs",
            return_value=source_refs,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.build_composite_planned_artifacts",
            return_value=planned_artifacts,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_git_commit",
            return_value="abc1234",
        ),
    ):
        request = _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            config_hash="hash-123",
            contract_ref="composite_publication",
            contract_version="1.0.0",
        )

    assert str(request.run_id) == _VALID_RUN_ID
    assert request.pipeline_name == "composite_publication"
    assert request.provider == "composite"
    assert request.entity == "composite_publication"
    assert request.launch_context == {"resume": True}
    assert request.runtime_config == _normalize_object(runtime)
    assert request.resolved_config == _normalize_object(config)
    assert request.source_refs == source_refs
    assert request.planned_artifacts == planned_artifacts
    assert request.pipeline_version == "1.0.0"
    assert request.git_commit == "abc1234"
    assert request.config_hash == "hash-123"
    assert request.contract_ref == "composite_publication"
    assert request.contract_version == "1.0.0"
