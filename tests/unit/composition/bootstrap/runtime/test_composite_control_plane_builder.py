"""Unit tests for composite control-plane builder helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from unittest.mock import patch

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    _build_composite_manifest_create_request,
    _normalize_object,
    build_composite_control_plane_bundle,
    resolve_composite_control_plane_flags,
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


class _RichMockCompositeConfig(_MockCompositeConfig):
    def __init__(self) -> None:
        super().__init__()
        self.seed = SimpleNamespace(pipeline="pubmed_publication")
        self.dependencies = [SimpleNamespace(pipeline="crossref_publication")]
        self.enrichers = [SimpleNamespace(pipeline="openalex_publication")]
        self.merge = SimpleNamespace(
            output_silver_path="data/output/silver/composite/publication",
            output_gold_path="data/output/gold/composite/publication",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "seed": {"pipeline": self.seed.pipeline},
            "dependencies": [{"pipeline": dep.pipeline} for dep in self.dependencies],
            "enrichers": [{"pipeline": enricher.pipeline} for enricher in self.enrichers],
            "merge": {
                "output_silver_path": self.merge.output_silver_path,
                "output_gold_path": self.merge.output_gold_path,
            },
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


def test_resolve_composite_control_plane_flags_disables_ledger_when_manifest_disabled() -> None:
    settings = SimpleNamespace(
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                run_manifest_enabled=False,
                run_ledger_enabled=True,
            )
        )
    )

    assert resolve_composite_control_plane_flags(settings) == (False, False)


def test_build_composite_control_plane_bundle_returns_empty_bundle_when_manifest_disabled(
    tmp_path: Path,
) -> None:
    config = cast(Any, _RichMockCompositeConfig())
    runtime = CompositeRuntimeConfig(resume=True)
    infra_context = cast(
        Any,
        SimpleNamespace(
            run_id=_VALID_RUN_ID,
            settings=SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(
                    control_plane=SimpleNamespace(
                        run_manifest_enabled=False,
                        run_ledger_enabled=True,
                    )
                ),
            ),
            logger=MagicMock(),
            metrics=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        ),
    )

    bundle = build_composite_control_plane_bundle(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )

    assert bundle.manifest_id is None
    assert bundle.run_ledger_service is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_composite_control_plane_bundle_can_disable_ledger_while_keeping_manifest(
    tmp_path: Path,
) -> None:
    config = cast(Any, _RichMockCompositeConfig())
    runtime = CompositeRuntimeConfig(resume=True)
    infra_context = cast(
        Any,
        SimpleNamespace(
            run_id=_VALID_RUN_ID,
            settings=SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(
                    control_plane=SimpleNamespace(
                        run_manifest_enabled=True,
                        run_ledger_enabled=False,
                    )
                ),
            ),
            logger=MagicMock(),
            metrics=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        ),
    )

    with patch(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_git_commit",
        return_value="abc1234",
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert isinstance(bundle.manifest_id, str)
    assert bundle.run_ledger_service is None
    assert (
        tmp_path / "output" / "control" / "run_manifest" / f"{bundle.manifest_id}.json"
    ).exists()
    assert not (
        tmp_path / "output" / "control" / "run_ledger" / f"{bundle.manifest_id}.jsonl"
    ).exists()


def test_build_composite_control_plane_bundle_persists_manifest_created_when_ledger_enabled(
    tmp_path: Path,
) -> None:
    config = cast(Any, _RichMockCompositeConfig())
    runtime = CompositeRuntimeConfig(resume=True)
    infra_context = cast(
        Any,
        SimpleNamespace(
            run_id=_VALID_RUN_ID,
            settings=SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(
                    control_plane=SimpleNamespace(
                        run_manifest_enabled=True,
                        run_ledger_enabled=True,
                    )
                ),
            ),
            logger=MagicMock(),
            metrics=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        ),
    )

    with patch(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_git_commit",
        return_value="abc1234",
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert isinstance(bundle.manifest_id, str)
    assert bundle.run_ledger_service is not None
    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{bundle.manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    first_entry = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_entry["event_type"] == "manifest_created"
    assert first_entry["manifest_id"] == bundle.manifest_id
