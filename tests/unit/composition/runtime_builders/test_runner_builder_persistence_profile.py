"""Persistence-profile specific runner-builder tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.unit.composition.runtime_builders.test_runner_builder import (
    _build_context,
    _build_factory_registry,
    _build_pipeline_config,
    _build_settings,
    _call_build_pipeline_runner,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_build_pipeline_runner_rejects_replay_ready_bounded_live_capture(
    tmp_path: Path,
) -> None:
    """Replay-ready live captures must fail closed without launch snapshots."""
    fake_factory, fake_registry = _build_factory_registry()

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
            RuntimeError,
            match="require immutable input snapshots",
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=False),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
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
                enabled=False
            ),
        )

    assert fake_factory.kwargs is None


@pytest.mark.unit
def test_build_pipeline_runner_rejects_missing_provenance_even_with_degraded_override(
    tmp_path: Path,
) -> None:
    """Executable manifests must keep full provenance even under degraded profiles."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit=None,
                source_revision_state="git_unavailable",
                dependency_lock_hash=None,
            ),
        ),
        pytest.raises(RuntimeError, match="requires git_commit code provenance"),
    ):
        _call_build_pipeline_runner(
            _build_context(
                limit=25,
                exact_replay=False,
                required_persistence_profile="degraded_observable",
            ),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
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


@pytest.mark.unit
def test_build_pipeline_runner_preserves_explicit_degraded_opt_down_with_dirty_source(
    tmp_path: Path,
) -> None:
    """Local diagnostic opt-downs must not claim replay-ready on dirty source."""
    fake_factory, fake_registry = _build_factory_registry()

    with patch(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="deadbeef" * 5,
            source_revision_state="dirty",
            dependency_lock_hash="sha256:test-lock",
        ),
    ):
        result = _call_build_pipeline_runner(
            _build_context(
                limit=25,
                exact_replay=False,
                required_persistence_profile="degraded_observable",
            ),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert result == "runner-instance"
    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["code_provenance"]["source_revision_state"] == "dirty"
    assert payload["launch_context"]["configured_required_persistence_profile"] == (
        "degraded_observable"
    )
    assert payload["launch_context"]["required_persistence_profile"] == (
        "degraded_observable"
    )
    assert payload["launch_context"]["required_persistence_profile_opt_down"] is True


@pytest.mark.unit
def test_build_pipeline_runner_keeps_exact_replay_strict_with_degraded_override(
    tmp_path: Path,
) -> None:
    """Exact replay must promote a degraded override back to strict provenance."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit=None,
                source_revision_state="git_unavailable",
                dependency_lock_hash=None,
            ),
        ),
        pytest.raises(RuntimeError, match="requires git_commit code provenance"),
    ):
        _call_build_pipeline_runner(
            _build_context(
                limit=25,
                exact_replay=True,
                required_persistence_profile="degraded_observable",
            ),
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

    assert fake_factory.kwargs is None


@pytest.mark.unit
def test_build_pipeline_runner_blocks_prod_degraded_override_without_snapshots(
    tmp_path: Path,
) -> None:
    """Production launches must promote degraded overrides and fail closed if replay-ready gaps remain."""
    fake_factory, fake_registry = _build_factory_registry()
    settings = _build_settings(
        data_dir=str(tmp_path),
        control_plane=SimpleNamespace(
            run_manifest_enabled=True,
            run_ledger_enabled=True,
            required_persistence_profile="degraded_observable",
        ),
    )
    settings.env = "prod"

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
            RuntimeError,
            match="required persistence profile 'replay_ready'",
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(
                limit=25,
                exact_replay=False,
                required_persistence_profile="degraded_observable",
            ),
            registry=fake_registry,
            settings=settings,
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=False
            ),
        )
    assert fake_factory.kwargs is None
