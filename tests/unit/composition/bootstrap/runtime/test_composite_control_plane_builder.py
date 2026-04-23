"""Unit tests for composite control-plane builder helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    _build_composite_manifest_create_request,
    _normalize_object,
    build_composite_control_plane_bundle,
    resolve_composite_control_plane_flags,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)

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
            "enrichers": [
                {"pipeline": enricher.pipeline} for enricher in self.enrichers
            ],
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
            input_snapshots=(
                RunInputSnapshotRef(
                    snapshot_id="sha256:seed",
                    content_hash="seed",
                    immutable_uri="bronze://pubmed/publication/batch_seed.jsonl.zst",
                ),
            ),
        ),
    )
    planned_artifacts = (
        RunArtifactRef(layer="silver", path="data/output/silver/composite/publication"),
    )
    runtime_snapshot = {"resume": True, "enrich_only": ["openalex_publication"]}
    resolved_snapshot = {"name": "composite_publication"}

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
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.build_composite_runtime_config_snapshot",
            return_value=runtime_snapshot,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.build_composite_resolved_config_snapshot",
            return_value=resolved_snapshot,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="abc1234",
                source_revision_state="clean",
            ),
        ),
    ):
        request = _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            resolved_config_hash="resolved-hash-123",
            effective_config_hash="effective-hash-123",
            dq_contract_compatibility_hash="dq-compat-123",
            effective_config_artifact_id="eca-123",
            contract_ref="composite_publication",
            contract_version="1.0.0",
            required_persistence_profile="replay_ready",
        )

    assert str(request.run_id) == _VALID_RUN_ID
    assert request.pipeline_name == "composite_publication"
    assert request.provider == "composite"
    assert request.entity == "composite_publication"
    assert request.launch_context == {"resume": True}
    assert request.runtime_config == runtime_snapshot
    assert request.resolved_config == resolved_snapshot
    assert request.source_refs == source_refs
    assert request.planned_artifacts == planned_artifacts
    assert request.pipeline_version == "1.0.0"
    assert request.git_commit == "abc1234"
    assert request.source_revision_state == "clean"
    assert request.config_hash == "resolved-hash-123"
    assert request.resolved_config_hash == "resolved-hash-123"
    assert request.effective_config_hash == "effective-hash-123"
    assert request.dq_contract_compatibility_hash == "dq-compat-123"
    assert request.effective_config_artifact_id == "eca-123"
    assert request.contract_ref == "composite_publication"
    assert request.contract_version == "1.0.0"
    assert request.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED


def test_normalize_object_delegates_to_shared_manifest_support() -> None:
    config = cast(Any, _MockCompositeConfig())

    result = _normalize_object(config)

    assert result == {
        "name": "composite_publication",
        "version": "1.0.0",
    }


def test_resolve_composite_control_plane_flags_disables_ledger_when_manifest_disabled() -> (
    None
):
    settings = SimpleNamespace(
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                run_manifest_enabled=False,
                run_ledger_enabled=True,
            )
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Composite execution requires run manifests",
    ):
        resolve_composite_control_plane_flags(settings)


def test_build_composite_control_plane_bundle_fails_closed_when_manifest_disabled(
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

    with pytest.raises(
        RuntimeError,
        match="Composite execution requires run manifests",
    ):
        build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

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
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="abc1234",
            source_revision_state="clean",
        ),
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert isinstance(bundle.manifest_id, str)
    assert isinstance(bundle.execution_fingerprint, str)
    assert bundle.run_ledger_service is None
    assert isinstance(bundle.effective_config_artifact_id, str)
    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{bundle.manifest_id}.json"
    )
    effective_config_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / f"{bundle.effective_config_artifact_id}.json"
    )
    assert manifest_path.exists()
    assert effective_config_path.exists()
    assert not (
        tmp_path / "output" / "control" / "run_ledger" / f"{bundle.manifest_id}.jsonl"
    ).exists()
    manifest = RunManifest.from_dict(json.loads(manifest_path.read_text("utf-8")))
    assert manifest.replay_capability == ReplayCapability.REBUILD_ONLY
    assert bundle.execution_fingerprint == manifest.execution_fingerprint
    assert (
        manifest.code_provenance.effective_config_artifact_id
        == bundle.effective_config_artifact_id
    )
    assert manifest.code_provenance.resolved_config_hash == bundle.resolved_config_hash
    assert manifest.code_provenance.effective_config_hash == bundle.effective_config_hash
    assert (
        manifest.launch_context["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )


def test_build_composite_control_plane_bundle_requires_ledger_for_forensic_grade_profile(
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
                        required_persistence_profile="forensic_grade",
                    )
                ),
            ),
            logger=MagicMock(),
            metrics=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'forensic_grade'",
    ):
        build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_composite_control_plane_bundle_rejects_replay_ready_profile(
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
                        required_persistence_profile="replay_ready",
                    )
                ),
            ),
            logger=MagicMock(),
            metrics=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="full cached-Bronze input snapshot envelope was not captured",
    ):
        build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_composite_control_plane_bundle_allows_replay_ready_with_full_snapshot_envelope(
    tmp_path: Path,
) -> None:
    config = cast(Any, _RichMockCompositeConfig())
    bronze_root = tmp_path / "cached-bronze"
    for provider, entity in (
        ("pubmed", "publication"),
        ("crossref", "publication"),
        ("openalex", "publication"),
    ):
        bronze_day = bronze_root / provider / entity / "2026-01-01"
        bronze_day.mkdir(parents=True)
        (bronze_day / f"batch_{provider}.jsonl.zst").write_bytes(
            f"{provider}-snapshot".encode()
        )
    runtime = CompositeRuntimeConfig(
        resume=True,
        use_cached_bronze=True,
        cached_bronze_path=str(bronze_root),
        cached_bronze_date="2026-01-01",
    )
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
                        required_persistence_profile="replay_ready",
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
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="abc1234",
            source_revision_state="clean",
        ),
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{bundle.manifest_id}.json"
    )
    manifest = RunManifest.from_dict(json.loads(manifest_path.read_text("utf-8")))
    assert manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    assert all(source_ref.input_snapshots for source_ref in manifest.source_refs)
    assert (
        manifest.code_provenance.effective_config_artifact_id
        == bundle.effective_config_artifact_id
    )
    assert manifest.code_provenance.effective_config_hash == bundle.effective_config_hash


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
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="abc1234",
            source_revision_state="clean",
        ),
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert isinstance(bundle.manifest_id, str)
    assert isinstance(bundle.execution_fingerprint, str)
    assert bundle.run_ledger_service is not None
    assert isinstance(bundle.effective_config_artifact_id, str)
    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{bundle.manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    first_entry = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_entry["event_type"] == "manifest_created"
    assert first_entry["manifest_id"] == bundle.manifest_id


def test_build_composite_control_plane_bundle_persists_effective_config_artifact_and_hashes(
    tmp_path: Path,
) -> None:
    config = cast(Any, _RichMockCompositeConfig())
    runtime = CompositeRuntimeConfig(resume=False)
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
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="abc1234",
            source_revision_state="clean",
        ),
    ):
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )

    assert bundle.resolved_config_hash
    assert bundle.effective_config_hash
    assert bundle.resolved_config_hash != bundle.effective_config_hash
    assert bundle.effective_config_artifact_id
    semantic_artifact_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / f"{bundle.effective_config_artifact_id}.json"
    )
    occurrence_artifact_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / "_occurrences"
        / f"{_VALID_RUN_ID}.json"
    )
    assert semantic_artifact_path.exists()
    assert occurrence_artifact_path.exists()
