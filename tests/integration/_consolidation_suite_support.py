"""Reusable helpers for consolidation campaign reproducibility lanes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.config import get_pipeline_config, get_settings
from tests.helpers.control_plane_replay import (
    PROJECT_ROOT,
    load_control_plane_payloads,
    load_tracked_fixture_entry,
    materialize_cached_bronze_batch,
    patch_clean_code_revision,
    run_cached_fixture_pipeline,
)


_PIPELINE_KEY = "chembl/activity"
_PIPELINE_NAME = "chembl_activity"


def patch_quarantine_adapter_for_cached_fixture_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid quarantine-delta side effects during cached fixture replays."""

    async def _write_many_without_delta(self, records):  # noqa: ANN001
        stored = getattr(self, "_test_quarantine_records", [])
        stored.extend([self._normalize_record(record) for record in records])
        self._test_quarantine_records = stored

    monkeypatch.setattr(
        "bioetl.infrastructure.quarantine.unified.UnifiedQuarantineAdapter.write_many",
        _write_many_without_delta,
    )


async def run_tracked_fixture_replay_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    date: str = "2026-03-25",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    """Run the same tracked fixture twice and return both control-plane payloads."""
    fixture_entry = load_tracked_fixture_entry(pipeline_key=_PIPELINE_KEY)
    assert fixture_entry.get("fixture_kind") == "tracked_ci_sample"

    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw
    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    assert tracked_fixture_path.exists(), (
        f"Missing tracked fixture: {tracked_fixture_path}"
    )

    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date=date,
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    patch_clean_code_revision(monkeypatch)
    patch_quarantine_adapter_for_cached_fixture_replay(monkeypatch)
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id_first = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date=date,
    )
    run_id_second = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date=date,
    )

    manifest_first, effective_first = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_first,
    )
    manifest_second, effective_second = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_second,
    )
    return (
        manifest_first,
        manifest_second,
        effective_first,
        effective_second,
        str(run_id_first),
        str(run_id_second),
    )
