"""Opt-in target profiles must keep legacy outputs and hash scope intact."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pandas as pd
import pandera.errors
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.config import PipelineConfig, TableConfig
from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
    TargetClassificationConfig,
)
from bioetl.domain.contracts.gold import ChEMBLTargetGoldSchema
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchemaV31,
    ChEMBLTargetGoldSchemaV32,
    target_v31_schema_hash,
)
from bioetl.domain.entities.chembl_structures_foundation import Target
from bioetl.domain.entities.chembl_target_classification import TargetV31, TargetV32
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
    target_v32_normalization_profile,
)
from bioetl.domain.normalization.target_classification_values import (
    project_classification_detail,
)
from bioetl.domain.schemas.chembl.target import (
    TargetSchema,
    TargetSchemaV31,
    TargetSchemaV32,
)
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    validate_contract_policy_registry_alignment,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from bioetl.infrastructure.schemas.silver_chembl_target_classification import (
    CHEMBL_TARGET_SCHEMA_V31,
    CHEMBL_TARGET_SCHEMA_V32,
)
from bioetl.infrastructure.schemas.target_classification_config import (
    TargetClassificationYamlConfig,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]


def _config(mode: str = "off", table_contract: str | None = None) -> PipelineYamlConfig:
    base = load_pipeline_config_from_root(
        "chembl_target", configs_root=ROOT / "configs"
    )
    options: dict[str, str] = {"mode": mode}
    if mode != "off":
        options.update(
            snapshot_manifest="snapshot.json", snapshot_manifest_sha256="a" * 64
        )
    if table_contract is not None:
        options["table_contract"] = table_contract
    return base.model_copy(
        update={
            "target_classification": TargetClassificationYamlConfig.model_validate(
                options
            )
        }
    )


def test_unset_table_contract_survives_exclude_none_dump() -> None:
    config = TargetClassificationYamlConfig()
    assert "table_contract" not in config.model_dump()
    assert "table_contract" not in config.model_dump(exclude_none=True)
    assert "table_contract" not in config.model_dump(exclude_unset=True)
    pinned = TargetClassificationYamlConfig(
        mode="enrich",
        snapshot_manifest="snapshot.json",
        snapshot_manifest_sha256="a" * 64,
        table_contract="3.1.0",
    )
    assert pinned.model_dump(exclude_none=True)["table_contract"] == "3.1.0"


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "guess"},
        {"mode": "enrich"},
        {"mode": "shadow", "snapshot_manifest": "x.json"},
        {"snapshot_manifest": "x.json", "snapshot_manifest_sha256": "ABC"},
        {"snapshot_manifest": " ", "snapshot_manifest_sha256": "a" * 64},
        {"snapshot_manifest": "x.json", "snapshot_manifest_sha256": "A" * 64},
        {"unexpected": "value"},
    ],
)
def test_invalid_and_unpinned_profiles_are_rejected(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        TargetClassificationYamlConfig.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "enrich"},
        {"mode": "shadow", "snapshot_manifest": "snapshot.json"},
        {"mode": "enrich", "snapshot_manifest": None, "snapshot_manifest_sha256": None},
        {
            "mode": "shadow",
            "snapshot_manifest": "snapshot.json",
            "snapshot_manifest_sha256": "not-a-hash",
        },
    ],
)
def test_generated_json_schema_also_rejects_unpinned_profiles(
    payload: dict[str, object],
) -> None:
    validator = Draft202012Validator(TargetClassificationYamlConfig.model_json_schema())
    assert list(validator.iter_errors(payload))
    assert validator.is_valid({"mode": "off"})
    assert validator.is_valid(
        {
            "mode": "enrich",
            "snapshot_manifest": "snapshot.json",
            "snapshot_manifest_sha256": "a" * 64,
        }
    )


@pytest.mark.parametrize(
    ("mode", "compatible_contracts"),
    [
        (None, {"3.0.0", None}),
        ("off", {"3.0.0", None}),
        ("shadow", {"3.0.0", None}),
        ("enrich", {"3.1.0", "3.2.0", None}),
    ],
)
@pytest.mark.parametrize("table_contract", [None, "3.0.0", "3.1.0", "3.2.0"])
def test_table_contract_selector_agrees_with_json_schemas(
    mode: str | None,
    compatible_contracts: set[str | None],
    table_contract: str | None,
) -> None:
    payload: dict[str, str | None] = {"table_contract": table_contract}
    if mode is not None:
        payload["mode"] = mode
    if mode in {"shadow", "enrich"}:
        payload.update(
            snapshot_manifest="snapshot.json", snapshot_manifest_sha256="a" * 64
        )

    expected = table_contract in compatible_contracts
    if expected:
        domain = TargetClassificationYamlConfig.model_validate(payload).to_domain()
        default = "3.1.0" if mode == "enrich" else "3.0.0"
        assert domain.contract_version == (table_contract or default)
    else:
        with pytest.raises(ValidationError):
            TargetClassificationYamlConfig.model_validate(payload)

    schema = TargetClassificationYamlConfig.model_json_schema()
    assert Draft202012Validator(schema).is_valid(payload) is expected

    generated = json.loads(
        (ROOT / "configs/_schema/pipeline.json").read_text(encoding="utf-8")
    )
    selector = generated["$defs"]["TargetClassificationYamlConfig"]
    assert Draft202012Validator(selector).is_valid(payload) is expected


def test_yaml_profile_roundtrips_to_immutable_domain_config() -> None:
    config = _config("shadow")
    domain = yaml_config_to_domain(config)
    assert domain.target_classification.mode == "shadow"
    assert domain.target_classification.snapshot_manifest_sha256 == "a" * 64
    assert domain.target_classification.contract_version == "3.0.0"
    with pytest.raises(FrozenInstanceError):
        domain.target_classification.mode = "enrich"  # type: ignore[misc]


def test_other_pipelines_cannot_enable_iuphar_target_classification() -> None:
    config = _config("enrich")
    payload = {
        "pipeline_name": "chembl_assay",
        "provider": "chembl",
        "entity_type": "assay",
        "business_primary_keys": ["assay_id"],
        "target_classification": config.target_classification.model_dump(),
    }
    with pytest.raises(ValidationError, match="only for chembl_target"):
        PipelineYamlConfig.model_validate(payload)
    with pytest.raises(ValueError, match="only for chembl_target"):
        PipelineConfig(
            pipeline_name="chembl_assay",
            provider="chembl",
            entity_type="assay",
            table=TableConfig(primary_keys=("assay_id",)),
            target_classification=config.target_classification.to_domain(),
        )


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_off_and_shadow_keep_exact_legacy_bindings(mode: str) -> None:
    config = _config(mode)
    before = config.model_dump()
    contract = load_pipeline_contract_policy("chembl", "target")
    profile = resolve_target_classification_profile(config, contract)
    assert profile.resolved_yaml_config is config
    assert profile.contract_policy is contract
    assert profile.contract_version == "3.0.0"
    assert profile.silver_schema is CHEMBL_TARGET_SCHEMA
    assert profile.pandera_silver_schema is TargetSchema
    assert profile.gold_schema is ChEMBLTargetGoldSchema
    assert profile.entity_class is Target
    assert not set(TARGET_CLASSIFICATION_FIELDS) & set(
        profile.content_hash_include_fields
    )
    assert config.model_dump() == before


def test_enrich_selects_one_consistent_additive_contract_without_mutating_input() -> (
    None
):
    config = _config("enrich")
    before = config.model_dump()
    contract = load_pipeline_contract_policy("chembl", "target")
    profile = resolve_target_classification_profile(config, contract)
    assert profile.contract_version == "3.1.0"
    assert profile.silver_schema is CHEMBL_TARGET_SCHEMA_V31
    assert profile.pandera_silver_schema is TargetSchemaV31
    assert profile.gold_schema is ChEMBLTargetGoldSchemaV31
    assert profile.entity_class is TargetV31
    assert profile.contract_policy.active_version == "3.1.0"
    assert profile.contract_policy.read_order == ["3.1.0"]
    assert profile.contract_policy.write_versions == ["3.1.0"]
    assert profile.contract_policy.rollout_mode == "single"
    validate_contract_policy_registry_alignment(profile.contract_policy)
    assert profile.contract_policy.hash_include == list(
        profile.content_hash_include_fields
    )
    assert profile.resolved_yaml_config.content_hash_policy.contract.version == "3.1.0"
    domain = yaml_config_to_domain(profile.resolved_yaml_config)
    business = next(group for group in domain.column_groups if group.name == "business")
    assert set(TARGET_CLASSIFICATION_FIELDS) <= set(business.fields)
    assert set(TARGET_CLASSIFICATION_FIELDS) <= set(
        next(g for g in domain.data_schema.column_groups if g.name == "business").fields
    )
    assert config.model_dump() == before
    assert contract.active_version == "3.0.0"


def test_enrich_cannot_fall_back_to_an_unscoped_hash_policy() -> None:
    config = _config("enrich").model_copy(update={"content_hash_policy": None})
    with pytest.raises(ValueError, match="explicit V30/V31"):
        resolve_target_classification_profile(config)
    selected = _config("enrich", table_contract="3.2.0").model_copy(
        update={"content_hash_policy": None}
    )
    with pytest.raises(ValueError, match="explicit 3.0.0/3.1.0/3.2.0"):
        resolve_target_classification_profile(selected)


def test_switching_mode_does_not_silently_downgrade_a_v31_hash_binding() -> None:
    enriched = resolve_target_classification_profile(_config("enrich"))
    disabled = enriched.resolved_yaml_config.model_copy(
        update={"target_classification": TargetClassificationYamlConfig()}
    )
    with pytest.raises(ValueError, match="legacy V30"):
        resolve_target_classification_profile(disabled)


def test_v31_arrow_and_entities_do_not_modify_the_v30_shape() -> None:
    old = CHEMBL_TARGET_SCHEMA.names
    new = CHEMBL_TARGET_SCHEMA_V31.names
    assert [name for name in new if name not in TARGET_CLASSIFICATION_FIELDS] == old
    assert all(
        CHEMBL_TARGET_SCHEMA_V31.field(name).nullable
        for name in TARGET_CLASSIFICATION_FIELDS
    )
    first_dq = next(i for i, name in enumerate(new) if name.startswith("_dq_"))
    assert all(new.index(name) < first_dq for name in TARGET_CLASSIFICATION_FIELDS)
    assert not set(TARGET_CLASSIFICATION_FIELDS) & {
        field.name for field in fields(Target)
    }
    assert set(TARGET_CLASSIFICATION_FIELDS) <= {
        field.name for field in fields(TargetV31)
    }


def _gold_frame() -> pd.DataFrame:
    row: dict[str, object] = dict.fromkeys(
        ChEMBLTargetGoldSchemaV31.to_schema().columns
    )
    row.update(
        entity_id="chembl:CHEMBL1",
        content_hash="a" * 64,
        target_id="CHEMBL1",
        species_group_flag=False,
        _index=0,
        _dq_warn=False,
        _dq_error=False,
        iuphar_class="Enzyme",
        iuphar_annotation_status="partial",
        target_class_profile_sha256="b" * 64,
    )
    return pd.DataFrame([row])


def test_v31_gold_accepts_direct_partial_and_nullable_unassigned_fields() -> None:
    validated = ChEMBLTargetGoldSchemaV31.validate(_gold_frame())
    assert validated.iloc[0]["iuphar_class"] == "Enzyme"
    assert validated.iloc[0]["local_class"] is None
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        ChEMBLTargetGoldSchema.validate(_gold_frame())


def test_v31_gold_rejects_missing_projection_and_malformed_profile_hash() -> None:
    with pytest.raises(pandera.errors.SchemaError):
        ChEMBLTargetGoldSchemaV31.validate(_gold_frame().drop(columns=["iuphar_class"]))
    frame = _gold_frame()
    frame["target_class_profile_sha256"] = "not-a-hash"
    with pytest.raises(pandera.errors.SchemaError):
        ChEMBLTargetGoldSchemaV31.validate(frame)


def test_legacy_hash_is_unchanged_while_v31_tracks_class_and_profile() -> None:
    old = resolve_target_classification_profile(_config("shadow"))
    new = resolve_target_classification_profile(_config("enrich"))
    v30 = EntityIdentityGenerator(
        content_hash_include_fields=set(old.content_hash_include_fields)
    )
    v31 = EntityIdentityGenerator(
        content_hash_include_fields=set(new.content_hash_include_fields)
    )
    source = {"target_id": "CHEMBL1", "pref_name": "Example", "taxonomy_id": 9606}
    classified = {
        **source,
        "iuphar_class": "Enzyme",
        "target_class_profile_sha256": "a" * 64,
    }
    assert v30.compute_content_hash("chembl", source) == v30.compute_content_hash(
        "chembl", classified
    )
    first = v31.compute_content_hash("chembl", classified)
    assert first != v31.compute_content_hash(
        "chembl", {**classified, "iuphar_class": "Receptor"}
    )
    assert first != v31.compute_content_hash(
        "chembl", {**classified, "target_class_profile_sha256": "b" * 64}
    )
    assert first == v31.compute_content_hash(
        "chembl", {**classified, "_run_id": "another", "_ingestion_ts": "later"}
    )


def test_domain_default_is_disabled_without_a_snapshot_claim() -> None:
    value = TargetClassificationConfig()
    assert not value.enabled
    assert value.snapshot_manifest is None
    assert value.snapshot_manifest_sha256 is None


def test_v31_identity_hash_tracks_the_actual_schema_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = target_v31_schema_hash()
    schema = ChEMBLTargetGoldSchemaV31.to_json_schema()
    monkeypatch.setattr(
        ChEMBLTargetGoldSchemaV31,
        "to_json_schema",
        classmethod(lambda _: {**schema, "title": "changed-contract"}),
    )
    assert len(before) == 64
    assert target_v31_schema_hash() != before


def test_v31_normalization_preserves_legacy_rules_and_accepts_new_hash_fields() -> None:
    legacy_identity = CHEMBL_TARGET_PROFILE.identity
    profile = target_v31_normalization_profile()
    assert profile.fields == CHEMBL_TARGET_PROFILE.fields | set(
        TARGET_CLASSIFICATION_FIELDS
    )
    for name, rule in CHEMBL_TARGET_PROFILE.field_rules.items():
        assert profile.rule_for(name) is rule
    for name in TARGET_CLASSIFICATION_FIELDS:
        rule = profile.rule_for(name)
        assert rule is not None and rule.include_in_hash
        assert rule.apply("  frozen decision  ") == "  frozen decision  "
        assert rule.apply(None) is None
    binding = resolve_target_classification_profile(_config("enrich"))
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target",
        profile=profile,
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset(binding.content_hash_include_fields),
    )
    source = {"target_id": "CHEMBL1", "iuphar_class": "Enzyme"}
    first = processor.compute_content_hash(source)
    assert first != processor.compute_content_hash(
        {**source, "iuphar_class": "Receptor"}
    )
    assert CHEMBL_TARGET_PROFILE.identity == legacy_identity
    assert CHEMBL_TARGET_PROFILE.fields.isdisjoint(TARGET_CLASSIFICATION_FIELDS)
    assert profile.identity.profile_hash != legacy_identity.profile_hash


def _detail(**overrides: object) -> dict[str, str | None]:
    payload: dict[str, object] = {
        "computed": True,
        "iuphar_type_raw": "enzyme",
        "annotation_status": "annotated",
        "family_ids": ("b", "a", "a"),
        "subclasses": ("zeta", "alpha"),
        "paths": (("2", ("leaf", "root")), ("1", ("root", "leaf"))),
        "local_status": "supported",
        "local_subclasses": ("local-b", "local-a"),
        "local_rule_ids": ("rule-b", "rule-a"),
        "effective_subclasses": ("eff-b", "eff-a"),
        "conflict_codes": ("conflict-b", "conflict-a"),
    }
    match_ids = overrides.pop("match_evidence_ids", ("match-b", "match-a"))
    local_ids = overrides.pop("local_evidence_ids", ("local-ev-b", "local-ev-a"))
    payload["evidence_ids"] = (match_ids, local_ids)
    payload.update(overrides)
    return project_classification_detail(**payload)  # type: ignore[arg-type]


def test_explicit_table_contract_selects_v32_without_changing_default_enrich() -> None:
    contract = load_pipeline_contract_policy("chembl", "target")
    default = resolve_target_classification_profile(_config("enrich"), contract)
    assert default.contract_version == "3.1.0"
    assert set(TARGET_CLASSIFICATION_DETAIL_FIELDS).isdisjoint(
        default.content_hash_include_fields
    )
    selected = resolve_target_classification_profile(
        _config("enrich", "3.2.0"), contract
    )
    assert selected.contract_version == "3.2.0"
    assert selected.entity_class is TargetV32
    assert selected.silver_schema is CHEMBL_TARGET_SCHEMA_V32
    assert selected.pandera_silver_schema is TargetSchemaV32
    assert selected.gold_schema is ChEMBLTargetGoldSchemaV32
    assert selected.contract_policy.active_version == "3.2.0"
    assert selected.contract_policy.read_order == ["3.2.0"]
    assert selected.contract_policy.write_versions == ["3.2.0"]
    validate_contract_policy_registry_alignment(selected.contract_policy)
    assert list(TARGET_CLASSIFICATION_DETAIL_FIELDS) == [
        name
        for name in selected.content_hash_include_fields
        if name in TARGET_CLASSIFICATION_DETAIL_FIELDS
    ]


@pytest.mark.parametrize(
    ("mode", "version"), [("off", "3.0.0"), ("shadow", "3.0.0"), ("enrich", "3.1.0")]
)
def test_absent_selector_matches_a_manifest_written_before_the_field(
    mode, version
) -> None:
    stored = _config(mode, version).target_classification.model_dump(mode="json")
    del stored["table_contract"]
    restored = TargetClassificationYamlConfig.model_validate(stored)
    assert restored.model_dump(mode="json") == stored
    assert restored.to_domain().contract_version == version


def test_v32_gold_contract_records_the_detail_normalization_profile() -> None:
    payload = json.loads(
        (ROOT / "docs/04-reference/contracts/gold/chembl_target_v3.2.json").read_text(
            encoding="utf-8"
        )
    )
    identity = target_v32_normalization_profile().identity
    assert payload["normalization_profile"] == {
        "ref": identity.profile_name,
        "version": identity.profile_version,
        "hash": identity.profile_hash,
    }


def test_unavailable_match_is_not_recorded_as_unannotated() -> None:
    detail = project_classification_detail(
        computed=True,
        iuphar_type_raw=None,
        annotation_status=None,
        match_status="source_unavailable",
        family_ids=(),
        subclasses=(),
        paths=(),
        local_status=None,
        local_subclasses=(),
        local_rule_ids=(),
        effective_subclasses=(),
        conflict_codes=(),
        evidence_ids=((), ()),
    )
    assert detail["iuphar_source_completeness"] == "source_unavailable"


@pytest.mark.parametrize(
    ("mode", "table_contract"),
    [("off", "3.2.0"), ("shadow", "3.1.0"), ("enrich", "3.0.0")],
)
def test_incompatible_profile_and_table_contract_are_rejected(
    mode: str, table_contract: str
) -> None:
    payload: dict[str, str] = {"mode": mode, "table_contract": table_contract}
    if mode != "off":
        payload.update(
            snapshot_manifest="snapshot.json", snapshot_manifest_sha256="a" * 64
        )
    with pytest.raises(ValidationError):
        TargetClassificationYamlConfig.model_validate(payload)


def test_v32_layers_share_detail_columns_and_keep_v31_fields() -> None:
    arrow = list(CHEMBL_TARGET_SCHEMA_V32.names)
    pandera = list(TargetSchemaV32.to_schema().columns)
    gold = list(ChEMBLTargetGoldSchemaV32.to_schema().columns)
    expected = (*TARGET_CLASSIFICATION_FIELDS, *TARGET_CLASSIFICATION_DETAIL_FIELDS)
    for names in (arrow, pandera, gold):
        start = names.index(expected[0])
        assert tuple(names[start : start + len(expected)]) == expected
    assert [name for name in arrow if name not in expected] == list(
        CHEMBL_TARGET_SCHEMA.names
    )
    assert set(TARGET_CLASSIFICATION_DETAIL_FIELDS) <= {
        field.name for field in fields(TargetV32)
    }


def test_v32_projection_is_stable_under_permutation_and_distinguishes_null() -> None:
    first = _detail()
    second = _detail(
        family_ids=("a", "b"),
        subclasses=("alpha", "zeta"),
        paths=(("1", ("root", "leaf")), ("2", ("leaf", "root"))),
        local_subclasses=("local-a", "local-b"),
        local_rule_ids=("rule-a", "rule-b"),
        effective_subclasses=("eff-a", "eff-b"),
        conflict_codes=("conflict-a", "conflict-b"),
        match_evidence_ids=("match-a", "match-b"),
        local_evidence_ids=("local-ev-a", "local-ev-b"),
    )
    assert first == second
    assert first["iuphar_source_completeness"] == "typed"
    empty = _detail(
        iuphar_type_raw=None,
        annotation_status=None,
        family_ids=(),
        subclasses=(),
        paths=(),
        local_status=None,
        local_subclasses=(),
        local_rule_ids=(),
        effective_subclasses=(),
        conflict_codes=(),
        match_evidence_ids=(),
        local_evidence_ids=(),
    )
    assert empty["iuphar_family_ids"] == "[]"
    assert empty["iuphar_source_completeness"] == "unannotated"
    absent = project_classification_detail(
        computed=False,
        iuphar_type_raw=None,
        annotation_status=None,
        family_ids=(),
        subclasses=(),
        paths=(),
        local_status=None,
        local_subclasses=(),
        local_rule_ids=(),
        effective_subclasses=(),
        conflict_codes=(),
        evidence_ids=((), ()),
    )
    assert all(value is None for value in absent.values())
    binding = resolve_target_classification_profile(_config("enrich", "3.2.0"))
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target",
        profile=target_v32_normalization_profile(),
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset(binding.content_hash_include_fields),
    )
    source = {"target_id": "CHEMBL1", **first}
    permuted = {"target_id": "CHEMBL1", **second}
    assert processor.compute_content_hash(source) == processor.compute_content_hash(
        permuted
    )
    assert processor.compute_content_hash(source) != processor.compute_content_hash(
        {"target_id": "CHEMBL1", **empty}
    )
    assert processor.compute_content_hash(
        {"target_id": "CHEMBL1", **empty}
    ) != processor.compute_content_hash({"target_id": "CHEMBL1", **absent})


def test_v32_gold_accepts_canonical_detail_and_rejects_unsorted_json() -> None:
    row: dict[str, object] = dict.fromkeys(
        ChEMBLTargetGoldSchemaV32.to_schema().columns
    )
    row.update(
        entity_id="chembl:CHEMBL1",
        content_hash="a" * 64,
        target_id="CHEMBL1",
        species_group_flag=False,
        _index=0,
        _dq_warn=False,
        _dq_error=False,
        target_class_profile_sha256="b" * 64,
        **_detail(),
    )
    validated = ChEMBLTargetGoldSchemaV32.validate(pd.DataFrame([row]))
    assert validated.iloc[0]["iuphar_family_ids"] == row["iuphar_family_ids"]
    row["iuphar_family_ids"] = '["b","a"]'
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        ChEMBLTargetGoldSchemaV32.validate(pd.DataFrame([row]))
