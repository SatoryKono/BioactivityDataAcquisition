"""Pure application helper coverage for the #10469 closeout."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bioetl.application.pipelines.crossref as crossref_pipeline
from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.application.pipelines.common.publication_vocab_observability import (
    _tokens_from_string_value,
    emit_unknown_publication_vocab_metrics,
)
from bioetl.application.pipelines.crossref.reference_extractors import (
    _clean_string,
    extract_references,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_data import (
    _build_comment_index,
)
from bioetl.application.pipelines.uniprot.extractors.extractor_helpers import (
    ExtractorHelper,
)
from bioetl.application.services.contracts.contract_migration_service import (
    ContractMigrationService,
)
from bioetl.application.services.control_plane.manifest.diagnostics.dq_details import (
    build_dq_details_summary_kwargs,
    load_str_collection,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    resolve_verify_verdict,
)
from bioetl.application.services.control_plane.replay._historical_claim_reason import (
    historical_universe_claim_reason,
)
from bioetl.application.services.control_plane.run_manifest_exact_replay_blockers import (
    requires_dependency_lock_provenance,
    snapshot_exact_replay_blockers,
)
from bioetl.application.services.export_lineage.debug_export_collector_helpers import (
    resolve_debug_record_index,
)
from bioetl.application.services.lineage.metadata_lineage_composite import (
    _build_cv_marker_summary,
    _build_provider_field_map,
)
from bioetl.application.services.workflow._observability_workflow_checkpoint_support import (
    _replay_capability,
    _requested_exact_replay,
)
from bioetl.application.services.workflow.control_plane.execution_service import (
    WorkflowExecutionService,
    _missing_now_factory,
)
from bioetl.domain.control_plane import ReplayCapability


pytestmark = pytest.mark.unit


def test_base_transformer_serialization_facades_delegate() -> None:
    assert _BaseTransformerRecordHelpersMixin._serialize_dict({"a": 1}) == '{"a":1}'
    assert _BaseTransformerRecordHelpersMixin._serialize_list([1, 2]) == "[1,2]"


def test_publication_vocabulary_helpers_ignore_unsupported_metric_and_blank_text() -> None:
    emit_unknown_publication_vocab_metrics(
        metrics=SimpleNamespace(),
        pipeline_name="crossref_publication",
        provider="crossref",
        normalized_business_data={"publication_type": "journal-article"},
    )
    assert _tokens_from_string_value("   ") == ()


def test_crossref_facade_and_reference_empty_paths() -> None:
    assert crossref_pipeline.__getattr__("CrossRefPublicationTransformer") is not None
    assert crossref_pipeline.__dir__() == sorted(crossref_pipeline.__all__)
    assert _clean_string("   ") is None
    assert extract_references({"reference": "invalid"}) == []


def test_uniprot_extractors_ignore_invalid_comment_and_alternative_name_items() -> None:
    assert _build_comment_index(["invalid", {}, {"commentType": "FUNCTION"}]) == {
        "FUNCTION": [{"commentType": "FUNCTION"}]
    }
    assert ExtractorHelper.count_list("invalid") is None
    assert ExtractorHelper.extract_alternative_names(
        {"alternativeNames": ["invalid", {"fullName": {"value": "Name"}}]}
    ) == '["Name"]'


def test_contract_migration_helpers_deduplicate_and_report_absent_guide() -> None:
    assert ContractMigrationService._supported_versions(
        {"supported_versions": ["", "1", "1", "2"]}
    ) == ("1", "2")
    assert (
        ContractMigrationService._resolve_migration_guide(
            {"migration_guides": {}}, from_version="1", to_version="2"
        )
        is None
    )


def test_manifest_verdict_distinguishes_effective_config_and_verified_cases() -> None:
    common = {
        "manifest_classification": "semantic_equivalent",
        "manifest_semantic_equivalent": True,
        "missing_evidence": (),
        "occurrence_only": False,
    }
    assert (
        resolve_verify_verdict(
            **common, effective_config_semantic_equivalent=False
        )
        == "effective_config_semantic_drift"
    )
    assert (
        resolve_verify_verdict(**common, effective_config_semantic_equivalent=True)
        == "cross_store_replay_verified"
    )


def test_historical_claim_reasons_cover_exact_and_durable_gaps() -> None:
    assert (
        historical_universe_claim_reason(
            fully_claimed=False,
            exact_replay_supported=False,
            durable_supported=True,
        )
        == "historical_replay_universe_artifact_blocks_universal_claim"
    )
    assert (
        historical_universe_claim_reason(
            fully_claimed=False,
            exact_replay_supported=True,
            durable_supported=False,
        )
        == "durable_evidence_coverage_blocks_universal_claim"
    )


def test_dq_details_helpers_load_lists_and_return_plain_kwargs() -> None:
    assert load_str_collection([1, "rule"]) == {"1", "rule"}
    result = build_dq_details_summary_kwargs(
        rule_ids={"rule"},
        dispositions=set(),
        report_paths=set(),
        violation_kinds=set(),
        cross_validation_rule_ids=set(),
        cross_validation_config_paths=set(),
        cross_validation_quarantine_policies=set(),
        cross_validation_replay_contracts=set(),
        occurrence_only_diagnostic_scopes=set(),
        has_signal=True,
        has_cross_validation_signal=False,
    )
    assert result["rule_ids"] == {"rule"}


def test_debug_export_and_empty_composite_lineage_helpers() -> None:
    assert resolve_debug_record_index({"_debug_record_index": "invalid"}) is None
    assert _build_cv_marker_summary(None) == {}
    assert _build_provider_field_map(()) == {}


def test_checkpoint_replay_helpers_cover_absent_and_non_mapping_launch_context() -> None:
    assert _replay_capability(None) is None
    inspection = SimpleNamespace(
        diagnostics={}, manifest=SimpleNamespace(launch_context="invalid")
    )
    assert _requested_exact_replay(inspection) is None


def test_workflow_missing_clock_factory_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="must be supplied"):
        _missing_now_factory()


def test_workflow_expected_metrics_delegate_to_runner() -> None:
    runner = MagicMock()
    service = WorkflowExecutionService(
        workflow_runner=runner,
        manifest_service=MagicMock(),
        workflow_ledger_port=MagicMock(),
        workflow_ledger_factory=MagicMock(),
        workflow_state_port=MagicMock(),
        workflow_lock_port=MagicMock(),
    )
    config = MagicMock()

    service.record_expected_pipeline_metrics(config)

    runner.record_expected_pipeline_metrics.assert_called_once_with(config)


def test_exact_replay_blockers_cover_capability_and_nonstrict_shortcut() -> None:
    manifest = SimpleNamespace(
        replay_capability=ReplayCapability.REBUILD_ONLY,
        code_provenance=SimpleNamespace(dependency_lock_hash=None),
    )
    policy = SimpleNamespace(
        snapshot_envelope=SimpleNamespace(
            any_input_snapshots=True,
            full_snapshot_envelope=True,
        ),
        strict_requirement_requested=False,
    )
    assert snapshot_exact_replay_blockers(
        manifest=manifest, policy_assessment=policy
    ) == ["exact_replay_capability_unavailable"]
    assert not requires_dependency_lock_provenance(
        manifest=manifest,
        profile=SimpleNamespace(strict_exact_replay_supported=True),
        policy_assessment=policy,
    )
