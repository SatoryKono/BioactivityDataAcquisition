#!/usr/bin/env python3
"""Generate a report-only inventory of fields still using fallback normalization."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

# Keep these import-light so router-level ``--help`` does not load the matrix
# generator and its runtime dependencies before argparse can exit.
FALLBACK_BUSINESS = "fallback_business"
FALLBACK_TECHNICAL_PASSTHROUGH = "fallback_technical_passthrough"
FALLBACK_SOURCES = {
    FALLBACK_BUSINESS,
    FALLBACK_TECHNICAL_PASSTHROUGH,
}


def _build_help_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of rows to render per Markdown section (default: 20)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for machine-readable JSON output",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional path for Markdown output",
    )
    parser.add_argument(
        "--max-fallback-business-fields",
        type=int,
        default=None,
        help=(
            "Optional ratchet threshold. Exit non-zero when "
            "fallback_business_field_count exceeds this value."
        ),
    )
    return parser


def _maybe_exit_help_only_cli() -> None:
    """Short-circuit CLI help before importing heavy matrix-generation code."""
    if __name__ != "__main__":
        return
    if not any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        return
    _build_help_arg_parser().parse_args()


_maybe_exit_help_only_cli()

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))


def _fallback_rows() -> list[dict[str, str]]:
    from scripts.docs.matrix import generate_pipeline_normalization_matrix as matrix

    rows = matrix.build_field_matrix_rows()
    return sorted(
        (row for row in rows if row["normalization_source"] in FALLBACK_SOURCES),
        key=lambda row: (
            row["normalization_source"],
            row["pipeline_name"],
            row["field_name"],
            row["normalizer"],
        ),
    )


def _build_payload(
    rows: list[dict[str, str]],
    *,
    coverage_kpi: dict[str, object] | None = None,
    surface_kpis: list[dict[str, object]] | None = None,
    semantic_invariants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    per_pipeline = Counter(row["pipeline_name"] for row in rows)
    per_pipeline_source = Counter(
        (row["pipeline_name"], row["normalization_source"]) for row in rows
    )
    per_normalizer = Counter(row["normalizer"] for row in rows)
    per_source = Counter(row["normalization_source"] for row in rows)
    return {
        "mode": "report-only",
        "scope": "entity_record_fallback_only",
        "coverage_kpi": coverage_kpi or {},
        "surface_kpis": surface_kpis or [],
        "semantic_invariants": semantic_invariants or [],
        "fallback_field_count": len(rows),
        "fallback_business_field_count": per_source[FALLBACK_BUSINESS],
        "fallback_technical_passthrough_field_count": per_source[
            FALLBACK_TECHNICAL_PASSTHROUGH
        ],
        "pipelines_with_fallback_count": len(per_pipeline),
        "sources": [
            {"normalization_source": source, "field_count": count}
            for source, count in sorted(
                per_source.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "pipelines": [
            {
                "pipeline_name": pipeline_name,
                "fallback_field_count": count,
                "fallback_business_field_count": per_pipeline_source[
                    (pipeline_name, FALLBACK_BUSINESS)
                ],
                "fallback_technical_passthrough_field_count": per_pipeline_source[
                    (pipeline_name, FALLBACK_TECHNICAL_PASSTHROUGH)
                ],
            }
            for pipeline_name, count in sorted(
                per_pipeline.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "normalizers": [
            {"normalizer": normalizer, "field_count": count}
            for normalizer, count in sorted(
                per_normalizer.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "entries": rows,
    }


def build_fallback_inventory_payload() -> dict[str, object]:
    """Return the current fallback normalization inventory payload."""
    from scripts.docs.matrix import generate_pipeline_normalization_matrix as matrix

    all_rows = matrix.build_field_matrix_rows()
    fallback_rows = [
        row for row in all_rows if row["normalization_source"] in FALLBACK_SOURCES
    ]
    return _build_payload(
        fallback_rows,
        coverage_kpi=matrix.build_entity_profile_coverage_kpi(all_rows),
        surface_kpis=matrix.build_surface_coverage_kpis(all_rows),
        semantic_invariants=matrix.build_profile_semantic_invariants(),
    )


def _render_markdown(payload: dict[str, object], *, limit: int) -> str:
    fallback_field_count = int(cast(int, payload["fallback_field_count"]))
    pipelines = cast(list[dict[str, object]], payload["pipelines"])
    normalizers = cast(list[dict[str, object]], payload["normalizers"])
    entries = cast(list[dict[str, object]], payload["entries"])

    lines = [
        "# Normalization Fallback Inventory",
        "",
        "- mode: report-only",
        "- scope: `entity_record_fallback_only`",
        (
            "- scope_note: Fallback inventory tracks only entity-record fallback "
            "normalization debt. Composite join-key and control-plane surfaces are "
            "reported separately in the matrix surface coverage summary."
        ),
        "",
        "## Surface Coverage Context",
        "",
    ]
    surface_kpis = cast(list[dict[str, Any]], payload.get("surface_kpis", []))
    if not surface_kpis and payload.get("coverage_kpi"):
        surface_kpis = [cast(dict[str, Any], payload["coverage_kpi"])]
    for kpi in surface_kpis:
        lines.append(
            f"- {kpi.get('surface', 'entity_record')} / {kpi.get('name', 'coverage_kpi')}: "
            f"`{float(kpi.get('value_pct', 0.0)):.2f}%` "
            f"(`{kpi.get('numerator', 0)}` / `{kpi.get('denominator', 0)}`) "
            f"{kpi.get('description', '')}".rstrip()
        )
    semantic_invariants = cast(
        list[dict[str, Any]], payload.get("semantic_invariants", [])
    )
    if semantic_invariants:
        lines.extend(["", "## Semantic Invariant Context", ""])
        for kpi in semantic_invariants:
            regressions = cast(list[str], kpi.get("regressions", []))
            regression_note = (
                f" Regressions: {', '.join(regressions)}." if regressions else ""
            )
            lines.append(
                f"- {kpi.get('surface', 'profile_semantics')} / {kpi.get('name', 'semantic_kpi')}: "
                f"`{float(kpi.get('value_pct', 0.0)):.2f}%` "
                f"(`{kpi.get('numerator', 0)}` / `{kpi.get('denominator', 0)}`) "
                f"{kpi.get('description', '')}".rstrip()
                + regression_note
            )
    lines.extend(
        [
            "",
            "## Entity Fallback Summary",
            "",
            f"- fallback_field_count: `{fallback_field_count}`",
            f"- fallback_business_field_count: `{payload['fallback_business_field_count']}`",
            f"- fallback_technical_passthrough_field_count: `{payload['fallback_technical_passthrough_field_count']}`",
            f"- pipelines_with_fallback_count: `{payload['pipelines_with_fallback_count']}`",
            "",
        ]
    )

    if fallback_field_count == 0:
        lines.append(
            "All entity-record fields are covered by explicit normalization contracts."
        )
        return "\n".join(lines)

    lines.extend(["## Fallback Categories", ""])
    for item in cast(list[dict[str, object]], payload["sources"])[:limit]:
        lines.append(
            f"- `{item['normalization_source']}` covers `{item['field_count']}` fields"
        )

    lines.extend(["## Top Pipelines", ""])
    for item in list(pipelines)[:limit]:
        lines.append(
            f"- `{item['pipeline_name']}` has `{item['fallback_field_count']}` fallback fields "
            f"(`fallback_business={item['fallback_business_field_count']}`, "
            f"`fallback_technical_passthrough={item['fallback_technical_passthrough_field_count']}`)"
        )

    lines.extend(["", "## Top Normalizers", ""])
    for item in list(normalizers)[:limit]:
        lines.append(f"- `{item['normalizer']}` covers `{item['field_count']}` fields")

    lines.extend(["", "## Sample Entries", ""])
    for row in list(entries)[:limit]:
        lines.append(
            f"- `{row['pipeline_name']}.{row['field_name']}` -> `{row['normalizer']}` "
            f"(`{row['normalization_source']}`)"
        )

    return "\n".join(lines)


def _write_text(path: Path, content: str, *, root: Path | None = None) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    return _build_help_arg_parser()


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    payload = build_fallback_inventory_payload()
    markdown = _render_markdown(payload, limit=args.limit)

    if args.json_out is not None:
        _write_text(args.json_out, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown_out is not None:
        _write_text(args.markdown_out, markdown + "\n")

    print(markdown)
    if args.max_fallback_business_fields is not None:
        actual = int(cast(int, payload["fallback_business_field_count"]))
        budget = args.max_fallback_business_fields
        if actual > budget:
            print(
                (
                    "fallback_business_field_count exceeds ratchet budget: "
                    f"{actual} > {budget}"
                ),
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
