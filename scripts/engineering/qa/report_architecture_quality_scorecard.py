#!/usr/bin/env python3
"""Regenerate architecture quality scorecard artifact."""

from __future__ import annotations

import json
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC_ROOT))

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)


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
    payload["semantic_completeness"] = "not_assessed; selected invariant links only"
    payload["generated_by"] = (
        "scripts/engineering/qa/report_architecture_quality_scorecard.py"
    )
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
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
