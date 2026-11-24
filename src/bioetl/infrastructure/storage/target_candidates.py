"""Build additive target candidates from frozen persisted rows, never refetch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import orjson
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
    target_v32_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LocalTargetClassificationEvidenceStore,
)
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
    _tree_hashes,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
    validate_deployment_binding,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    assert_candidate_cohort_closure as _assert_candidate_cohort_closure,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    candidate_input_row_id,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    business_fields as _business,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    by_id as _by_id,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    read_delta as _read_delta,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    scoped_target_hash as _scoped_target_hash,
)
from bioetl.infrastructure.storage.target_migration_validation import (
    _frozen_v31_hash_fields,
    _load_candidate_profile,
    compare_target_rows,
    validate_target_candidate,
)
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_file


@dataclass(frozen=True, slots=True)
class TargetCandidateBuildRequest:
    paths: TargetMigrationPaths
    input_manifest: Path
    input_manifest_sha256: str
    output_dir: Path
    legacy_include_fields: tuple[str, ...]
    run_id: str
    run_started_at: str
    deployment: TargetDeploymentBinding


def freeze_target_inputs(
    paths: TargetMigrationPaths,
    *,
    legacy_include_fields: tuple[str, ...],
    output: Path,
    restoration_manifest: Path | None = None,
) -> dict[str, object]:
    """Record stable table versions/files/cohorts without writing a source table."""
    checked = paths.checked()
    _safe_output(output, paths, directory=False)
    workspace = paths.workspace.resolve()
    relative_output = output.resolve().relative_to(workspace)
    safe_output = workspace.joinpath(*relative_output.parts)
    before = _input_facts(checked)
    silver, gold = _read_delta(checked["silver"]), _read_delta(checked["gold"])
    compare_target_rows(silver, silver, legacy_include_fields)
    compare_target_rows(gold, gold, legacy_include_fields)
    if not {identity for (identity, _), _row in _by_id(gold).items()}.issubset(
        identity for (identity, _), _row in _by_id(silver).items()
    ):
        raise ValueError("original Gold targets have no persisted Silver source")
    closure_gold, restoration_record = _frozen_restoration(
        paths, checked, restoration_manifest
    )
    _assert_candidate_cohort_closure(checked, [*gold, *closure_gold])
    if _input_facts(checked) != before:
        raise ValueError("source changed during target input freeze")
    document: dict[str, object] = {
        "artifact": "bioetl_target_candidate_inputs",
        "schema_version": 1,
        "inputs": before,
        "cohorts": _cohort_keys(silver, gold),
        "legacy_include_fields": list(legacy_include_fields),
        "fk_restoration": restoration_record,
    }
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    with safe_output.open("xb") as handle:
        handle.write(canonical_json_bytes(document))
    return document


def _frozen_restoration(
    paths: TargetMigrationPaths,
    checked: dict[str, Path],
    manifest: Path | None,
) -> tuple[list[dict[str, object]], dict[str, str] | None]:
    """Read a validated additive cohort without copying it into canonical Gold."""
    if manifest is None:
        return [], None
    from bioetl.infrastructure.storage.target_fk_restoration import (
        load_published_restoration,
    )

    published = load_published_restoration(
        manifest,
        workspace=paths.workspace,
        silver=checked["silver"],
        gold=checked["gold"],
        assay=checked["assay"],
        config=checked["config"],
    )
    relative = manifest.resolve().relative_to(paths.workspace.resolve()).as_posix()
    return list(published.additions["gold"]), {
        "manifest": relative,
        "sha256": sha256_file(manifest),
    }


def _append_frozen_restoration(
    request: TargetCandidateBuildRequest,
    frozen: Mapping[str, object],
    silver: list[dict[str, object]],
    gold: list[dict[str, object]],
) -> tuple[Path | None, list[dict[str, object]], list[dict[str, object]]]:
    """Add the frozen restored rows after the original cohort identity check."""
    record = frozen.get("fk_restoration")
    if not isinstance(record, dict):
        return None, silver, gold
    manifest = request.paths.workspace / str(record["manifest"])
    if sha256_file(manifest) != record["sha256"]:
        raise ValueError("target FK restoration digest mismatch")
    from bioetl.infrastructure.storage.target_fk_restoration import (
        load_published_restoration,
    )

    published = load_published_restoration(
        manifest,
        workspace=request.paths.workspace,
        silver=request.paths.silver,
        gold=request.paths.gold,
        assay=request.paths.assay,
        config=request.paths.config,
    )
    return (
        manifest,
        [*silver, *published.additions["silver"]],
        [*gold, *published.additions["gold"]],
    )


def _cohort_keys(
    silver: list[dict[str, object]], gold: list[dict[str, object]]
) -> dict[str, list[list[object]]]:
    """Retain per-layer versions in the JSON representation used by the freeze."""
    return {
        name: [list(key) for key in sorted(_by_id(rows))]
        for name, rows in (("silver", silver), ("gold", gold))
    }


def _input_facts(paths: dict[str, Path]) -> dict[str, object]:
    """Capture Delta identities, versions, file hashes, and config digest."""
    facts: dict[str, object] = {}
    for name in ("silver", "gold", "assay"):
        table = DeltaTable(str(paths[name]))
        _assert_local_files(table, paths[name])
        facts[name] = {
            "uri": paths[name].as_uri(),
            "version": table.version(),
            "table_id": table.metadata().id,
            "files": _tree_hashes(paths[name]),
        }
    facts["config"] = {
        "uri": paths["config"].as_uri(),
        "sha256": sha256_file(paths["config"]),
    }
    return facts


def _assert_local_files(table: DeltaTable, root: Path) -> None:
    """Reject Delta data files outside the preserved table root."""
    from bioetl.infrastructure.storage.delta.table_ops import resolve_parquet_file_uri

    for uri in table.file_uris():
        path = Path(resolve_parquet_file_uri(uri)).resolve()
        if not path.is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("target bundle has external Delta data-file references")


def _safe_output(path: Path, paths: TargetMigrationPaths, *, directory: bool) -> None:
    """Validate output containment, disjointness, and occurrence freshness."""
    resolved = path.resolve()
    if (
        path.name == ".env"
        or path.name.startswith(".env.")
        or path.name.endswith(".env")
    ):
        raise ValueError("candidate outputs cannot be environment files")
    if (
        not resolved.is_relative_to(paths.workspace.resolve())
        or resolved == paths.workspace.resolve()
    ):
        raise ValueError("candidate output escapes the approved workspace")
    _assert_output_disjoint(resolved, paths)
    if path.exists() and (not directory or any(path.iterdir())):
        raise ValueError("candidate output occurrence already exists")
    _assert_no_path_links(path)


def _assert_output_disjoint(resolved: Path, paths: TargetMigrationPaths) -> None:
    """Reject output paths that overlap preserved or candidate resources."""
    for original in (
        paths.silver,
        paths.gold,
        paths.assay,
        paths.config,
        paths.backup,
        paths.candidate_silver,
        paths.candidate_gold,
        paths.candidate_config,
    ):
        source = original.resolve()
        if (
            resolved == source
            or resolved.is_relative_to(source)
            or source.is_relative_to(resolved)
        ):
            raise ValueError("candidate evidence output overlaps a preserved resource")


def _assert_no_path_links(path: Path) -> None:
    """Reject symlink and junction ancestors before creating output."""
    for parent in (path, *path.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("candidate output refuses symlink/junction paths")


def _verified_inputs(
    request: TargetCandidateBuildRequest, checked: dict[str, Path]
) -> dict[str, object]:
    """Verify the frozen manifest and unchanged source facts before building."""
    if sha256_file(request.input_manifest) != request.input_manifest_sha256:
        raise ValueError("target input manifest digest mismatch")
    document = orjson.loads(request.input_manifest.read_bytes())
    if (
        document.get("artifact") != "bioetl_target_candidate_inputs"
        or document.get("schema_version") != 1
    ):
        raise ValueError("unsupported target input freeze")
    if document.get("legacy_include_fields") != list(request.legacy_include_fields):
        raise ValueError("target frozen hash policy differs")
    if document.get("inputs") != _input_facts(checked):
        raise ValueError("target sources differ from the frozen occurrence")
    return cast("dict[str, object]", document)


def _write_layer(
    destination: Path,
    original: Path,
    rows: list[dict[str, object]],
    columns: tuple[str, ...] = TARGET_CLASSIFICATION_FIELDS,
) -> None:
    """Write additive classification fields while retaining the original Delta schema."""
    table = DeltaTable(str(original))
    old_schema = delta_schema_to_pyarrow(table.schema())
    names = set(old_schema.names)
    if names.intersection(columns):
        raise ValueError("candidate builder requires a legacy V30 source")
    schema = pa.schema(
        [
            *old_schema,
            *(pa.field(name, pa.string()) for name in columns),
        ]
    )
    output = pa.Table.from_pylist(rows, schema=schema)
    write_deltalake(
        str(destination),
        output,
        mode="error",
        partition_by=table.metadata().partition_columns or None,
    )


def build_target_candidates(request: TargetCandidateBuildRequest) -> dict[str, object]:
    """Publish only new destinations; a failed occurrence is retained for review."""
    checked = request.paths.checked()
    validate_deployment_binding(checked, request.deployment)
    for name in ("candidate_silver", "candidate_gold"):
        if checked[name].exists() and any(checked[name].iterdir()):
            raise ValueError("target candidate destination is not empty")
    _safe_output(request.output_dir, request.paths, directory=True)
    frozen = _verified_inputs(request, checked)
    profile = _load_candidate_profile(checked, workspace=request.paths.workspace)
    from bioetl.infrastructure.storage.target_migration_validation import (
        _candidate_table_contract,
    )

    contract = _candidate_table_contract(checked)
    columns = TARGET_CLASSIFICATION_FIELDS
    fields = _frozen_v31_hash_fields(checked, request.legacy_include_fields)
    normalization = target_v31_normalization_profile()
    if contract == "3.2.0":
        columns = (*columns, *TARGET_CLASSIFICATION_DETAIL_FIELDS)
        fields = tuple(dict.fromkeys((*fields, *TARGET_CLASSIFICATION_DETAIL_FIELDS)))
        normalization = target_v32_normalization_profile()
    old_silver, old_gold = _read_delta(checked["silver"]), _read_delta(checked["gold"])
    expected_cohorts = _cohort_keys(old_silver, old_gold)
    if frozen["cohorts"] != expected_cohorts:
        raise ValueError("target frozen cohort identity differs")
    restoration_manifest, old_silver, old_gold = _append_frozen_restoration(
        request, frozen, old_silver, old_gold
    )
    request.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = IupharTargetClassificationAdapter(profile, table_contract=contract)
    store = LocalTargetClassificationEvidenceStore(
        request.output_dir / "classification",
        mode="enrich",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
        normalization_version=profile.normalization_version,
        rules_version=profile.rules_version,
        classification_schema_version=profile.classification_schema_version,
        matching_policy_version=profile.matching_policy_version,
    )
    projections: dict[str, dict[str, str | None]] = {}
    new_silver: list[dict[str, object]] = []
    row_ids = []
    for row in old_silver:
        identity = str(row["target_id"])
        result = adapter.classify_record(
            _business(row),
            input_row_id=candidate_input_row_id(identity),
            run_id=request.run_id,
            run_started_at=request.run_started_at,
        )
        projected = {name: result.projection.get(name) for name in columns}
        projections[identity] = projected
        updated = {**row, **projected}
        updated["content_hash"] = _scoped_target_hash(updated, fields, normalization)
        new_silver.append(updated)
        store.publish_result(result, run_id=request.run_id, batch_id="frozen-silver")
        row_ids.append(result.input_row_id)
    new_gold = []
    for row in old_gold:
        updated = {**row, **projections[str(row["target_id"])]}
        updated["content_hash"] = _scoped_target_hash(updated, fields, normalization)
        new_gold.append(updated)
    _verified_inputs(request, checked)
    _write_layer(checked["candidate_silver"], checked["silver"], new_silver, columns)
    _write_layer(checked["candidate_gold"], checked["gold"], new_gold, columns)
    validation = validate_target_candidate(
        checked,
        request.legacy_include_fields,
        workspace=request.paths.workspace,
        restoration_manifest=restoration_manifest,
    )
    _verified_inputs(request, checked)
    evidence = store.finalize_run(
        run_id=request.run_id, expected_row_ids=tuple(sorted(row_ids))
    )
    manifest: dict[str, object] = {
        "artifact": "bioetl_target_candidate_build",
        "schema_version": 1,
        "status": "complete",
        "run_id": request.run_id,
        "input_manifest_sha256": request.input_manifest_sha256,
        "deployment": request.deployment.document(),
        "validation": validation,
        "evidence_manifest": {"immutable_uri": evidence.uri, "sha256": evidence.sha256},
        "candidate_files": {
            name: _tree_hashes(checked[name])
            for name in ("candidate_silver", "candidate_gold")
        },
    }
    with (request.output_dir / "build-manifest.json").open("xb") as handle:
        handle.write(canonical_json_bytes(manifest))
    return manifest


__all__ = [
    "TargetCandidateBuildRequest",
    "build_target_candidates",
    "freeze_target_inputs",
]
