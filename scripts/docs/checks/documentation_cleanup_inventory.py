#!/usr/bin/env python3
"""Generate/check the documentation cleanup inventory.

The inventory is intentionally deterministic: it is derived from tracked files,
local markdown links, exact normalized duplicate groups, and the generated
artifact routing registry. It does not use wall-clock time.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is present in project envs.
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON = (
    PROJECT_ROOT / "docs/reports/generated/documentation-cleanup-inventory.json"
)
DEFAULT_MD = PROJECT_ROOT / "docs/reports/generated/documentation-cleanup-inventory.md"
ROUTING_CONFIG = PROJECT_ROOT / "configs/quality/generated_artifact_routing.yaml"

DOC_ROOTS = (
    "docs/",
    "reports/",
    "plans/",
    "reviews/",
    "audits/",
    "analyses/",
    "research/",
    "architecture/",
    "diagrams/",
)
ROOT_DOCS = {"README.md", "CHANGELOG.md", "mkdocs.yml", "AGENTS.md"}
DOC_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".mmd",
    ".mermaid",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}
TEXT_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".mmd",
    ".mermaid",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}
CANONICAL_FILES = {
    "README.md",
    "CHANGELOG.md",
    "mkdocs.yml",
    "AGENTS.md",
    "docs/00-project/NORMATIVE_SOURCES.md",
    "docs/00-project/RULES.md",
    "docs/01-requirements/REQUIREMENTS.md",
    "docs/00-project/glossary.md",
    "docs/00-project/00-map.md",
    "docs/00-project/architecture-index.md",
}
GENERATED_PATH_MARKERS = (
    "/generated/",
    "/bundles/",
    "/svg/",
    "/png/",
    "/descriptions/",
)
WORKING_PATH_PREFIXES = (
    "docs/plans/",
    "docs/reports/",
    "reports/",
    "plans/",
    "reviews/",
    "audits/",
    "analyses/",
    "research/",
)
WORKING_NAME_RE = re.compile(
    r"(^|/)(plan|audit|review|investigation|roadmap|migration|closeout|issue-pack|report)[-_]",
    re.IGNORECASE,
)
GENERATED_MARKER_RE = re.compile(
    r"generated|auto-generated|do not edit|do not modify|machine-generated|this file is generated",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class Route:
    route_id: str
    generator: str
    output_kind: str
    commit_policy: str
    outputs: tuple[str, ...]
    notes: str


def _repo_relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _run_git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.splitlines()


def _is_doc_like(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return path in ROOT_DOCS or (
        path.startswith(DOC_ROOTS) and suffix in DOC_EXTENSIONS
    )


def _read_text(path: str) -> str:
    full = PROJECT_ROOT / path
    if not full.exists() or full.stat().st_size > 3_000_000:
        return ""
    try:
        return full.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_owner(text: str) -> str | None:
    for line in text[:1500].splitlines():
        if line.startswith("Owner:"):
            return line.split(":", 1)[1].strip() or None
        if line.startswith("owner:"):
            return line.split(":", 1)[1].strip() or None
    return None


def _extract_declared_status(text: str) -> str | None:
    for line in text[:1500].splitlines():
        stripped = line.strip()
        if stripped.startswith("Status:"):
            return stripped.split(":", 1)[1].strip() or None
        if stripped.startswith("status:"):
            return stripped.split(":", 1)[1].strip() or None
        if stripped.startswith("*Status:"):
            return stripped.strip("*").split(":", 1)[1].strip() or None
    return None


def _load_routes() -> list[Route]:
    if yaml is None or not ROUTING_CONFIG.exists():
        return []
    raw = yaml.safe_load(ROUTING_CONFIG.read_text(encoding="utf-8")) or {}
    routes: list[Route] = []
    for item in raw.get("routes", []):
        routes.append(
            Route(
                route_id=str(item.get("id", "")),
                generator=str(item.get("generator", "")),
                output_kind=str(item.get("output_kind", "")),
                commit_policy=str(item.get("commit_policy", "")),
                outputs=tuple(str(output) for output in item.get("outputs", [])),
                notes=str(item.get("notes", "")),
            )
        )
    return routes


def _matches_output(path: str, output: str) -> bool:
    if output.endswith("/"):
        return path.startswith(output)
    if "*" in output:
        pattern = "^" + re.escape(output).replace(r"\*", ".*") + "$"
        return re.match(pattern, path) is not None
    return path == output


def _route_for(path: str, routes: list[Route]) -> Route | None:
    for route in routes:
        if any(_matches_output(path, output) for output in route.outputs):
            return route
    return None


def _outgoing_links(text: str) -> list[str]:
    links: list[str] = []
    for match in LINK_RE.finditer(text):
        raw = match.group(2).strip()
        if not raw or raw.startswith(
            ("#", "http://", "https://", "mailto:", "tel:", "app://")
        ):
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw):
            continue
        target = raw.split()[0].split("#", 1)[0]
        if not target:
            continue
        links.append(urllib.parse.unquote(target))
    return links


def _resolve_link(path: str, target: str) -> str | None:
    line_ref_match = re.match(
        r"(.+\.(?:md|py|yaml|yml|json|csv|toml|txt|mmd|mermaid)):\d+$",
        target,
    )
    if line_ref_match:
        target = line_ref_match.group(1)
    candidate = Path(target)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / path).parent / candidate
    try:
        resolved = candidate.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    return resolved.as_posix()


def _duplicate_groups(texts: dict[str, str]) -> dict[str, int]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path, text in texts.items():
        if not text:
            continue
        normalized = "\n".join(
            line.rstrip() for line in text.replace("\r\n", "\n").split("\n")
        ).strip()
        if not normalized:
            continue
        by_hash[sha256(normalized.encode("utf-8")).hexdigest()].append(path)
    groups: dict[str, int] = {}
    group_id = 1
    for members in sorted(
        (sorted(paths) for paths in by_hash.values() if len(paths) > 1),
        key=lambda paths: (paths[0], len(paths)),
    ):
        for path in members:
            groups[path] = group_id
        group_id += 1
    return groups


def _diagram_kind(path: str) -> str | None:
    if not path.startswith("docs/02-architecture/diagrams/"):
        return None
    if path.endswith(".mmd"):
        if "/class-diagrams/90-pkg-" in path:
            return "diagram_generated_source"
        if (
            "/architecture/" in path
            or "/class-diagrams/" in path
            or "/foundation/" in path
        ):
            return "diagram_canonical_source"
    if path.endswith(".mermaid") and "/views/" in path:
        return "diagram_decomposed_view"
    if "/svg/" in path or "/png/" in path:
        return "diagram_render_artifact"
    if "/bundles/" in path:
        return "diagram_bundle"
    if "/descriptions/" in path:
        return "diagram_description"
    if "/governance/" in path or path.endswith("/diagrams/README.md"):
        return "diagram_governance"
    if "/manifests/" in path or "/tooling/" in path:
        return "diagram_tooling"
    return "diagram_support"


def _classify(
    path: str,
    text: str,
    duplicate_group: int | None,
    route: Route | None,
) -> tuple[str, str, str]:
    declared = (_extract_declared_status(text) or "").lower()
    diagram_kind = _diagram_kind(path)
    generated_marker = GENERATED_MARKER_RE.search(text[:2500] or "") is not None

    if path in CANONICAL_FILES or path.startswith("docs/02-architecture/decisions/"):
        return "Canonical", "current", "keep"
    if path.startswith("docs/99-archive/"):
        return "Archived", "historical", "keep"
    if path == "docs/00-project/DOCUMENTATION_GOVERNANCE.md":
        return "Duplicate", "migration-required", "replace-with-link"
    if "obsolete duplicate" in text[:1000].lower() or declared == "retired":
        return "Deprecated", "migration-required", "replace-with-link"
    if (
        route
        or generated_marker
        or any(marker in path for marker in GENERATED_PATH_MARKERS)
    ):
        return "Generated", "regenerate", "generate-automatically"
    if duplicate_group and not path.startswith(
        ("docs/99-archive/", "reports/quality/")
    ):
        return "Duplicate", "migration-required", "merge"
    if diagram_kind and diagram_kind.startswith("diagram_"):
        if diagram_kind in {
            "diagram_canonical_source",
            "diagram_governance",
            "diagram_tooling",
        }:
            return "Active", "current", "keep"
        return "Generated", "regenerate", "generate-automatically"
    if path.startswith(WORKING_PATH_PREFIXES) or WORKING_NAME_RE.search(path):
        return "Working", "review-required", "archive-after-migration"
    if path.startswith("docs/") or path in ROOT_DOCS:
        return "Active", "current", "keep"
    return "Unknown", "review-required", "inventory-review"


def _build_inventory() -> dict[str, Any]:
    tracked = [path for path in _run_git_ls_files() if _is_doc_like(path)]
    texts = {
        path: _read_text(path)
        for path in tracked
        if Path(path).suffix.lower() in TEXT_EXTENSIONS
    }
    duplicate_groups = _duplicate_groups(texts)
    routes = _load_routes()
    incoming: Counter[str] = Counter()
    outgoing_counts: Counter[str] = Counter()

    for path, text in texts.items():
        outgoing = _outgoing_links(text)
        outgoing_counts[path] = len(outgoing)
        for target in outgoing:
            resolved = _resolve_link(path, target)
            if resolved:
                incoming[resolved] += 1

    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    duplicate_group_count = len(set(duplicate_groups.values()))

    for path in sorted(tracked):
        text = texts.get(path, "")
        route = _route_for(path, routes)
        duplicate_group = duplicate_groups.get(path)
        status, freshness, action = _classify(path, text, duplicate_group, route)
        status_counts[status] += 1
        action_counts[action] += 1
        section = (
            path.split("/")[1]
            if path.startswith("docs/") and "/" in path
            else path.split("/")[0]
        )
        section_counts[section] += 1
        records.append(
            {
                "path": path,
                "extension": Path(path).suffix.lower() or "(none)",
                "section": section,
                "owner": _extract_owner(text) or "BioETL Team",
                "declared_status": _extract_declared_status(text),
                "status": status,
                "freshness": freshness,
                "inbound_links": int(incoming[path]),
                "outbound_links": int(outgoing_counts[path]),
                "duplicate_group": duplicate_group,
                "diagram_kind": _diagram_kind(path),
                "generated_route": route.route_id if route else None,
                "generator": route.generator if route else None,
                "commit_policy": route.commit_policy if route else None,
                "recommended_action": action,
            }
        )

    routes_payload = [
        {
            "id": route.route_id,
            "generator": route.generator,
            "output_kind": route.output_kind,
            "commit_policy": route.commit_policy,
            "outputs": list(route.outputs),
            "notes": route.notes,
        }
        for route in sorted(routes, key=lambda item: item.route_id)
    ]

    return {
        "schema_version": 1,
        "generator": "python -m scripts.docs generate-cleanup-inventory --update",
        "check_command": "python -m scripts.docs generate-cleanup-inventory --check",
        "source_inputs": [
            "git ls-files",
            "configs/quality/generated_artifact_routing.yaml",
            "local markdown links",
        ],
        "summary": {
            "total_doc_like_tracked": len(records),
            "by_status": dict(sorted(status_counts.items())),
            "by_recommended_action": dict(sorted(action_counts.items())),
            "by_section": dict(sorted(section_counts.items())),
            "duplicate_group_count": duplicate_group_count,
            "generated_route_count": len(routes_payload),
        },
        "generated_routes": routes_payload,
        "files": records,
    }


def _md_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return output


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    files = payload["files"]
    generated_routes = payload["generated_routes"]

    lines: list[str] = [
        "# Documentation Cleanup Inventory",
        "",
        "> Generated by `python -m scripts.docs generate-cleanup-inventory --update`.",
        "> Do not edit this file manually; update the generator or routing registry instead.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(
        _md_table(
            ["Metric", "Value"],
            [
                ["Tracked doc-like files", summary["total_doc_like_tracked"]],
                ["Duplicate groups", summary["duplicate_group_count"]],
                ["Generated routes", summary["generated_route_count"]],
            ],
        )
    )
    lines.extend(["", "## Status Counts", ""])
    lines.extend(
        _md_table(
            ["Status", "Count"],
            [[key, value] for key, value in summary["by_status"].items()],
        )
    )
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(
        _md_table(
            ["Action", "Count"],
            [[key, value] for key, value in summary["by_recommended_action"].items()],
        )
    )

    high_signal = [
        row
        for row in files
        if row["status"] in {"Duplicate", "Deprecated", "Unknown"}
        or row["recommended_action"] in {"archive-after-migration", "inventory-review"}
    ][:80]
    lines.extend(["", "## Cleanup Candidates", ""])
    lines.extend(
        _md_table(
            ["Path", "Status", "Inbound", "Action"],
            [
                [
                    f"`{row['path']}`",
                    row["status"],
                    row["inbound_links"],
                    row["recommended_action"],
                ]
                for row in high_signal
            ],
        )
    )

    generated_examples = [
        row
        for row in files
        if row["status"] == "Generated"
        and (row["generated_route"] or row["diagram_kind"])
    ][:80]
    lines.extend(["", "## Generated Artifact Examples", ""])
    lines.extend(
        _md_table(
            ["Path", "Route", "Kind", "Generator"],
            [
                [
                    f"`{row['path']}`",
                    row["generated_route"] or "",
                    row["diagram_kind"] or "",
                    row["generator"] or "",
                ]
                for row in generated_examples
            ],
        )
    )

    lines.extend(["", "## Generated Route Registry", ""])
    lines.extend(
        _md_table(
            ["Route", "Generator", "Commit Policy"],
            [
                [route["id"], f"`{route['generator']}`", route["commit_policy"]]
                for route in generated_routes[:80]
            ],
        )
    )

    lines.extend(
        [
            "",
            "## Verification",
            "",
            "- `python -m scripts.docs generate-cleanup-inventory --check`",
            "- `python -m scripts.docs check-links --links --specs --configs`",
            "- `python -m scripts.docs check-drift --runtime-mirrors --freshness`",
            "",
            "The JSON sibling contains the complete per-file matrix.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--update", action="store_true", help="Regenerate inventory files."
    )
    mode.add_argument(
        "--check", action="store_true", help="Check generated inventory drift."
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--print-summary", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = _build_inventory()
    json_content = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    md_content = _render_markdown(payload)

    if args.print_summary:
        print(
            json.dumps(payload["summary"], ensure_ascii=False, indent=2, sort_keys=True)
        )

    if args.check:
        mismatches = []
        for path, content in (
            (args.json_output, json_content),
            (args.markdown_output, md_content),
        ):
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                mismatches.append(_repo_relative(path))
        if mismatches:
            for mismatch in mismatches:
                print(f"[drift] mismatch: {mismatch}")
            print(
                "[hint] run: python -m scripts.docs generate-cleanup-inventory --update"
            )
            return 1
        print("[documentation-cleanup-inventory] inventory is synchronized")
        return 0

    if args.update or not args.check:
        changed = [
            _write_if_changed(args.json_output, json_content),
            _write_if_changed(args.markdown_output, md_content),
        ]
        if any(changed):
            print("[documentation-cleanup-inventory] inventory updated")
        else:
            print("[documentation-cleanup-inventory] inventory already synchronized")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
