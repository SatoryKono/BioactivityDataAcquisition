"""TC-13 delivery names, collision, and the public batch call."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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


@pytest.mark.parametrize("failure", [KeyboardInterrupt, SystemExit])
def test_manifest_interrupt_rolls_back_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[BaseException]
) -> None:
    from iuphar_target_class import delivery

    source = _copy_example(tmp_path)
    original = source.read_bytes()
    publish = delivery._create_new

    def interrupt(path: Path, payload: bytes, *, root: Path) -> bool:
        if path.name.endswith(".manifest.json"):
            raise failure()
        return publish(path, payload, root=root)

    monkeypatch.setattr(delivery, "_create_new", interrupt)
    with pytest.raises(failure):
        run_batch(source, root=tmp_path, snapshot_id="s", rules_version="v", run_id="r")
    assert list(tmp_path.iterdir()) == [source]
    assert source.read_bytes() == original
    monkeypatch.setattr(delivery, "_create_new", publish)
    assert run_batch(
        source, root=tmp_path, snapshot_id="s", rules_version="v", run_id="r"
    ).written


@pytest.mark.parametrize("contents", ["", "old_iuphar_class\nReceptor\n"])
def test_missing_identity_header_rejects_before_publication(
    tmp_path: Path, contents: str
) -> None:
    source = tmp_path / "missing.csv"
    source.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match="input_row_id"):
        run_batch(source, root=tmp_path, snapshot_id="s", rules_version="v", run_id="r")
    assert list(tmp_path.iterdir()) == [source]
    assert source.read_text(encoding="utf-8") == contents


def test_long_result_name_keeps_csv_template_and_uses_bounded_manifest(
    tmp_path: Path,
) -> None:
    source = _copy_example(tmp_path, "a" * 190 + ".csv")
    original = source.read_bytes()
    run_id = "12345678-1234-1234-1234-123456789012"
    _, expected = result_names(
        source.name, snapshot_id="s", rules_version="v", run_id=run_id
    )
    assert len(expected.encode("utf-8")) <= 255
    assert len((expected + ".manifest.json").encode("utf-8")) > 255
    result = run_batch(
        source, root=tmp_path, snapshot_id="s", rules_version="v", run_id=run_id
    )
    assert result.written
    assert result.normalized_name == expected
    assert result.manifest_name is not None
    manifest_path = tmp_path / result.manifest_name
    assert len(manifest_path.name.encode("utf-8")) <= 255
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["normalized_name"] == expected
    assert manifest["source_name"] == source.name
    assert source.read_bytes() == original
    assert not run_batch(
        source, root=tmp_path, snapshot_id="s", rules_version="v", run_id=run_id
    ).written


_EXAMPLE = (
    Path(__file__).resolve().parents[3]
    / "data/iuphar_target_class/delivery/example-input.csv"
)


def _copy_example(tmp_path: Path, name: str = "example-input.csv") -> Path:
    destination = tmp_path / name
    destination.write_bytes(_EXAMPLE.read_bytes())
    return destination


@pytest.mark.parametrize(
    "collision", ["none", "result", "manifest", "result_race", "manifest_race"]
)
def test_delivery_provenance_keeps_original_source_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, collision: str
) -> None:
    from iuphar_target_class import delivery

    source = _copy_example(tmp_path, "данные исходные.CSV")
    original = source.read_bytes()
    _, safe = result_names(
        source.name, snapshot_id="snap", rules_version="v1", run_id="provenance"
    )
    blocked = tmp_path / (f"{safe}.manifest.json" if "manifest" in collision else safe)
    if collision in {"result", "manifest"}:
        blocked.write_bytes(b"keep")
    publish = delivery._create_new

    def race(path: Path, payload: bytes, *, root: Path) -> bool:
        if collision.endswith("_race") and path == blocked:
            return False
        return publish(path, payload, root=root)

    monkeypatch.setattr(delivery, "_create_new", race)
    result = run_batch(
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="v1",
        run_id="provenance",
    )
    assert result.source_name == source.name
    assert result.normalized_name == safe
    assert result.written is (collision == "none")
    assert source.read_bytes() == original
    if collision == "none":
        assert result.manifest_name is not None
        manifest = json.loads(
            (tmp_path / result.manifest_name).read_text(encoding="utf-8")
        )
        assert manifest["source_name"] == source.name
        assert manifest["normalized_name"] == safe
    else:
        assert result.diagnostic == "name_collision"
    if collision in {"result", "manifest"}:
        assert blocked.read_bytes() == b"keep"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_input_row_ids_survive_csv_bom(tmp_path: Path, encoding: str) -> None:
    source = tmp_path / "bom.csv"
    original = (
        "input_row_id,old_iuphar_class\nстрока-1,Receptor\nrow-2,Enzyme\n".encode(
            encoding
        )
    )
    source.write_bytes(original)
    result = run_batch(
        source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id="bom"
    )
    with (tmp_path / result.normalized_name).open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["input_row_id"] for row in rows] == ["строка-1", "row-2"]
    assert [row["legacy_iuphar_class"] for row in rows] == ["Receptor", "Enzyme"]
    assert source.read_bytes() == original


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
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    written = tmp_path / first.normalized_name
    before = written.read_bytes()
    second = run_batch(
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-2",
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
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    written = tmp_path / first.normalized_name
    before = written.read_bytes()
    second = run_batch(
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
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
    source = _copy_example(tmp_path, "in put.csv")
    code = main(
        [
            "--root",
            str(tmp_path),
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


def test_path_outside_root_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_bytes(_EXAMPLE.read_bytes())
    with pytest.raises(ValueError, match="path escapes root"):
        run_batch(
            outside,
            root=root,
            snapshot_id="snap",
            rules_version="plan-v1-r8",
            run_id="run-1",
        )
    assert list(root.iterdir()) == []


def test_comma_in_a_field_stays_one_value(tmp_path: Path) -> None:
    source = tmp_path / "comma.csv"
    source.write_text(
        'input_row_id,old_iuphar_class\nrow-1,"A, B"\n',
        encoding="utf-8",
        newline="\n",
    )
    result = run_batch(
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    text = (tmp_path / result.normalized_name).read_text(encoding="utf-8")
    parsed = list(csv.DictReader(text.splitlines()))
    assert parsed[0]["legacy_iuphar_class"] == "A, B"


def test_manifest_name_keeps_the_result_extension(tmp_path: Path) -> None:
    lower_dir = tmp_path / "lower"
    upper_dir = tmp_path / "upper"
    lower_dir.mkdir()
    upper_dir.mkdir()
    lower = _copy_example(lower_dir, "a.csv")
    upper = _copy_example(upper_dir, "b.CSV")
    first = run_batch(
        lower,
        root=lower_dir,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    second = run_batch(
        upper,
        root=upper_dir,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    assert first.manifest_name is not None
    assert second.manifest_name is not None
    assert first.manifest_name.endswith(".csv.manifest.json")
    assert second.manifest_name.endswith(".CSV.manifest.json")
    assert first.manifest_name != second.manifest_name


def test_existing_manifest_blocks_without_writing_the_result(tmp_path: Path) -> None:
    source = _copy_example(tmp_path, "a.csv")
    _, safe = result_names(
        "a.csv",
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    manifest = tmp_path / f"{safe}.manifest.json"
    manifest.write_text("keep\n", encoding="utf-8", newline="\n")
    result = run_batch(
        source,
        root=tmp_path,
        snapshot_id="snap",
        rules_version="plan-v1-r8",
        run_id="run-1",
    )
    assert result.written is False
    assert result.diagnostic == "name_collision"
    assert manifest.read_text(encoding="utf-8") == "keep\n"
    assert not (tmp_path / safe).exists()


def test_module_cli_runs_in_a_separate_process(tmp_path: Path) -> None:
    source = _copy_example(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "iuphar_target_class.delivery",
            "--root",
            str(tmp_path),
            "--source",
            str(source),
            "--snapshot",
            "snap",
            "--rules",
            "plan-v1-r8",
            "--run-id",
            "cli",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / result.stdout.strip()).is_file()


def test_manifest_failure_rolls_back_csv_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from iuphar_target_class import delivery

    source = _copy_example(tmp_path)
    create = delivery._create_new

    def fail_manifest(path: Path, payload: bytes, *, root: Path) -> bool:
        if path.name.endswith(".manifest.json"):
            raise OSError("disk full")
        return create(path, payload, root=root)

    with monkeypatch.context() as context:
        context.setattr(delivery, "_create_new", fail_manifest)
        with pytest.raises(OSError, match="disk full"):
            run_batch(
                source,
                root=tmp_path,
                snapshot_id="snap",
                rules_version="v1",
                run_id="retry",
            )
    assert set(tmp_path.iterdir()) == {source}
    result = run_batch(
        source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id="retry"
    )
    assert result.written
    assert result.manifest_name is not None
    assert (tmp_path / result.manifest_name).is_file()


def test_csv_output_preserves_special_characters(tmp_path: Path) -> None:
    source = tmp_path / "quoted.csv"
    legacy = 'A, B "quoted"\nnext line'
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["input_row_id", "old_iuphar_class"])
        writer.writeheader()
        writer.writerow({"input_row_id": "row-1", "old_iuphar_class": legacy})
    result = run_batch(
        source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id="quoted"
    )
    with (tmp_path / result.normalized_name).open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["legacy_iuphar_class"] == legacy
    assert None not in rows[0]


def test_concurrent_normalized_name_collision_preserves_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from iuphar_target_class import delivery

    source = _copy_example(tmp_path)
    barrier = Barrier(2)
    serialize = delivery._csv_bytes

    def synchronized_rows(rows: tuple[dict[str, str], ...]) -> bytes:
        payload = serialize(rows)
        barrier.wait(timeout=10)
        return payload

    monkeypatch.setattr(delivery, "_csv_bytes", synchronized_rows)

    def publish(run_id: str):
        return run_batch(
            source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id=run_id
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(publish, ("run:1", "run?1")))
    assert sum(result.written for result in results) == 1
    assert sorted(result.diagnostic or "written" for result in results) == [
        "name_collision",
        "written",
    ]
    assert results[0].normalized_name == results[1].normalized_name
    assert (
        (tmp_path / results[0].normalized_name)
        .read_bytes()
        .startswith(b"input_row_id,")
    )


def _names(source_name: str, run_id: str) -> tuple[str, str]:
    _, safe = result_names(
        source_name,
        snapshot_id="snap",
        rules_version="v1",
        run_id=run_id,
    )
    return safe, f"{safe}.manifest.json"


def _dangling_entry(tmp_path: Path, name: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pretend ``name`` is a dangling symlink whose resolve() follows elsewhere."""
    target = tmp_path / "unrelated.csv"
    real_resolve = Path.resolve
    real_lstat = Path.lstat
    real_link = os.link

    def resolve(self: Path, *args: object, **kwargs: object) -> Path:
        if self.name == name:
            return target
        return real_resolve(self, *args, **kwargs)

    def lstat(self: Path) -> os.stat_result:
        if self.name == name:
            return os.stat_result((0o120777, 0, 0, 1, 0, 0, 0, 0, 0, 0))
        return real_lstat(self)

    def link(src: object, dst: object, *args: object, **kwargs: object) -> None:
        if Path(str(dst)).name == name:
            raise FileExistsError(name)
        real_link(src, dst, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(os, "link", link)
    return target


def test_dangling_result_symlink_is_a_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_example(tmp_path)
    safe, _manifest = _names(source.name, "link")
    target = _dangling_entry(tmp_path, safe, monkeypatch)
    result = run_batch(
        source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id="link"
    )
    assert result.written is False
    assert result.diagnostic == "name_collision"
    assert not target.exists()
    assert not (tmp_path / safe).exists()


def test_dangling_manifest_symlink_is_a_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_example(tmp_path)
    safe, manifest = _names(source.name, "link")
    target = _dangling_entry(tmp_path, manifest, monkeypatch)
    result = run_batch(
        source, root=tmp_path, snapshot_id="snap", rules_version="v1", run_id="link"
    )
    assert result.written is False
    assert result.diagnostic == "name_collision"
    assert not target.exists()
    assert not (tmp_path / safe).exists()
    assert not (tmp_path / manifest).exists()


def test_long_result_name_publishes_with_a_short_temp_prefix(tmp_path: Path) -> None:
    source = _copy_example(tmp_path, f"{'a' * 210}.csv")
    result = run_batch(
        source, root=tmp_path, snapshot_id="s", rules_version="v", run_id="r"
    )
    assert result.written is True
    assert result.manifest_name is not None
    assert len(result.normalized_name) == 233
    assert len(result.manifest_name) == 247
    assert (tmp_path / result.normalized_name).is_file()
    assert (tmp_path / result.manifest_name).is_file()
