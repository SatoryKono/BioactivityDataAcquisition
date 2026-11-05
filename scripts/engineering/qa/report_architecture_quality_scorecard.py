#!/usr/bin/env python3
"""Regenerate architecture quality scorecard artifact."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC_ROOT))

from scripts.engineering.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)

# Titles under "Key Invariants" in docs/02-architecture/domain/aggregate-invariants.md.
# The registry binds a different, narrower invariant wording; these titles are the
# semantic-completeness set for issue #12715.
DOCUMENTED_KEY_INVARIANTS: dict[str, tuple[str, ...]] = {
    "Batch": (
        "Content Hash Immutability",
        "No Records After Sealed",
        "One-Way State Transitions",
        "Atomic Commit",
        "Write-Once",
    ),
    "PipelineRun": (
        "Immutable Manifest",
        "Append-Only Ledger",
        "Deterministic ID",
        "No State Reversion",
        "Provenance Preservation",
        "Stage Evidence",
    ),
    "QuarantineEntry": (
        "Immutable Root Cause",
        "Resolution Tracking",
        "One-Time Resolution",
        "Exclusion Rationale",
        "Audit Trail",
        "Reprocessing Requires New ID",
    ),
}
_GAP_SOURCE = "docs/02-architecture/domain/aggregate-invariants.md"
_GAP_STATUS = "no_direct_test_link"


def semantic_completeness_payload(
    aggregates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    """Return the registry status string and uncovered documented key invariants."""
    gaps: list[dict[str, str]] = []
    for row in aggregates:
        aggregate = str(row["aggregate"])
        linked = {
            str(item["invariant"]).casefold() for item in row["invariant_test_links"]
        }
        for name in DOCUMENTED_KEY_INVARIANTS[aggregate]:
            key = name.casefold()
            if key in linked:
                continue
            gaps.append(
                {
                    "aggregate": aggregate,
                    "documented_invariant": name,
                    "source": _GAP_SOURCE,
                    "status": _GAP_STATUS,
                }
            )
    if gaps:
        status = (
            "not_assessed; documented key invariants in "
            "semantic_completeness_gaps have no direct registry test link"
        )
    else:
        status = (
            "assessed; every documented key invariant has a direct registry test link"
        )
    return status, gaps


def _refresh_aggregate_test_links() -> None:
    """Bind selected invariant claims to existing executable test symbols."""
    path = PROJECT_ROOT / "reports/quality/domain-aggregate-invariant-registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = {
        "Batch": (1, "test_record_indices_follow_start_index_law"),
        "PipelineRun": (1, "test_success_only_stage_sequences_can_complete"),
        "QuarantineEntry": (0, "test_payload_and_metadata_accessors_are_defensive"),
    }
    for row in payload["aggregates"]:
        invariant_index, symbol = selected[row["aggregate"]]
        candidates = []
        for test_path in row["test_paths"]:
            tree = ast.parse((PROJECT_ROOT / test_path).read_text(encoding="utf-8"))
            if any(
                isinstance(node, ast.FunctionDef) and node.name == symbol
                for node in ast.walk(tree)
            ):
                candidates.append(test_path)
        if len(candidates) != 1:
            raise ValueError(f"Invariant test symbol must resolve uniquely: {symbol}")
        row["invariant_test_links"] = [
            {
                "invariant": row["invariants"][invariant_index],
                "test_path": candidates[0],
                "test_symbol": symbol,
            }
        ]
    status, gaps = semantic_completeness_payload(payload["aggregates"])
    payload["semantic_completeness"] = status
    payload["semantic_completeness_gaps"] = gaps
    payload["generated_by"] = (
        "scripts/engineering/qa/report_architecture_quality_scorecard.py"
    )
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    """Refresh aggregate evidence and write the architecture scorecard."""
    _refresh_aggregate_test_links()
    payload = build_architecture_quality_scorecard(repo_root=PROJECT_ROOT)
    DEFAULT_OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote architecture quality scorecard: {DEFAULT_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
