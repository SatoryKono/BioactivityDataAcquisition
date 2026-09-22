#!/usr/bin/env python3
"""``cast(Any, ...)`` typing census for ``src/bioetl`` (AUD-006 / #10596).

Every ``cast(Any`` call site is classified as ``justified`` when its bounded
statement window (the matching line plus the two following lines, mirroring
``tests/architecture/test_any_budget.py`` handling of Ruff-split casts) carries
one of the reviewed justification markers:

* ``PD3`` / ``PD6`` host-attribute-default markers,
* ``TYPE-002`` policy references,
* ``Any: mixin host`` / ``Any: host attr`` / ``Any: JSON`` reason tags,
* or the call is routed through ``as_mixin_host(``.

Everything else is ``unjustified`` for the purposes of this census, even when
it carries a free-form ``# Any: <reason>`` comment (those reasons are still
surfaced in ``unjustified_reason_tags`` so they can be triaged into reviewed
categories or replaced with Protocol host surfaces).

The report is deterministic (sorted by path then line, no timestamps) and is
written atomically (temp file -> ``os.replace``).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

__all__ = [
    "DEFAULT_JSON",
    "DEFAULT_MD",
    "JUSTIFICATION_CATEGORIES",
    "build_cast_any_census",
    "classify_statement_window",
    "render_markdown",
    "scan_cast_any_findings",
]

SCHEMA_VERSION = "cast-any-typing-census-v1"
LINKED_ISSUE = "#10596"
DEFAULT_SRC_ROOT = Path("src/bioetl")
DEFAULT_JSON = Path("reports/quality/cast-any-typing-census.json")
DEFAULT_MD = Path("reports/quality/cast-any-typing-census.md")

# Ordered so the first matching category wins; keeps classification stable.
JUSTIFICATION_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("pd3_host_attr_default", "PD3"),
    ("pd6_host_attr_default", "PD6"),
    ("type_002_policy", "TYPE-002"),
    ("any_mixin_host", "Any: mixin host"),
    ("any_host_attr", "Any: host attr"),
    ("any_json", "Any: JSON"),
)
AS_MIXIN_HOST_CATEGORY = "as_mixin_host_call"
UNJUSTIFIED_CATEGORY = "unjustified"
STATEMENT_WINDOW_LINES = 3

_CAST_ANY_RE = re.compile(r"\bcast\(\s*Any\b")
_AS_MIXIN_HOST_RE = re.compile(r"\bas_mixin_host\(")
_REASON_TAG_RE = re.compile(r"#\s*Any:\s*(?P<reason>[^#\r\n]*)")
_PD4_HOST_DEFAULT_MARKER = "PD4"

# Sub-buckets inside ``unjustified`` used only for triage visibility.
UNJUSTIFIED_SUBCATEGORY_PD4 = "pd4_host_default_pending_protocol"
UNJUSTIFIED_SUBCATEGORY_FREE_FORM = "free_form_reason"
UNJUSTIFIED_SUBCATEGORY_NONE = "no_reason_tag"


def _layer_for(rel_path: str) -> str:
    parts = rel_path.split("/")
    # src/bioetl/<layer>/...
    if len(parts) >= 3 and parts[0] == "src" and parts[1] == "bioetl":
        return parts[2] if len(parts) > 3 else "bioetl_root"
    return parts[0] if parts else "unknown"


def classify_statement_window(window: str) -> str:
    """Return the census category for one bounded ``cast(Any`` statement window."""
    for category, marker in JUSTIFICATION_CATEGORIES:
        if marker in window:
            return category
    if _AS_MIXIN_HOST_RE.search(window):
        return AS_MIXIN_HOST_CATEGORY
    return UNJUSTIFIED_CATEGORY


def _reason_tag(window: str) -> str | None:
    match = _REASON_TAG_RE.search(window)
    if match is None:
        return None
    reason = match.group("reason").strip()
    return reason or None


def _unjustified_subcategory(window: str, reason_tag: str | None) -> str:
    if _PD4_HOST_DEFAULT_MARKER in window:
        return UNJUSTIFIED_SUBCATEGORY_PD4
    if reason_tag:
        return UNJUSTIFIED_SUBCATEGORY_FREE_FORM
    return UNJUSTIFIED_SUBCATEGORY_NONE


def _docstring_line_numbers(text: str) -> set[int]:
    """Return all line numbers covered by module/class/function docstrings."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    covered: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = first.end_lineno or first.lineno
            covered.update(range(first.lineno, end + 1))
    return covered


def _iter_source_files(src_root: Path) -> list[Path]:
    return sorted(
        path for path in src_root.rglob("*.py") if "__pycache__" not in path.parts
    )


def scan_cast_any_findings(
    repo_root: Path,
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
) -> list[dict[str, Any]]:
    """Scan ``src_root`` for ``cast(Any`` call sites and classify each one."""
    absolute_src_root = (repo_root / src_root).resolve()
    findings: list[dict[str, Any]] = []
    for path in _iter_source_files(absolute_src_root):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        rel_path = path.relative_to(repo_root).as_posix()
        docstring_lines = _docstring_line_numbers(text)
        seen_lines: set[int] = set()
        for match in _CAST_ANY_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            if lineno in seen_lines or lineno in docstring_lines:
                continue
            if lines[lineno - 1].lstrip().startswith("#"):
                continue
            seen_lines.add(lineno)
            window = "\n".join(lines[lineno - 1 : lineno - 1 + STATEMENT_WINDOW_LINES])
            category = classify_statement_window(window)
            reason_tag = _reason_tag(window)
            justified = category != UNJUSTIFIED_CATEGORY
            findings.append(
                {
                    "path": rel_path,
                    "line": lineno,
                    "layer": _layer_for(rel_path),
                    "category": category,
                    "justified": justified,
                    "unjustified_subcategory": (
                        None
                        if justified
                        else _unjustified_subcategory(window, reason_tag)
                    ),
                    "reason_tag": reason_tag,
                    "snippet": lines[lineno - 1].strip()[:120],
                }
            )
    findings.sort(key=lambda item: (str(item["path"]), int(item["line"])))
    return findings


def _top_files(findings: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    totals: Counter[str] = Counter()
    unjustified: Counter[str] = Counter()
    for item in findings:
        path = str(item["path"])
        totals[path] += 1
        if not item["justified"]:
            unjustified[path] += 1
    ordered = sorted(
        totals,
        key=lambda path: (-unjustified.get(path, 0), -totals[path], path),
    )
    return [
        {
            "path": path,
            "total": totals[path],
            "unjustified": unjustified.get(path, 0),
            "justified": totals[path] - unjustified.get(path, 0),
        }
        for path in ordered[:limit]
    ]


def build_cast_any_census(
    repo_root: Path,
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
    top_limit: int = 25,
) -> dict[str, Any]:
    """Build the deterministic census payload."""
    findings = scan_cast_any_findings(repo_root, src_root=src_root)
    by_category: Counter[str] = Counter(str(item["category"]) for item in findings)
    by_layer_total: Counter[str] = Counter(str(item["layer"]) for item in findings)
    by_layer_unjustified: Counter[str] = Counter(
        str(item["layer"]) for item in findings if not item["justified"]
    )
    reason_tags: Counter[str] = Counter(
        str(item["reason_tag"])
        for item in findings
        if not item["justified"] and item["reason_tag"]
    )
    unjustified_subcategories: Counter[str] = Counter(
        str(item["unjustified_subcategory"])
        for item in findings
        if not item["justified"]
    )
    justified_count = sum(1 for item in findings if item["justified"])
    unjustified_count = len(findings) - justified_count
    return {
        "schema_version": SCHEMA_VERSION,
        "linked_issue": LINKED_ISSUE,
        "policy": {
            "scope": src_root.as_posix(),
            "statement_window_lines": STATEMENT_WINDOW_LINES,
            "justified_markers": [marker for _, marker in JUSTIFICATION_CATEGORIES]
            + ["as_mixin_host("],
            "ratchet": "configs/quality/cast_any_unjustified_budget.yaml",
            "ratchet_policy": "shrink_only",
        },
        "summary": {
            "total_cast_any_count": len(findings),
            "justified_count": justified_count,
            "unjustified_count": unjustified_count,
            "by_category": {
                category: by_category.get(category, 0)
                for category in [name for name, _ in JUSTIFICATION_CATEGORIES]
                + [AS_MIXIN_HOST_CATEGORY, UNJUSTIFIED_CATEGORY]
            },
            "by_layer": {
                layer: {
                    "total": by_layer_total[layer],
                    "unjustified": by_layer_unjustified.get(layer, 0),
                }
                for layer in sorted(by_layer_total)
            },
            "unjustified_by_subcategory": {
                subcategory: unjustified_subcategories.get(subcategory, 0)
                for subcategory in (
                    UNJUSTIFIED_SUBCATEGORY_PD4,
                    UNJUSTIFIED_SUBCATEGORY_FREE_FORM,
                    UNJUSTIFIED_SUBCATEGORY_NONE,
                )
            },
            "file_count": len({str(item["path"]) for item in findings}),
        },
        "top_files": _top_files(findings, limit=top_limit),
        "unjustified_reason_tags": [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                reason_tags.items(), key=lambda pair: (-pair[1], pair[0])
            )
        ],
        "findings": findings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# cast(Any) typing census",
        "",
        f"Linked issue: {report['linked_issue']} (AUD-006). Schema: `{report['schema_version']}`.",
        "",
        "Justified markers: "
        + ", ".join(f"`{marker}`" for marker in report["policy"]["justified_markers"])
        + ".",
        "",
        f"- total_cast_any_count: {summary['total_cast_any_count']}",
        f"- justified_count: {summary['justified_count']}",
        f"- unjustified_count: {summary['unjustified_count']}",
        f"- file_count: {summary['file_count']}",
        "",
        "## By category",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in summary["by_category"].items():
        lines.append(f"| `{category}` | {count} |")
    lines += [
        "",
        "## By layer",
        "",
        "| Layer | Total | Unjustified |",
        "| --- | ---: | ---: |",
    ]
    for layer, counts in summary["by_layer"].items():
        lines.append(f"| `{layer}` | {counts['total']} | {counts['unjustified']} |")
    lines += [
        "",
        "## Unjustified by sub-bucket (triage only)",
        "",
        "| Sub-bucket | Count |",
        "| --- | ---: |",
    ]
    for subcategory, count in summary["unjustified_by_subcategory"].items():
        lines.append(f"| `{subcategory}` | {count} |")
    lines += [
        "",
        "## Top files",
        "",
        "| Path | Total | Justified | Unjustified |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in report["top_files"]:
        lines.append(
            f"| `{row['path']}` | {row['total']} | {row['justified']} | {row['unjustified']} |"
        )
    lines += [
        "",
        "## Unjustified free-form reason tags",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ]
    for row in report["unjustified_reason_tags"]:
        lines.append(f"| `{row['reason']}` | {row['count']} |")
    lines.append("")
    return "\n".join(lines)


def _write_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _serialize_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-root", type=Path, default=DEFAULT_SRC_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed JSON differs from the live census.",
    )
    args = parser.parse_args(argv)

    report = build_cast_any_census(REPO_ROOT, src_root=args.src_root)
    json_out = resolve_output_path(args.json_out, root=REPO_ROOT)
    md_out = resolve_output_path(args.md_out, root=REPO_ROOT)
    json_payload = _serialize_json(report)
    md_payload = render_markdown(report)

    if args.check:
        committed = json_out.read_text(encoding="utf-8") if json_out.exists() else ""
        committed_md = md_out.read_text(encoding="utf-8") if md_out.exists() else ""
        if committed != json_payload or committed_md != md_payload:
            print(
                f"cast(Any) census drift detected: rerun without --check ({json_out})"
            )
            return 1
        print("cast(Any) census in sync")
        return 0

    _write_atomic(json_out, json_payload)
    _write_atomic(md_out, md_payload)
    summary = report["summary"]
    print("Wrote", json_out)
    print("Wrote", md_out)
    print(
        "summary total=",
        summary["total_cast_any_count"],
        "justified=",
        summary["justified_count"],
        "unjustified=",
        summary["unjustified_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
