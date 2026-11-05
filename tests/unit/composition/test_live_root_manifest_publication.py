"""New-run publication records the manifest in the dashboard live root."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from bioetl.composition.control_plane_paths import (
    publish_new_run_manifest_to_live_root,
)
from bioetl.composition.runtime_builders.run_manifest_builder import (
    _publish_manifest_and_refs,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType


def _manifest() -> RunManifest:
    return RunManifest(
        manifest_id="new-manifest",
        execution_fingerprint="fp-new",
        run_id=RunID(UUID("00000000-0000-4000-8000-000000000333")),
        run_type=RunType.BACKFILL,
        pipeline_name="uniprot_protein",
    )


def test_dashboard_alias_receives_only_the_new_manifest(tmp_path: Path) -> None:
    source = tmp_path / "pack" / "output" / "control" / "run_manifest"
    source.mkdir(parents=True)
    (source / "old-tree.json").write_text("{}", encoding="utf-8")
    live_root = tmp_path / "dashboard"
    settings = SimpleNamespace(
        dashboard_data_root=live_root,
        data_dir=tmp_path / "pack",
    )

    result = publish_new_run_manifest_to_live_root(
        manifest=_manifest(),
        settings=settings,  # type: ignore[arg-type]
        source_base=source,
    )

    live = live_root / "output" / "control" / "run_manifest"
    assert result.outcome == "recorded"
    assert (live / "new-manifest.json").is_file()
    assert not (live / "old-tree.json").exists()


def test_unset_alias_keeps_the_run_data_root(tmp_path: Path) -> None:
    source = tmp_path / "data" / "output" / "control" / "run_manifest"
    source.mkdir(parents=True)
    settings = SimpleNamespace(dashboard_data_root=None, data_dir=tmp_path / "data")

    result = publish_new_run_manifest_to_live_root(
        manifest=_manifest(),
        settings=settings,  # type: ignore[arg-type]
        source_base=source,
    )

    assert result.outcome == "already_live"
    assert not (source / "new-manifest.json").exists()


def test_publication_hook_forwards_the_saved_manifest(
    monkeypatch, tmp_path: Path
) -> None:
    manifest = _manifest()
    store = SimpleNamespace(base_path=tmp_path / "run_manifest")
    seen: dict[str, object] = {}
    module = "bioetl.composition.runtime_builders.run_manifest_builder"
    monkeypatch.setattr(f"{module}.create_manifest_store", lambda _inputs: store)
    monkeypatch.setattr(f"{module}.maybe_create_ledger_service", lambda **_kwargs: None)
    monkeypatch.setattr(
        f"{module}.emit_replay_reconstructability_metric", lambda **_kwargs: None
    )
    monkeypatch.setattr(f"{module}.create_manifest_record", lambda **_kwargs: manifest)
    monkeypatch.setattr(
        f"{module}.register_pipeline_manifest_location_soft", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        f"{module}._require_cached_bronze_snapshots", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        f"{module}.create_control_plane_refs_for_manifest",
        lambda **_kwargs: "refs",
    )

    def _publish(**kwargs: object) -> str:
        seen.update(kwargs)
        return "recorded"

    monkeypatch.setattr(f"{module}.publish_new_run_manifest_to_live_root", _publish)
    context = SimpleNamespace(
        reproducibility_context=SimpleNamespace(
            strict_exact_replay_supported=False,
            required_persistence_profile="degraded_observable",
        ),
        contract_identity=None,
    )
    refs, ledger = _publish_manifest_and_refs(
        ctx=SimpleNamespace(exact_replay=False),  # type: ignore[arg-type]
        inputs=SimpleNamespace(  # type: ignore[arg-type]
            settings=SimpleNamespace(data_dir=tmp_path),
            observability=SimpleNamespace(metrics=None),
        ),
        ledger_enabled=False,
        manifest_context=context,  # type: ignore[arg-type]
        manifest_create_request=SimpleNamespace(),  # type: ignore[arg-type]
        provenance=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert refs == "refs"
    assert ledger is None
    assert seen["manifest"] is manifest
    assert seen["source_base"] == store.base_path
