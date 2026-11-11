"""TC-13 delivery names, collision, and the public batch call."""

from __future__ import annotations

from pathlib import Path

import pytest

from iuphar_target_class.delivery import (
    contract_document,
    main,
    output_row,
    result_names,
    run_batch,
)

pytestmark = pytest.mark.unit
_EXAMPLE = (
    Path(__file__).resolve().parents[3]
    / "data/iuphar_target_class/delivery/example-input.csv"
)


def _copy_example(tmp_path: Path, name: str = "example-input.csv") -> Path:
    destination = tmp_path / name
    destination.write_bytes(_EXAMPLE.read_bytes())
    return destination


def test_reserved_characters_are_replaced_in_every_part() -> None:
    raw, safe = result_names(
        "bad:name.csv",
        snapshot_id="snap/1",
        rules_version="rule*1",
        run_id="run?1",
    )
    assert raw == "bad:name__targetclass_snap/1_rule*1_run?1.csv"
    assert safe == "bad_name__targetclass_snap_1_rule_1_run_1.csv"
    assert "/" not in safe
    assert "*" not in safe


def test_rerun_new_file(tmp_path: Path) -> None:
    source = _copy_example(tmp_path)
    first = run_batch(
        source, snapshot_id="snap", rules_version="plan-v1-r8", run_id="run-1"
    )
    written = tmp_path / first.normalized_name
    before = written.read_bytes()
    second = run_batch(
        source, snapshot_id="snap", rules_version="plan-v1-r8", run_id="run-2"
    )
    assert first.written is True
    assert second.written is True
    assert first.normalized_name != second.normalized_name
    assert written.read_bytes() == before
    assert (tmp_path / second.normalized_name).is_file()
    assert first.directory == str(tmp_path)


def test_name_collision_blocked(tmp_path: Path) -> None:
    source = _copy_example(tmp_path)
    first = run_batch(
        source, snapshot_id="snap", rules_version="plan-v1-r8", run_id="run-1"
    )
    written = tmp_path / first.normalized_name
    before = written.read_bytes()
    second = run_batch(
        source, snapshot_id="snap", rules_version="plan-v1-r8", run_id="run-1"
    )
    assert second.written is False
    assert second.diagnostic == "name_collision"
    assert written.read_bytes() == before


def test_local_class_is_not_copied_into_iuphar_class() -> None:
    row = output_row(
        {
            "input_row_id": "row-1",
            "old_iuphar_class": "Old receptor",
            "iuphar_class": "",
            "local_class": "Enzyme",
            "effective_class": "Enzyme",
        }
    )
    assert row["legacy_iuphar_class"] == "Old receptor"
    assert row["iuphar_class"] == ""
    assert row["effective_class"] == "Enzyme"


def test_batch_cli_writes_beside_the_example(tmp_path: Path) -> None:
    source = _copy_example(tmp_path, "in:put.csv")
    code = main(
        [
            "--source",
            str(source),
            "--snapshot",
            "snap",
            "--rules",
            "plan-v1-r8",
            "--run-id",
            "run-9",
        ]
    )
    assert code == 0
    written = list(tmp_path.glob("*__targetclass_snap_plan-v1-r8_run-9.csv"))
    assert len(written) == 1
    assert written[0].parent == source.parent
    document = contract_document()
    assert document["mapping_version"] is None
    assert document["biological_accuracy_accepted"] is False
    assert document["rules_version"] == "plan-v1-r8"
