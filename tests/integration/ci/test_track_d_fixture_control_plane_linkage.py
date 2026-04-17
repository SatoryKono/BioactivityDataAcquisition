"""Track D integration checks for tracked Bronze fixtures and control-plane linkage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
import zstandard as zstd

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from bioetl.composition.factories import _observability_wiring
from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.config import get_pipeline_config, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRACKED_FIXTURE_MANIFEST = (
    PROJECT_ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
)
_PIPELINE_KEY = "chembl/activity"
_PIPELINE_NAME = "chembl_activity"


def _load_tracked_fixture_entry() -> dict[str, object]:
    payload = yaml.safe_load(TRACKED_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("Fixture manifest payload must be a mapping")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, dict):
        raise AssertionError("Fixture manifest must contain a fixtures mapping")
    entry = fixtures.get(_PIPELINE_KEY)
    if not isinstance(entry, dict):
        raise AssertionError(f"Fixture manifest entry missing for {_PIPELINE_KEY}")
    return entry


def _materialize_cached_bronze_batch(
    *,
    tracked_fixture_path: Path,
    cache_root: Path,
    date: str,
) -> Path:
    date_dir = cache_root / date
    date_dir.mkdir(parents=True, exist_ok=True)
    batch_path = date_dir / f"batch_{date}_tracked_fixture.jsonl.zst"
    raw_payload = tracked_fixture_path.read_bytes()
    compressed_payload = zstd.ZstdCompressor(level=3).compress(raw_payload)
    batch_path.write_bytes(compressed_payload)
    return batch_path


def _load_control_plane_payloads(*, data_dir: Path, run_id: RunID) -> tuple[dict, dict]:
    manifest_root = data_dir / "output" / "control" / "run_manifest"
    manifest_index = manifest_root / "_by_run_id" / f"{run_id}.txt"
    assert manifest_index.exists(), f"Missing run-manifest index for run_id={run_id}"
    manifest_id = manifest_index.read_text(encoding="utf-8").strip()
    manifest_payload = json.loads(
        (manifest_root / f"{manifest_id}.json").read_text(encoding="utf-8")
    )

    code_provenance = manifest_payload.get("code_provenance")
    assert isinstance(code_provenance, dict), "Manifest code_provenance is required"
    effective_id = code_provenance.get("effective_config_artifact_id")
    assert isinstance(effective_id, str) and effective_id, (
        "Manifest must reference effective_config_artifact_id"
    )

    effective_root = data_dir / "output" / "control" / "effective_config"
    effective_index = effective_root / "_by_run_id" / f"{run_id}.txt"
    assert effective_index.exists(), (
        f"Missing effective-config index for run_id={run_id}"
    )
    assert effective_index.read_text(encoding="utf-8").strip() == effective_id
    effective_payload = json.loads(
        (effective_root / f"{effective_id}.json").read_text(encoding="utf-8")
    )
    return manifest_payload, effective_payload


async def _run_cached_fixture_pipeline(*, cached_bronze_path: Path) -> RunID:
    run_id = RunID(uuid4())
    context = PipelineRunContext(
        pipeline_name=_PIPELINE_NAME,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=5,
        exact_replay=True,
        cached_bronze=CachedBronzeContext.from_options(
            path=str(cached_bronze_path),
            date="2026-03-25",
        ),
    )
    runner = bootstrap_pipeline_runner(context)
    await runner.run()
    return run_id


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_run_persists_linked_control_plane_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracked fixture replay must produce linked manifest/effective-config artifacts."""
    fixture_entry = _load_tracked_fixture_entry()
    assert fixture_entry.get("fixture_kind") == "tracked_ci_sample"

    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw
    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    assert tracked_fixture_path.exists(), (
        f"Missing tracked fixture: {tracked_fixture_path}"
    )

    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    _materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    monkeypatch.setenv("BIOETL_TEST_RELAXED_DQ", "1")
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id_first = await _run_cached_fixture_pipeline(
        cached_bronze_path=cached_root,
    )
    run_id_second = await _run_cached_fixture_pipeline(
        cached_bronze_path=cached_root,
    )

    manifest_first, effective_first = _load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_first,
    )
    manifest_second, effective_second = _load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_second,
    )

    code_provenance_first = manifest_first["code_provenance"]
    code_provenance_second = manifest_second["code_provenance"]
    assert manifest_first["launch_context"]["exact_replay"] is True
    assert manifest_second["launch_context"]["exact_replay"] is True
    assert manifest_first["runtime_config"]["exact_replay"] is True
    assert manifest_second["runtime_config"]["exact_replay"] is True
    source_refs_first = manifest_first.get("source_refs")
    source_refs_second = manifest_second.get("source_refs")
    assert isinstance(source_refs_first, list) and source_refs_first
    assert isinstance(source_refs_second, list) and source_refs_second
    snapshots_first = source_refs_first[0].get("input_snapshots")
    snapshots_second = source_refs_second[0].get("input_snapshots")
    assert isinstance(snapshots_first, list) and snapshots_first
    assert isinstance(snapshots_second, list) and snapshots_second
    assert snapshots_first == snapshots_second
    assert isinstance(snapshots_first[0].get("snapshot_id"), str)
    assert isinstance(snapshots_first[0].get("content_hash"), str)
    assert isinstance(snapshots_first[0].get("immutable_uri"), str)
    assert code_provenance_first["contract_ref"] == "chembl.activity"
    assert code_provenance_second["contract_ref"] == "chembl.activity"
    assert isinstance(code_provenance_first.get("contract_version"), str)
    assert isinstance(code_provenance_second.get("contract_version"), str)
    assert code_provenance_first["config_hash"] == code_provenance_second["config_hash"]
    assert (
        code_provenance_first["dq_contract_compatibility_hash"]
        == code_provenance_second["dq_contract_compatibility_hash"]
    )
    assert (
        code_provenance_first["effective_config_artifact_id"]
        == code_provenance_second["effective_config_artifact_id"]
    )
    semantic_first = effective_first["semantic_artifact"]
    semantic_second = effective_second["semantic_artifact"]
    assert effective_first["artifact_id"] == effective_second["artifact_id"]
    assert (
        semantic_first["effective_config_hash"]
        == semantic_second["effective_config_hash"]
    )
    assert (
        semantic_first["dq_contract_compatibility_hash"]
        == semantic_second["dq_contract_compatibility_hash"]
    )

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_exact_replay_avoids_live_data_source_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact replay must stay offline and avoid live data source construction."""
    fixture_entry = _load_tracked_fixture_entry()
    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw

    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    batch_path = _materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    monkeypatch.setenv("BIOETL_TEST_RELAXED_DQ", "1")

    def _raise_live_data_source(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "exact replay attempted live data source construction instead of offline cached Bronze replay"
        )

    monkeypatch.setattr(
        _observability_wiring,
        "_create_data_source",
        _raise_live_data_source,
    )
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = await _run_cached_fixture_pipeline(cached_bronze_path=cached_root)
    manifest_payload, _effective_payload = _load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id,
    )
    snapshots = manifest_payload["source_refs"][0]["input_snapshots"]

    assert manifest_payload["launch_context"]["exact_replay"] is True
    assert manifest_payload["runtime_config"]["exact_replay"] is True
    assert len(snapshots) == 1
    assert snapshots[0]["immutable_uri"] == str(batch_path)

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_exact_replay_without_materialized_cached_bronze_batches_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact replay must fail closed and avoid publishing a manifest without snapshots."""
    await asyncio.sleep(0)
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    (cached_root / "2026-03-25").mkdir(parents=True, exist_ok=True)

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    monkeypatch.setenv("BIOETL_TEST_RELAXED_DQ", "1")
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = RunID(uuid4())
    context = PipelineRunContext(
        pipeline_name=_PIPELINE_NAME,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=5,
        exact_replay=True,
        cached_bronze=CachedBronzeContext.from_options(
            path=str(cached_root),
            date="2026-03-25",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Cached Bronze execution requires at least one persisted batch file "
            "for snapshot provenance"
        ),
    ):
        bootstrap_pipeline_runner(context)

    manifest_index = (
        data_dir
        / "output"
        / "control"
        / "run_manifest"
        / "_by_run_id"
        / f"{run_id}.txt"
    )
    assert not manifest_index.exists()

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()
