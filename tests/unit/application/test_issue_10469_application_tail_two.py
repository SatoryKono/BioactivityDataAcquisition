"""Behavioral coverage for one-line application residuals in issue #10469."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
import polars as pl

from bioetl.application.composite.runner_pkg.runner_checkpoint_save_observability import (
    checkpoint_saved_at_epoch_seconds,
)
from bioetl.application.composite.runner_pkg.runner_observability_helpers import (
    resolve_composite_dq_timestamp,
)
from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
    initialize_runner_runtime_state,
)
from bioetl.application.core.base_transformer._structural_policy_coercion import (
    _coerce_float,
)
from bioetl.application.core.base_transformer._structural_policy_support import (
    NoOpStructuralPolicy,
    build_structural_policy,
)
from bioetl.application.observability.control_plane_evidence.failure_reasons import (
    build_failure_reason_rows,
)
from bioetl.application.observability.observer_health_mixin import (
    _ObserverHealthEmissionMixin,
)
from bioetl.application.pipelines.crossref._publication_field_extractors import (
    extract_license_url,
)
from bioetl.application.pipelines.openalex._extractors_common import _resolve_funder_id
from bioetl.application.pipelines.openalex._extractors_topics_grants import extract_topics
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.services.ops.bronze_cleanup_service import BronzeCleanupService
from bioetl.application.services.run_reports.paths import write_report_root_source_identity
from bioetl.application.services.control_plane.effective_config.serialization import to_jsonable
from bioetl.application.services.control_plane.ledger.service import (
    _missing_occurred_at_factory,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support import (
    resolve_attained_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
    resolve_required_profile_requirements,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    _resolve_policy_value,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    resolve_cross_surface_replay_verdict,
)
from bioetl.application.services.control_plane.manifest.service_scaffold import (
    _missing_manifest_id_factory,
)
from bioetl.application.services.control_plane.replay import (
    _bundle_descriptor_payloads as bundle_payloads,
)
from bioetl.application.services.dq._checks_business import _evaluate_single_rule
from bioetl.application.services.dq._checks_statistical import _null_rate_status
from bioetl.application.services.export_lineage.debug_export_collector_gold_mixin import (
    _canonical_gold_filter_reason_code,
)
from bioetl.application.services.quality._dq_report_layer_flows import (
    _metric_severity_for_check_payload,
)
from bioetl.application.services.workflow._observability_workflow_lookup_support import (
    _copy_checkpoint_metadata,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.domain.types import HealthStatus
from bioetl.domain.value_objects.dq_report import DQCheckStatus

pytestmark = pytest.mark.unit


def test_float_coercion_rejects_non_numeric_objects() -> None:
    assert _coerce_float(object(), allow_string_coercion=True) is None


def test_structural_policy_without_schema_is_noop() -> None:
    policy = build_structural_policy(domain_config=object(), pandera_silver_schema=None)

    assert isinstance(policy, NoOpStructuralPolicy)


def test_crossref_license_rejects_non_mapping_first_item() -> None:
    assert extract_license_url({"license": ["not-a-license-object"]}) is None


def test_openalex_funder_id_accepts_nested_identifier_shape() -> None:
    assert (
        _resolve_funder_id(
            {"funder": {"id": "https://openalex.org/F123"}},
            award_openalex_id=None,
        )
        == "https://openalex.org/F123"
    )


def test_openalex_topics_ignore_non_mapping_items() -> None:
    assert extract_topics(cast(Any, ["invalid"])) == []


def test_openalex_transformer_rejects_non_list_collection() -> None:
    assert OpenAlexPublicationTransformer._ensure_dict_list({"id": "W1"}) == []


def test_pubmed_abstract_none_is_not_structured() -> None:
    assert AbstractExtractor.is_abstract_structured(None) is False


def test_failure_reason_aggregation_ignores_successes() -> None:
    entry = SimpleNamespace(
        status="success",
        event_type="run_completed",
        error_type=None,
        event_family="lifecycle",
        stage="completed",
    )
    rows, total = build_failure_reason_rows(cast(Any, (entry,)))

    assert total == 0
    assert all(row["count"] == 0 for row in rows)


def test_observer_health_preserves_canonical_enum() -> None:
    assert (
        _ObserverHealthEmissionMixin._resolve_health_status(
            health_status=HealthStatus.DEGRADED,
            healthy=True,
        )
        is HealthStatus.DEGRADED
    )


@pytest.mark.asyncio
async def test_bronze_cleanup_rejects_negative_retention_before_io() -> None:
    service = BronzeCleanupService(
        storage=MagicMock(),
        logger=MagicMock(),
        clock=MagicMock(),
    )

    with pytest.raises(ValueError, match="retention_days cannot be negative"):
        await service.cleanup(retention_days=-1)


def test_report_source_identity_rejects_non_digest(tmp_path: Any) -> None:
    with pytest.raises(ValueError, match="64-character lowercase hex digest"):
        write_report_root_source_identity(report_root=tmp_path, source_id="invalid")


def test_workflow_transform_registry_reports_membership() -> None:
    registry = WorkflowTransformRegistry()
    registry.register("reconcile", lambda: None)

    assert registry.contains("reconcile") is True


def test_checkpoint_timestamp_without_clock_is_absent() -> None:
    assert checkpoint_saved_at_epoch_seconds(SimpleNamespace()) is None


def test_composite_dq_timestamp_defaults_to_epoch() -> None:
    assert (
        resolve_composite_dq_timestamp(
            cached_bronze_date=None,
            started_at=None,
        ).timestamp()
        == 0.0
    )


def test_composite_runner_requires_explicit_run_id() -> None:
    with pytest.raises(ValueError, match="requires explicit run_id"):
        initialize_runner_runtime_state(object(), None)


def test_effective_config_serializes_datetime_as_iso8601() -> None:
    value = datetime(2026, 9, 16, 12, 30, tzinfo=UTC)

    assert to_jsonable(value) == "2026-09-16T12:30:00+00:00"


def test_control_plane_factories_must_be_injected_by_composition() -> None:
    with pytest.raises(RuntimeError, match="occurred_at_factory must be supplied"):
        _missing_occurred_at_factory()
    with pytest.raises(RuntimeError, match="manifest_id_factory must be supplied"):
        _missing_manifest_id_factory()


def test_attained_profile_reports_replay_ready_when_forensics_are_incomplete() -> None:
    assert (
        resolve_attained_profile(
            replay_ready_missing_requirements=[],
            forensic_grade_missing_requirements=["archive"],
        )
        == "replay_ready"
    )


def test_degraded_profile_has_no_required_missing_surfaces() -> None:
    assert resolve_required_profile_requirements(
        required_profile="degraded_observable",
        replay_ready_missing_requirements=["manifest"],
        forensic_grade_missing_requirements=["archive"],
    ) == ("degraded_observable", [])


def test_policy_summary_reports_mixed_values() -> None:
    assert _resolve_policy_value({"strict", "compat"}) == "mixed"


def test_replay_verdict_prioritizes_checkpoint_incompatibility() -> None:
    assert (
        resolve_cross_surface_replay_verdict(
            semantic_equivalent=True,
            occurrence_only=True,
            checkpoint_compatible=False,
        )
        == "checkpoint_incompatible"
    )


def test_replay_taxonomy_projection_fails_closed_on_non_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = MagicMock(return_value=["invalid"])
    monkeypatch.setattr(
        bundle_payloads,
        "import_module",
        lambda _name: SimpleNamespace(resolve_replay_taxonomy_projection=resolver),
    )

    assert bundle_payloads.resolve_replay_taxonomy_projection() == {}


def test_unknown_business_rule_condition_is_non_blocking() -> None:
    rule = SimpleNamespace(
        column="value",
        condition="custom",
        allowed_values=None,
        minimum=None,
        maximum=None,
        pattern=None,
    )

    assert _evaluate_single_rule(pl.DataFrame({"value": [1]}), cast(Any, rule)) == (
        True,
        0,
    )


def test_null_rate_warning_band_is_explicit() -> None:
    assert _null_rate_status(3.0) is DQCheckStatus.WARN


def test_existing_gold_semantic_reason_code_is_preserved() -> None:
    reason = "gold_semantic_inactive_record"

    assert _canonical_gold_filter_reason_code(reason) == reason


def test_non_mapping_dq_check_has_no_metric_severity() -> None:
    assert _metric_severity_for_check_payload("invalid") is None


def test_checkpoint_metadata_mapping_is_detached() -> None:
    source = {"offset": 3}
    copied = _copy_checkpoint_metadata(source)
    source["offset"] = 4

    assert copied == {"offset": 3}
