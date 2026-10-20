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
"""Unit tests for file-backed lineage fragment storage."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import bioetl.infrastructure.control_plane._file_lineage_index as lineage_index_module
import bioetl.infrastructure.control_plane.file_lineage_store as lineage_store_module
import pytest
from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.infrastructure.storage.atomic import AtomicWriteError
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileLineageStore
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def test_file_store_round_trips_fragments_by_id_run_manifest_and_node(tmp_path) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    run_id = RunID(deterministic_uuid_value("lineage_store.round_trip"))
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_id}",
        label="chembl_activity",
    )
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=12,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-1",
        run_id=str(run_id),
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        nodes=(run_node, dataset_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=dataset_node,
                target=run_node,
                run_id=str(run_id),
                manifest_id="manifest-1",
                created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-1",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    store.save(fragment)

    loaded_by_semantic_id = store.get("silver:fragment-1")

    assert loaded_by_semantic_id is not None
    assert loaded_by_semantic_id.fragment_id == "silver:fragment-1"
    assert loaded_by_semantic_id.stored_fragment_id is not None
    assert loaded_by_semantic_id.run_id == str(run_id)
    assert loaded_by_semantic_id.manifest_id == "manifest-1"
    assert store.list_by_run_id(run_id) == [loaded_by_semantic_id]
    assert store.list_by_manifest_id("manifest-1") == [loaded_by_semantic_id]
    assert store.list_by_node_id(dataset_node.node_id) == [loaded_by_semantic_id]


def test_file_store_emits_lineage_read_metric_on_manifest_lookup(tmp_path) -> None:
    metrics = MagicMock()
    store = FileLineageStore(
        base_path=tmp_path / "lineage",
        metrics=metrics,
    )
    run_id = RunID(deterministic_uuid_value("lineage_store.metrics"))
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_id}",
        label="chembl_activity",
    )
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=13,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-2",
        run_id=str(run_id),
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-2",
        nodes=(run_node, dataset_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=dataset_node,
                target=run_node,
                run_id=str(run_id),
                manifest_id="manifest-2",
                created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-2",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    store.save(fragment)
    loaded = store.get(fragment.fragment_id)
    assert loaded is not None
    metrics.reset_mock()

    assert store.list_by_manifest_id("manifest-2") == [loaded]

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "lineage",
            "operation": "list_by_manifest_id",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_preserves_occurrence_specific_history_for_semantically_equivalent_fragments(
    tmp_path,
) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    first_run_id = RunID(deterministic_uuid_value("lineage_store.first_history"))
    second_run_id = RunID(deterministic_uuid_value("lineage_store.second_history"))

    def _build_fragment(*, run_id: RunID, manifest_id: str) -> LineageGraphFragment:
        run_node = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id=f"run:{run_id}",
            label="chembl_activity",
        )
        dataset_node = DatasetRef(
            layer="silver",
            logical_name="chembl.activity",
            version=12,
            provider="chembl",
            entity="activity",
            path="data/output/silver/chembl/activity",
            manifest_id=manifest_id,
            run_id=str(run_id),
        ).to_node_ref()
        return LineageGraphFragment(
            fragment_id="silver:fragment-semantic",
            nodes=(run_node, dataset_node),
            edges=(
                LineageEdge(
                    edge_type=LineageEdgeType.PRODUCED_BY,
                    source=dataset_node,
                    target=run_node,
                    run_id=str(run_id),
                    manifest_id=manifest_id,
                    created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                ),
            ),
            run_id=str(run_id),
            manifest_id=manifest_id,
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

    first_fragment = _build_fragment(run_id=first_run_id, manifest_id="manifest-1")
    second_fragment = _build_fragment(run_id=second_run_id, manifest_id="manifest-2")

    store.save(first_fragment)
    store.save(second_fragment)

    first_loaded = store.list_by_run_id(first_run_id)
    second_loaded = store.list_by_run_id(second_run_id)

    assert len(first_loaded) == 1
    assert len(second_loaded) == 1
    assert first_loaded[0].fragment_id == "silver:fragment-semantic"
    assert second_loaded[0].fragment_id == "silver:fragment-semantic"
    assert first_loaded[0].stored_fragment_id is not None
    assert second_loaded[0].stored_fragment_id is not None
    assert first_loaded[0].stored_fragment_id != second_loaded[0].stored_fragment_id
    assert first_loaded[0].manifest_id == "manifest-1"
    assert second_loaded[0].manifest_id == "manifest-2"
    assert store.list_by_manifest_id("manifest-1") == first_loaded
    assert store.list_by_manifest_id("manifest-2") == second_loaded
    assert (
        store.get_occurrence(first_loaded[0].stored_fragment_id or "")
        == first_loaded[0]
    )
    assert (
        store.get_occurrence(second_loaded[0].stored_fragment_id or "")
        == second_loaded[0]
    )

    with pytest.raises(
        ValueError,
        match="Semantic lineage fragment id resolves to multiple stored occurrence records",
    ):
        store.get("silver:fragment-semantic")


def test_file_store_rolls_back_fragment_and_indexes_when_index_append_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    run_id = RunID(deterministic_uuid_value("lineage_store.rollback"))
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_id}",
        label="chembl_activity",
    )
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=14,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-rollback",
        run_id=str(run_id),
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-rollback",
        nodes=(run_node, dataset_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=dataset_node,
                target=run_node,
                run_id=str(run_id),
                manifest_id="manifest-rollback",
                created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-rollback",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    original_append = lineage_store_module._append_jsonl_payload
    call_count = {"value": 0}
    fail_appends = {"enabled": True}

    def _fail_on_second_append(path, payload) -> int:
        call_count["value"] += 1
        if fail_appends["enabled"] and call_count["value"] == 2:
            raise OSError("simulated lineage index append failure")
        return original_append(path, payload)

    monkeypatch.setattr(
        lineage_store_module,
        "_append_jsonl_payload",
        _fail_on_second_append,
    )

    with pytest.raises(OSError, match="simulated lineage index append failure"):
        store.save(fragment)

    stored_fragment_id = lineage_store_module._build_stored_fragment_id(fragment)
    fragment_path = (
        store.base_path
        / "fragments"
        / (f"{lineage_store_module._stable_key_filename(stored_fragment_id)}.json")
    )
    assert not fragment_path.exists()
    semantic_index = store._semantic_fragment_index_path(fragment.fragment_id)
    semantic_text = (
        semantic_index.read_text(encoding="utf-8") if semantic_index.exists() else ""
    )
    assert semantic_text.strip() == ""
    assert store.list_by_run_id(run_id) == []
    assert store.list_by_manifest_id("manifest-rollback") == []
    assert store.list_by_node_id(dataset_node.node_id) == []

    fail_appends["enabled"] = False
    call_count["value"] = 0
    store.save(fragment)
    previous_size = semantic_index.stat().st_size
    previous_payload = fragment_path.read_text(encoding="utf-8")
    assert store.list_by_run_id(run_id)[0].created_at == fragment.created_at

    fail_appends["enabled"] = True
    call_count["value"] = 0
    replacement = replace(
        fragment,
        created_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        edges=(),
    )
    with pytest.raises(OSError, match="simulated lineage index append failure"):
        store.save(replacement)

    assert semantic_index.stat().st_size == previous_size
    assert fragment_path.read_text(encoding="utf-8") == previous_payload
    restored = store.list_by_run_id(run_id)
    assert len(restored) == 1
    assert restored[0].created_at == fragment.created_at
    assert len(restored[0].edges) == 1
    assert store.list_by_manifest_id("manifest-rollback")[0].created_at == (
        fragment.created_at
    )
    assert store.list_by_node_id(dataset_node.node_id)[0].created_at == (
        fragment.created_at
    )


def test_file_store_get_fails_closed_on_truncated_semantic_index_tail(tmp_path) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    semantic_index = store._semantic_fragment_index_path("silver:fragment-broken")
    semantic_index.parent.mkdir(parents=True, exist_ok=True)
    semantic_index.write_text('{"key":"broken"', encoding="utf-8")

    with pytest.raises(ValueError, match="truncated tail line"):
        store.get("silver:fragment-broken")


def test_file_store_fails_closed_on_truncated_index_tail(tmp_path) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    run_id = RunID(deterministic_uuid_value("lineage_store.truncated_tail"))
    index_path = store._run_index_path(str(run_id))
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        f'{{"fragment_id":"fragment-1","key":"{run_id}"}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="truncated tail line"):
        store.list_by_run_id(run_id)


def test_lineage_store_append_jsonl_payload_uses_control_plane_flush_policy(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flush_calls: list[int] = []

    monkeypatch.setattr(
        lineage_store_module,
        "flush_control_plane_file_descriptor",
        flush_calls.append,
    )

    checkpoint_offset = lineage_store_module._append_jsonl_payload(
        tmp_path / "lineage" / "index.jsonl",
        b'{"fragment_id":"fragment-1","key":"dataset-1"}\n',
    )

    assert checkpoint_offset == 0
    assert len(flush_calls) == 1


def test_lineage_index_build_stored_fragment_id_preserves_semantic_id_without_occurrence_anchors() -> (
    None
):
    fragment = LineageGraphFragment(fragment_id="semantic-only")

    assert lineage_index_module.build_stored_fragment_id(fragment) == "semantic-only"


def test_lineage_index_load_fragment_ids_handles_blank_and_duplicate_entries(
    tmp_path,
) -> None:
    index_path = tmp_path / "lineage" / "index.jsonl"
    index_path.parent.mkdir(parents=True)

    assert lineage_index_module.load_fragment_ids(index_path, key="dataset-1") == []

    index_path.write_text("   \n", encoding="utf-8")
    assert lineage_index_module.load_fragment_ids(index_path, key="dataset-1") == []

    index_path.write_text(
        '{"key":"dataset-1","fragment_id":"fragment-1"}\n'
        "\n"
        '{"key":"dataset-1","fragment_id":"fragment-1"}\n',
        encoding="utf-8",
    )

    assert lineage_index_module.load_fragment_ids(index_path, key="dataset-1") == [
        "fragment-1"
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ('{"key":"dataset-1","fragment_id":"fragment-1"}\nnot-json\n', "line 2"),
        ("[]\n", "payload must be a JSON object"),
        ('{"key":"other","fragment_id":"fragment-1"}\n', "unexpected key"),
        ('{"key":"dataset-1"}\n', "missing fragment_id"),
        ('{"key":"dataset-1","fragment_id":"   "}\n', "missing fragment_id"),
    ),
)
def test_lineage_index_load_fragment_ids_rejects_malformed_records(
    tmp_path,
    payload: str,
    message: str,
) -> None:
    index_path = tmp_path / "lineage" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(payload, encoding="utf-8")

    with pytest.raises(
        lineage_index_module.LineageIndexCorruptionError,
        match=message,
    ):
        lineage_index_module.load_fragment_ids(index_path, key="dataset-1")


class _RecordingTruncateOs:
    O_RDWR = 2

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def open(self, path: Path, flags: int) -> int:
        self.calls.append(("open", path))
        assert flags == self.O_RDWR
        return 11

    def ftruncate(self, file_descriptor: int, offset: int) -> None:
        self.calls.append(("ftruncate", (file_descriptor, offset)))

    def close(self, file_descriptor: int) -> None:
        self.calls.append(("close", file_descriptor))


def test_lineage_index_truncate_to_offset_is_noop_for_missing_path(tmp_path) -> None:
    recording_os = _RecordingTruncateOs()
    flush_calls: list[int] = []

    lineage_index_module.truncate_index_to_offset(
        tmp_path / "missing.jsonl",
        offset=7,
        os_module=recording_os,
        flush_file_descriptor=flush_calls.append,
    )

    assert recording_os.calls == []
    assert flush_calls == []


def test_lineage_index_truncate_to_offset_truncates_and_flushes_existing_path(
    tmp_path,
) -> None:
    index_path = tmp_path / "lineage" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text("existing\npayload\n", encoding="utf-8")
    recording_os = _RecordingTruncateOs()
    flush_calls: list[int] = []

    lineage_index_module.truncate_index_to_offset(
        index_path,
        offset=8,
        os_module=recording_os,
        flush_file_descriptor=flush_calls.append,
    )

    assert recording_os.calls == [
        ("open", index_path),
        ("ftruncate", (11, 8)),
        ("close", 11),
    ]
    assert flush_calls == [11]


class _FakeAppendStat:
    st_size = 5


class _ZeroWriteOs:
    def __init__(self) -> None:
        self.closed: list[int] = []

    def open(self, path: Path, flags: int, mode: int) -> int:
        return 17

    def fstat(self, file_descriptor: int) -> _FakeAppendStat:
        return _FakeAppendStat()

    def write(self, file_descriptor: int, payload: bytes) -> int:
        return 0

    def close(self, file_descriptor: int) -> None:
        self.closed.append(file_descriptor)


def test_lineage_index_append_jsonl_payload_rejects_empty_write(tmp_path) -> None:
    fake_os = _ZeroWriteOs()

    with pytest.raises(OSError, match="empty write"):
        lineage_index_module.append_jsonl_payload(
            tmp_path / "lineage" / "index.jsonl",
            b"payload\n",
            open_flags=0,
            os_module=fake_os,
            flush_file_descriptor=lambda file_descriptor: None,
        )

    assert fake_os.closed == [17]


class _PartialWriteFailingOs:
    def __init__(self) -> None:
        self.truncations: list[tuple[int, int]] = []
        self.closed: list[int] = []
        self.write_calls = 0

    def open(self, path: Path, flags: int, mode: int) -> int:
        return 19

    def fstat(self, file_descriptor: int) -> _FakeAppendStat:
        return _FakeAppendStat()

    def write(self, file_descriptor: int, payload: bytes) -> int:
        self.write_calls += 1
        if self.write_calls == 1:
            return 2
        raise OSError("simulated write failure")

    def ftruncate(self, file_descriptor: int, offset: int) -> None:
        self.truncations.append((file_descriptor, offset))

    def close(self, file_descriptor: int) -> None:
        self.closed.append(file_descriptor)


def test_lineage_index_append_jsonl_payload_rolls_back_partial_write(
    tmp_path,
) -> None:
    fake_os = _PartialWriteFailingOs()
    flush_calls: list[int] = []

    with pytest.raises(OSError, match="simulated write failure"):
        lineage_index_module.append_jsonl_payload(
            tmp_path / "lineage" / "index.jsonl",
            b"payload\n",
            open_flags=0,
            os_module=fake_os,
            flush_file_descriptor=flush_calls.append,
        )

    assert fake_os.truncations == [(19, 5)]
    assert fake_os.closed == [19]
    assert flush_calls == [19]


def test_lineage_index_append_jsonl_payload_rolls_back_partial_write_and_fails(
    tmp_path,
) -> None:
    class _PartialWriteAndRollbackFailingOs:
        def __init__(self) -> None:
            self.closed: list[int] = []
            self.write_calls = 0

        def open(self, path: Path, flags: int, mode: int) -> int:
            return 19

        def fstat(self, file_descriptor: int) -> _FakeAppendStat:
            return _FakeAppendStat()

        def write(self, file_descriptor: int, payload: bytes) -> int:
            self.write_calls += 1
            if self.write_calls == 1:
                return 2
            raise OSError("simulated write failure")

        def ftruncate(self, file_descriptor: int, offset: int) -> None:
            raise OSError("simulated ftruncate failure")

        def close(self, file_descriptor: int) -> None:
            self.closed.append(file_descriptor)

    fake_os = _PartialWriteAndRollbackFailingOs()
    flush_calls: list[int] = []

    with pytest.raises(OSError, match="simulated write failure") as exc_info:
        lineage_index_module.append_jsonl_payload(
            tmp_path / "lineage" / "index.jsonl",
            b"payload\n",
            open_flags=0,
            os_module=fake_os,
            flush_file_descriptor=flush_calls.append,
        )

    assert any(
        "simulated ftruncate failure" in note for note in exc_info.value.__notes__
    )
    assert fake_os.closed == [19]
    assert flush_calls == []


def _dataset_fragment(
    *,
    fragment_id: str,
    node_id: str,
    run_id: str,
    manifest_id: str,
    label: str,
) -> LineageGraphFragment:
    return LineageGraphFragment(
        fragment_id=fragment_id,
        nodes=(
            LineageNodeRef(
                node_type=LineageNodeType.DATASET,
                node_id=node_id,
                label=label,
                attributes={},
            ),
        ),
        edges=(),
        run_id=run_id,
        manifest_id=manifest_id,
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


def _index_records(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_file_lineage_store_concurrent_save(tmp_path) -> None:
    store1 = FileLineageStore(base_path=tmp_path / "lineage")
    store2 = FileLineageStore(base_path=tmp_path / "lineage")
    shared_node_id = "silver:shared-node"

    from concurrent.futures import ThreadPoolExecutor

    def save_fragment(store: FileLineageStore, prefix: str) -> None:
        store.save(
            _dataset_fragment(
                fragment_id=f"silver:{prefix}-fragment-1",
                node_id=shared_node_id,
                run_id=f"run-{prefix}",
                manifest_id=f"manifest-{prefix}",
                label=f"dataset-{prefix}",
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(save_fragment, store1, "a")
        f2 = executor.submit(save_fragment, store2, "b")
        f1.result()
        f2.result()

    assert {item.fragment_id for item in store1.list_by_run_id("run-a")} == {
        "silver:a-fragment-1"
    }
    assert {item.fragment_id for item in store2.list_by_run_id("run-b")} == {
        "silver:b-fragment-1"
    }
    shared = store1.list_by_node_id(shared_node_id)
    assert {item.fragment_id for item in shared} == {
        "silver:a-fragment-1",
        "silver:b-fragment-1",
    }
    records = _index_records(store1._node_index_path(shared_node_id))
    assert len(records) == 2
    assert all(record["key"] == shared_node_id for record in records)


def test_file_lineage_store_concurrent_save_and_fail(tmp_path, monkeypatch) -> None:
    store1 = FileLineageStore(base_path=tmp_path / "lineage")
    store2 = FileLineageStore(base_path=tmp_path / "lineage")
    shared_node_id = "silver:shared-node-1"

    from concurrent.futures import ThreadPoolExecutor
    import threading

    barrier = threading.Barrier(2)
    fragment = _dataset_fragment(
        fragment_id="silver:shared-fragment-1",
        node_id=shared_node_id,
        run_id="run-shared",
        manifest_id="manifest-shared",
        label="dataset-shared",
    )

    def save_fragment_1(store: FileLineageStore) -> None:
        barrier.wait()
        store.save(fragment)

    def save_fragment_2(store: FileLineageStore) -> None:
        original_append = lineage_store_module._append_jsonl_payload
        call_count = {"value": 0}
        failing_thread = threading.current_thread()

        def _fail_on_second_append(path: Path, payload: bytes) -> int:
            if threading.current_thread() is not failing_thread:
                return original_append(path, payload)
            call_count["value"] += 1
            if call_count["value"] == 2:
                raise OSError("simulated lineage index append failure")
            return original_append(path, payload)

        monkeypatch.setattr(
            lineage_store_module,
            "_append_jsonl_payload",
            _fail_on_second_append,
        )
        barrier.wait()
        with pytest.raises(OSError, match="simulated lineage index append failure"):
            store.save(fragment)

    with ThreadPoolExecutor(max_workers=2) as executor:
        failed = executor.submit(save_fragment_2, store2)
        succeeded = executor.submit(save_fragment_1, store1)
        succeeded.result()
        failed.result()

    assert len(store1.list_by_run_id("run-shared")) == 1
    assert len(store1.list_by_node_id(shared_node_id)) == 1
    assert len(_index_records(store1._node_index_path(shared_node_id))) == 1


def test_exclusive_lock_closes_descriptor_when_acquire_fails(
    tmp_path, monkeypatch
) -> None:
    import fcntl

    closed: list[int] = []
    real_close = os.close

    def _close(file_descriptor: int) -> None:
        closed.append(file_descriptor)
        real_close(file_descriptor)

    monkeypatch.setattr(os, "close", _close)

    def _fail_lock(*_args: object, **_kwargs: object) -> None:
        raise OSError("ENOLCK")

    monkeypatch.setattr(fcntl, "flock", _fail_lock)
    with pytest.raises(OSError, match="ENOLCK"):
        with lineage_store_module._exclusive_base_lock(tmp_path / "_save.lock"):
            pass
    assert closed


def test_windows_byte_lock_initializes_empty_lock_file(tmp_path) -> None:
    lock_path = tmp_path / "_save.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    calls: list[tuple[int, int, int, int]] = []

    def locking(file_descriptor: int, mode: int, nbytes: int) -> None:
        calls.append(
            (file_descriptor, mode, nbytes, os.lseek(file_descriptor, 0, os.SEEK_CUR))
        )

    try:
        lineage_store_module._lock_byte_range(lock_fd, locking=locking, mode=7)
    finally:
        os.close(lock_fd)

    assert lock_path.stat().st_size == 1
    assert calls == [(calls[0][0], 7, 1, 0)]


def test_rollback_save_collects_atomic_write_error(tmp_path, monkeypatch) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    fragment_path = tmp_path / "fragment.json"
    fragment_path.write_text("{}", encoding="utf-8")

    def _fail_restore(_path: Path, _payload: str) -> None:
        raise AtomicWriteError(fragment_path, "restore failed")

    monkeypatch.setattr(lineage_store_module, "atomic_write_text", _fail_restore)
    errors = store._rollback_save(
        fragment_path=fragment_path,
        existing_fragment_payload='{"kept": true}',
        index_rollbacks=[],
    )
    assert len(errors) == 1
    assert isinstance(errors[0], AtomicWriteError)
