"""Semantic validation for deterministic RAG catalog/chunk manifest pairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory.rag._validation_checks import (
    add_issue,
    catalog_sources,
    current_eligible_sources,
    validate_catalog_metadata,
    validate_chunks,
    validate_counts,
    validate_source_files,
    validate_source_identity,
)
from memory.rag._validation_model import (
    FULL_BUILD_SCOPE,
    SUPPORTED_BUILD_SCOPES,
    RagManifestValidationError,
    RagValidationIssue,
    RagValidationReport,
    calculate_source_surface_sha256,
    capture_rag_git_identity,
    capture_rag_source_identity,
    normalize_rag_source_path,
)
from memory.resources import MEMORY_ROOT

__all__ = [
    "RagManifestValidationError",
    "RagValidationIssue",
    "RagValidationReport",
    "calculate_source_surface_sha256",
    "capture_rag_git_identity",
    "capture_rag_source_identity",
    "normalize_rag_source_path",
    "require_valid_rag_manifest",
    "validate_rag_manifest_files",
    "validate_rag_manifest_payload",
]


def _resolve_eligible_sources(
    *,
    root: Path,
    indexed_sources: set[str],
    build_scope: str | None,
    expected_source_paths: list[Path] | tuple[Path, ...] | None,
    verify_sources: bool,
) -> set[str]:
    if expected_source_paths is not None:
        return {
            normalize_rag_source_path(path.as_posix(), allow_virtual_fragment=False)
            for path in expected_source_paths
        }
    if build_scope == FULL_BUILD_SCOPE and verify_sources:
        return current_eligible_sources(root)
    return set(indexed_sources)


def _mark_extra_source_chunks_stale(
    *,
    issues: list[RagValidationIssue],
    build_scope: str | None,
    indexed_sources: set[str],
    eligible_sources: set[str],
    chunk_sources: dict[int, str | None],
    stale_indices: set[int],
) -> None:
    if build_scope != FULL_BUILD_SCOPE or indexed_sources == eligible_sources:
        return
    missing_from_catalog = eligible_sources - indexed_sources
    extra_in_catalog = indexed_sources - eligible_sources
    add_issue(
        issues,
        "source_set_mismatch",
        "catalog.sources",
        "full catalog source set differs from the current eligible set "
        f"(missing={len(missing_from_catalog)}, extra={len(extra_in_catalog)})",
    )
    for index, source_path in chunk_sources.items():
        if source_path in extra_in_catalog:
            stale_indices.add(index)


def _mark_stale_source_chunks(
    *,
    chunk_sources: dict[int, str | None],
    stale_source_paths: set[str],
    stale_indices: set[int],
) -> None:
    for index, source_path in chunk_sources.items():
        if source_path in stale_source_paths:
            stale_indices.add(index)


def _resolve_source_identity(
    *,
    root: Path,
    catalog: dict[str, Any],
    issues: list[RagValidationIssue],
    build_scope: str | None,
    indexed_sources: set[str],
    eligible_sources: set[str],
    verify_sources: bool,
) -> tuple[str | None, bool]:
    if verify_sources:
        identity_sources = (
            eligible_sources if build_scope == FULL_BUILD_SCOPE else indexed_sources
        )
        return validate_source_identity(root, catalog, identity_sources, issues)
    stored_hash = catalog.get("source_surface_sha256")
    current_hash = stored_hash if isinstance(stored_hash, str) else None
    return current_hash, False


def validate_rag_manifest_payload(
    root: Path,
    catalog: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    require_build_scope: str | None = None,
    expected_source_paths: list[Path] | tuple[Path, ...] | None = None,
    verify_sources: bool = True,
) -> RagValidationReport:
    """Validate one in-memory catalog/chunk pair against current sources."""
    issues: list[RagValidationIssue] = []
    build_scope = validate_catalog_metadata(
        catalog,
        issues,
        require_build_scope=require_build_scope,
    )
    sources = catalog_sources(catalog, issues)
    if verify_sources:
        missing_paths, content_stale_paths = validate_source_files(
            root,
            sources,
            issues,
        )
    else:
        missing_paths, content_stale_paths = set(), set()
    chunks_by_source, chunk_sources, stale_indices = validate_chunks(
        chunks,
        sources,
        issues,
    )
    validate_counts(catalog, sources, chunks, chunks_by_source, issues)

    indexed_sources = set(sources)
    eligible_sources = _resolve_eligible_sources(
        root=root,
        indexed_sources=indexed_sources,
        build_scope=build_scope,
        expected_source_paths=expected_source_paths,
        verify_sources=verify_sources,
    )
    _mark_extra_source_chunks_stale(
        issues=issues,
        build_scope=build_scope,
        indexed_sources=indexed_sources,
        eligible_sources=eligible_sources,
        chunk_sources=chunk_sources,
        stale_indices=stale_indices,
    )
    _mark_stale_source_chunks(
        chunk_sources=chunk_sources,
        stale_source_paths=missing_paths | content_stale_paths,
        stale_indices=stale_indices,
    )
    current_hash, identity_mismatch = _resolve_source_identity(
        root=root,
        catalog=catalog,
        issues=issues,
        build_scope=build_scope,
        indexed_sources=indexed_sources,
        eligible_sources=eligible_sources,
        verify_sources=verify_sources,
    )
    if identity_mismatch:
        stale_indices.update(range(len(chunks)))

    return RagValidationReport(
        issues=tuple(issues),
        build_scope=build_scope,
        eligible_source_count=len(eligible_sources),
        indexed_source_count=len(indexed_sources),
        chunk_count=len(chunks),
        missing_path_count=len(missing_paths),
        stale_chunk_count=len(stale_indices),
        source_surface_sha256=current_hash,
    )


def _invalid_file_report(path: Path, message: str) -> RagValidationReport:
    return RagValidationReport(
        issues=(
            RagValidationIssue(
                code="manifest_io_error",
                path=str(path),
                message=message,
            ),
        ),
        build_scope=None,
        eligible_source_count=0,
        indexed_source_count=0,
        chunk_count=0,
        missing_path_count=0,
        stale_chunk_count=0,
        source_surface_sha256=None,
    )


def validate_rag_manifest_files(
    root: Path,
    catalog_path: Path,
    chunks_path: Path,
    *,
    require_build_scope: str | None = None,
    verify_sources: bool = True,
) -> RagValidationReport:
    """Load and semantically validate a catalog/chunk manifest pair."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    catalog_path = resolve_output_path(catalog_path, root=root)
    chunks_path = resolve_output_path(chunks_path, root=root)
    try:
        catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _invalid_file_report(catalog_path, str(exc))
    if not isinstance(catalog_payload, dict):
        return _invalid_file_report(catalog_path, "catalog root must be an object")

    chunks: list[dict[str, Any]] = []
    try:
        for line_number, raw_line in enumerate(
            chunks_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            if not isinstance(row, dict):
                return _invalid_file_report(
                    chunks_path,
                    f"chunk row {line_number} must be an object",
                )
            chunks.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _invalid_file_report(chunks_path, str(exc))
    return validate_rag_manifest_payload(
        root,
        catalog_payload,
        chunks,
        require_build_scope=require_build_scope,
        verify_sources=verify_sources,
    )


def require_valid_rag_manifest(report: RagValidationReport) -> RagValidationReport:
    """Raise a typed error unless a validation report is successful."""
    if not report.ok:
        raise RagManifestValidationError(report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a deterministic RAG catalog/chunk manifest pair."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root whose current sources must match the manifest.",
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=MEMORY_ROOT / "derived" / "rag" / "manifests",
        help="Directory containing corpus_catalog.json and chunks.jsonl.",
    )
    parser.add_argument(
        "--require-build-scope",
        choices=tuple(sorted(SUPPORTED_BUILD_SCOPES)),
        default=None,
        help="Optionally require full or workflow build scope.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the RAG manifest validator CLI."""
    args = _build_parser().parse_args(argv)
    manifest_dir = args.manifest_dir.resolve()
    report = validate_rag_manifest_files(
        args.root.resolve(),
        manifest_dir / "corpus_catalog.json",
        manifest_dir / "chunks.jsonl",
        require_build_scope=args.require_build_scope,
    )
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    elif report.ok:
        print(
            "RAG manifest validation passed: "
            f"sources={report.indexed_source_count}, chunks={report.chunk_count}"
        )
    else:
        print("RAG manifest validation failed:")
        for issue in report.issues:
            print(f"- [{issue.code}] {issue.path}: {issue.message}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
