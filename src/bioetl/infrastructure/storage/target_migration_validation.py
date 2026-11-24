"""Full-cohort checks and managed-writer quiescence for target promotion."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import psutil
import yaml
from pandera.pandas import DataFrameModel

from bioetl.domain.config.target_classification import (
    resolve_physical_table_contract,
)
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
    target_v32_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.acceptance_receipt import load_profile
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import LoadedIupharProfile
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    assert_candidate_cohort_closure as _assert_candidate_cohort_closure,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    classification_fields,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    verify_candidate_hashes as _verify_candidate_hashes,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    verify_source_classifications as _verify_source_classifications,
)
from bioetl.infrastructure.storage.target_migration_dependencies import (
    _local_path,
)
from bioetl.infrastructure.storage.target_migration_physical import (
    validate_physical_projection,
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


def assert_no_managed_writers() -> None:
    """Refuse migration while known pipeline or orchestrated writers live."""
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == os.getpid():
            continue
        if _managed_writer_command(process.info.get("cmdline") or ()):
            raise RuntimeError(
                f"managed writer is still active: PID {process.info['pid']}"
            )


def _bioetl_arguments(argv: Sequence[str]) -> list[str]:
    for index, arg in enumerate(argv):
        is_cli_module = (
            arg == "bioetl.interfaces.cli" and index > 0 and argv[index - 1] == "-m"
        )
        if is_cli_module or Path(arg).name.lower() in {
            "bioetl",
            "bioetl.exe",
            "bioetl-script.py",
        }:
            args = list(argv[index + 1 :])
            return args[1:] if args[:1] == ["--"] else args
    return []


_WRITER_VALUE_OPTIONS = frozenset(
    [
        "--pipeline",
        "--source",
        "--composite",
        "--run-type",
        "--limit",
        "--start-offset",
        "--input-csv",
        "--filter-column",
        "--filter-field",
        "--vacuum-retention-days",
        "--resume-run-id",
        "--resume-manifest-id",
        "--debug-export-dir",
        "--debug-export-format",
        "--cached-bronze-path",
        "--cached-bronze-date",
        "--required-persistence-profile",
        "--replay-of-run-id",
        "--replay-of-manifest-id",
        "--health-port",
        "--observability-backend-port",
        "--breakpoints",
        "--mode",
        "--seed-limit",
        "--enrich-only",
        "--force-enricher",
        "--only-steps",
        "--reconciliation-mode",
        "--log-level",
        "--execution-context",
        "--force-steps",
        "--repair-steps",
    ]
)


def _writer_options(args: list[str]) -> list[str]:
    """Keep option values from masquerading as read-only flags or commands."""
    options, remaining = [], iter(args)
    for argument in remaining:
        if argument == "--":
            break
        if argument in _WRITER_VALUE_OPTIONS:
            argument = f"{argument}={next(remaining, '')}"
        options.append(argument)
    return options


def _managed_batch_writer(command: str, options: list[str]) -> bool:
    """Classify composite writers and last-source ChEMBL batches."""
    if command == "run-composite":
        return True
    if "--list-only" in options:
        return False
    for index in range(len(options) - 1, -1, -1):
        option = options[index]
        if option.startswith("--source="):
            return option == "--source=chembl"
    return False


def _managed_writer_command(argv: Sequence[str]) -> bool:
    """Recognize maintained pipeline and orchestrator writer commands."""
    if any("workflow-campaigns" in arg.replace("\\", "/").split("/") for arg in argv):
        return True
    args = _writer_options(_bioetl_arguments(argv))
    if any(flag in args for flag in ("--dry-run", "--help", "-h")):
        return False
    if any(
        args[index : index + 2] == ["workflow", "run"] for index in range(len(args) - 1)
    ):
        return True
    if args[:1] in (["run-all"], ["run-composite"]):
        return _managed_batch_writer(args[0], args[1:])
    return bool({"run", "debug"}.intersection(args)) and (
        "chembl_target" in args or "--pipeline=chembl_target" in args
    )


def compare_target_rows(
    original: Sequence[Mapping[str, object]],
    candidate: Sequence[Mapping[str, object]],
    legacy_include_fields: tuple[str, ...],
    *,
    allowed_additions: frozenset[tuple[str, int | None]] = frozenset(),
) -> dict[str, int]:
    """Reject subsets, changed old fields, duplicates or legacy-hash drift.

    ``allowed_additions`` is the exact set of verified FK restorations. Any
    other extra or missing identity still fails the cohort check.
    """
    if not legacy_include_fields:
        raise ValueError("explicit frozen legacy hash include-policy required")
    old, new = _by_id(original), _by_id(candidate)
    if set(old) - set(new) or set(new) - set(old) != set(allowed_additions):
        raise ValueError("candidate target IDs differ from the full canonical cohort")
    for key, previous in old.items():
        current = new[key]
        _assert_legacy_values(str(key), previous, current)
        old_hash = _scoped_target_hash(
            previous, legacy_include_fields, CHEMBL_TARGET_PROFILE
        )
        new_legacy_hash = _scoped_target_hash(
            current, legacy_include_fields, CHEMBL_TARGET_PROFILE
        )
        if old_hash != previous.get("content_hash") or old_hash != new_legacy_hash:
            raise ValueError("legacy 3.0 hash equivalence failed")
    return {
        "rows": len(new),
        "legacy_hashes_verified": len(old),
        "restored_rows": len(new) - len(old),
    }


def _assert_restored_values(
    key: str,
    published: Mapping[str, object],
    current: Mapping[str, object],
    *,
    contract: str,
) -> None:
    """Keep a published restoration intact apart from its candidate hash and classification."""
    for field, value in published.items():
        if field == "content_hash":
            continue
        if (
            field not in current
            or type(current[field]) is not type(value)
            or current[field] != value
        ):
            raise ValueError(f"restored target changed: {key}/{field}")
    unexpected = set(current) - set(published) - set(classification_fields(contract))
    if unexpected:
        raise ValueError(f"restored target gained unexpected fields: {key}")


def _assert_legacy_values(
    key: str, previous: Mapping[str, object], current: Mapping[str, object]
) -> None:
    """Preserve every old physical value, including storage/runtime metadata."""
    if previous.get("entity_id") != current.get("entity_id"):
        raise ValueError(f"candidate changed legacy entity_id: {key}")
    for field, value in previous.items():
        if field == "content_hash":
            continue
        if (
            field not in current
            or type(current[field]) is not type(value)
            or current[field] != value
        ):
            kind = "technical" if field.startswith("_") else "business"
            raise ValueError(f"candidate changed legacy {kind} field: {key}/{field}")


def _frozen_v31_hash_fields(
    paths: dict[str, Path],
    legacy_include_fields: tuple[str, ...],
    contract: str = "3.1.0",
) -> tuple[str, ...]:
    """Extend the exact canonical V30 scope; candidate YAML cannot weaken it."""
    config = yaml.safe_load(paths["config"].read_text(encoding="utf-8"))
    configured = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    if not configured or configured != legacy_include_fields:
        raise ValueError(
            "migration hash scope differs from the frozen canonical V30 policy"
        )
    return tuple(
        dict.fromkeys((*legacy_include_fields, *classification_fields(contract)))
    )


def _candidate_classification(paths: dict[str, Path]) -> dict[str, object]:
    config = yaml.safe_load(paths["candidate_config"].read_text(encoding="utf-8"))
    classification = config["pipeline"]["target_classification"]
    if not isinstance(classification, dict):
        raise ValueError("candidate target classification must be a mapping")
    return classification


def _candidate_table_contract(paths: dict[str, Path]) -> str:
    """Missing candidate YAML keeps the admitted 3.1.0 checker."""
    if "candidate_config" not in paths:
        return "3.1.0"
    selected = _candidate_classification(paths).get("table_contract")
    if selected is not None and not isinstance(selected, str):
        raise ValueError("candidate table_contract must be a string")
    return resolve_physical_table_contract("enrich", selected)


def validate_target_candidate(
    paths: dict[str, Path],
    legacy_include_fields: tuple[str, ...],
    *,
    workspace: Path | None = None,
    restoration_manifest: Path | None = None,
) -> dict[str, object]:
    """Validate admission, strict candidate schemas and both entire cohorts."""
    from bioetl.domain.schemas.chembl.target import TargetSchemaV31, TargetSchemaV32
    from bioetl.infrastructure.config.target_classification_profile import (
        ChEMBLTargetGoldSchemaV31,
        ChEMBLTargetGoldSchemaV32,
    )

    profile = _load_candidate_profile(paths, workspace=workspace)
    contract = _candidate_table_contract(paths)
    include_fields = _frozen_v31_hash_fields(paths, legacy_include_fields, contract)
    silver_schema: type[DataFrameModel] = TargetSchemaV31
    gold_schema: type[DataFrameModel] = ChEMBLTargetGoldSchemaV31
    if contract == "3.2.0":
        silver_schema = TargetSchemaV32
        gold_schema = ChEMBLTargetGoldSchemaV32
    additions = _restoration_additions(
        paths, workspace=workspace, manifest=restoration_manifest
    )
    result: dict[str, object] = {}
    layers = {}
    for name, schema in (
        ("silver", silver_schema),
        ("gold", gold_schema),
    ):
        result[name], layers[name] = _validate_candidate_layer(
            name,
            schema,
            paths,
            profile.profile_sha256,
            legacy_include_fields,
            include_fields,
            contract,
            additions[name],
        )
    _verify_source_classifications(layers, profile, contract)
    _assert_candidate_cohort_closure(paths, layers["gold"])
    result["fk_closure"] = "PASS"
    result["profile_sha256"] = profile.profile_sha256
    return result


def _load_candidate_profile(
    paths: dict[str, Path], workspace: Path | None = None
) -> LoadedIupharProfile:
    """Require the exact admitted enrich profile selected by candidate YAML."""
    classification = _candidate_classification(paths)
    if classification["mode"] != "enrich":
        raise ValueError("candidate configuration must select admitted enrich")
    manifest = classification["snapshot_manifest"]
    digest = classification["snapshot_manifest_sha256"]
    if not isinstance(manifest, str) or not isinstance(digest, str):
        raise ValueError("candidate classification requires a profile path and digest")
    if workspace is not None:
        profile_path = _local_path(workspace, str(manifest), base=workspace)
    else:
        profile_path = Path(manifest)
        if not profile_path.is_absolute():
            # Entity configuration lives at configs/entities/chembl/target.yaml.
            profile_path = paths["config"].resolve().parents[3] / profile_path
    return load_profile(
        profile_path,
        digest,
        require_acceptance=True,
    )


def _restoration_additions(
    paths: dict[str, Path], *, workspace: Path | None, manifest: Path | None
) -> dict[str, dict[tuple[str, int | None], Mapping[str, object]]]:
    """Load verified additive rows; an absent manifest adds nothing."""
    empty: dict[str, dict[tuple[str, int | None], Mapping[str, object]]] = {
        "silver": {},
        "gold": {},
    }
    if manifest is None:
        return empty
    if workspace is None:
        raise ValueError("target FK restoration requires the approved workspace")
    from bioetl.infrastructure.storage.target_fk_restoration import (
        load_published_restoration,
    )

    published = load_published_restoration(
        manifest,
        workspace=workspace,
        silver=paths["silver"],
        gold=paths["gold"],
        assay=paths["assay"],
        config=paths["config"],
    )
    return {
        layer: dict(_by_id(rows)) if rows else {}
        for layer, rows in published.additions.items()
    }


def _validate_candidate_layer(
    name: str,
    schema: type[DataFrameModel],
    paths: dict[str, Path],
    profile_sha256: str,
    legacy_include_fields: tuple[str, ...],
    include_fields: tuple[str, ...],
    contract: str,
    additions: Mapping[tuple[str, int | None], Mapping[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Validate one full layer and its unchanged legacy/hash projection."""
    old = _read_delta(paths[name])
    new = _read_delta(paths["candidate_" + name])
    result: dict[str, object] = dict(
        compare_target_rows(
            old, new, legacy_include_fields, allowed_additions=frozenset(additions)
        )
    )
    if additions:
        current = _by_id(new)
        for key, published in additions.items():
            _assert_restored_values(
                str(key), published, current[key], contract=contract
            )
    result["physical_projection"] = validate_physical_projection(
        name, schema, old, new, contract
    )
    if any(row.get("target_class_profile_sha256") != profile_sha256 for row in new):
        raise ValueError("candidate rows belong to another IUPHAR profile")
    hash_profile = (
        target_v32_normalization_profile()
        if contract == "3.2.0"
        else target_v31_normalization_profile()
    )
    _verify_candidate_hashes(new, include_fields, hash_profile)
    return result, new
