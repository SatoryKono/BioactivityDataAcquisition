#!/usr/bin/env python3
"""Generate/check compatibility facade snapshot companion docs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
    from _compatibility_registry import (  # type: ignore[import-not-found]
        DEFAULT_REGISTRY_PATH,
        DEFAULT_SRC_ROOT,
        CompatibilityRegistry,
        find_first_party_imports_of_measured_only_modules,
        load_compatibility_registry,
        scan_docstring_tracked_modules,
        validate_measured_docstring_surface,
        validate_measured_only_ratchet,
    )
else:
    raise SystemExit(
        "Run this generator as a script from the repository root, not as a package module."
    )


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-snapshot.md"
)
_FRONTMATTER_DELIMITER = "---"
_NONE_BULLET = "- None."


def _ensure_repo_path(path: Path) -> Path:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to write outside {resolved_root}: {resolved_path}")
    return resolved_path


def _repo_relative_path(path: Path) -> Path:
    safe_path = _ensure_repo_path(path)
    return safe_path.relative_to(ROOT.resolve())


def _normalize_repo_relative_path(path: Path) -> Path:
    """Normalize and validate a repository-relative path."""
    if path.is_absolute():
        raise ValueError(f"expected repository-relative path, got absolute path: {path}")

    normalized_parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"refusing parent traversal path: {path}")
        normalized_parts.append(part)

    if not normalized_parts:
        raise ValueError("refusing empty repository-relative path")
    return Path(*normalized_parts)


def _write_repo_text(relative_path: Path, content: str) -> None:
    """Write generated snapshot content via a repository-relative path."""
    safe_relative_path = _normalize_repo_relative_path(relative_path)
    target_path = _ensure_repo_path(ROOT / safe_relative_path)
    target_path.write_text(content, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/check the compatibility facade snapshot companion file."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Fail on drift.")
    mode.add_argument("--update", action="store_true", help="Rewrite snapshot file.")
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to compatibility registry YAML.",
    )
    parser.add_argument(
        "--src-root",
        default=str(DEFAULT_SRC_ROOT),
        help="Source root used for docstring-tracking validation.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Generated markdown snapshot path.",
    )
    return parser.parse_args()


def _render_path_list(paths: list[str]) -> list[str]:
    if not paths:
        return [_NONE_BULLET]
    return [f"- `{path}`" for path in paths]


def _render_measured_only_modules(registry: CompatibilityRegistry) -> list[str]:
    if not registry.measured_only_modules:
        return [_NONE_BULLET]

    lines: list[str] = []
    for row in registry.measured_only_modules:
        lines.append(
            f"- `{row.path}` — owner: `{row.owner}`, review: `{row.review_date}`, "
            f"policy: `{row.new_code_policy}`, promote on: `{row.promotion_trigger}`, "
            f"reason: {row.reason}"
        )
    return lines


def _render_measured_only_ratchet(registry: CompatibilityRegistry) -> list[str]:
    lines = [
        f"- Max measured-only modules: `{registry.measured_only_ratchet.max_total_modules}`",
    ]
    for scope in registry.measured_only_ratchet.scoped_limits:
        lines.append(
            f"- `{scope.path_prefix}` <= `{scope.max_modules}` measured-only modules"
        )
    return lines


def _render_measured_only_review_workflow(registry: CompatibilityRegistry) -> list[str]:
    workflow = registry.measured_only_review_workflow
    lines = [
        f"- Review cadence: `{workflow.review_cadence}`",
        "- Required checks:",
    ]
    lines.extend(f"  - {check}" for check in workflow.required_checks)
    lines.append("- Allowed outcomes:")
    lines.extend(f"  - `{outcome}`" for outcome in workflow.allowed_outcomes)
    lines.append(
        "- Promotion requires curated row: "
        f"`{str(workflow.promotion_requires_curated_row).lower()}`"
    )
    return lines


def _render_import_violations(
    measured_only_import_violations: dict[str, tuple[str, ...]],
) -> list[str]:
    """Render measured-only import violations as markdown bullets."""
    if not measured_only_import_violations:
        return ["- None."]
    return [
        f"- `{module}` imported by {', '.join(f'`{path}`' for path in importers)}"
        for module, importers in sorted(measured_only_import_violations.items())
    ]


def _summary_section(
    *,
    registry: CompatibilityRegistry,
    discovered_paths: list[str],
    unexpected_paths: list[str],
    missing_paths: list[str],
    measured_only_import_violations: dict[str, tuple[str, ...]],
    ratchet_violations: tuple[str, ...],
) -> list[str]:
    """Render snapshot summary section."""
    return [
        "## Summary",
        "",
        f"- Registry YAML: `{DEFAULT_REGISTRY_PATH.relative_to(ROOT).as_posix()}`",
        f"- Curated inventory rows: `{len(registry.curated_rows)}`",
        f"- Transition debt rows: `{len(registry.transition_debt)}`",
        f"- Retained public entrypoints: `{len(registry.retained_entrypoints)}`",
        f"- Measured tracked modules: `{len(registry.measured_tracked_paths)}`",
        f"- Measured-only modules outside curated inventory: `{len(registry.measured_only_paths)}`",
        f"- Discovered docstring-tracked modules: `{len(discovered_paths)}`",
        f"- Unexpected docstring-tracked modules: `{len(unexpected_paths)}`",
        f"- Missing allowlisted measured-only modules: `{len(missing_paths)}`",
        (
            "- First-party src imports targeting measured-only modules: "
            f"`{len(measured_only_import_violations)}`"
        ),
        f"- Ratchet violations: `{len(ratchet_violations)}`",
        "",
    ]


def _measured_only_section(
    *,
    registry: CompatibilityRegistry,
    scoped_ratchet_counts: dict[str, int],
    ratchet_violations: tuple[str, ...],
) -> list[str]:
    """Render measured-only allowlist, ratchet, and workflow sections."""
    return [
        "## Measured-Only Allowlist",
        "",
        *_render_measured_only_modules(registry),
        "",
        "## Measured-Only Ratchet",
        "",
        *_render_measured_only_ratchet(registry),
        "",
        "### Live Ratchet Counts",
        "",
        f"- Total measured-only modules: `{len(registry.measured_only_modules)}`",
        *[
            f"- `{path_prefix}` currently has `{scoped_ratchet_counts[path_prefix]}` modules"
            for path_prefix in sorted(scoped_ratchet_counts)
        ],
        "",
        "### Ratchet Violations",
        "",
        *_render_path_list(list(ratchet_violations)),
        "",
        "## Measured-Only Review Workflow",
        "",
        *_render_measured_only_review_workflow(registry),
        "",
    ]


def _docstring_validation_section(
    *,
    discovered_paths: list[str],
    unexpected_paths: list[str],
    missing_paths: list[str],
    measured_only_import_violations: dict[str, tuple[str, ...]],
) -> list[str]:
    """Render live docstring tracking validation section."""
    return [
        "## Live Docstring Tracking Validation",
        "",
        "### Discovered Docstring-Tracked Modules",
        "",
        *_render_path_list(discovered_paths),
        "",
        "### Unexpected Docstring-Tracked Modules",
        "",
        *_render_path_list(unexpected_paths),
        "",
        "### Missing Allowlisted Measured-Only Modules",
        "",
        *_render_path_list(missing_paths),
        "",
        "### First-Party Src Imports Of Measured-Only Modules",
        "",
        *_render_import_violations(measured_only_import_violations),
        "",
    ]


def render_snapshot(
    registry: CompatibilityRegistry,
    *,
    discovered_docstring_modules: set[str],
    unexpected_docstring_modules: set[str],
    missing_measured_only_modules: set[str],
    measured_only_import_violations: dict[str, tuple[str, ...]],
    ratchet_violations: tuple[str, ...],
    scoped_ratchet_counts: dict[str, int],
) -> str:
    tracked_paths = sorted(registry.measured_tracked_paths)
    discovered_paths = sorted(discovered_docstring_modules)
    unexpected_paths = sorted(unexpected_docstring_modules)
    missing_paths = sorted(missing_measured_only_modules)
    sections = [
        "# Compatibility Facade Snapshot (Generated)",
        "",
        "> Generated by `scripts/engineering/qa/generate_compatibility_facade_snapshot.py`. Do not edit manually.",
        "",
        *_summary_section(
            registry=registry,
            discovered_paths=discovered_paths,
            unexpected_paths=unexpected_paths,
            missing_paths=missing_paths,
            measured_only_import_violations=measured_only_import_violations,
            ratchet_violations=ratchet_violations,
        ),
        "## Tracked Docstring Prefixes",
        "",
        *[f"- `{prefix}`" for prefix in registry.tracked_docstring_prefixes],
        "",
        "## Expected Measured Registry",
        "",
        *_render_path_list(tracked_paths),
        "",
        *_measured_only_section(
            registry=registry,
            scoped_ratchet_counts=scoped_ratchet_counts,
            ratchet_violations=ratchet_violations,
        ),
        *_docstring_validation_section(
            discovered_paths=discovered_paths,
            unexpected_paths=unexpected_paths,
            missing_paths=missing_paths,
            measured_only_import_violations=measured_only_import_violations,
        ),
    ]
    return "\n".join(sections)


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith(f"{_FRONTMATTER_DELIMITER}\n"):
        return None, text
    parts = text.split(f"\n{_FRONTMATTER_DELIMITER}\n", 1)
    if len(parts) != 2:
        return None, text
    frontmatter, body = parts
    return f"{frontmatter}\n{_FRONTMATTER_DELIMITER}\n", body


def _validation_has_issues(
    *,
    unexpected: set[str],
    missing: set[str],
    measured_only_import_violations: dict[str, tuple[str, ...]],
    ratchet_violations: tuple[str, ...],
) -> bool:
    """Return True when live validation produced any actionable issue."""
    return bool(
        unexpected or missing or measured_only_import_violations or ratchet_violations
    )


def _print_validation_issues(
    *,
    level: str,
    unexpected: set[str],
    missing: set[str],
    measured_only_import_violations: dict[str, tuple[str, ...]],
    ratchet_violations: tuple[str, ...],
) -> None:
    """Print drift/warn details for validation findings."""
    if unexpected:
        print(f"[{level}] unexpected docstring-tracked modules:")
        for path in sorted(unexpected):
            print(f"  - {path}")
    if missing:
        print(f"[{level}] missing allowlisted measured-only modules:")
        for path in sorted(missing):
            print(f"  - {path}")
    if measured_only_import_violations:
        print(f"[{level}] first-party src imports measured-only modules:")
        for module, importers in sorted(measured_only_import_violations.items()):
            joined = ", ".join(importers)
            print(f"  - {module}: {joined}")
    if ratchet_violations:
        print(f"[{level}] measured-only ratchet violations:")
        for violation in ratchet_violations:
            print(f"  - {violation}")


def main() -> int:
    args = _parse_args()
    registry = load_compatibility_registry(Path(args.registry))
    discovered = scan_docstring_tracked_modules(
        src_root=Path(args.src_root),
        prefixes=registry.tracked_docstring_prefixes,
    )
    unexpected, missing = validate_measured_docstring_surface(
        registry,
        src_root=Path(args.src_root),
    )
    measured_only_import_violations = find_first_party_imports_of_measured_only_modules(
        registry,
        src_root=Path(args.src_root),
    )
    ratchet_violations, scoped_ratchet_counts = validate_measured_only_ratchet(
        registry
    )
    rendered = render_snapshot(
        registry,
        discovered_docstring_modules=discovered,
        unexpected_docstring_modules=unexpected,
        missing_measured_only_modules=missing,
        measured_only_import_violations=measured_only_import_violations,
        ratchet_violations=ratchet_violations,
        scoped_ratchet_counts=scoped_ratchet_counts,
    )
    output_path = _ensure_repo_path(Path(args.output))
    current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
    frontmatter, current_body = _split_frontmatter(current)
    if args.check:
        is_error = False
        if current_body != rendered:
            print(f"[drift] mismatch: {output_path.as_posix()}")
            is_error = True
        if _validation_has_issues(
            unexpected=unexpected,
            missing=missing,
            measured_only_import_violations=measured_only_import_violations,
            ratchet_violations=ratchet_violations,
        ):
            _print_validation_issues(
                level="drift",
                unexpected=unexpected,
                missing=missing,
                measured_only_import_violations=measured_only_import_violations,
                ratchet_violations=ratchet_violations,
            )
            is_error = True
        if is_error:
            return 1
        print("[ok] compatibility facade snapshot is up to date")
        return 0
    output_path = _ensure_repo_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_with_frontmatter = f"{frontmatter}{rendered}" if frontmatter else rendered
    _write_repo_text(_repo_relative_path(output_path), rendered_with_frontmatter)
    print(f"[updated] wrote {output_path.as_posix()}")
    if _validation_has_issues(
        unexpected=unexpected,
        missing=missing,
        measured_only_import_violations=measured_only_import_violations,
        ratchet_violations=ratchet_violations,
    ):
        _print_validation_issues(
            level="warn",
            unexpected=unexpected,
            missing=missing,
            measured_only_import_violations=measured_only_import_violations,
            ratchet_violations=ratchet_violations,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
