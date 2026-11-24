"""Real Delta schemas prevent destructive writes across target profiles."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.infrastructure.storage import target_classification_guard as guard
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
    classification_profile_name,
    get_target_table_profile,
)

pytestmark = pytest.mark.unit


def _table(path: Path, fields: tuple[str, ...] = ()) -> None:
    write_deltalake(
        str(path),
        pa.table({name: ["fixture"] for name in ("target_id", *fields)}),
    )


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_legacy_modes_accept_real_v30_tables(tmp_path: Path, mode: str) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    _table(silver)
    _table(gold)
    assert_target_table_compatibility(silver_path=silver, gold_path=gold, mode=mode)


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_legacy_mode_refuses_enriched_gold_before_clear(
    tmp_path: Path, mode: str
) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    _table(silver)
    _table(gold, TARGET_CLASSIFICATION_FIELDS)
    with pytest.raises(ValueError, match="physical rollback"):
        assert_target_table_compatibility(silver_path=silver, gold_path=gold, mode=mode)
    assert (silver / "_delta_log").is_dir()
    assert (gold / "_delta_log").is_dir()


def test_enrich_requires_migration_for_real_v30_table(tmp_path: Path) -> None:
    _table(tmp_path / "silver")
    with pytest.raises(ValueError, match="complete-cohort migration"):
        assert_target_table_compatibility(
            silver_path=tmp_path / "silver", gold_path=tmp_path / "gold", mode="enrich"
        )


def test_enrich_accepts_complete_v31_and_empty_candidate_destinations(
    tmp_path: Path,
) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    assert_target_table_compatibility(silver_path=silver, gold_path=gold, mode="enrich")
    _table(silver, TARGET_CLASSIFICATION_FIELDS)
    _table(gold, TARGET_CLASSIFICATION_FIELDS)
    assert_target_table_compatibility(silver_path=silver, gold_path=gold, mode="enrich")


def test_profile_inspection_refuses_mixed_pair_and_supports_partial_run(
    tmp_path: Path,
) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    assert get_target_table_profile(silver_path=silver, gold_path=gold) == "empty"
    _table(silver)
    assert get_target_table_profile(silver_path=silver, gold_path=gold) == "V30"
    _table(gold, TARGET_CLASSIFICATION_FIELDS)
    with pytest.raises(ValueError, match="mixed V30/V31"):
        get_target_table_profile(silver_path=silver, gold_path=gold)


def test_v32_fields_do_not_become_an_implicit_v31_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guard, "TARGET_CLASSIFICATION_V32_FIELDS", ("iuphar_subclass",))
    fields = frozenset((*TARGET_CLASSIFICATION_FIELDS, "iuphar_subclass"))
    assert classification_profile_name(fields) == "V32"
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    _table(silver, (*TARGET_CLASSIFICATION_FIELDS, "iuphar_subclass"))
    _table(gold, (*TARGET_CLASSIFICATION_FIELDS, "iuphar_subclass"))
    assert get_target_table_profile(silver_path=silver, gold_path=gold) == "V32"
    with pytest.raises(ValueError, match="cannot write an existing V32"):
        assert_target_table_compatibility(
            silver_path=silver, gold_path=gold, mode="enrich"
        )


def test_partial_v32_contract_requires_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        guard,
        "TARGET_CLASSIFICATION_V32_FIELDS",
        ("iuphar_subclass", "iuphar_family_id"),
    )
    fields = frozenset((*TARGET_CLASSIFICATION_FIELDS, "iuphar_subclass"))
    with pytest.raises(ValueError, match="incomplete target classification"):
        classification_profile_name(fields)


def test_partial_schema_and_unrecognised_directory_require_recovery(
    tmp_path: Path,
) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    _table(silver, (TARGET_CLASSIFICATION_FIELDS[0],))
    with pytest.raises(ValueError, match="incomplete target classification"):
        assert_target_table_compatibility(
            silver_path=silver, gold_path=gold, mode="enrich"
        )
    other = tmp_path / "unrecognised"
    other.mkdir()
    (other / "precious.bin").write_bytes(b"preserve")
    with pytest.raises(ValueError, match="unrecognised target directory"):
        assert_target_table_compatibility(silver_path=other, gold_path=gold, mode="off")
    assert (other / "precious.bin").read_bytes() == b"preserve"


def test_v32_contract_refuses_existing_v30_and_v31_tables(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    current = tmp_path / "current"
    detailed_root = tmp_path / "detailed"
    for root, fields in (
        (legacy, ()),
        (current, TARGET_CLASSIFICATION_FIELDS),
        (
            detailed_root,
            (*TARGET_CLASSIFICATION_FIELDS, *TARGET_CLASSIFICATION_DETAIL_FIELDS),
        ),
    ):
        _table(root / "silver", fields)
        _table(root / "gold", fields)
    for root in (legacy, current):
        with pytest.raises(ValueError, match="migration is a later task"):
            assert_target_table_compatibility(
                silver_path=root / "silver",
                gold_path=root / "gold",
                mode="enrich",
                table_contract="3.2.0",
            )
    assert_target_table_compatibility(
        silver_path=detailed_root / "silver",
        gold_path=detailed_root / "gold",
        mode="enrich",
        table_contract="3.2.0",
    )
    with pytest.raises(ValueError, match="cannot write an existing V32"):
        assert_target_table_compatibility(
            silver_path=detailed_root / "silver",
            gold_path=detailed_root / "gold",
            mode="enrich",
        )
    with pytest.raises(ValueError, match="physical rollback"):
        assert_target_table_compatibility(
            silver_path=detailed_root / "silver",
            gold_path=detailed_root / "gold",
            mode="off",
        )
