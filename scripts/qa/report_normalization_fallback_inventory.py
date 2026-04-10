#!/usr/bin/env python3
"""Generate a report-only inventory of fields still using fallback normalization."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    FALLBACK_BUSINESS,
    FALLBACK_TECHNICAL_PASSTHROUGH,
    build_field_matrix_rows,
)

FALLBACK_SOURCES = {
    FALLBACK_BUSINESS,
    FALLBACK_TECHNICAL_PASSTHROUGH,
}


def _fallback_rows() -> list[dict[str, str]]:
    rows = build_field_matrix_rows()
    return sorted(
        (row for row in rows if row["normalization_source"] in FALLBACK_SOURCES),
        key=lambda row: (
            row["normalization_source"],
            row["pipeline_name"],
            row["field_name"],
            row["normalizer"],
        ),
    )


def _build_payload(rows: list[dict[str, str]]) -> dict[str, object]:
    per_pipeline = Counter(row["pipeline_name"] for row in rows)
    per_normalizer = Counter(row["normalizer"] for row in rows)
    per_source = Counter(row["normalization_source"] for row in rows)
    return {
        "mode": "report-only",
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
            {"pipeline_name": pipeline_name, "fallback_field_count": count}
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
    return _build_payload(_fallback_rows())


def _render_markdown(payload: dict[str, object], *, limit: int) -> str:
    fallback_field_count = int(payload["fallback_field_count"])
    pipelines = payload["pipelines"]
    normalizers = payload["normalizers"]
    entries = payload["entries"]

    lines = [
        "# Normalization Fallback Inventory",
        "",
        "- mode: report-only",
        f"- fallback_field_count: `{fallback_field_count}`",
        f"- fallback_business_field_count: `{payload['fallback_business_field_count']}`",
        f"- fallback_technical_passthrough_field_count: `{payload['fallback_technical_passthrough_field_count']}`",
        f"- pipelines_with_fallback_count: `{payload['pipelines_with_fallback_count']}`",
        "",
    ]

    if fallback_field_count == 0:
        lines.append("All pipeline fields are covered by explicit normalization contracts.")
        return "\n".join(lines)

    lines.extend(["## Fallback Categories", ""])
    for item in list(payload["sources"])[:limit]:
        lines.append(
            f"- `{item['normalization_source']}` covers `{item['field_count']}` fields"
        )

    lines.extend(["## Top Pipelines", ""])
    for item in list(pipelines)[:limit]:
        lines.append(
            f"- `{item['pipeline_name']}` has `{item['fallback_field_count']}` fallback fields"
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


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
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
        actual = int(payload["fallback_business_field_count"])
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
