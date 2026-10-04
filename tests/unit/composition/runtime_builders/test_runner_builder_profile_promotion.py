"""Exact replay profile promotion preserves required producer evidence."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.unit.composition.runtime_builders.runner_builder_test_support import (
    _build_context,
    _build_factory_registry,
    _build_pipeline_config,
    _build_settings,
    _call_build_pipeline_runner,
)

pytestmark = pytest.mark.unit


def test_build_pipeline_runner_promotes_supported_exact_replay_to_family_default_profile(
    tmp_path: Path,
) -> None:
    """Supported exact-replay launches inherit the published replay-ready default."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with patch(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="deadbeef" * 5,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock",
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["launch_context"]["required_persistence_profile"] == "replay_ready"
    assert payload["launch_context"]["replay_readiness_verdict"] == (
        "exact_replay_ready"
    )
    assert payload["launch_context"]["strict_exact_replay_supported"] is True
    assert payload["launch_context"]["replay_family_contract"] == (
        "snapshot_backed_exact_replay"
    )


def test_build_pipeline_runner_promoted_replay_ready_requires_ledger(
    tmp_path: Path,
) -> None:
    """Exact replay auto-promotion must re-check ledger after profile resolution."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="deadbeef" * 5,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        ),
        pytest.raises(
            RuntimeError, match="required persistence profile 'replay_ready'"
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
