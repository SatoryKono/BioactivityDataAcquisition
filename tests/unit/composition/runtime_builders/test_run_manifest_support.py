"""Unit tests for run-manifest support helpers around replay boundaries."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    _RunManifestCreateRequestInputs,
    build_manifest_create_request,
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_launch_context_snapshot,
    build_run_source_refs,
    resolve_contract_identity,
    resolve_replay_capability,
    validate_reproducible_sink_modes,
)
from bioetl.domain.control_plane import ReplayCapability, RunInputSnapshotRef
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings


def _make_settings(**overrides: object) -> Settings:
    return cast(Settings, SimpleNamespace(bronze_path=Path("/unused"), **overrides))


def _make_run_context(**overrides: object) -> PipelineRunContext:
    defaults = {
        "pipeline_name": "chembl_activity",
        "resume": False,
        "dry_run": False,
        "limit": None,
        "query": None,
        "start_offset": None,
        "log_level": "INFO",
        "ignore_yaml_filter": False,
        "skip_gold": False,
        "exact_replay": False,
        "vacuum": None,
        "input_filter": None,
        "cached_bronze": None,
    }
    defaults.update(overrides)
    return cast(PipelineRunContext, SimpleNamespace(**defaults))


def _make_manifest_request(
    *,
    exact_replay: bool = False,
    required_persistence_profile: str = "degraded_observable",
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY,
) -> RunManifestCreateSpec:
    return RunManifestCreateSpec(
        run_id=RunID(uuid4()),
        run_type="incremental",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={
            "exact_replay": exact_replay,
            "required_persistence_profile": required_persistence_profile,
        },
        runtime_config={},
        resolved_config={},
        replay_capability=replay_capability,
    )


@pytest.mark.unit
def test_emit_replay_reconstructability_metric_is_owned_by_creation_support() -> None:
    assert emit_replay_reconstructability_metric.__module__.endswith(
        "_run_manifest_creation_support"
    )


@pytest.mark.unit
def test_build_manifest_create_request_uses_supplied_reproducibility_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_build_manifest_source_refs(**kwargs: object):
        captured["required_persistence_profile"] = kwargs[
            "required_persistence_profile"
        ]
        return ("source-ref",)

    def _fake_build_manifest_launch_context(
        *, reproducibility_context: object, **_: object
    ):
        captured["launch_context_context"] = reproducibility_context
        return {"required_persistence_profile": "forensic_grade", "exact_replay": False}

    def _fake_build_replay_assessment(**_: object):
        return SimpleNamespace(
            replay_readiness_verdict=SimpleNamespace(value="rebuild_only"),
            blocking_gaps=(),
        )

    def _fake_assemble_manifest_create_spec(**kwargs: object):
        captured["assemble_request_inputs"] = kwargs["request_inputs"]
        return RunManifestCreateSpec(
            run_id=RunID(uuid4()),
            run_type="incremental",
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context=kwargs["launch_context"],
            runtime_config={},
            resolved_config={},
            replay_capability=ReplayCapability.REBUILD_ONLY,
        )

    def _fake_validate_required_runtime_persistence_profile(**kwargs: object):
        captured["validated_required_profile"] = kwargs["required_persistence_profile"]

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_manifest_source_refs",
        _fake_build_manifest_source_refs,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_manifest_launch_context",
        _fake_build_manifest_launch_context,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_replay_assessment",
        _fake_build_replay_assessment,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._assemble_manifest_create_spec",
        _fake_assemble_manifest_create_spec,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support.validate_required_runtime_persistence_profile",
        _fake_validate_required_runtime_persistence_profile,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support.resolve_code_revision_for_manifest",
        lambda **_: "rev-1",
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._manifest_support.resolve_replay_parentage",
        lambda **_: (None, None),
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._manifest_support.resolve_replay_capability",
        lambda **_: ReplayCapability.REBUILD_ONLY,
    )

    reproducibility_context = SimpleNamespace(
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
        family="strict",
        replay_family_contract="strict",
        strict_replay_runtime_verdict="rebuild_only",
        support_scope="supported",
        reason="fixture",
    )
    request = build_manifest_create_request(
        _RunManifestCreateRequestInputs(
            ctx=_make_run_context(),
            inputs=SimpleNamespace(
                cached_bronze=None,
                runtime_config=SimpleNamespace(),
                settings=SimpleNamespace(test_mode=False, debug=False),
            ),
            provider="chembl",
            entity="activity",
            reproducibility_context=reproducibility_context,
            run_type_value="incremental",
            execution_context_value="isolated",
            config_hash="resolved-hash",
            resolved_config_hash="resolved-hash",
            effective_config_hash="effective-hash",
            contract_ref="chembl.activity",
            contract_version="1.2.3",
            contract_schema_hash="schema-deadbeef",
            dq_policy_ref="chembl.activity.policy",
            rule_bundle_version="2026.04",
            normalization_profile_ref="chembl.activity.norm",
            normalization_profile_version="1.0.0",
            normalization_profile_hash="f" * 64,
            dq_contract_compatibility_hash="dq-hash",
            effective_config_artifact_id="artifact-1",
        )
    )

    assert request.launch_context["required_persistence_profile"] == "forensic_grade"
    assert captured["required_persistence_profile"] == "forensic_grade"
    assert captured["validated_required_profile"] == "forensic_grade"
    assert captured["launch_context_context"] is reproducibility_context


@pytest.mark.unit
def test_cached_bronze_snapshot_refs_keep_stable_identity_when_mtime_changes(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_day = bronze_root / "2026-04-12"
    bronze_day.mkdir(parents=True)
    batch_file = bronze_day / "batch_demo.jsonl.zst"
    batch_file.write_bytes(b"stable-snapshot-bytes")

    first = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )
    original_mtime = batch_file.stat().st_mtime
    os.utime(batch_file, (original_mtime + 10, original_mtime + 10))
    second = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].snapshot_id == second[0].snapshot_id
    assert first[0].content_hash == second[0].content_hash
    assert first[0].immutable_uri == second[0].immutable_uri
    assert first[0].immutable_uri == "bronze://2026-04-12/batch_demo.jsonl.zst"
    assert first[0].captured_at != second[0].captured_at
    assert datetime.fromtimestamp(original_mtime, tz=UTC) == first[0].captured_at


@pytest.mark.unit
def test_cached_bronze_snapshot_identity_is_content_addressed_not_locator(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    first_day = bronze_root / "2026-04-12"
    second_day = bronze_root / "2026-04-13"
    first_day.mkdir(parents=True)
    second_day.mkdir(parents=True)
    (first_day / "batch_demo.jsonl.zst").write_bytes(b"same-payload")
    (second_day / "batch_renamed.jsonl.zst").write_bytes(b"same-payload")

    first = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )
    second = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-13",
    )

    assert first[0].snapshot_id == second[0].snapshot_id
    assert first[0].snapshot_id == f"sha256:{first[0].content_hash}"
    assert first[0].immutable_uri == "bronze://2026-04-12/batch_demo.jsonl.zst"
    assert second[0].immutable_uri == "bronze://2026-04-13/batch_renamed.jsonl.zst"


@pytest.mark.unit
def test_cached_bronze_snapshot_refs_are_sorted_by_snapshot_identity(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_day = bronze_root / "2026-04-12"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_b.jsonl.zst").write_bytes(b"batch-b")
    (bronze_day / "batch_a.jsonl.zst").write_bytes(b"batch-a")

    refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )

    snapshot_ids = [ref.snapshot_id for ref in refs]
    assert snapshot_ids == sorted(snapshot_ids)


@pytest.mark.unit
def test_build_run_source_refs_fails_closed_for_exact_replay_without_snapshots() -> (
    None
):
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=True)
    cached_bronze = SimpleNamespace(
        enabled=True,
        bronze_path="test-output/does-not-exist",
        bronze_date="2026-04-12",
    )

    with pytest.raises(
        RuntimeError,
        match="Cached Bronze execution requires at least one persisted batch file",
    ):
        build_run_source_refs(
            ctx=ctx,
            cached_bronze=cached_bronze,
            settings=settings,
            provider="chembl",
            entity="activity",
        )


@pytest.mark.unit
def test_build_run_source_refs_fails_closed_for_replay_ready_without_snapshots() -> (
    None
):
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=False)

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'replay_ready'",
    ):
        build_run_source_refs(
            ctx=ctx,
            cached_bronze=None,
            settings=settings,
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
        )


@pytest.mark.unit
def test_build_run_source_refs_accepts_manifest_backed_snapshot_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=True)
    manifest_snapshot = RunInputSnapshotRef(
        snapshot_id="sha256:manifest-snapshot",
        content_hash="manifest-snapshot",
        immutable_uri="bronze://chembl/activity/manifest.jsonl.zst",
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_support.resolve_pipeline_input_snapshot_refs",
        lambda **_: (manifest_snapshot,),
    )

    source_refs = build_run_source_refs(
        ctx=ctx,
        cached_bronze=None,
        settings=settings,
        provider="chembl",
        entity="activity",
        required_persistence_profile="replay_ready",
    )

    assert len(source_refs) == 1
    assert source_refs[0].input_snapshots == (manifest_snapshot,)


@pytest.mark.unit
def test_resolve_replay_capability_requires_persisted_snapshots_for_exact_replay() -> (
    None
):
    no_snapshot_refs = (
        SimpleNamespace(provider="chembl", entity="activity", input_snapshots=()),
    )
    snapshot_refs = (
        SimpleNamespace(
            provider="chembl",
            entity="activity",
            input_snapshots=(SimpleNamespace(snapshot_id="snap-1"),),
        ),
    )

    assert (
        resolve_replay_capability(
            source_refs=no_snapshot_refs,
            resume_requested=False,
        )
        is ReplayCapability.REBUILD_ONLY
    )
    assert (
        resolve_replay_capability(
            source_refs=no_snapshot_refs,
            resume_requested=True,
        )
        is ReplayCapability.RESUME_ONLY
    )
    assert (
        resolve_replay_capability(
            source_refs=snapshot_refs,
            resume_requested=False,
        )
        is ReplayCapability.EXACT_REPLAY_SUPPORTED
    )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_append_without_contract() -> None:
    with pytest.raises(RuntimeError, match="idempotency_contract"):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(enabled=True, mode="append"),
                    "gold": SimpleNamespace(enabled=False, mode="scd2"),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_allows_non_strict_append_with_contract() -> (
    None
):
    validate_reproducible_sink_modes(
        yaml_config=SimpleNamespace(
            sink={
                "silver": SimpleNamespace(
                    enabled=True,
                    mode="append",
                    idempotency_contract="append_log",
                ),
                "gold": SimpleNamespace(
                    enabled=False,
                    mode="scd2",
                    idempotency_contract="scd2",
                ),
            }
        ),
        strict_replay_requested=False,
    )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_disallowed_append_contract() -> None:
    with pytest.raises(RuntimeError, match="idempotency_contract=disallowed"):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="disallowed",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_incompatible_append_contract() -> (
    None
):
    with pytest.raises(
        RuntimeError,
        match=r"sink\.silver\.mode=append is incompatible with "
        r"sink\.silver\.idempotency_contract=merge_upsert",
    ):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="merge_upsert",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_append_in_strict_replay_context() -> (
    None
):
    with pytest.raises(
        RuntimeError,
        match="Strict reproducibility contexts cannot use append-mode Silver/Gold",
    ):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="occurrence_only",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=True,
        )


@pytest.mark.unit
def test_build_launch_context_snapshot_marks_ordinary_source_boundary() -> None:
    ctx = _make_run_context(
        limit=10,
        query="assay_type=B",
        exact_replay=True,
        cached_bronze=SimpleNamespace(enabled=True),
    )

    launch_context = build_launch_context_snapshot(
        ctx,
        run_type_value="incremental",
        execution_context_value="pipeline",
        required_persistence_profile="replay_ready",
    )

    assert launch_context["execution_context"] == "pipeline"
    assert launch_context["required_persistence_profile"] == "replay_ready"
    assert (
        launch_context["exact_replay_support_boundary"]
        == "snapshot_backed_source_runs_only"
    )


@pytest.mark.unit
def test_build_launch_context_snapshot_marks_composite_snapshot_envelope_boundary() -> (
    None
):
    ctx = _make_run_context(limit=10)

    launch_context = build_launch_context_snapshot(
        ctx,
        run_type_value="incremental",
        execution_context_value="composite",
        required_persistence_profile="degraded_observable",
    )

    assert launch_context["execution_context"] == "composite"
    assert launch_context["required_persistence_profile"] == "degraded_observable"
    assert (
        launch_context["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )


@pytest.mark.unit
def test_resolve_contract_identity_reads_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text(
        """
entries:
  chembl.activity:
    dq_policy_ref: chembl.activity.policy
    rule_bundle_version: "2026.04"
    identity:
      contract_version: "1.2.3"
      schema_hash: deadbeef
      normalization_profile_ref: "chembl.activity"
      normalization_profile_version: "1.0.0"
      normalization_profile_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = resolve_contract_identity(provider="chembl", entity="activity")

    assert result.contract_ref == "chembl.activity"
    assert result.contract_version == "1.2.3"
    assert result.contract_schema_hash == "deadbeef"
    assert result.dq_policy_ref == "chembl.activity.policy"
    assert result.rule_bundle_version == "2026.04"
    assert result.normalization_profile_ref == "chembl.activity"
    assert result.normalization_profile_version == "1.0.0"
    assert (
        result.normalization_profile_hash
        == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.unit
def test_resolve_contract_identity_falls_back_when_registry_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text("entries: [invalid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = resolve_contract_identity(provider="chembl", entity="activity")

    assert result.contract_ref == "chembl.activity"
    assert result.contract_version is None
    assert result.contract_schema_hash is None
    assert result.dq_policy_ref is None
    assert result.rule_bundle_version is None
    assert result.normalization_profile_ref is None
    assert result.normalization_profile_version is None
    assert result.normalization_profile_hash is None


@pytest.mark.unit
def test_resolve_contract_identity_fails_closed_for_strict_context_when_registry_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text("entries: [invalid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="Strict reproducibility contexts require"):
        resolve_contract_identity(
            provider="chembl",
            entity="activity",
            strict=True,
        )


@pytest.mark.unit
def test_resolve_contract_identity_fails_closed_when_strict_identity_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text(
        """
entries:
  chembl.activity:
    identity:
      contract_version: "1.2.3"
      schema_hash: deadbeef
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        RuntimeError,
        match=(
            "missing: dq_policy_ref, rule_bundle_version, "
            "normalization_profile_ref, normalization_profile_version, "
            "normalization_profile_hash"
        ),
    ):
        resolve_contract_identity(
            provider="chembl",
            entity="activity",
            strict=True,
        )


@pytest.mark.unit
def test_replay_reconstructability_metric_is_reconstructable_for_non_strict_runs() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=False,
            required_persistence_profile="degraded_observable",
            replay_capability=ReplayCapability.REBUILD_ONLY,
        ),
        strict_exact_replay_supported=False,
        metrics=metrics,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": "chembl_activity",
            "replay_capability": "rebuild_only",
            "strict_requirement": "false",
            "status": "reconstructable",
        },
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "rebuild_only",
            "status": "not_requested",
        },
    )


@pytest.mark.unit
def test_replay_reconstructability_metric_marks_strict_runs_not_reconstructable() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=True,
            required_persistence_profile="forensic_grade",
            replay_capability=ReplayCapability.RESUME_ONLY,
        ),
        strict_exact_replay_supported=False,
        metrics=metrics,
    )

    metrics.increment_counter.assert_has_calls(
        [
            call(
                "bioetl_replay_reconstructability_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "replay_capability": "resume_only",
                    "strict_requirement": "true",
                    "status": "not_reconstructable",
                },
            ),
            call(
                "bioetl_replay_drift_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "replay_capability": "resume_only",
                    "drift_type": "strict_replay_not_reconstructable",
                    "status": "detected",
                },
            ),
        ]
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "resume_only",
            "status": "blocked",
        },
    )


@pytest.mark.unit
def test_replay_reconstructability_metric_marks_strict_runs_reconstructable_when_supported() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=False,
            required_persistence_profile="replay_ready",
            replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        ),
        strict_exact_replay_supported=True,
        metrics=metrics,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": "chembl_activity",
            "replay_capability": "exact_replay_supported",
            "strict_requirement": "true",
            "status": "reconstructable",
        },
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "exact_replay_supported",
            "status": "not_requested",
        },
    )
