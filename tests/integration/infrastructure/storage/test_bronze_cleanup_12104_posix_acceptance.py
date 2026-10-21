"""Independent POSIX acceptance for #12104; synthetic production-written data only.

Ownership tests assert the same refusal criteria that failed before the repair.
No sidecar-derived scope is supplied as a configured owner.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.composition.factories.storage._bronze import create_bronze_writer
from bioetl.composition.factories.storage._context_resolution import (
    build_storage_creation_context,
)
from bioetl.composition.factories.storage.factory import StorageFactory
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    destructive_cleanup_supported,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator
from tests.unit.composition.factories.storage.test_storage_factory import (
    _make_config,
    _make_settings,
    _make_sink_layer,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not destructive_cleanup_supported(),
        reason="POSIX anchored destructive capability required",
    ),
]
CUTOFF = datetime(2024, 6, 1, tzinfo=UTC)
DATES = (datetime(2024, 2, 29, tzinfo=UTC), CUTOFF, datetime(2024, 6, 2, tzinfo=UTC))


def composed_writer(
    tmp_path: Path, *, flat: bool, owner: str = "chembl"
) -> BronzeWriter:
    root = tmp_path / "neutral"
    settings = _make_settings(
        test_mode=False,
        bronze_path=root,
        silver_path=tmp_path / "silver",
        gold_path=tmp_path / "gold",
        checkpoint_path=tmp_path / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(root, save_json=True, flat_structure=flat),
        silver_layer=_make_sink_layer(settings.silver_path),
        gold_layer=_make_sink_layer(settings.gold_path),
    )
    config.provider = owner
    if owner == "chembl":
        return StorageFactory.create(
            settings=settings,
            config=config,
            logger=NoOpLogger(),
            metrics=NoOpMetrics(),
            audit=NoOpAudit(),
            tracing=NoOpTracing(),
            silver_validator=NoOpValidator(),
        ).adapter.bronze
    # Exercise the actual Bronze composition subpath; unrelated Silver/Gold
    # policy resolution must not substitute for Bronze unknown-owner refusal.
    ctx = build_storage_creation_context(
        settings=settings,
        config=config,
        logger=NoOpLogger(),
        pipeline_name="unknown_activity",
    )
    return create_bronze_writer(
        writer_cls=BronzeWriter,
        base_path=ctx.bronze_path,
        config=ctx.bronze_config if owner != "absent" else None,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracing=NoOpTracing(),
        metadata_coordinator=None,
        audit=NoOpAudit(),
        flat_structure=ctx.bronze_flat,
    )


async def write_group(
    writer: BronzeWriter,
    date: datetime,
    index: int,
    *,
    provider="pubchem",
    entity="compound",
) -> list[Path]:
    relative = await writer.write_bronze(
        records=iter([b'{"synthetic":true}\n']),
        provider=provider,
        entity=entity,
        date=date,
        batch_id=BatchID(UUID(int=index)),
        run_id=RunID(UUID(int=99)),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=date,
    )
    payload = writer.base_path / relative.relative_path
    members = [payload, Path(f"{payload}.meta.json")]
    if payload.with_suffix("").exists():
        members.append(payload.with_suffix(""))
    assert all(p.is_file() for p in members)
    sidecar = json.loads(members[1].read_text())
    assert (sidecar["provider"], sidecar["entity"]) == (provider, entity)
    return members


@pytest.mark.parametrize("owner", ["chembl", "unknown_provider", "absent"])
async def test_flat_configured_owner_refuses_foreign_group(
    tmp_path: Path, owner: str
) -> None:
    assert destructive_cleanup_supported(), (
        "requires actual POSIX destructive capability"
    )
    writer = composed_writer(tmp_path, flat=True, owner=owner)
    members = await write_group(writer, DATES[0], 1)
    before = {p: p.read_bytes() for p in members}
    # Deliberately no provider/entity filters: flat's explicit-filter contract
    # is unchanged. The expected configured identity stays A or unknown.
    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    actual = await writer.cleanup_old_files(CUTOFF)
    repeat = await writer.cleanup_old_files(CUTOFF)
    observation = {
        "configured_owner": owner,
        "batch_owner": "pubchem/compound",
        "dry_run": dry,
        "apply": actual,
        "repeat": repeat,
        "members_remaining": [p.name for p in members if p.exists()],
    }
    print(json.dumps(observation, sort_keys=True))
    assert actual["files_removed"] == 0, observation
    assert all(p.exists() and p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("flat", [False, True], ids=["hierarchical", "flat"])
async def test_retention_real_writer_old_boundary_new_unknown_repeat(
    tmp_path: Path, flat: bool
) -> None:
    assert destructive_cleanup_supported()
    writer = composed_writer(tmp_path, flat=flat)
    groups = [
        await write_group(writer, date, i + 10, provider="chembl", entity="activity")
        for i, date in enumerate(DATES)
    ]
    assert all(len(group) == 3 for group in groups)
    retained = {p: p.read_bytes() for group in groups[1:] for p in group}
    unknown = groups[0][0].parent / "manual.txt"
    unknown.write_bytes(b"unknown content stays")
    orphan = (
        groups[0][0].parent
        / "batch_2024-02-29_00000000-0000-0000-0000-000000000077.jsonl.zst.meta.json"
    )
    orphan.write_bytes(b"orphan stays")
    snapshot = {p: p.read_bytes() for p in writer.base_path.rglob("*") if p.is_file()}
    preview = writer.preview_cleanup()
    assert preview["file_count"] == 11  # 3 x triplets + two unknown files
    assert all(p.read_bytes() == value for p, value in snapshot.items())
    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    assert dry["files_planned"] == 3
    assert dry["files_removed"] == 0
    assert all(p.read_bytes() == value for p, value in snapshot.items())
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 3
    assert result["bytes_freed"] == sum(len(snapshot[p]) for p in groups[0])
    assert not any(p.exists() for p in groups[0])
    assert all(p.read_bytes() == value for p, value in retained.items())
    assert unknown.read_bytes() == b"unknown content stays"
    assert orphan.read_bytes() == b"orphan stays"
    repeat = await writer.cleanup_old_files(CUTOFF)
    assert repeat["files_removed"] == 0
    assert repeat["files_planned"] == 0


@pytest.mark.parametrize("owner", ["chembl", "unknown_provider", "absent"])
async def test_pending_foreign_group_cannot_bypass_configured_owner(
    tmp_path: Path, owner: str
) -> None:
    from bioetl.infrastructure.storage.bronze.cleanup_group_journal import GroupJournal
    from bioetl.infrastructure.storage.bronze.cleanup_group_schema import GroupSpec
    from bioetl.infrastructure.storage.bronze.cleanup_support import bronze_tree_lock

    writer = composed_writer(tmp_path, flat=True, owner=owner)
    members = await write_group(writer, DATES[0], 1)
    with bronze_tree_lock(writer.base_path, exclusive=True) as lease:
        journal = GroupJournal(lease)
        journal.begin(
            GroupSpec(
                "pubchem",
                "compound",
                "2024-02-29",
                str(UUID(int=1)),
                "2024-06-01",
                True,
            )
        )
    snapshot = {p: p.read_bytes() for p in writer.base_path.rglob("*") if p.is_file()}
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 0
    assert all(p.exists() and p.read_bytes() == value for p, value in snapshot.items())
    assert all(p.exists() for p in members)


async def test_configured_owner_can_resume_own_flat_group(tmp_path: Path) -> None:
    from bioetl.infrastructure.storage.bronze.cleanup_group_journal import GroupJournal
    from bioetl.infrastructure.storage.bronze.cleanup_group_schema import GroupSpec
    from bioetl.infrastructure.storage.bronze.cleanup_support import bronze_tree_lock

    writer = composed_writer(tmp_path, flat=True)
    members = await write_group(
        writer, DATES[0], 1, provider="chembl", entity="activity"
    )
    with bronze_tree_lock(writer.base_path, exclusive=True) as lease:
        GroupJournal(lease).begin(
            GroupSpec(
                "chembl", "activity", "2024-02-29", str(UUID(int=1)), "2024-06-01", True
            )
        )
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 3
    assert not any(p.exists() for p in members)
    assert (await writer.cleanup_old_files(CUTOFF))["files_removed"] == 0


async def test_hierarchical_configured_owner_refuses_foreign_group(
    tmp_path: Path,
) -> None:
    writer = composed_writer(tmp_path, flat=False)
    members = await write_group(writer, DATES[0], 1)
    snapshot = {p: p.read_bytes() for p in members}
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 0
    assert result["files_planned"] == 0
    assert result["files_conflicted"] == 0
    assert result["directories_conflicted"] == 0
    assert all(p.exists() and p.read_bytes() == value for p, value in snapshot.items())


async def test_hierarchical_unfiltered_cleanup_drops_owned_keeps_foreign(
    tmp_path: Path,
) -> None:
    writer = composed_writer(tmp_path, flat=False)
    foreign = await write_group(writer, DATES[0], 1)
    owned = await write_group(writer, DATES[0], 2, provider="chembl", entity="activity")
    foreign_bytes = {path: path.read_bytes() for path in foreign}
    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    assert dry["files_planned"] == 3
    assert dry["files_removed"] == 0
    assert dry["files_conflicted"] == 0
    actual = await writer.cleanup_old_files(CUTOFF)
    assert actual["files_removed"] == 3
    assert actual["files_conflicted"] == 0
    assert actual["bytes_conflicted"] == 0
    assert actual["directories_conflicted"] == 0
    assert not any(path.exists() for path in owned)
    assert all(
        path.exists() and path.read_bytes() == data
        for path, data in foreign_bytes.items()
    )


async def test_hierarchical_explicit_foreign_filter_stays_fail_closed(
    tmp_path: Path,
) -> None:
    writer = composed_writer(tmp_path, flat=False)
    members = await write_group(writer, DATES[0], 3)
    before = {path: path.read_bytes() for path in members}
    result = await writer.cleanup_old_files(
        CUTOFF, provider="pubchem", entity="compound"
    )
    assert result["files_removed"] == 0
    assert result["files_conflicted"] >= 1
    assert all(
        path.exists() and path.read_bytes() == data for path, data in before.items()
    )


@pytest.mark.parametrize("flat", [False, True], ids=["hierarchical", "flat"])
async def test_bounded_preview_real_writer(
    tmp_path: Path, flat: bool, monkeypatch
) -> None:
    from bioetl.infrastructure.storage.bronze import cleanup_preview_mixin

    writer = composed_writer(tmp_path, flat=flat)
    members = await write_group(
        writer, DATES[0], 88, provider="chembl", entity="activity"
    )
    for i in range(10):
        (members[0].parent / f"unknown_{i}.txt").write_bytes(b"retain")
    snapshot = {p: p.read_bytes() for p in writer.base_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(cleanup_preview_mixin, "_PREVIEW_MAX_ENTRIES", 6)
    with pytest.raises(ValueError, match="filesystem entries"):
        writer.preview_cleanup()
    assert all(p.exists() and p.read_bytes() == value for p, value in snapshot.items())


@pytest.mark.parametrize(
    "filters",
    [{"provider": "chembl"}, {"entity": "activity"}, {"provider": ""}, {"entity": ""}],
)
async def test_flat_explicit_filters_refuse_before_traversal(
    tmp_path: Path, filters, monkeypatch
) -> None:
    from bioetl.infrastructure.storage.bronze import cleanup_preview_mixin

    writer = composed_writer(tmp_path, flat=True)
    members = await write_group(writer, DATES[0], 89)
    snapshot = {p: p.read_bytes() for p in members}

    def forbidden_traversal(*args, **kwargs):
        pytest.fail("flat explicit filter reached filesystem traversal")

    monkeypatch.setattr(cleanup_preview_mixin.os, "scandir", forbidden_traversal)
    with pytest.raises(ValueError):
        writer.preview_cleanup(**filters)
    for dry_run in (True, False):
        with pytest.raises(ValueError):
            await writer.cleanup_old_files(CUTOFF, dry_run=dry_run, **filters)
    assert all(p.read_bytes() == value for p, value in snapshot.items())
