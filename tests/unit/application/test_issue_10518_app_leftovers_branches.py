"""Stream B APP: leftover compatibility, metrics, gold-filter, and chained-key branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.helpers.dependency_chained_key_resolver import (
    ChainedKeyResolver,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
    _validate_exact_replay_and_snapshots,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
    lenient_pipeline_version_message,
    validate_lenient_dq_compatibility,
)
from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
    _gold_filter_contract_version,
    _gold_filter_message,
    _gold_filter_reason_code,
    _gold_filter_rule_id,
)
from bioetl.domain.composite import DependencyConfig

pytestmark = pytest.mark.unit


def test_lenient_dq_and_pipeline_version_messages() -> None:
    ok, messages = validate_lenient_dq_compatibility(
        SimpleNamespace(dq_contract_compatibility_hash=None),  # type: ignore[arg-type]
        SimpleNamespace(dq_contract_compatibility_hash=None),  # type: ignore[arg-type]
    )
    assert ok is True
    assert messages
    major_ok, major_msg = lenient_pipeline_version_message("2.0.0", "1.0.0")
    assert major_ok is False
    assert "Major" in major_msg
    minor_ok, minor_msg = lenient_pipeline_version_message("1.2.0", "1.1.0")
    assert minor_ok is True
    assert "Minor" in minor_msg
    patch_ok, patch_msg = lenient_pipeline_version_message("1.1.2", "1.1.1")
    assert patch_ok is True
    assert "Patch" in patch_msg
    short_ok, _short = lenient_pipeline_version_message("1", "1")
    assert short_ok is True


def test_exact_replay_requires_checkpoint_mode_and_fingerprint() -> None:
    messages: list[str] = []
    current = SimpleNamespace(
        exact_replay=True,
        input_snapshot_fingerprint="abc",
        input_snapshot_ids=("s1",),
    )
    checkpoint = SimpleNamespace(
        exact_replay=False,
        input_snapshot_fingerprint=None,
        input_snapshot_ids=(),
    )
    compatible = _validate_exact_replay_and_snapshots(
        current,  # type: ignore[arg-type]
        checkpoint,  # type: ignore[arg-type]
        messages,
        execution_identity_compatible=True,
    )
    assert compatible is False
    assert any("exact replay" in item.lower() for item in messages)

    messages.clear()
    checkpoint = SimpleNamespace(
        exact_replay=True,
        input_snapshot_fingerprint=None,
        input_snapshot_ids=(),
    )
    compatible = _validate_exact_replay_and_snapshots(
        current,  # type: ignore[arg-type]
        checkpoint,  # type: ignore[arg-type]
        messages,
        execution_identity_compatible=True,
    )
    assert compatible is False
    assert "checkpoint_missing_snapshot_anchor" in messages


def test_gold_filter_helpers_none_and_profile_scope() -> None:
    assert _gold_filter_message(None)
    assert _gold_filter_rule_id(None) == ""
    assert _gold_filter_contract_version(None)
    semantic = _gold_filter_reason_code({"reason_code": "gold_semantic_business"})
    assert semantic.startswith("gold_semantic_")
    profile = _gold_filter_reason_code({"semantic_scope": "profile-exclusion"})
    assert "profile" in profile or profile.endswith("exclusion")


def test_pipeline_metrics_noop_without_backend() -> None:
    recorder = PipelineMetricsRecorder(metrics=None, pipeline="chembl_activity")
    recorder.record_pipeline_stage_expected(stage="gold", expected=True)
    recorder.record_stage_backlog(run_type="full", stage="gold", count=1)
    recorder.record_batch_lifecycle_event(
        run_type="full", event="flush", stage="gold", status="ok"
    )
    recorder.record_output_artifact_publication(stage="gold", status="written")


def test_chained_key_resolver_missing_reader_source_and_join_key() -> None:
    resolver = ChainedKeyResolver(resolver_helper=MagicMock())
    dependency = DependencyConfig(
        pipeline="chembl_activity",
        join_keys=("molecule_chembl_id",),
        key_source="chembl_molecule",
    )
    with pytest.raises(ValueError, match="delta_reader"):
        resolver._require_delta_reader(dependency, None)
    with pytest.raises(ValueError, match="unknown"):
        resolver._resolve_source_config(dependency, {})
    source_keys = pl.DataFrame({"other": [1]})
    with pytest.raises(ValueError, match="not found"):
        resolver._validate_join_key(source_keys, dependency, "chembl/molecule")
