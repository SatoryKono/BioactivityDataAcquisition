#!/usr/bin/env python3
"""Generate a deterministic observed-value inventory from tracked ChEMBL Bronze fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "reports" / "generated"
DEFAULT_JSON_OUT = DEFAULT_OUT_DIR / "chembl_observed_value_inventory.json"
DEFAULT_CSV_OUT = DEFAULT_OUT_DIR / "chembl_observed_value_inventory.csv"
DEFAULT_MD_OUT = DEFAULT_OUT_DIR / "chembl_observed_value_inventory.md"


@dataclass(frozen=True, slots=True)
class FixtureSummaryRow:
    pipeline_name: str
    fixture_key: str
    field_name: str
    non_null_count: int
    null_count: int
    distinct_count: int
    observed_examples: tuple[str, ...]
    fixture_path: str

    def as_csv_row(self) -> dict[str, object]:
        return {
            "pipeline_name": self.pipeline_name,
            "fixture_key": self.fixture_key,
            "field_name": self.field_name,
            "non_null_count": self.non_null_count,
            "null_count": self.null_count,
            "distinct_count": self.distinct_count,
            "observed_examples": " | ".join(self.observed_examples),
            "fixture_path": self.fixture_path,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} must decode to a mapping"
    return payload


def _chembl_fixture_entries() -> list[tuple[str, dict[str, Any]]]:
    fixtures = _load_yaml(MANIFEST_PATH).get("fixtures", {})
    assert isinstance(fixtures, dict)
    return sorted(
        (
            (fixture_key, entry)
            for fixture_key, entry in fixtures.items()
            if isinstance(fixture_key, str)
            and fixture_key.startswith("chembl/")
            and isinstance(entry, dict)
            and entry.get("fixture_kind") == "tracked_ci_sample"
        ),
        key=lambda item: item[0],
    )


def _tracked_fixture_paths(fixture_key: str, entry: dict[str, Any]) -> tuple[str, ...]:
    fixture_path_raw = entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str), f"{fixture_key}: fixture_path missing"
    tracked_paths = [fixture_path_raw]

    edge_fixtures = entry.get("edge_fixtures", [])
    assert isinstance(edge_fixtures, list), f"{fixture_key}: edge_fixtures must be a list"
    for edge_entry in edge_fixtures:
        if not isinstance(edge_entry, dict):
            continue
        if edge_entry.get("fixture_kind") != "tracked_edge_case_sample":
            continue
        edge_path = edge_entry.get("fixture_path")
        assert isinstance(edge_path, str), f"{fixture_key}: edge fixture path missing"
        tracked_paths.append(edge_path)

    return tuple(dict.fromkeys(tracked_paths))


def _canonical_example(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            assert isinstance(payload, dict), f"{path} rows must be JSON objects"
            rows.append(payload)
    return rows


def _pipeline_name_from_fixture_key(fixture_key: str) -> str:
    provider, entity = fixture_key.split("/", maxsplit=1)
    return f"{provider}_{entity}"


def _summarize_fixture(
    fixture_key: str,
    entry: dict[str, Any],
    *,
    max_examples: int,
) -> list[FixtureSummaryRow]:
    tracked_paths = _tracked_fixture_paths(fixture_key, entry)
    rows: list[dict[str, Any]] = []
    for fixture_path_raw in tracked_paths:
        rows.extend(_load_jsonl(PROJECT_ROOT / fixture_path_raw))

    field_values: dict[str, set[str]] = defaultdict(set)
    non_null_counts: dict[str, int] = defaultdict(int)
    null_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        for field_name, value in row.items():
            if value is None:
                null_counts[field_name] += 1
                continue
            non_null_counts[field_name] += 1
            field_values[field_name].add(_canonical_example(value))

    pipeline_name = _pipeline_name_from_fixture_key(fixture_key)
    summaries: list[FixtureSummaryRow] = []
    for field_name in sorted(set(non_null_counts) | set(null_counts) | set(field_values)):
        examples = tuple(sorted(field_values.get(field_name, set()))[:max_examples])
        summaries.append(
            FixtureSummaryRow(
                pipeline_name=pipeline_name,
                fixture_key=fixture_key,
                field_name=field_name,
                non_null_count=non_null_counts.get(field_name, 0),
                null_count=null_counts.get(field_name, 0),
                distinct_count=len(field_values.get(field_name, set())),
                observed_examples=examples,
                fixture_path=" | ".join(tracked_paths),
            )
        )
    return summaries


def build_inventory_payload(*, max_examples: int = 5) -> dict[str, object]:
    fixture_payloads: list[dict[str, object]] = []
    all_rows: list[FixtureSummaryRow] = []
    for fixture_key, entry in _chembl_fixture_entries():
        summaries = _summarize_fixture(fixture_key, entry, max_examples=max_examples)
        all_rows.extend(summaries)
        fixture_payloads.append(
            {
                "fixture_key": fixture_key,
                "pipeline_name": _pipeline_name_from_fixture_key(fixture_key),
                "fixture_path": entry["fixture_path"],
                "tracked_fixture_paths": list(_tracked_fixture_paths(fixture_key, entry)),
                "tracked_fixture_count": len(_tracked_fixture_paths(fixture_key, entry)),
                "records": entry["records"],
                "field_count": len(summaries),
            }
        )

    return {
        "source": "tracked_chembl_bronze_fixtures",
        "manifest_path": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "fixtures_count": len(fixture_payloads),
        "field_rows_count": len(all_rows),
        "fixtures": fixture_payloads,
        "rows": [
            {
                "pipeline_name": row.pipeline_name,
                "fixture_key": row.fixture_key,
                "field_name": row.field_name,
                "non_null_count": row.non_null_count,
                "null_count": row.null_count,
                "distinct_count": row.distinct_count,
                "observed_examples": list(row.observed_examples),
                "fixture_path": row.fixture_path,
            }
            for row in all_rows
        ],
    }


def _render_markdown(payload: dict[str, object], *, limit: int) -> str:
    fixtures = payload["fixtures"]
    rows = payload["rows"]
    assert isinstance(fixtures, list)
    assert isinstance(rows, list)

    lines = [
        "# ChEMBL Bronze Observed Value Inventory",
        "",
        f"- source: `{payload['source']}`",
        f"- manifest_path: `{payload['manifest_path']}`",
        f"- fixtures_count: `{payload['fixtures_count']}`",
        f"- field_rows_count: `{payload['field_rows_count']}`",
        "",
        "## Fixture Summary",
        "",
    ]
    for fixture in fixtures:
        assert isinstance(fixture, dict)
        lines.append(
            f"- `{fixture['pipeline_name']}` -> `{fixture['field_count']}` fields from `{fixture['fixture_path']}`"
        )

    lines.extend(["", "## Sample Field Rows", ""])
    for row in rows[:limit]:
        assert isinstance(row, dict)
        lines.append(
            f"- `{row['pipeline_name']}.{row['field_name']}` distinct=`{row['distinct_count']}` "
            f"non_null=`{row['non_null_count']}` examples=`{', '.join(row['observed_examples'])}`"
        )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _render_csv(rows: list[dict[str, object]]) -> str:
    buffer = StringIO(newline="")
    fieldnames = [
        "pipeline_name",
        "fixture_key",
        "field_name",
        "non_null_count",
        "null_count",
        "distinct_count",
        "observed_examples",
        "fixture_path",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_csv(rows), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-examples", type=int, default=5)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the current outputs already match the generated payload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    payload = build_inventory_payload(max_examples=args.max_examples)
    markdown = _render_markdown(payload, limit=args.limit) + "\n"
    csv_rows = [
        FixtureSummaryRow(
            pipeline_name=str(row["pipeline_name"]),
            fixture_key=str(row["fixture_key"]),
            field_name=str(row["field_name"]),
            non_null_count=int(row["non_null_count"]),
            null_count=int(row["null_count"]),
            distinct_count=int(row["distinct_count"]),
            observed_examples=tuple(str(value) for value in row["observed_examples"]),
            fixture_path=str(row["fixture_path"]),
        ).as_csv_row()
        for row in payload["rows"]
        if isinstance(row, dict)
    ]
    rendered_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if args.check:
        current_json = args.json_out.read_text(encoding="utf-8") if args.json_out.exists() else ""
        current_md = args.markdown_out.read_text(encoding="utf-8") if args.markdown_out.exists() else ""
        current_csv = args.csv_out.read_text(encoding="utf-8") if args.csv_out.exists() else ""
        rendered_csv = _render_csv(csv_rows)

        if current_json != rendered_json or current_md != markdown or current_csv != rendered_csv:
            print("ChEMBL observed value inventory is stale. Re-run the report generator.", file=sys.stderr)
            return 1
        return 0

    _write_json(args.json_out, payload)
    _write_csv(args.csv_out, csv_rows)
    _write_text(args.markdown_out, markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
