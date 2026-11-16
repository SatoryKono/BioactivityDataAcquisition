"""Full target migration admission rejects forged identities and decisions."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest
import yaml
from deltalake import write_deltalake

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchemaV31,
)
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
    LoadedIupharProfile,
    LoadedIupharSnapshot,
)
from bioetl.infrastructure.storage import target_migration_validation as validation
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
)
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation
from iuphar_target_class.pipeline import IndexedSnapshot
from iuphar_target_class.snapshot import Completeness
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]


def _synthetic_profile(tmp_path: Path) -> LoadedIupharProfile:
    """Explicit software fixture; this is not a biological acceptance receipt."""
    raw = canonical_json_bytes({"targetId": 1, "type": "gpcr"}).decode()
    snapshot = IndexedSnapshot.build(
        snapshot_id="migration-fixture",
        mapping_version="synthetic-mapping",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P12345",), None, None, "9606", ("Fixture",), ()),
        ),
        annotations={
            "1": ProviderAnnotation(
                "1", "gpcr", (), sha256_bytes(raw.encode()), "9606", raw
            )
        },
        family_nodes=(),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
    )
    loaded = LoadedIupharSnapshot(
        snapshot,
        Completeness(True, True, False, True, "synthetic fixture"),
        "b" * 64,
        (tmp_path / "snapshot.json").as_uri(),
        "2026-11-16T00:00:00+00:00",
        frozenset({"9606"}),
        {},
    )
    return LoadedIupharProfile(
        loaded,
        "a" * 64,
        (tmp_path / "profile.json").as_uri(),
        "c" * 64,
        "bioetl-iuphar-input-v1",
        "plan-v1-r8",
        "3.1.0",
    )


def _processor(
    fields: tuple[str, ...], *, enrich: bool
) -> RecordNormalizationProcessor:
    return RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target",
        profile=target_v31_normalization_profile() if enrich else CHEMBL_TARGET_PROFILE,
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset(fields),
    )


def _old_row(target_id: str, fields: tuple[str, ...]) -> dict[str, object]:
    row = {
        "target_id": target_id,
        "entity_id": "chembl:" + target_id,
        "content_hash": "0" * 64,
        "target_type": "SINGLE PROTEIN",
        "pref_name": "Fixture",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "organism_class": None,
        "species_group_flag": False,
        "component_accessions": '["P12345"]',
        "target_description": None,
        "_run_id": "synthetic-old-run",
        "_run_type": "backfill",
        "_ingestion_ts": "2026-11-16T00:00:00+00:00",
        "_index": 0,
        "_dq_warn": False,
        "_dq_error": False,
    }
    return _processor(fields, enrich=False).normalize_record(row)


def _gold(row: dict[str, object]) -> dict[str, object]:
    source = {
        **row,
        "description": row.get("target_description"),
        "taxonomy_id": 9606.0,
    }
    return {
        field: source.get(field)
        for field in ChEMBLTargetGoldSchemaV31.to_schema().columns
        if field not in TARGET_CLASSIFICATION_FIELDS or field in row
    }


@pytest.fixture
def admitted_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = yaml.safe_load((ROOT / "configs/entities/chembl/target.yaml").read_text())
    fields = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    config_path = tmp_path / "target.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    paths = {
        name: tmp_path / name
        for name in ("silver", "gold", "assay", "candidate_silver", "candidate_gold")
    }
    paths["config"] = config_path
    profile = _synthetic_profile(tmp_path)
    classifier = IupharTargetClassificationAdapter(profile)
    old_silver = [_old_row("CHEMBL1", fields), _old_row("CHEMBL2", fields)]
    new_silver = []
    v31_fields = (*fields, *TARGET_CLASSIFICATION_FIELDS)
    for row in old_silver:
        result = classifier.classify_record(
            row,
            input_row_id="fixture:" + str(row["target_id"]),
            run_id="synthetic-candidate",
            run_started_at="2026-11-16T00:00:00+00:00",
        )
        candidate = {**row, **result.projection}
        candidate["content_hash"] = _processor(
            v31_fields, enrich=True
        ).compute_content_hash(candidate)
        new_silver.append(candidate)
    tables = {
        paths["silver"]: old_silver,
        paths["gold"]: [_gold(old_silver[0])],
        paths["candidate_silver"]: new_silver,
        paths["candidate_gold"]: [_gold(new_silver[0])],
        paths["assay"]: [{"target_id": "CHEMBL1"}, {"target_id": None}],
    }
    monkeypatch.setattr(validation, "_load_candidate_profile", lambda _: profile)
    monkeypatch.setattr(validation, "_read_delta", lambda path: tables[path])
    return paths, fields, tables


def test_silver_superset_preserves_each_complete_layer_and_final_gold_closure(
    admitted_candidate,
):
    paths, fields, _ = admitted_candidate
    report = validation.validate_target_candidate(paths, fields)
    assert report["silver"]["rows"] == 2
    assert report["gold"]["rows"] == 1
    assert report["fk_closure"] == "PASS"


def test_candidate_entity_identity_cannot_change(admitted_candidate):
    paths, fields, tables = admitted_candidate
    tables[paths["candidate_silver"]][0]["entity_id"] = "forged:identity"
    with pytest.raises(ValueError, match="legacy entity_id"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize("layer", ["candidate_silver", "candidate_gold"])
def test_well_formed_dummy_v31_hash_is_rejected(admitted_candidate, layer):
    paths, fields, tables = admitted_candidate
    tables[paths[layer]][0]["content_hash"] = "d" * 64
    with pytest.raises(ValueError, match="V31 content hash"):
        validation.validate_target_candidate(paths, fields)


def test_invented_class_with_recomputed_valid_hash_is_rejected(admitted_candidate):
    paths, fields, tables = admitted_candidate
    row = tables[paths["candidate_silver"]][0]
    row["iuphar_class"] = "Enzyme"
    row["content_hash"] = _processor(
        (*fields, *TARGET_CLASSIFICATION_FIELDS), enrich=True
    ).compute_content_hash(row)
    with pytest.raises(ValueError, match="classification differs from admitted source"):
        validation.validate_target_candidate(paths, fields)


def test_gold_projection_must_equal_its_classified_silver_source(admitted_candidate):
    paths, fields, tables = admitted_candidate
    row = tables[paths["candidate_gold"]][0]
    row["effective_class"] = "Enzyme"
    processor = _processor((*fields, *TARGET_CLASSIFICATION_FIELDS), enrich=True)
    hash_input = {**row, "target_description": row["description"]}
    hash_input.pop("description")
    row["content_hash"] = processor.compute_content_hash(
        processor.normalize_business_data(hash_input)
    )
    with pytest.raises(ValueError, match="classification differs from admitted source"):
        validation.validate_target_candidate(paths, fields)


def test_migration_plan_cannot_weaken_frozen_canonical_hash_scope(admitted_candidate):
    paths, fields, _ = admitted_candidate
    with pytest.raises(ValueError, match="frozen canonical V30 policy"):
        validation.validate_target_candidate(paths, fields[:-1])


def test_final_gold_foreign_key_gap_is_rejected(admitted_candidate):
    paths, fields, tables = admitted_candidate
    tables[paths["assay"]].append({"target_id": "CHEMBL3"})
    with pytest.raises(ValueError, match="foreign-key closure"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize("existing", ["silver", "gold"])
def test_destructive_enrich_preserves_existing_v31_table(tmp_path: Path, existing: str):
    table = tmp_path / existing
    write_deltalake(
        str(table),
        pa.table(
            {name: ["fixture"] for name in ("target_id", *TARGET_CLASSIFICATION_FIELDS)}
        ),
    )
    original = {
        path.relative_to(table): path.read_bytes()
        for path in table.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError, match="before destructive writes"):
        assert_target_table_compatibility(
            silver_path=tmp_path / "silver",
            gold_path=tmp_path / "gold",
            mode="enrich",
            destructive=True,
        )
    assert original == {
        path.relative_to(table): path.read_bytes()
        for path in table.rglob("*")
        if path.is_file()
    }


def test_destructive_enrich_allows_empty_candidate_destinations(tmp_path: Path):
    assert_target_table_compatibility(
        silver_path=tmp_path / "silver",
        gold_path=tmp_path / "gold",
        mode="enrich",
        destructive=True,
    )
