"""Shared replay/control-plane helpers for tracked fixture tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
import zstandard as zstd

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from bioetl.composition.services.versioning import CodeRevisionProvenance
from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
from bioetl.domain.types import RunID, RunType

__all__ = [
    "PROJECT_ROOT",
    "TRACKED_FIXTURE_MANIFEST",
    "build_cached_fixture_run_context",
    "build_tracked_fixture_exact_replay_matrix_payload",
    "load_control_plane_bundle",
    "load_control_plane_payloads",
    "load_tracked_fixture_entry",
    "materialize_cached_bronze_batch",
    "patch_clean_code_revision",
    "run_cached_fixture_pipeline",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACKED_FIXTURE_MANIFEST = (
    PROJECT_ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
)


def load_tracked_fixture_entry(*, pipeline_key: str) -> dict[str, object]:
    payload = yaml.safe_load(TRACKED_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("Fixture manifest payload must be a mapping")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, dict):
        raise AssertionError("Fixture manifest must contain a fixtures mapping")
    entry = fixtures.get(pipeline_key)
    if not isinstance(entry, dict):
        raise AssertionError(f"Fixture manifest entry missing for {pipeline_key}")
    return entry


def materialize_cached_bronze_batch(
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


def load_control_plane_payloads(
    *,
    data_dir: Path,
    run_id: RunID,
) -> tuple[dict[str, object], dict[str, object]]:
    manifest_root = data_dir / "output" / "control" / "run_manifest"
    manifest_index = manifest_root / "_by_run_id" / f"{run_id}.txt"
    if not manifest_index.exists():
        raise AssertionError(f"Missing run-manifest index for run_id={run_id}")
    manifest_id = manifest_index.read_text(encoding="utf-8").strip()
    manifest_payload = json.loads(
        (manifest_root / f"{manifest_id}.json").read_text(encoding="utf-8")
    )

    code_provenance = manifest_payload.get("code_provenance")
    if not isinstance(code_provenance, dict):
        raise AssertionError("Manifest code_provenance is required")
    effective_id = code_provenance.get("effective_config_artifact_id")
    if not isinstance(effective_id, str) or not effective_id:
        raise AssertionError("Manifest must reference effective_config_artifact_id")

    effective_root = data_dir / "output" / "control" / "effective_config"
    effective_index = effective_root / "_by_run_id" / f"{run_id}.txt"
    if not effective_index.exists():
        raise AssertionError(f"Missing effective-config index for run_id={run_id}")
    if effective_index.read_text(encoding="utf-8").strip() != effective_id:
        raise AssertionError(
            "Effective-config index must resolve to the manifest-linked artifact id"
        )
    effective_payload = json.loads(
        (effective_root / f"{effective_id}.json").read_text(encoding="utf-8")
    )
    return manifest_payload, effective_payload


def _load_effective_occurrence(
    *,
    data_dir: Path,
    run_id: RunID,
    effective_artifact_id: str,
) -> dict[str, object]:
    effective_root = data_dir / "output" / "control" / "effective_config"
    occurrence_path = effective_root / "_occurrences" / f"{run_id}.json"
    if not occurrence_path.exists():
        raise AssertionError(f"Missing effective-config occurrence for run_id={run_id}")
    effective_occurrence = json.loads(occurrence_path.read_text(encoding="utf-8"))
    if not isinstance(effective_occurrence, dict):
        raise AssertionError("Effective-config occurrence payload must be a mapping")
    if effective_occurrence.get("artifact_id") != effective_artifact_id:
        raise AssertionError(
            "Effective-config occurrence must resolve to the manifest-linked artifact"
        )
    if effective_occurrence.get("run_id") != str(run_id):
        raise AssertionError(
            "Effective-config occurrence must preserve the persisted run identifier"
        )
    return effective_occurrence


def _load_ledger_entries(
    *,
    data_dir: Path,
    run_id: RunID,
    manifest_id: str,
) -> list[dict[str, object]]:
    ledger_root = data_dir / "output" / "control" / "run_ledger"
    ledger_index = ledger_root / "_by_run_id" / f"{run_id}.txt"
    if not ledger_index.exists():
        raise AssertionError(f"Missing run-ledger index for run_id={run_id}")
    if ledger_index.read_text(encoding="utf-8").strip() != manifest_id:
        raise AssertionError(
            "Run-ledger index must resolve to the persisted manifest identifier"
        )
    ledger_path = ledger_root / f"{manifest_id}.jsonl"
    if not ledger_path.exists():
        raise AssertionError(
            f"Missing run-ledger payload for manifest_id={manifest_id}"
        )
    return _load_jsonl_mapping_entries(
        ledger_path,
        message="Run-ledger payload entries must be mappings",
    )


def _load_lineage_fragments(
    *, data_dir: Path, run_id: RunID
) -> list[dict[str, object]]:
    lineage_root = data_dir / "output" / "control" / "lineage"
    lineage_index = (
        lineage_root
        / "_by_run_id"
        / f"{hashlib.sha256(str(run_id).encode('utf-8')).hexdigest()}.jsonl"
    )
    if not lineage_index.exists():
        return []

    fragments_dir = lineage_root / "fragments"
    lineage_fragments: list[dict[str, object]] = []
    for index_payload in _load_jsonl_mapping_entries(
        lineage_index,
        message="Lineage index payload must be a mapping",
    ):
        fragment_id = index_payload.get("fragment_id")
        if not isinstance(fragment_id, str) or not fragment_id:
            raise AssertionError("Lineage index entry must contain fragment_id")
        fragment_path = fragments_dir / f"{fragment_id}.json"
        if not fragment_path.exists():
            continue
        fragment_payload = json.loads(fragment_path.read_text(encoding="utf-8"))
        if not isinstance(fragment_payload, dict):
            raise AssertionError("Lineage fragment payload must be a mapping")
        lineage_fragments.append(fragment_payload)
    return lineage_fragments


def _load_jsonl_mapping_entries(
    path: Path,
    *,
    message: str,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise AssertionError(message)
        entries.append(payload)
    return entries


def load_control_plane_bundle(
    *,
    data_dir: Path,
    run_id: RunID,
) -> dict[str, object]:
    """Load persisted control-plane artifacts that should agree for one run."""
    manifest_payload, effective_payload = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id,
    )
    manifest_id = _required_string(
        manifest_payload,
        "manifest_id",
        "Manifest payload must contain manifest_id",
    )
    code_provenance = _required_mapping(
        manifest_payload,
        "code_provenance",
        "Manifest code_provenance is required",
    )
    effective_artifact_id = _required_string(
        code_provenance,
        "effective_config_artifact_id",
        "Manifest must reference effective_config_artifact_id",
    )
    effective_occurrence = _load_effective_occurrence(
        data_dir=data_dir,
        run_id=run_id,
        effective_artifact_id=effective_artifact_id,
    )
    ledger_entries = _load_ledger_entries(
        data_dir=data_dir,
        run_id=run_id,
        manifest_id=manifest_id,
    )
    lineage_fragments = _load_lineage_fragments(
        data_dir=data_dir,
        run_id=run_id,
    )

    return {
        "manifest_payload": manifest_payload,
        "effective_payload": effective_payload,
        "effective_occurrence": effective_occurrence,
        "ledger_entries": ledger_entries,
        "lineage_fragments": lineage_fragments,
    }


def patch_clean_code_revision(
    monkeypatch: pytest.MonkeyPatch,
    *,
    git_commit: str = "test-clean-replay",
) -> None:
    """Keep replay evidence tests independent from the local dirty worktree."""
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        lambda: CodeRevisionProvenance(
            git_commit=git_commit,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock-clean-replay",
        ),
        raising=True,
    )


def build_cached_fixture_run_context(
    *,
    pipeline_name: str,
    cached_bronze_path: Path,
    date: str,
    run_id: RunID | None = None,
    limit: int = 5,
) -> PipelineRunContext:
    return PipelineRunContext(
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()) if run_id is None else run_id,
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=limit,
        exact_replay=True,
        cached_bronze=CachedBronzeContext.from_options(
            path=str(cached_bronze_path),
            date=date,
        ),
    )


async def run_cached_fixture_pipeline(
    *,
    pipeline_name: str,
    cached_bronze_path: Path,
    date: str,
    limit: int = 5,
) -> RunID:
    context = build_cached_fixture_run_context(
        pipeline_name=pipeline_name,
        cached_bronze_path=cached_bronze_path,
        date=date,
        limit=limit,
    )
    runner = bootstrap_pipeline_runner(context)
    await runner.run()
    return context.run_id


def _required_mapping(
    payload: dict[str, object],
    key: str,
    message: str,
) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise AssertionError(message)
    return value


def _required_string(
    payload: dict[str, object],
    key: str,
    message: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AssertionError(message)
    return value


def _input_snapshot_ids(manifest_payload: dict[str, object]) -> list[str]:
    source_refs = manifest_payload.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        raise AssertionError("Manifest must contain at least one source_ref")
    first_source_ref = source_refs[0]
    if not isinstance(first_source_ref, dict):
        raise AssertionError("Manifest source_ref payload must be a mapping")
    snapshots = first_source_ref.get("input_snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise AssertionError("Manifest source_ref must contain input snapshots")

    snapshot_ids: list[str] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            raise AssertionError("Input snapshot payload must be a mapping")
        snapshot_ids.append(
            _required_string(
                snapshot,
                "snapshot_id",
                "Input snapshot must contain snapshot_id",
            )
        )
    return snapshot_ids


def build_tracked_fixture_exact_replay_matrix_payload(
    *,
    pipeline_name: str,
    manifest_payload: dict[str, object],
    effective_payload: dict[str, object],
    occurrences: list[dict[str, str]],
    case_name: str = "ordinary_supported_family_cached_bronze_exact_replay",
) -> dict[str, object]:
    code_provenance = _required_mapping(
        manifest_payload,
        "code_provenance",
        "Manifest code_provenance payload must be a mapping",
    )
    semantic_artifact = _required_mapping(
        effective_payload,
        "semantic_artifact",
        "Effective-config payload must contain semantic_artifact",
    )

    return {
        "pipeline_name": pipeline_name,
        "case": case_name,
        "replay_capability": _required_string(
            manifest_payload,
            "replay_capability",
            "Manifest replay_capability must be a string",
        ),
        "semantic_identity": {
            "execution_fingerprint": _required_string(
                manifest_payload,
                "execution_fingerprint",
                "Manifest execution_fingerprint must be a string",
            ),
            "effective_config_artifact_id": _required_string(
                code_provenance,
                "effective_config_artifact_id",
                "Manifest code_provenance must contain effective_config_artifact_id",
            ),
            "effective_config_hash": _required_string(
                semantic_artifact,
                "effective_config_hash",
                "Effective-config semantic_artifact must contain effective_config_hash",
            ),
            "dq_contract_compatibility_hash": _required_string(
                semantic_artifact,
                "dq_contract_compatibility_hash",
                "Effective-config semantic_artifact must contain dq_contract_compatibility_hash",
            ),
            "snapshot_ids": _input_snapshot_ids(manifest_payload),
        },
        "occurrences": occurrences,
    }
