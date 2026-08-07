#!/usr/bin/env python3
"""Generate docs export artifacts from a manifest with legacy path resolution."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "docs" / "exports" / "full-docs-inputs-no-plans-reports-skills.txt"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "docs"
    / "exports"
    / "full-documentation-no-plans-reports-skills.merged.md"
)
EXPORT_TITLE = "BioETL Documentation (excluding plans/reports/skills)"
STATUS_LINE = (
    "_Status: Generated export artifact (non-normative). Canonical project guidance "
    "remains in `docs/02-architecture/**`, `docs/03-guides/**`, and "
    "`docs/04-reference/**`._"
)

EXACT_REPLACEMENTS: dict[str, str] = {
    "docs/00-project/agents/AGENT.md": "docs/00-project/ai/agents/guides/AGENT.md",
    "docs/00-project/agents/CLAUDE.md": "docs/00-project/ai/agents/CLAUDE.md",
    "docs/00-project/agents/CODEX.md": "docs/00-project/ai/agents/guides/CODEX.md",
    "docs/00-project/agents/GEMINI.md": "docs/00-project/ai/agents/guides/GEMINI.md",
    "docs/00-project/agents/README.md": "docs/00-project/ai/agents/README.md",
    "docs/00-project/agents/diagram_docs_orchestrator.md": (
        "docs/00-project/ai/agents/runtime/py-diagram-docs-orchestrator.md"
    ),
    "docs/00-project/agents/memory.md": "docs/00-project/ai/memory/agent-memory.md",
    "docs/00-project/agents/orchestration/ORCHESTRATION.md": (
        "docs/00-project/ai/agents/orchestration/ORCHESTRATION.md"
    ),
    "docs/00-project/agents/qa_orchestrator.md": (
        "docs/00-project/ai/agents/runtime/py-qa-orchestrator.md"
    ),
    "docs/02-architecture/06-diagram-policy.md": (
        "docs/02-architecture/diagrams/governance/policy.md"
    ),
    "docs/02-architecture/architecture-diagrams.md": (
        "docs/02-architecture/diagrams/guide/architecture-reference.md"
    ),
    "docs/02-architecture/container-diagram.md": (
        "docs/02-architecture/diagrams/guide/container-reference.md"
    ),
    "docs/02-architecture/data-flow.md": (
        "docs/02-architecture/diagrams/guide/data-flow-reference.md"
    ),
    "docs/02-architecture/diagrams.md": "docs/02-architecture/diagrams/README.md",
    "docs/02-architecture/mmd-diagrams/README.md": (
        "docs/02-architecture/diagrams/README.md"
    ),
    "docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.md": (
        "docs/02-architecture/diagrams/bundles/class.bundle.md"
    ),
    "docs/02-architecture/mmd-diagrams/diagram-descriptions.md": (
        "docs/02-architecture/diagrams/descriptions/class-summary.md"
    ),
    "docs/02-architecture/mmd-diagrams/diagram-descriptions/class-diagrams-descriptions.md": (
        "docs/02-architecture/diagrams/descriptions/class-summary.md"
    ),
    "docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.md": (
        "docs/02-architecture/diagrams/bundles/foundation.bundle.md"
    ),
}

PREFIX_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (
        "docs/02-architecture/diagram-descriptions/diagrams/mermaid/",
        "docs/02-architecture/diagrams/descriptions/views/",
    ),
    (
        "docs/02-architecture/diagram-descriptions/mmd-diagrams/architecture/",
        "docs/02-architecture/diagrams/descriptions/architecture/",
    ),
    (
        "docs/02-architecture/diagram-descriptions/mmd-diagrams/class-diagrams/",
        "docs/02-architecture/diagrams/descriptions/class/",
    ),
    (
        "docs/02-architecture/diagram-descriptions/mmd-diagrams/foundation/",
        "docs/02-architecture/diagrams/descriptions/foundation/",
    ),
    (
        "docs/02-architecture/diagram-descriptions/mmd-diagrams/views/",
        "docs/02-architecture/diagrams/descriptions/views/",
    ),
    (
        "docs/02-architecture/diagram-descriptions/INDEX.md",
        "docs/02-architecture/diagrams/descriptions/INDEX.md",
    ),
    (
        "docs/02-architecture/mmd-diagrams/docs/",
        "docs/02-architecture/diagrams/governance/",
    ),
    (
        "docs/02-architecture/mmd-diagrams/architecture/",
        "docs/02-architecture/diagrams/architecture/",
    ),
    (
        "docs/02-architecture/mmd-diagrams/class-diagrams/",
        "docs/02-architecture/diagrams/class-diagrams/",
    ),
    (
        "docs/02-architecture/mmd-diagrams/foundation/",
        "docs/02-architecture/diagrams/foundation/",
    ),
    (
        "docs/02-architecture/mmd-diagrams/views/",
        "docs/02-architecture/diagrams/views/",
    ),
    ("docs/03-guides/migration-", "docs/99-archive/guides/migration-"),
    ("docs/05-operations/verification/", "docs/99-archive/verification/"),
)

REMOVED_PATHS: frozenset[str] = frozenset(
    {
        "docs/99-archive/audit/00-audit-baseline-2026-02-23.md",
        "docs/99-archive/audit/02-test-baseline-2026-02-23.md",
        "docs/audit-bolt-branches-merge-plan.md",
        "docs/codex-setup.md",
    }
)


@dataclass(frozen=True)
class Resolution:
    """Manifest path resolution result."""

    original: str
    resolved: str | None
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate docs export artifacts from a manifest file."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the manifest file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the merged output file.",
    )
    parser.add_argument(
        "--rewrite-manifest",
        action="store_true",
        help="Overwrite manifest with normalized current paths.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if unresolved entries remain after legacy remapping.",
    )
    return parser.parse_args()


def load_manifest_entries(manifest_path: Path) -> list[str]:
    return [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_basename_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for path in DOCS_ROOT.rglob("*.md"):
        index[path.name].append(path.as_posix())
    for matches in index.values():
        matches.sort()
    return index


def to_repo_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def resolve_path(entry: str, basename_index: dict[str, list[str]]) -> Resolution:
    candidate = PROJECT_ROOT / entry
    if candidate.is_file():
        return Resolution(entry, entry, "direct")

    if entry in REMOVED_PATHS:
        return Resolution(entry, None, "removed")

    exact = EXACT_REPLACEMENTS.get(entry)
    if exact is not None and (PROJECT_ROOT / exact).is_file():
        return Resolution(entry, exact, "exact")

    for old_prefix, new_prefix in PREFIX_REPLACEMENTS:
        if entry.startswith(old_prefix):
            remapped = entry.replace(old_prefix, new_prefix, 1)
            if (PROJECT_ROOT / remapped).is_file():
                return Resolution(entry, remapped, "prefix")

    basename_matches = basename_index.get(Path(entry).name, [])
    if len(basename_matches) == 1:
        return Resolution(entry, to_repo_path(Path(basename_matches[0])), "basename")

    return Resolution(entry, None, "unresolved")


def normalize_manifest(
    entries: list[str], basename_index: dict[str, list[str]]
) -> tuple[list[str], list[Resolution]]:
    normalized: list[str] = []
    skipped: list[Resolution] = []
    seen: set[str] = set()

    for entry in entries:
        resolution = resolve_path(entry, basename_index)
        if resolution.resolved is None:
            skipped.append(resolution)
            continue
        if resolution.resolved in seen:
            continue
        normalized.append(resolution.resolved)
        seen.add(resolution.resolved)

    return normalized, skipped


def generate_export_content(resolved_paths: list[str]) -> str:
    today = date.today().isoformat()
    blocks = [
        "---",
        f'title: "{EXPORT_TITLE}"',
        f"date: {today}",
        "---",
        "",
        f"# {EXPORT_TITLE}",
        "",
        f"_Generated: {today}_",
        STATUS_LINE,
        "",
        r"\newpage",
        "",
    ]

    for repo_path in resolved_paths:
        full_path = PROJECT_ROOT / repo_path
        source_label = full_path.relative_to(DOCS_ROOT).as_posix()
        content = full_path.read_text(encoding="utf-8").rstrip()
        blocks.extend(
            [
                f"# Source: `{source_label}`",
                "",
                content,
                "",
            ]
        )

    return "\n".join(blocks) + "\n"


def write_manifest(manifest_path: Path, resolved_paths: list[str]) -> None:
    manifest_path.write_text(
        "\n".join(resolved_paths) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def print_summary(
    total_entries: int, resolved_paths: list[str], skipped: list[Resolution]
) -> None:
    reasons = Counter(item.reason for item in skipped)
    print(f"manifest_entries={total_entries}")
    print(f"resolved_entries={len(resolved_paths)}")
    print(f"skipped_entries={len(skipped)}")
    if reasons:
        print(
            "skip_breakdown="
            + ", ".join(f"{k}:{v}" for k, v in sorted(reasons.items()))
        )
    if skipped:
        print("skipped_paths:")
        for item in skipped:
            print(f"  - {item.reason}: {item.original}")


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    output_path = args.output.resolve()

    entries = load_manifest_entries(manifest_path)
    basename_index = build_basename_index()
    resolved_paths, skipped = normalize_manifest(entries, basename_index)

    unresolved = [item for item in skipped if item.reason == "unresolved"]
    if args.check and unresolved:
        print_summary(len(entries), resolved_paths, skipped)
        return 1

    if args.rewrite_manifest:
        write_manifest(manifest_path, resolved_paths)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        generate_export_content(resolved_paths),
        encoding="utf-8",
        newline="\n",
    )

    print_summary(len(entries), resolved_paths, skipped)
    print(f"manifest_path={manifest_path}")
    print(f"output_path={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
