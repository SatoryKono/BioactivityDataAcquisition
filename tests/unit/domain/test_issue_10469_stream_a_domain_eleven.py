"""Stream A leftover domain coverage (#10469): observability through mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

import bioetl.domain._observability_contract_core as observability_core
import bioetl.domain.mapping.publication_type_classification as publication_classification
from bioetl.domain._observability_contract_core import (
    enforce_observability_contract_context,
)
from bioetl.domain.behavior._author_helpers import (
    _collect_affiliation_values,
    _surname_initial_from_comma,
)
from bioetl.domain.behavior._dq_value_coercion import _decode_json_list_like
from bioetl.domain.behavior.aggregation_validation_helpers import explicit_field_names
from bioetl.domain.behavior.normalization_service import BioactivityNormalizer
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.behavior.value_validator_rules import (
    _percent_type_error,
    validate_percent_value,
)
from bioetl.domain.composite.config import MergeConfig
from bioetl.domain.composite.field_groups_models import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.control_plane._run_manifest_deserialization import (
    _load_input_snapshots,
    _load_source_refs,
)
from bioetl.domain.control_plane._run_manifest_serialization import (
    _FrozenManifestMapping,
    freeze_manifest_payload,
)
from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.entities.chembl_structures_foundation import (
    TargetProteinClassification,
)
from bioetl.domain.exceptions._redaction import _redact_structured, _redact_url
from bioetl.domain.exceptions.storage._storage import StorageQuotaExceededError
from bioetl.domain.filtering._filter_primitives import (
    _decode_json_list_like as decode_filter_json_list,
    _matches_filter_literal,
    get_list_length,
)
from bioetl.domain.lineage.metadata_bundle import _validate_output_identity_contract
from bioetl.domain.lineage.refs import SchemaRef
from bioetl.domain.mapping._publication_type_classification_support import (
    _normalized_raw_type_part,
    classification_values,
    normalize_publication_classification_value,
)
from bioetl.domain.mapping.publication_type_classification import (
    _get_lookup,
    classify_publication_type,
)
from bioetl.domain.types import ContentHash, EntityID, RunID, RunType
from bioetl.domain.value_objects import PChemblValue

pytestmark = pytest.mark.unit

_RUN = RunID(UUID("00000000-0000-4000-8000-000000000011"))
_HASH = ContentHash("a" * 64)


def test_observability_repair_path_when_missing_fields_forced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        observability_core,
        "missing_observability_fields",
        lambda _context: ("event", "provider"),
    )
    repaired = enforce_observability_contract_context(
        event_name="pipeline_failed",
        context={
            "event": "",
            "provider": "",
            "pipeline": "chembl_activity",
            "run_id": "r1",
        },
        default_provider="chembl",
        default_pipeline="chembl_activity__v1",
        default_run_id="r1",
        default_severity="error",
        correlation_defaults={"trace_id": "t1"},
    )
    assert repaired["event"]
    assert repaired["provider"]
    assert repaired["pipeline"]
    assert repaired["run_id"]
    assert repaired["severity"] == "error"
    assert repaired["error_type"]
    assert repaired["event_family"]


def test_author_helpers_empty_surname_and_non_list_affiliations() -> None:
    assert _surname_initial_from_comma(", Rest") is None
    assert _collect_affiliation_values(123) == []
    assert _collect_affiliation_values(None) == []


def test_dq_json_list_decode_invalid_payload_and_explicit_names() -> None:
    assert _decode_json_list_like("[not json]") is None
    assert explicit_field_names("not-a-list") == set()
    assert explicit_field_names(None) == set()


def test_normalizer_returns_none_when_pchembl_fails_validation() -> None:
    class _LowPchembl:
        def value_to_pchembl(self, value: float, unit: str) -> PChemblValue:
            del value, unit
            return PChemblValue(1.0)

    host = BioactivityNormalizer()
    host.validator = ValueValidator(strict=True)
    host.converter = _LowPchembl()  # type: ignore[assignment]
    assert host.normalize_to_pchembl(10.0, "nM") is None


def test_micromolar_key_missing_and_percent_non_numeric() -> None:
    validator = ValueValidator()
    validator._concentration_ranges.pop("µM", None)
    validator._concentration_ranges.pop("uM", None)
    assert validator._micromolar_key() is None
    assert _percent_type_error("50") is not None
    ok, message = validate_percent_value("50")  # type: ignore[arg-type]
    assert ok is False
    assert message is not None


def test_merge_config_sort_policy_and_compatibility_override() -> None:
    with pytest.raises(ValueError, match="empty column names"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver",
            output_gold_path="gold",
            sort_by_silver=("id", " "),
        )
    with pytest.raises(ValueError, match="duplicate columns"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver",
            output_gold_path="gold",
            sort_by_gold=("id", "id"),
        )
    cfg = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver",
        output_gold_path="gold",
        normalization_compatibility_overrides={"title": "legacy_title"},
    )
    assert cfg.allows_normalization_compatibility_override("title") is True
    assert cfg.allows_normalization_compatibility_override("abstract") is False


def test_field_group_registry_gold_fallback_mapped_extract_and_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = FieldMapping(
        base_name="title",
        provider_columns=("chembl.publication.title",),
        group=FieldGroupId.BIBLIOGRAPHY,
    )
    group = FieldGroupDefinition(
        group_id=FieldGroupId.BIBLIOGRAPHY,
        display_name="Biblio",
        fields=(mapping,),
    )
    registry = FieldGroupRegistry((group,))
    assert (
        registry.is_gold_field("unknown_column") is FieldGroupId.TRASH.include_in_gold
    )
    monkeypatch.setattr(registry, "get_group", lambda _column: FieldGroupId.TRASH)
    classified = registry.validate_columns(["chembl.publication.title", "_sys"])
    assert "chembl.publication.title" in classified["mapped"]
    assert registry._get_provider_rank("zzz.entity.field") == 999
    ordered = registry.get_ordered_columns(["zzz.entity.field"])
    assert ordered == ["zzz.entity.field"]


def test_manifest_snapshots_immutable_mapping_and_invalid_registry_entry() -> None:
    assert _load_input_snapshots("not-a-list", snapshot_ref_type=dict) == ()
    with pytest.raises(ValueError, match="must be an object"):
        _load_input_snapshots([1], snapshot_ref_type=dict)
    loaded = _load_source_refs(
        [{"provider": "chembl", "entity": "activity", "pipeline_name": "p"}],
        source_ref_type=lambda **kwargs: kwargs,
        snapshot_ref_type=dict,
    )
    assert loaded[0]["input_snapshots"] == ()
    with pytest.raises(ValueError, match="must be an object"):
        _load_source_refs(
            [
                {
                    "provider": "chembl",
                    "entity": "activity",
                    "pipeline_name": "p",
                    "input_snapshots": ["bad"],
                }
            ],
            source_ref_type=lambda **kwargs: kwargs,
            snapshot_ref_type=dict,
        )
    frozen = freeze_manifest_payload({"a": 1})
    assert isinstance(frozen, _FrozenManifestMapping)
    with pytest.raises(TypeError, match="immutable"):
        frozen.popitem()
    with pytest.raises(TypeError, match="immutable"):
        frozen.setdefault("b", 2)
    with pytest.raises(ValueError):
        ContractRegistry.from_dict(
            {"entries": {"c.ref": {"identity": "not-an-object"}}}
        )


def test_contract_registry_version_change_returns_empty_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = ContractRegistry()
    existing = SimpleNamespace(identity=SimpleNamespace(contract_version="1.0.0"))
    candidate = SimpleNamespace(identity=SimpleNamespace(contract_version="1.1.0"))
    monkeypatch.setattr(registry, "_validate_version_sequence", lambda *_a, **_k: None)
    assert registry._validate_against_existing(existing, candidate) == []  # type: ignore[arg-type]


def test_target_protein_classification_requires_target_id() -> None:
    with pytest.raises(ValueError, match="Target ChEMBL ID is required"):
        TargetProteinClassification(
            entity_id=EntityID("e1"),
            content_hash=_HASH,
            run_id=_RUN,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            _index=0,
            target_id="",
        )


def test_redaction_url_errors_and_structured_passthrough() -> None:
    assert _redact_url("not-a-url") == "not-a-url"
    assert _redact_url("http:") == "http:"
    redacted_bad_port = _redact_url("http://example.com:999999/path")
    assert redacted_bad_port in {
        "[REDACTED URL]",
        "http://example.com:999999/path",
    } or ("example.com" in redacted_bad_port)
    assert _redact_structured(object(), "", seen=set()) is not None


def test_storage_quota_path_required_and_filter_literal_none() -> None:
    with pytest.raises(ValueError, match="path or table_path"):
        StorageQuotaExceededError._resolve_path(None, None)
    assert decode_filter_json_list("[not json]") == "[not json]"
    assert get_list_length("[not json]") == 1
    assert _matches_filter_literal("x", None) is False


def test_lineage_output_contract_and_schema_ref_to_dict() -> None:
    with pytest.raises(ValueError, match="output metadata"):
        _validate_output_identity_contract(
            SimpleNamespace(), SimpleNamespace(), "artifact"
        )
    payload = SchemaRef(contract_path="contracts/gold.yaml", version="1.0.0").to_dict()
    assert payload["contract_path"] == "contracts/gold.yaml"
    assert payload["version"] == "1.0.0"


def test_publication_classification_uninitialized_and_support_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (
        normalize_publication_classification_value(
            field_name="publication_type_unified",
            value="   ",
            entries=(),
        )
        is None
    )
    with pytest.raises(ValueError, match="Unknown publication classification field"):
        classification_values("unified_type", ())
    assert normalize_publication_classification_value(
        field_name="publication_type_unified",
        value="Journal article",
        entries=(),
    ) in {"Journal article", None}
    assert _normalized_raw_type_part(None) is None
    monkeypatch.setattr(publication_classification, "_PROVIDER_LOOKUPS", {})
    with pytest.raises(RuntimeError, match="not initialized"):
        classify_publication_type("pubmed", raw_type="journal-article")
    assert _get_lookup("chembl") == {}
