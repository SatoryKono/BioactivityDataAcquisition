"""Stream A L12 application residuals for #10469 / #10516."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.helpers.coordinator_execution import (
    EnricherExecutionContext,
    handle_enricher_timeout,
)
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
    FieldInfo,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_phase_completion import (
    record_dependencies_stage_completed,
    record_seed_stage_completed,
)
from bioetl.application.services.control_plane.ledger.core_events import (
    _coalesce_missing,
    record_dq_policy_applied,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestService,
)
from bioetl.application.services.control_plane.manifest.validation import (
    _is_production_launch_context,
    _validate_replay_capable_profile_floor,
    _validate_strict_replay_provenance,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)
from bioetl.domain.exceptions import BioETLError
from tests.unit.application.composite.test_runner import create_runner
from tests.unit.application.core.test_base_transformer import ConcreteTransformer
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


pytestmark = pytest.mark.unit


def test_preflight_field_priority_appends_incompatible_type_issue() -> None:
    service = CompositePreflightValidationService(MagicMock())
    issues, resolved = service._validate_field_priority(
        "mixed",
        ("chembl", "crossref"),
        frozenset({"chembl", "crossref"}),
        {
            "chembl": {
                "mixed": FieldInfo(
                    name="mixed", dtype="str", nullable=True, source="chembl"
                )
            },
            "crossref": {
                "mixed": FieldInfo(
                    name="mixed", dtype="int", nullable=True, source="crossref"
                )
            },
        },
    )

    assert resolved == "chembl"
    assert any(issue.issue_type == "type_mismatch" for issue in issues)


def test_required_enricher_timeout_logs_and_reraises() -> None:
    enricher = SimpleNamespace(
        pipeline="crossref_publication",
        required=True,
        timeout_seconds=1,
    )
    host = SimpleNamespace(_logger=MagicMock())
    context = EnricherExecutionContext(
        enricher=enricher,  # type: ignore[arg-type]
        records_input=2,
        started_at=datetime(2026, 9, 17, tzinfo=UTC),
        started_monotonic_at=1.0,
    )

    with pytest.raises(TimeoutError, match="Required enricher timed out"):
        handle_enricher_timeout(host, context, TimeoutError("inner"))

    host._logger.error.assert_called_once()
    assert host._logger.error.call_args.kwargs["enricher"] == "crossref_publication"


@pytest.mark.asyncio
async def test_composite_runner_maps_unexpected_bioetl_error() -> None:
    runner = create_runner()
    runner._run_with_managed_lock = AsyncMock(  # type: ignore[method-assign]
        side_effect=BioETLError("unexpected domain failure")
    )

    with pytest.raises(BioETLError, match="unexpected domain failure"):
        await runner.run()


def test_seed_resume_and_dependency_completion_record_control_plane_events() -> None:
    ledger = MagicMock()
    host = SimpleNamespace(
        _metrics=MagicMock(),
        _config=SimpleNamespace(name="publication"),
        _run_ledger_service=ledger,
        _manifest_id="manifest-1",
    )
    seed = SeedResult(
        pipeline_name="chembl_activity",
        records_extracted=10,
        records_silver=8,
        resumed=True,
    )
    record_seed_stage_completed(host, seed)
    host._metrics.increment_counter.assert_called()

    failed = DependencyResult(
        pipeline_name="chembl_target",
        status=DependencyStatus.FAILED,
        records_extracted=4,
        records_silver=1,
        resumed=True,
    )
    timed_out = DependencyResult(
        pipeline_name="chembl_assay",
        status=DependencyStatus.TIMEOUT,
        records_extracted=2,
        records_silver=0,
    )
    record_dependencies_stage_completed(
        host,
        {"chembl_target": failed, "chembl_assay": timed_out},
    )
    ledger.record_composite_dependency_completed.assert_called()


def test_transformer_execution_mixin_wrappers_delegate_shadow_and_metrics() -> None:
    transformer = ConcreteTransformer(
        provider="test",
        dependencies=build_test_transformer_dependencies(),
    )
    context = MagicMock()

    assert transformer._evaluate_semantic_shadow_decision(None) is None
    transformer._record_structural_policy_metrics(action=None, shadow_comparison=None)
    transformer._apply_silver_filter(context, None, 0)


def test_ledger_core_events_keep_existing_values_and_merge_details() -> None:
    assert _coalesce_missing("kept", "default") == "kept"
    assert _coalesce_missing(None, "default") == "default"

    captured: dict[str, object] = {}

    class _Appender:
        def _append(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(event_type=kwargs.get("event_type"))

    entry = record_dq_policy_applied(
        _Appender(),  # type: ignore[arg-type]
        stage="gold",
        rule_id="gold.not_null.id",
        details={"extra": "anchor"},
    )
    assert entry.event_type == "dq_policy_applied"
    assert captured["details"]["extra"] == "anchor"
    assert captured["details"]["rule_id"] == "gold.not_null.id"


def test_manifest_persistence_guard_rejects_run_id_lookup_failures() -> None:
    manifest = SimpleNamespace(manifest_id="manifest-1", run_id="run-1")
    matching = SimpleNamespace(manifest_id="manifest-1", run_id="run-1")

    missing_owner = SimpleNamespace(
        manifest_port=SimpleNamespace(
            get=lambda _manifest_id: matching,
            get_by_run_id=lambda _run_id: None,
        )
    )
    with pytest.raises(RuntimeError, match="not resolvable by run_id"):
        RunManifestService._assert_manifest_persisted(  # type: ignore[arg-type]
            missing_owner, manifest
        )

    mismatched_owner = SimpleNamespace(
        manifest_port=SimpleNamespace(
            get=lambda _manifest_id: matching,
            get_by_run_id=lambda _run_id: SimpleNamespace(
                manifest_id="other-manifest", run_id="run-1"
            ),
        )
    )
    with pytest.raises(RuntimeError, match="different manifest_id"):
        RunManifestService._assert_manifest_persisted(  # type: ignore[arg-type]
            mismatched_owner, manifest
        )


def test_manifest_validation_opt_down_and_strict_planned_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.validation."
        "resolve_reproducibility_family_profile",
        lambda **_kwargs: SimpleNamespace(
            strict_exact_replay_supported=True,
            default_required_persistence_profile="replay_ready",
        ),
    )
    opt_down = SimpleNamespace(
        provider="chembl",
        entity="activity",
        contract_ref="chembl.activity",
        launch_context={
            "required_persistence_profile": "degraded_observable",
            "required_persistence_profile_opt_down": True,
            "configured_required_persistence_profile": "degraded_observable",
            "exact_replay": False,
            "env": "dev",
            "execution_context": "source",
        },
    )
    _validate_replay_capable_profile_floor(opt_down)  # type: ignore[arg-type]

    assert _is_production_launch_context(
        SimpleNamespace(launch_context={"execution_context": "production"})
    )
    assert not _is_production_launch_context(SimpleNamespace(launch_context="invalid"))

    provenance = SimpleNamespace(
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="abc",
        dq_policy_ref="dq",
        rule_bundle_version="1.0",
        effective_config_artifact_id="artifact-1",
    )
    with pytest.raises(RuntimeError, match="planned_artifacts"):
        _validate_strict_replay_provenance(
            SimpleNamespace(
                launch_context={"exact_replay": True},
                planned_artifacts=(),
            ),  # type: ignore[arg-type]
            provenance,  # type: ignore[arg-type]
        )


def test_normalize_run_type_accepts_raw_string() -> None:
    service = RunManifestService(
        manifest_port=MagicMock(),
        _manifest_id_factory=lambda: "manifest-1",
    )
    from bioetl.domain.types import RunType

    assert service._normalize_run_type("incremental") is RunType.INCREMENTAL
