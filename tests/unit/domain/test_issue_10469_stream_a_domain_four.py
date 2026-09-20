"""Stream A domain coverage for #10469 / #10519 (hierarchy, chem, aggregation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from io import StringIO
from uuid import UUID

import pytest
import yaml

from bioetl.domain.behavior.chemical_standardization import (
    standardize_chemical_structure,
)
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.control_plane._reproducibility_profile_builders import (
    _build_composite_reproducibility_family_profile,
    _build_source_reproducibility_family_profile,
    _resolve_source_profile_reason,
    _source_support_state,
    resolve_reproducibility_family,
)
from bioetl.domain.control_plane._run_manifest_serialization import (
    _FrozenManifestMapping,
    freeze_manifest_payload,
    normalize_manifest_created_at,
    normalize_manifest_serializable,
)
from bioetl.domain.control_plane.config_source_hashing import (
    _UniqueKeySafeLoader,
    _construct_unique_mapping,
    _to_canonical_jsonable,
    compute_canonical_yaml_sha256,
    compute_config_source_hashes,
)
from bioetl.domain.lineage.refs import (
    DatasetRef,
    LineageNodeRef,
    SchemaRef,
    TransformRef,
)
from bioetl.domain.medallion import Layer
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassLevel,
)

pytestmark = pytest.mark.unit


def _level(level_id: int, name: str | None = "n") -> ProteinClassLevel:
    return ProteinClassLevel(id=level_id, name=name, desc=None)


def test_protein_class_hierarchy_path_leaf_and_validation_branches() -> None:
    with pytest.raises(ValueError, match="leaf_id must be positive"):
        ProteinClassHierarchy(
            l1=_level(1),
            l2=ProteinClassLevel.empty(),
            l3=ProteinClassLevel.empty(),
            l4=ProteinClassLevel.empty(),
            l5=ProteinClassLevel.empty(),
            leaf_id=0,
        )
    with pytest.raises(ValueError, match="must be positive"):
        ProteinClassLevel(id=0, name="x", desc=None)

    projected = ProteinClassHierarchy(
        l1=_level(1, "Root"),
        l2=_level(2, None),
        l3=ProteinClassLevel.empty(),
        l4=ProteinClassLevel.empty(),
        l5=ProteinClassLevel.empty(),
        leaf_id=2,
    )
    assert projected.path_ids == (1, 2)
    assert projected.path_names == ("Root", "")
    assert projected.path_labels == ("1:Root", "2")
    assert projected.depth == 1
    assert projected.root_id == 1
    assert projected.is_leaf is False

    leafed = ProteinClassHierarchy(
        l1=_level(1),
        l2=_level(2),
        l3=_level(3),
        l4=_level(4),
        l5=_level(5),
        leaf_id=5,
        path=(_level(1), _level(5)),
    )
    assert leafed.is_leaf is True
    assert leafed.path_levels[-1].id == 5

    with pytest.raises(ValueError, match="must not be empty"):
        ProteinClassHierarchy(
            l1=_level(1),
            l2=ProteinClassLevel.empty(),
            l3=ProteinClassLevel.empty(),
            l4=ProteinClassLevel.empty(),
            l5=ProteinClassLevel.empty(),
            leaf_id=1,
            path=(),
        )
    with pytest.raises(ValueError, match="must end at leaf_id"):
        ProteinClassHierarchy(
            l1=_level(1),
            l2=_level(2),
            l3=ProteinClassLevel.empty(),
            l4=ProteinClassLevel.empty(),
            l5=ProteinClassLevel.empty(),
            leaf_id=2,
            path=(_level(1),),
        )
    with pytest.raises(ValueError, match="must not contain cycles"):
        ProteinClassHierarchy(
            l1=_level(1),
            l2=_level(2),
            l3=ProteinClassLevel.empty(),
            l4=ProteinClassLevel.empty(),
            l5=ProteinClassLevel.empty(),
            leaf_id=1,
            path=(_level(1), _level(1)),
        )


def test_chemical_standardization_covers_invalid_blank_and_deferred_parent_paths() -> (
    None
):
    missing = standardize_chemical_structure(
        canonical_smiles="  ",
        isomeric_smiles=None,
        inchi="",
        inchi_key=None,
    )
    assert missing.chemical_standardization_status == "missing_structure"

    invalid = standardize_chemical_structure(
        canonical_smiles=1,
        isomeric_smiles=["C"],
        inchi=object(),
        inchi_key=2,
    )
    assert invalid.chemical_standardization_status == "invalid"
    assert "canonical_smiles_invalid" in invalid.chemical_standardization_warnings

    deferred = standardize_chemical_structure(
        canonical_smiles="CCO.O",
        isomeric_smiles="CCO.N",
        inchi="not-inchi",
        inchi_key="not-a-key",
        covalent_unit_count=2,
        charge=1,
    )
    assert deferred.chemical_standardization_status in {"partial", "invalid"}
    assert (
        "multi_component_parent_deferred" in deferred.chemical_standardization_warnings
    )
    assert "charge_normalization_deferred" in deferred.chemical_standardization_warnings
    assert "inchi_invalid" in deferred.chemical_standardization_warnings
    assert "inchi_key_invalid" in deferred.chemical_standardization_warnings

    from_smiles = standardize_chemical_structure(
        canonical_smiles="CCO",
        isomeric_smiles=None,
        inchi=None,
        inchi_key=None,
    )
    assert from_smiles.structure_parent_key == "smiles:CCO"
    assert (
        "parent_key_from_smiles_without_inchi_key"
        in from_smiles.chemical_standardization_warnings
    )


def test_aggregation_config_coercion_and_validation_errors() -> None:
    with pytest.raises(ValueError, match="Invalid aggregation function"):
        AggregationFunction.from_string("median")
    with pytest.raises(ValueError, match="Invalid cardinality"):
        EnricherCardinality.from_string("many")
    spec = AggregationFieldSpec(source_field="term", agg_function="first")  # type: ignore[arg-type]
    assert spec.agg_function is AggregationFunction.FIRST
    assert spec.effective_output_field == "term"

    config = AggregationConfig(
        group_by="document_chembl_id",
        fields=[
            {
                "source_field": "term",
                "agg_function": "collect_list",
                "output_field": " terms ",
            }
        ],
        order_by="term",
    )
    assert config.order_by == ("term",)
    assert config.fields[0].output_field == "terms"

    with pytest.raises(TypeError, match="string or sequence"):
        AggregationConfig(
            group_by="k",
            fields=[AggregationFieldSpec("a", AggregationFunction.FIRST)],
            order_by=1,
        )
    with pytest.raises(ValueError, match="cannot contain empty"):
        AggregationConfig(
            group_by="k",
            fields=[AggregationFieldSpec("a", AggregationFunction.FIRST)],
            order_by=[" "],
        )
    with pytest.raises(ValueError, match="cannot contain duplicate"):
        AggregationConfig(
            group_by="k",
            fields=[AggregationFieldSpec("a", AggregationFunction.FIRST)],
            order_by=["a", "a"],
        )
    with pytest.raises(ValueError, match="must be a sequence"):
        AggregationConfig(group_by="k", fields="term")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="cannot be empty"):
        AggregationConfig(group_by="k", fields=[])
    with pytest.raises(ValueError, match="must be AggregationFieldSpec"):
        AggregationConfig(group_by="k", fields=[1])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="duplicate output field"):
        AggregationConfig(
            group_by="k",
            fields=(
                AggregationFieldSpec("term", AggregationFunction.FIRST),
                AggregationFieldSpec("term", AggregationFunction.COUNT),
            ),
        )
    with pytest.raises(ValueError, match="output_field must be a string"):
        AggregationFieldSpec("term", AggregationFunction.FIRST, output_field=1)  # type: ignore[arg-type]


def test_reproducibility_profile_builders_cover_family_resolution_and_support_states() -> (
    None
):
    assert (
        resolve_reproducibility_family(provider=None, entity=None, contract_ref="  ")
        is None
    )
    assert resolve_reproducibility_family(
        provider="chembl", entity="activity", contract_ref=None
    ) == ("chembl.activity")
    assert (
        resolve_reproducibility_family(
            provider="", entity="", contract_ref="chembl.assay"
        )
        == "chembl.assay"
    )
    assert (
        _resolve_source_profile_reason(supported=True, published=True)
        == "family_within_supported_boundary"
    )
    assert _resolve_source_profile_reason(supported=False, published=True).startswith(
        "family_within_published"
    )
    assert _resolve_source_profile_reason(supported=False, published=False).startswith(
        "family_outside"
    )
    assert _source_support_state(supported=False, published=True) == "rebuild_only"
    assert _source_support_state(supported=False, published=False) == "debug_only"
    source = _build_source_reproducibility_family_profile(
        family="unknown.family", execution_context="source"
    )
    assert source.strict_exact_replay_supported is False
    composite = _build_composite_reproducibility_family_profile(
        family="composite.activity", execution_context="composite"
    )
    assert composite.replay_family_contract == "rebuild_only"


def test_run_manifest_serialization_freezes_and_normalizes_nested_payloads() -> None:
    class _Kind(Enum):
        LIVE = "live"

    @dataclass
    class _Row:
        kind: _Kind
        ident: UUID
        when: datetime

    frozen = freeze_manifest_payload(
        {"items": [{"n": 1}, {"n": 2}], "tags": {"b", "a"}}
    )
    assert isinstance(frozen, _FrozenManifestMapping)
    with pytest.raises(TypeError, match="immutable"):
        frozen["x"] = 1  # type: ignore[index]
    with pytest.raises(TypeError, match="immutable"):
        del frozen["items"]
    with pytest.raises(TypeError, match="immutable"):
        frozen.clear()
    with pytest.raises(TypeError, match="immutable"):
        frozen.pop("items")
    with pytest.raises(TypeError, match="immutable"):
        frozen.update(x=1)

    naive = datetime(2026, 1, 1, 12, 0)
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert normalize_manifest_created_at(naive).tzinfo is UTC
    assert normalize_manifest_created_at(aware).hour == 12
    encoded = normalize_manifest_serializable(
        _Row(
            kind=_Kind.LIVE,
            ident=UUID("12345678-1234-5678-1234-567812345678"),
            when=aware,
        )
    )
    assert encoded["kind"] == "live"
    assert encoded["ident"] == "12345678-1234-5678-1234-567812345678"
    assert isinstance(normalize_manifest_serializable({1, 3, 2}), list)


def test_config_source_hashing_covers_unhashable_keys_enum_and_yml_suffix() -> None:
    class _Mode(Enum):
        A = "a"

    assert _to_canonical_jsonable((_Mode.A, datetime(2026, 1, 1, tzinfo=UTC))) == [
        "a",
        "2026-01-01T00:00:00+00:00",
    ]
    with pytest.raises(ValueError, match="must be hashable"):
        compute_canonical_yaml_sha256(b"? [1, 2]: value\n")
    with pytest.raises(ValueError, match="key collision"):
        _to_canonical_jsonable({1: "a", "1": "b"})
    hashes = compute_config_source_hashes(
        source_path="configs/base/pipeline.YML", raw_bytes=b"a: 1\n"
    )
    assert hashes.hash_strategy == "canonical_yaml"
    sequence_node = yaml.compose("[1, 2]")
    loader = _UniqueKeySafeLoader(StringIO(""))
    with pytest.raises((TypeError, AttributeError, yaml.YAMLError)):
        _construct_unique_mapping(loader, sequence_node)


def test_lineage_refs_cover_encoding_defaults_and_from_dict_optional_fields() -> None:
    dataset = DatasetRef(layer=Layer.SILVER, logical_name="foo:bar@x", version="1")
    assert "%3A" in dataset.node_id
    assert "%40" in dataset.node_id
    assert dataset.to_node_ref().node_type.value == "dataset"
    restored = DatasetRef.from_dict(dataset.to_dict())
    assert restored.logical_name == "foo:bar@x"

    node = LineageNodeRef.from_dict(
        {"node_type": "run", "node_id": "run:1", "label": None, "attributes": "skip"}
    )
    assert node.label is None
    assert node.attributes == {}

    transform = TransformRef(name="normalize")
    assert "unknown_pipeline" in transform.node_id
    assert "unknown_version" in transform.node_id
    assert TransformRef.from_dict(transform.to_dict()).name == "normalize"

    schema = SchemaRef.from_dict(
        {
            "contract_path": "contracts/gold.yaml",
            "version": None,
            "validation_mode": None,
            "dataset_name": None,
        }
    )
    assert schema.node_id.endswith("unknown_version")
    assert schema.to_node_ref().label == "contracts/gold.yaml"
