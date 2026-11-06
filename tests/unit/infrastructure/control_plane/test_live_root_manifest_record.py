"""Live-root recording keeps existing manifests and skips historical trees."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.live_run_manifest_catalog import (
    LiveRootRecordResult,
    record_manifest_in_live_catalog,
    snapshot_manifest_catalog,
)

_RUN_ID = RunID(UUID("00000000-0000-4000-8000-000000000111"))
_OTHER_RUN_ID = RunID(UUID("00000000-0000-4000-8000-000000000222"))


def _manifest(
    *,
    manifest_id: str,
    run_id: RunID = _RUN_ID,
    predecessor_manifest_id: str | None = None,
    pipeline_name: str = "uniprot_protein",
) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        predecessor_manifest_id=predecessor_manifest_id,
        execution_fingerprint=f"fp-{manifest_id}",
        run_id=run_id,
        run_type=RunType.BACKFILL,
        pipeline_name=pipeline_name,
        provider="uniprot",
        entity="protein",
    )


def _save(base: Path, manifest: RunManifest) -> None:
    FileRunManifestStore(base_path=base).save(manifest)


def test_same_root_does_not_write_a_second_copy(tmp_path: Path) -> None:
    live = tmp_path / "output" / "control" / "run_manifest"
    seed = _manifest(manifest_id="seed-manifest", run_id=_OTHER_RUN_ID)
    _save(live, seed)
    before = (live / "seed-manifest.json").read_bytes()

    result = record_manifest_in_live_catalog(
        manifest=_manifest(manifest_id="new-manifest"),
        live_base=live,
        source_base=live,
    )

    assert result.outcome == "already_live"
    assert result.catalog_snapshot == ("seed-manifest",)
    assert not (live / "new-manifest.json").exists()
    assert (live / "seed-manifest.json").read_bytes() == before


def test_new_run_is_recorded_and_historical_tree_stays_put(tmp_path: Path) -> None:
    live = tmp_path / "data" / "output" / "control" / "run_manifest"
    source = (
        tmp_path
        / "data"
        / "workflow-old"
        / "pack"
        / "output"
        / "control"
        / "run_manifest"
    )
    source.mkdir(parents=True)
    historical = source / "historical-only.json"
    historical.write_text('{"historical": true}', encoding="utf-8")
    _save(
        source,
        _manifest(
            manifest_id="predecessor-manifest",
            pipeline_name="uniprot_protein",
        ),
    )
    bronze = (
        tmp_path / "data" / "workflow-old" / "pack" / "output" / "bronze" / "row.json"
    )
    bronze.parent.mkdir(parents=True)
    bronze.write_text("bronze", encoding="utf-8")
    seed = _manifest(
        manifest_id="seed-manifest",
        run_id=_OTHER_RUN_ID,
        pipeline_name="chembl_assay",
    )
    _save(live, seed)
    seed_bytes = (live / "seed-manifest.json").read_bytes()
    manifest = _manifest(
        manifest_id="new-manifest",
        predecessor_manifest_id="predecessor-manifest",
    )
    _save(source, manifest)
    sidecar = source / "new-manifest.contract-evidence.json"
    sidecar.write_text('{"manifest_id": "new-manifest"}\n', encoding="utf-8")

    result = record_manifest_in_live_catalog(
        manifest=manifest,
        live_base=live,
        source_base=source,
    )

    assert result.outcome == "recorded"
    assert result.catalog_snapshot == ("seed-manifest",)
    assert snapshot_manifest_catalog(live) == ("new-manifest", "seed-manifest")
    assert (live / "seed-manifest.json").read_bytes() == seed_bytes
    assert (live / "_by_run_id" / f"{_RUN_ID}.txt").read_text(encoding="utf-8") == (
        "new-manifest"
    )
    assert (live / "new-manifest.contract-evidence.json").read_text(
        encoding="utf-8"
    ) == '{"manifest_id": "new-manifest"}\n'
    assert not (live / "predecessor-manifest.json").exists()
    assert not (live / "historical-only.json").exists()
    assert not (tmp_path / "data" / "output" / "bronze").exists()
    assert historical.read_text(encoding="utf-8") == '{"historical": true}'


def test_existing_live_manifest_for_the_run_is_not_replaced(tmp_path: Path) -> None:
    live = tmp_path / "run_manifest"
    recorded = _manifest(manifest_id="recorded-manifest")
    _save(live, recorded)
    before = (live / "recorded-manifest.json").read_bytes()
    index_before = (live / "_by_run_id" / f"{_RUN_ID}.txt").read_text(encoding="utf-8")

    result = record_manifest_in_live_catalog(
        manifest=_manifest(manifest_id="replacement-manifest"),
        live_base=live,
        source_base=tmp_path / "other",
    )

    assert result.outcome == "kept_existing"
    assert result.catalog_snapshot == ("recorded-manifest",)
    assert (live / "recorded-manifest.json").read_bytes() == before
    assert (live / "_by_run_id" / f"{_RUN_ID}.txt").read_text(encoding="utf-8") == (
        index_before
    )
    assert not (live / "replacement-manifest.json").exists()


def test_verified_successor_advances_the_index_and_keeps_the_file(
    tmp_path: Path,
) -> None:
    live = tmp_path / "run_manifest"
    initial = _manifest(manifest_id="initial-manifest")
    _save(live, initial)
    successor = _manifest(
        manifest_id="successor-manifest",
        predecessor_manifest_id="initial-manifest",
    )

    result = record_manifest_in_live_catalog(
        manifest=successor,
        live_base=live,
        source_base=tmp_path / "source",
    )

    assert result.outcome == "recorded"
    assert (live / "initial-manifest.json").is_file()
    assert (live / "successor-manifest.json").is_file()
    assert (live / "_by_run_id" / f"{_RUN_ID}.txt").read_text(encoding="utf-8") == (
        "successor-manifest"
    )
    unrelated = _manifest(
        manifest_id="other-manifest",
        predecessor_manifest_id="missing-manifest",
    )
    kept = record_manifest_in_live_catalog(
        manifest=unrelated,
        live_base=live,
        source_base=tmp_path / "source",
    )
    assert kept.outcome == "kept_existing"
    assert not (live / "other-manifest.json").exists()
    assert (live / "_by_run_id" / f"{_RUN_ID}.txt").read_text(encoding="utf-8") == (
        "successor-manifest"
    )


def test_different_bytes_for_the_same_manifest_id_are_kept(tmp_path: Path) -> None:
    live = tmp_path / "run_manifest"
    live.mkdir()
    target = live / "new-manifest.json"
    target.write_text('{"manifest_id": "hand-edited"}', encoding="utf-8")

    result = record_manifest_in_live_catalog(
        manifest=_manifest(manifest_id="new-manifest"),
        live_base=live,
        source_base=tmp_path / "other",
    )

    assert result.outcome == "kept_existing"
    assert target.read_text(encoding="utf-8") == '{"manifest_id": "hand-edited"}'


def _recorded_pair(tmp_path: Path) -> tuple[Path, Path, RunManifest, bytes]:
    live = tmp_path / "run_manifest"
    source = tmp_path / "source"
    manifest = _manifest(manifest_id="new-manifest")
    _save(live, manifest)
    _save(source, manifest)
    return live, source, manifest, (live / "new-manifest.json").read_bytes()


def _record_pair(
    live: Path, source: Path, manifest: RunManifest
) -> LiveRootRecordResult:
    return record_manifest_in_live_catalog(
        manifest=manifest,
        live_base=live,
        source_base=source,
    )


def test_identical_live_record_is_not_rewritten(tmp_path: Path) -> None:
    live, source, manifest, before = _recorded_pair(tmp_path)

    result = _record_pair(live, source, manifest)

    assert result.outcome == "already_recorded"
    assert (live / "new-manifest.json").read_bytes() == before


def test_already_recorded_manifest_receives_a_later_sidecar(tmp_path: Path) -> None:
    live, source, manifest, before = _recorded_pair(tmp_path)
    sidecar = source / "new-manifest.contract-evidence.json"
    sidecar.write_text('{"manifest_id": "new-manifest"}\n', encoding="utf-8")

    result = _record_pair(live, source, manifest)

    assert result.outcome == "already_recorded"
    assert (live / "new-manifest.json").read_bytes() == before
    assert (live / sidecar.name).read_text(encoding="utf-8") == sidecar.read_text(
        encoding="utf-8"
    )
    (live / sidecar.name).write_text("kept\n", encoding="utf-8")
    sidecar.write_text('{"manifest_id": "replaced"}\n', encoding="utf-8")
    _record_pair(live, source, manifest)
    assert (live / sidecar.name).read_text(encoding="utf-8") == "kept\n"
