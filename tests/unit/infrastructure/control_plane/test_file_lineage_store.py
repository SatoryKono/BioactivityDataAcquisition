"""Unit tests for file-backed lineage fragment storage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import bioetl.infrastructure.control_plane._file_lineage_index as lineage_index_module
import bioetl.infrastructure.control_plane.file_lineage_store as lineage_store_module
from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
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
    metrics.reset_mock()

    assert store.list_by_manifest_id("manifest-2") == [fragment]

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

    def _fail_on_second_append(path, payload) -> int:
        call_count["value"] += 1
        if call_count["value"] == 2:
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
    assert store.list_by_run_id(run_id) == []
    assert store.list_by_manifest_id("manifest-rollback") == []
    assert store.list_by_node_id(dataset_node.node_id) == []


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
