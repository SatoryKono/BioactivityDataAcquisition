"""Per-run boundary for composite replay; family support alone is insufficient."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import RunManifest


def _valid_binding(key: object, value: object) -> bool:
    return isinstance(key, str) and isinstance(value, str) and bool(value)


def _valid_bindings(bindings: object) -> bool:
    if not isinstance(bindings, dict) or not bindings:
        return False
    return all(_valid_binding(key, value) for key, value in bindings.items())


def _sources_match(manifest: RunManifest, bindings: dict[str, str]) -> bool:
    sources = manifest.source_refs
    if not sources or any(not source.input_snapshots for source in sources):
        return False
    return set(bindings) == {source.pipeline_name for source in sources}


def _seed_is_bound(manifest: RunManifest, bindings: dict[str, str]) -> bool:
    seed = manifest.resolved_config.get("seed")
    return isinstance(seed, dict) and seed.get("pipeline") in bindings


def _has_stage_override(manifest: RunManifest) -> bool:
    return any(
        manifest.launch_context.get(key)
        for key in (
            "resume",
            "dry_run",
            "required_only",
            "enrich_only",
            "force_enricher",
        )
    )


def has_composite_replay_bindings(manifest: RunManifest) -> bool:
    """Require completed child identities and a full envelope for every child."""
    bindings = manifest.launch_context.get("child_replay_manifests")
    if not _valid_bindings(bindings):
        return False
    assert isinstance(bindings, dict)  # Established by the binding validator.
    return all(
        (
            _sources_match(manifest, bindings),
            _seed_is_bound(manifest, bindings),
            not _has_stage_override(manifest),
            len(set(bindings.values())) == len(bindings),
        )
    )
