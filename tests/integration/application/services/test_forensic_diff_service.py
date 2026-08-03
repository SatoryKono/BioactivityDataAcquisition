# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for unified forensic run diff service."""

from __future__ import annotations

import pytest
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from bioetl.application.services.control_plane.forensic import ForensicRunDiffService
from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    _artifact_refs,
    _coerce_int,
    _dict_or_empty,
    _forensic_diff_payload,
    _lineage_closure_payload,
    _metadata_sidecar_missing_count,
    _missing_evidence,
    _resolve_forensic_verdict,
    _string_list,
    _string_list_or_empty,
    _trace_complete,
    _trace_missing_requirements,
)
from bioetl.application.services.control_plane.forensic_diff_service import (
    _inspection_service_factory_from_ports,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunType
from bioetl.infrastructure.control_plane import FileArtifactByteComparisonAdapter
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.unit.application.services.run_manifest_test_support import (
    FIXED_TIME,
    VALID_CONFIG_HASH,
    make_run_manifest,
)


pytestmark = pytest.mark.integration


def test_forensic_diff_reports_semantic_and_artifact_evidence() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    left_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    right_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    left = make_run_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        config_hash=VALID_CONFIG_HASH,
    )
    right = make_run_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        run_type=RunType.REBUILD,
        config_hash="b" * 64,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="artifact-left",
            manifest_id="manifest-left",
            run_id=left_run_id,
            event_type="artifact_published",
            occurred_at=FIXED_TIME,
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:fragment-1",
            details={
                "artifact_path": "data/output/silver/chembl/activity",
                "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
            },
        )
    )
    service = ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.compare("manifest-left", "manifest-right")
    payload = result.to_dict()

    assert payload["classification"] == "semantic_drift"
    assert payload["semantic_equivalent"] is False
    assert payload["forensic_diff"]["verdict"] == "semantic_drift"
    assert payload["left_diagnostics"]["published_artifact_count"] == 1
    assert payload["right_diagnostics"]["published_artifact_count"] == 0
    assert payload["artifact_completeness"]["left"]["complete"] is True
    assert payload["artifact_completeness"]["right"]["complete"] is False
    assert payload["missing_evidence"]["right"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]


def test_forensic_diff_classifies_occurrence_only_drift() -> None:
    manifest_store = InMemoryRunManifestStore()
    left_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    right_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=left_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=right_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["occurrence_only"] is True
    assert payload["classification"] == "occurrence_only"


def test_forensic_diff_classifies_exact_match() -> None:
    manifest_store = InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-left").to_dict()

    assert payload["classification"] == "identical"
    assert payload["semantic_equivalent"] is True
    assert payload["occurrence_only"] is False


def test_forensic_diff_classifies_missing_optional_evidence() -> None:
    manifest_store = InMemoryRunManifestStore()
    left_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    right_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=left_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=right_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["missing_evidence"]["left"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]
    assert payload["missing_evidence"]["right"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]


def test_forensic_diff_reports_missing_sidecars_and_incomplete_trace() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(make_run_manifest(manifest_id="manifest-left", run_id=run_id))
    ledger_store.append(
        RunLedgerEntry(
            entry_id="artifact-left",
            manifest_id="manifest-left",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=FIXED_TIME,
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:fragment-1",
            details={"artifact_path": "data/output/silver/chembl/activity"},
        )
    )
    service = ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    payload = service.compare("manifest-left", "manifest-left").to_dict()

    assert payload["artifact_completeness"]["left"]["complete"] is False
    assert (
        payload["artifact_completeness"]["left"]["metadata_sidecar_missing_count"] == 1
    )
    assert payload["missing_evidence"]["left"] == ["metadata_sidecars_missing"]


def test_forensic_diff_reports_checkpoint_mismatch() -> None:
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=deterministic_run_uuid_from_callsite("test_forensic_diff_service"),
            execution_fingerprint="fingerprint-left",
            config_hash=VALID_CONFIG_HASH,
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=deterministic_run_uuid_from_callsite("test_forensic_diff_service"),
            execution_fingerprint="fingerprint-right",
            config_hash="c" * 64,
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["checkpoint_compatibility"]["available"] is True
    assert payload["checkpoint_compatibility"]["compatible"] is False
    assert (
        "execution_fingerprint"
        in payload["checkpoint_compatibility"]["mismatched_fields"]
    )


def test_forensic_diff_marks_byte_equivalence_unavailable_without_port() -> None:
    manifest_store = InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(make_run_manifest(manifest_id="manifest-left", run_id=run_id))
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-left").to_dict()

    assert payload["artifact_byte_equivalence"]["available"] is False
    assert (
        payload["artifact_byte_equivalence"]["comparison_scope"]
        == "unavailable_no_port"
    )


def test_forensic_diff_reports_byte_mismatch_when_artifacts_differ() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    left_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    right_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(
        make_run_manifest(manifest_id="manifest-left", run_id=left_run_id)
    )
    manifest_store.save(
        make_run_manifest(manifest_id="manifest-right", run_id=right_run_id)
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        left_artifact = root / "left.bin"
        right_artifact = root / "right.bin"
        left_artifact.write_text("left", encoding="utf-8")
        right_artifact.write_text("right", encoding="utf-8")
        left_meta = root / "left_metadata.txt"
        right_meta = root / "right_metadata.txt"
        left_meta.write_text("left-meta", encoding="utf-8")
        right_meta.write_text("right-meta", encoding="utf-8")
        ledger_store.append(
            RunLedgerEntry(
                entry_id="artifact-left",
                manifest_id="manifest-left",
                run_id=left_run_id,
                event_type="artifact_published",
                occurred_at=FIXED_TIME,
                stage="silver",
                dataset_ref="silver:chembl.activity@1",
                lineage_fragment_id="silver:fragment-1",
                details={
                    "artifact_path": str(left_artifact),
                    "metadata_path": str(left_meta),
                },
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="artifact-right",
                manifest_id="manifest-right",
                run_id=right_run_id,
                event_type="artifact_published",
                occurred_at=FIXED_TIME,
                stage="silver",
                dataset_ref="silver:chembl.activity@1",
                lineage_fragment_id="silver:fragment-1",
                details={
                    "artifact_path": str(right_artifact),
                    "metadata_path": str(right_meta),
                },
            )
        )
        service = ForensicRunDiffService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            artifact_byte_comparison_port=FileArtifactByteComparisonAdapter(),
        )

        payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["artifact_byte_equivalence"]["available"] is True
    assert payload["artifact_byte_equivalence"]["equivalent"] is False
    assert payload["artifact_byte_equivalence"]["mismatched_artifacts"]


def test_forensic_diff_reports_occurrence_only_sidecar_drift_as_semantic_match() -> (
    None
):
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    left_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    right_run_id = deterministic_run_uuid_from_callsite("test_forensic_diff_service")
    manifest_store.save(
        make_run_manifest(manifest_id="manifest-left", run_id=left_run_id)
    )
    manifest_store.save(
        make_run_manifest(manifest_id="manifest-right", run_id=right_run_id)
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        left_meta = root / "left_metadata.yaml"
        right_meta = root / "right_metadata.yaml"
        left_meta.write_text(
            "run_id: left\nmanifest_id: manifest-left\nvalue: stable\n",
            encoding="utf-8",
        )
        right_meta.write_text(
            "run_id: right\nmanifest_id: manifest-right\nvalue: stable\n",
            encoding="utf-8",
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="artifact-left",
                manifest_id="manifest-left",
                run_id=left_run_id,
                event_type="artifact_published",
                occurred_at=FIXED_TIME,
                stage="silver",
                dataset_ref="silver:chembl.activity@1",
                lineage_fragment_id="silver:fragment-1",
                details={
                    "artifact_path": str(left_meta),
                    "metadata_path": str(left_meta),
                },
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="artifact-right",
                manifest_id="manifest-right",
                run_id=right_run_id,
                event_type="artifact_published",
                occurred_at=FIXED_TIME,
                stage="silver",
                dataset_ref="silver:chembl.activity@1",
                lineage_fragment_id="silver:fragment-1",
                details={
                    "artifact_path": str(right_meta),
                    "metadata_path": str(right_meta),
                },
            )
        )
        service = ForensicRunDiffService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            artifact_byte_comparison_port=FileArtifactByteComparisonAdapter(),
        )

        payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["artifact_byte_equivalence"]["available"] is True
    assert payload["artifact_byte_equivalence"]["equivalent"] is True
    assert payload["artifact_byte_equivalence"]["semantic_equivalent"] is True
    assert payload["artifact_byte_equivalence"]["raw_byte_equivalent"] is False
    assert payload["artifact_byte_equivalence"]["occurrence_only"] is True
    assert payload["artifact_byte_equivalence"]["occurrence_only_artifacts"]


class TestHelperFunctions:
    """Test helper functions for better coverage."""

    def test_dict_or_empty_with_dict(self):
        """Test _dict_or_empty with dict input."""
        result = _dict_or_empty({"key": "value"})
        assert result == {"key": "value"}

    def test_dict_or_empty_with_non_dict(self):
        """Test _dict_or_empty with non-dict input."""
        result = _dict_or_empty("not_a_dict")
        assert result == {}

    def test_dict_or_empty_with_none(self):
        """Test _dict_or_empty with None."""
        result = _dict_or_empty(None)
        assert result == {}

    def test_dict_or_empty_with_list(self):
        """Test _dict_or_empty with list."""
        result = _dict_or_empty(["item1", "item2"])
        assert result == {}

    def test_artifact_refs_with_valid_list(self):
        """Test _artifact_refs with valid artifact refs."""
        diagnostics = {
            "artifact_refs": [
                {"artifact_path": "/path1", "metadata_path": "/meta1"},
                {"artifact_path": "/path2", "metadata_path": "/meta2"},
            ]
        }
        result = _artifact_refs(diagnostics)
        assert len(result) == 2
        assert result[0]["artifact_path"] == "/path1"

    def test_artifact_refs_with_non_list(self):
        """Test _artifact_refs with non-list input."""
        diagnostics = {"artifact_refs": "not_a_list"}
        result = _artifact_refs(diagnostics)
        assert result == []

    def test_artifact_refs_with_missing_key(self):
        """Test _artifact_refs when key is missing."""
        diagnostics = {}
        result = _artifact_refs(diagnostics)
        assert result == []

    def test_artifact_refs_with_mixed_types(self):
        """Test _artifact_refs with mixed ref types."""
        diagnostics = {
            "artifact_refs": [
                {"artifact_path": "/path1"},
                "not_a_dict",
                {"artifact_path": "/path2"},
            ]
        }
        result = _artifact_refs(diagnostics)
        assert len(result) == 2  # Only valid dicts

    def test_metadata_sidecar_missing_count(self):
        """Test _metadata_sidecar_missing_count."""
        diagnostics = {
            "artifact_refs": [
                {"artifact_path": "/path1", "metadata_path": "/meta1"},
                {"artifact_path": "/path2"},  # Missing metadata
                {"artifact_path": "/path3", "metadata_path": "/meta3"},
            ]
        }
        result = _metadata_sidecar_missing_count(diagnostics)
        assert result == 1

    def test_metadata_sidecar_missing_count_empty_refs(self):
        """Test _metadata_sidecar_missing_count with empty refs."""
        diagnostics = {"artifact_refs": []}
        result = _metadata_sidecar_missing_count(diagnostics)
        assert result == 0

    def test_coerce_int_with_int(self):
        """Test _coerce_int with integer."""
        assert _coerce_int(42) == 42

    def test_coerce_int_with_float(self):
        """Test _coerce_int with float."""
        assert _coerce_int(42.7) == 42

    def test_coerce_int_with_string(self):
        """Test _coerce_int with valid string."""
        assert _coerce_int("42") == 42

    def test_coerce_int_with_invalid_string(self):
        """Test _coerce_int with invalid string."""
        assert _coerce_int("not_a_number") == 0

    def test_coerce_int_with_bool(self):
        """Test _coerce_int with boolean."""
        assert _coerce_int(True) == 1
        assert _coerce_int(False) == 0

    def test_coerce_int_with_none(self):
        """Test _coerce_int with None."""
        assert _coerce_int(None) == 0

    def test_trace_missing_requirements_with_list(self):
        """Test _trace_missing_requirements with list."""
        diagnostics = {
            "produced_artifact_trace": {
                "missing_requirements": ["req1", "req2", "req3"]
            }
        }
        result = _trace_missing_requirements(diagnostics)
        assert result == ("req1", "req2", "req3")

    def test_trace_missing_requirements_with_non_list(self):
        """Test _trace_missing_requirements with non-list."""
        diagnostics = {
            "produced_artifact_trace": {"missing_requirements": "not_a_list"}
        }
        result = _trace_missing_requirements(diagnostics)
        assert result == ()

    def test_trace_missing_requirements_missing_key(self):
        """Test _trace_missing_requirements when key is missing."""
        diagnostics = {"produced_artifact_trace": {}}
        result = _trace_missing_requirements(diagnostics)
        assert result == ()

    def test_string_list_or_empty_with_list(self):
        """Test _string_list_or_empty with list."""
        result = _string_list_or_empty(["item1", "item2"])
        assert result == ["item1", "item2"]

    def test_string_list_or_empty_with_non_list(self):
        """Test _string_list_or_empty with non-list."""
        result = _string_list_or_empty("not_a_list")
        assert result == []

    def test_string_list_or_empty_with_mixed_types(self):
        """Test _string_list_or_empty with mixed types."""
        result = _string_list_or_empty([1, "item", None, 2.5])
        assert result == ["1", "item", "None", "2.5"]

    def test_string_list_with_tuple(self):
        """Test _string_list with tuple."""
        result = _string_list(("item1", "item2", "item3"))
        assert result == ["item1", "item2", "item3"]
        assert isinstance(result, list)

    def test_string_list_with_empty_tuple(self):
        """Test _string_list with empty tuple."""
        result = _string_list(())
        assert result == []

    def test_trace_complete_with_true(self):
        """Test _trace_complete when complete is True."""
        diagnostics = {"produced_artifact_trace": {"complete": True}}
        assert _trace_complete(diagnostics) is True

    def test_trace_complete_with_false(self):
        """Test _trace_complete when complete is False."""
        diagnostics = {"produced_artifact_trace": {"complete": False}}
        assert _trace_complete(diagnostics) is False

    def test_trace_complete_missing_key(self):
        """Test _trace_complete when key is missing."""
        diagnostics = {"produced_artifact_trace": {}}
        assert _trace_complete(diagnostics) is False

    def test_lineage_closure_payload_supported(self):
        """Test _lineage_closure_payload with supported boundary."""
        mock_result = MagicMock()
        mock_result.manifest.manifest_id = "test-manifest"
        mock_result.diagnostics = {"lineage_closure_boundary": {"supported": True}}

        result = _lineage_closure_payload(mock_result)
        assert result["status"] == "supported"
        assert result["supported"] is True

    def test_lineage_closure_payload_unsupported(self):
        """Test _lineage_closure_payload with unsupported boundary."""
        mock_result = MagicMock()
        mock_result.manifest.manifest_id = "test-manifest"
        mock_result.diagnostics = {"lineage_closure_boundary": {"supported": False}}

        result = _lineage_closure_payload(mock_result)
        assert result["status"] == "unsupported"
        assert result["supported"] is False

    def test_lineage_closure_payload_missing(self):
        """Test _lineage_closure_payload with missing boundary."""
        mock_result = MagicMock()
        mock_result.manifest.manifest_id = "test-manifest"
        mock_result.diagnostics = {"lineage_closure_boundary": {}}

        result = _lineage_closure_payload(mock_result)
        assert result["status"] == "missing"
        assert result["supported"] is None

    def test_lineage_closure_payload_missing_boundary_key(self):
        """Test _lineage_closure_payload when boundary key is missing."""
        mock_result = MagicMock()
        mock_result.manifest.manifest_id = "test-manifest"
        mock_result.diagnostics = {}

        result = _lineage_closure_payload(mock_result)
        assert result["status"] == "missing"

    def test_inspection_service_factory_with_provided_factory(self):
        """Test _inspection_service_factory_from_ports with provided factory."""
        mock_factory = MagicMock()
        mock_port = MagicMock()

        result = _inspection_service_factory_from_ports(
            manifest_port=mock_port,
            ledger_port=None,
            provided_factory=mock_factory,
        )

        assert result == mock_factory

    def test_inspection_service_factory_without_provided_factory(self):
        """Test _inspection_service_factory_from_ports without provided factory."""
        mock_port = MagicMock()

        result = _inspection_service_factory_from_ports(
            manifest_port=mock_port,
            ledger_port=None,
            provided_factory=None,
        )

        assert callable(result)

    def test_missing_evidence_with_all_missing(self):
        """Test _missing_evidence when all evidence is missing."""
        mock_result = MagicMock()
        mock_result.ledger_entries = []
        mock_result.diagnostics = {
            "published_artifact_count": 0,
            "missing_artifact_links": 1,
            "produced_artifact_trace": {"complete": False},
            "lineage_closure_boundary": {},
        }

        result = _missing_evidence(mock_result)
        assert "run_ledger_entries_missing" in result
        assert "published_artifacts_missing" in result
        assert "artifact_links_incomplete" in result
        assert "produced_artifact_trace_incomplete" in result
        assert "lineage_closure_boundary_missing" in result

    def test_missing_evidence_with_complete_evidence(self):
        """Test _missing_evidence when evidence is complete."""
        mock_result = MagicMock()
        mock_result.ledger_entries = [MagicMock()]
        mock_result.diagnostics = {
            "published_artifact_count": 5,
            "missing_artifact_links": 0,
            "produced_artifact_trace": {"complete": True},
            "lineage_closure_boundary": {"supported": True},
        }

        result = _missing_evidence(mock_result)
        assert len(result) == 0

    def test_missing_evidence_with_partial_evidence(self):
        """Test _missing_evidence with partial evidence."""
        mock_result = MagicMock()
        mock_result.ledger_entries = [MagicMock()]
        mock_result.diagnostics = {
            "published_artifact_count": 5,
            "missing_artifact_links": 0,
            "produced_artifact_trace": {"complete": True},
            "lineage_closure_boundary": {"supported": False},
        }

        result = _missing_evidence(mock_result)
        assert "lineage_closure_boundary_unsupported" in result
        assert "run_ledger_entries_missing" not in result

    def test_resolve_forensic_verdict_prefers_checkpoint_incompatibility(self):
        """Checkpoint incompatibility should override semantic-equivalent replay verdicts."""
        manifest_diff = MagicMock(
            classification="identical",
            occurrence_only=False,
        )

        verdict = _resolve_forensic_verdict(
            manifest_diff=manifest_diff,
            forensic_diff={"checkpoint_anchors": {"compatible": False}},
        )

        assert verdict == "checkpoint_incompatible"

    def test_resolve_forensic_verdict_preserves_semantic_drift(self):
        """Semantic drift should map directly to the terminal forensic verdict."""
        manifest_diff = MagicMock(
            classification="semantic_drift",
            occurrence_only=False,
        )

        verdict = _resolve_forensic_verdict(
            manifest_diff=manifest_diff,
            forensic_diff={"checkpoint_anchors": {"compatible": True}},
        )

        assert verdict == "semantic_drift"

    def test_resolve_forensic_verdict_occurrence_only_replay(self):
        """Occurrence-only diffs should keep the replay-specific verdict."""
        manifest_diff = MagicMock(
            classification="occurrence_only",
            occurrence_only=True,
        )

        verdict = _resolve_forensic_verdict(
            manifest_diff=manifest_diff,
            forensic_diff={"checkpoint_anchors": {"compatible": True}},
        )

        assert verdict == "occurrence_only_replay"

    def test_resolve_forensic_verdict_semantic_equivalent_replay(self):
        """Semantic equivalents without blockers should emit the stable replay verdict."""
        manifest_diff = MagicMock(
            classification="identical",
            occurrence_only=False,
        )

        verdict = _resolve_forensic_verdict(
            manifest_diff=manifest_diff,
            forensic_diff={},
        )

        assert verdict == "semantic_equivalent_replay"

    def test_forensic_diff_payload_backfills_missing_verdict(self):
        """Missing forensic verdicts should be synthesized from the manifest diff."""
        manifest_diff = MagicMock(
            classification="occurrence_only",
            occurrence_only=True,
            cross_surface_replay_diff={"checkpoint_anchors": {"compatible": True}},
        )

        payload = _forensic_diff_payload(manifest_diff)

        assert payload["verdict"] == "occurrence_only_replay"

    def test_artifact_byte_equivalence_reports_missing_refs_when_port_cannot_compare(
        self,
    ):
        """Comparison should stay unavailable when either side lacks artifact refs."""
        mock_port = MagicMock()
        mock_result = MagicMock()
        mock_result.diagnostics = {"artifact_refs": []}

        service = ForensicRunDiffService(
            manifest_port=MagicMock(),
            artifact_byte_comparison_port=mock_port,
        )

        payload = service._build_artifact_byte_equivalence(
            left=mock_result,
            right=mock_result,
        )

        assert payload == {
            "available": False,
            "equivalent": None,
            "compared_artifacts": [],
            "missing_artifacts": [],
            "mismatched_artifacts": [],
            "comparison_scope": "unavailable_missing_refs",
        }
        mock_port.compare_artifacts.assert_not_called()
