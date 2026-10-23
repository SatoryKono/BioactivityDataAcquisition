#!/usr/bin/env python3
"""Build a pytest nodeid inventory with one canonical lane owner per node.

Collection uses pytest's own session, not a text scan for ``::``. Lane
membership comes from ``configs/quality/test_matrix.yaml`` path prefixes,
``--ignore`` entries, and marker expressions. The output path is fixed so
CLI arguments cannot choose a filesystem sink.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
import yaml

from scripts.engineering.common.repo_paths import (
    REPO_ROOT,
    ensure_safe_cli_argv,
    read_text_confined,
    write_text_confined,
)

_MATRIX_PATH: Final[str] = "configs/quality/test_matrix.yaml"
_OUTPUT_PATH: Final[str] = "reports/quality/pytest-nodeid-inventory.json"
_COLLECT_ROOTS: Final[tuple[str, ...]] = ("tests",)
_UMBRELLA_LANES: Final[frozenset[str]] = frozenset({"coverage-verify"})
_OWNER_PRIORITY: Final[tuple[str, ...]] = (
    "AgentMemory",
    "Agent",
    "Docs",
    "Diagram",
    "FullOnly",
    "Core",
)
_LANE_OWNER: Final[dict[str, str]] = {
    "smoke": "FullOnly",
    "unit-fast": "Core",
    "unit-filesystem-contracts": "Core",
    "repo-backed-unit": "Core",
    "unit-scripts-tooling": "Core",
    "unit-parallel-safe": "Core",
    "integration-replay": "Core",
    "integration-determinism": "Core",
    "integration-idempotency": "Core",
    "integration-composite-resume": "Core",
    "security": "Core",
    "contracts": "Core",
    "architecture": "Core",
    "architecture-fast-boundary": "Core",
    "architecture-slow-governance": "Core",
    "architecture-read-only-audit": "Core",
    "e2e": "FullOnly",
    "e2e-smoke": "FullOnly",
    "e2e-nightly-full": "FullOnly",
    "e2e-nightly-live": "FullOnly",
    "prompt-tests-nightly": "Agent",
    "memory": "AgentMemory",
    "performance": "FullOnly",
    "coverage-verify": "Core",
}
_WORKFLOW_BY_OWNER: Final[dict[str, str]] = {
    "Core": "tests",
    "AgentMemory": "tests",
    "Agent": "tests",
    "Docs": "docs",
    "Diagram": "docs",
    "FullOnly": "nightly",
    "unowned": "unassigned",
}


@dataclass(frozen=True)
class LaneRule:
    """One test-matrix lane reduced to the fields the inventory matches on."""

    name: str
    prefixes: tuple[str, ...]
    ignores: tuple[str, ...]
    marker_expression: str


@dataclass(frozen=True)
class CollectedNode:
    """One pytest item captured at collection finish."""

    nodeid: str
    file: str
    type_name: str
    markers: tuple[str, ...]
    fixtures: tuple[str, ...]


@dataclass(frozen=True)
class OwnerDecision:
    """Canonical owner plus the lanes that produced it."""

    canonical_owner: str
    overlap_rationale: str | None
    lanes: tuple[str, ...]


def _normalize_prefix(prefix: str) -> str:
    text = prefix.replace("\\", "/").lstrip("./")
    if text.endswith(".py"):
        return text
    return text if text.endswith("/") else f"{text}/"


def marker_expression_matches(markers: set[str], expression: str) -> bool:
    """Match a conjunction of ``marker`` / ``not marker`` tokens.

    Lane expressions in the committed matrix are ``and`` chains only.
    """

    if not expression.strip():
        return True
    for part in expression.split(" and "):
        token = part.strip()
        if token.startswith("not "):
            if token.removeprefix("not ").strip() in markers:
                return False
            continue
        if token not in markers:
            return False
    return True


def _ignored(file_name: str, ignores: tuple[str, ...]) -> bool:
    for ignore in ignores:
        needle = _normalize_prefix(ignore)
        if file_name == needle.rstrip("/") or file_name.startswith(needle):
            return True
    return False


def _prefix_matches(file_name: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        needle = _normalize_prefix(prefix)
        if needle.endswith(".py"):
            if file_name == needle:
                return True
            continue
        if file_name.startswith(needle):
            return True
    return False


def lane_matches(rule: LaneRule, file_name: str, markers: set[str]) -> bool:
    """Return whether one collected file belongs to ``rule``."""

    if _ignored(file_name, rule.ignores):
        return False
    if not _prefix_matches(file_name, rule.prefixes):
        return False
    return marker_expression_matches(markers, rule.marker_expression)


def load_lane_rules(matrix: Mapping[str, object]) -> tuple[LaneRule, ...]:
    """Read lane path, ignore, and marker rules from the test matrix."""

    test_lanes = matrix.get("test_lanes")
    if not isinstance(test_lanes, Mapping):
        raise ValueError("test_matrix.yaml is missing test_lanes")
    lanes = test_lanes.get("lanes")
    if not isinstance(lanes, Mapping):
        raise ValueError("test_matrix.yaml is missing test_lanes.lanes")
    rules: list[LaneRule] = []
    for name, info in lanes.items():
        if not isinstance(name, str) or not isinstance(info, Mapping):
            raise ValueError(f"invalid lane entry: {name!r}")
        rules.append(
            LaneRule(
                name=name,
                prefixes=_string_tuple(info.get("paths")),
                ignores=_ignore_args(info.get("pytest_args")),
                marker_expression=_marker_expression(info.get("marker_expression")),
            )
        )
    missing = [rule.name for rule in rules if rule.name not in _LANE_OWNER]
    if missing:
        raise ValueError(f"unmapped test lanes: {missing}")
    return tuple(rules)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(str(item) for item in value)


def _marker_expression(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _ignore_args(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    ignores: list[str] = []
    tokens = [str(item) for item in value]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--ignore="):
            ignores.append(token.split("=", 1)[1])
        elif token == "--ignore" and index + 1 < len(tokens):
            index += 1
            ignores.append(tokens[index])
        index += 1
    return tuple(ignores)


def decide_owner(lane_names: Sequence[str]) -> OwnerDecision:
    """Pick one canonical owner. Smoke overlap is the only allowed duplicate."""

    substantive = tuple(name for name in lane_names if name not in _UMBRELLA_LANES)
    if not substantive:
        return OwnerDecision("unowned", None, ())
    owners = {_LANE_OWNER[name] for name in substantive}
    if len(owners) == 1:
        rationale = None
        if "smoke" in substantive and len(substantive) > 1:
            rationale = "intentional smoke execution"
        return OwnerDecision(next(iter(owners)), rationale, substantive)
    if "smoke" in substantive:
        chosen = next(owner for owner in _OWNER_PRIORITY if owner in owners)
        return OwnerDecision(chosen, "intentional smoke execution", substantive)
    return OwnerDecision("unowned", "multiple canonical owners", substantive)


def fallback_owner(file_name: str, markers: set[str]) -> OwnerDecision | None:
    """Own tests that PR lanes exclude on purpose.

    ``coverage-verify`` is an umbrella rerun. A node that matches only that
    lane, or no lane, would otherwise stay unowned and fail ``--update``.
    """

    if file_name.startswith("tests/benchmarks/") or "benchmark" in markers:
        return OwnerDecision("FullOnly", None, ("benchmarks",))
    if "performance" in markers:
        return OwnerDecision("FullOnly", None, ("performance",))
    if "slow" in markers:
        return OwnerDecision("FullOnly", None, ("slow",))
    if "memory" in markers:
        return OwnerDecision("AgentMemory", None, ("memory",))
    if file_name.startswith("tests/e2e/"):
        return OwnerDecision("FullOnly", None, ("e2e",))
    if "repo_backed" in markers:
        return OwnerDecision("FullOnly", None, ("repo-backed-outside-lane",))
    if "subprocess_backed" in markers:
        return OwnerDecision("FullOnly", None, ("subprocess-backed",))
    return None


def semantic_criticality(canonical_owner: str) -> str:
    """Map a canonical owner to production criticality."""

    if canonical_owner in {"Core", "FullOnly"}:
        return "critical"
    return "non-critical"


def workflow_job(canonical_owner: str) -> str:
    """Map a canonical owner to the workflow job that executes it."""

    return _WORKFLOW_BY_OWNER.get(canonical_owner, "unassigned")


def matching_lanes(
    rules: Sequence[LaneRule],
    file_name: str,
    markers: set[str],
) -> tuple[str, ...]:
    """Return lane names whose path and marker rules accept this file."""

    return tuple(rule.name for rule in rules if lane_matches(rule, file_name, markers))


def build_record(
    node: CollectedNode,
    rules: Sequence[LaneRule],
) -> dict[str, object]:
    """Turn one collected node into a deterministic inventory record."""

    markers = set(node.markers)
    decision = decide_owner(matching_lanes(rules, node.file, markers))
    if decision.canonical_owner == "unowned" and not decision.lanes:
        decision = fallback_owner(node.file, markers) or decision
    return {
        "canonical_owner": decision.canonical_owner,
        "execution_policy": ",".join(decision.lanes) if decision.lanes else "unowned",
        "file": node.file,
        "fixtures": list(node.fixtures),
        "nodeid": node.nodeid,
        "overlap_rationale": decision.overlap_rationale,
        "semantic_production_criticality": semantic_criticality(
            decision.canonical_owner
        ),
        "type": node.type_name,
        "workflow_job": workflow_job(decision.canonical_owner),
    }


def _node_from_item(item: pytest.Item, root: Path) -> CollectedNode:
    candidate = Path(str(item.path))
    try:
        relative = candidate.resolve().relative_to(root).as_posix()
    except ValueError:
        relative = candidate.as_posix()
    markers = tuple(sorted({mark.name for mark in item.iter_markers()}))
    names = getattr(item, "fixturenames", ())
    fixtures = tuple(sorted(str(name) for name in names))
    return CollectedNode(
        nodeid=item.nodeid,
        file=relative,
        type_name=type(item).__name__,
        markers=markers,
        fixtures=fixtures,
    )


def collect_nodes(
    paths: Sequence[str] = _COLLECT_ROOTS,
    *,
    root: Path = REPO_ROOT,
) -> tuple[int, tuple[CollectedNode, ...]]:
    """Collect pytest items and preserve pytest's exit status."""

    found: list[CollectedNode] = []

    class _InventoryPlugin:
        def pytest_collection_finish(self, session: pytest.Session) -> None:
            found.extend(_node_from_item(item, root) for item in session.items)

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        exit_code = int(
            pytest.main(
                [
                    "--collect-only",
                    "--artifact-selection=all",
                    "-p",
                    "no:cacheprovider",
                    *paths,
                ],
                plugins=[_InventoryPlugin()],
            )
        )
    if exit_code != 0:
        sys.stderr.write(stdout_buffer.getvalue())
        sys.stderr.write(stderr_buffer.getvalue())
    return exit_code, tuple(found)


def _head_sha() -> str:
    completed = subprocess.run(
        ensure_safe_cli_argv(["git", "rev-parse", "HEAD"]),
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def build_inventory(
    nodes: Sequence[CollectedNode],
    rules: Sequence[LaneRule],
    *,
    source_commit: str,
) -> dict[str, object]:
    """Assemble the sorted inventory document."""

    records = [build_record(node, rules) for node in nodes]
    records.sort(key=lambda record: str(record["nodeid"]))
    counts = Counter(str(record["nodeid"]) for record in records)
    duplicates = sorted(nodeid for nodeid, count in counts.items() if count > 1)
    unowned = [
        str(record["nodeid"])
        for record in records
        if record["canonical_owner"] == "unowned"
    ]
    return {
        "count": len(records),
        "duplicate_nodeids": duplicates,
        "nodes": records,
        "schema_version": 1,
        "source_commit": source_commit,
        "unowned_count": len(unowned),
        "unowned_nodeids": unowned,
    }


def _dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _problems(payload: Mapping[str, object]) -> list[str]:
    """Fail on duplicate or unowned nodes.

    ``source_commit`` records the HEAD that generated the file. Comparing it
    with the commit that contains the file can never succeed, so freshness is
    the collected ``nodes`` list.
    """

    problems: list[str] = []
    duplicates = payload.get("duplicate_nodeids")
    if isinstance(duplicates, list) and duplicates:
        problems.append(f"duplicate nodeids: {len(duplicates)}")
    unowned = payload.get("unowned_count")
    if unowned != 0:
        problems.append(f"unowned nodeids: {unowned}")
    return problems


def _check(expected: Mapping[str, object]) -> int:
    try:
        existing_text = read_text_confined(_OUTPUT_PATH)
    except (OSError, ValueError) as exc:
        print(f"inventory read failed: {exc}", file=sys.stderr)
        return 1
    existing = json.loads(existing_text)
    if not isinstance(existing, dict):
        print("inventory payload must be an object", file=sys.stderr)
        return 1
    if existing.get("nodes") != expected.get("nodes"):
        print("inventory nodes differ from the committed manifest", file=sys.stderr)
        return 1
    problems = _problems(existing)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"Inventory matches {_OUTPUT_PATH}.")
    return 0


def _load_matrix() -> dict[str, object]:
    loaded = yaml.safe_load(read_text_confined(_MATRIX_PATH))
    if not isinstance(loaded, dict):
        raise ValueError("test matrix must be a mapping")
    return loaded


def main(argv: Sequence[str] | None = None) -> int:
    """Collect nodeids and either write the fixed manifest or check it."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.check and args.update:
        print("pass only one of --check or --update", file=sys.stderr)
        return 2

    rules = load_lane_rules(_load_matrix())
    exit_code, nodes = collect_nodes()
    if exit_code != 0:
        print(f"pytest collection failed with exit {exit_code}", file=sys.stderr)
        return exit_code

    head = _head_sha()
    inventory = build_inventory(nodes, rules, source_commit=head)
    if args.check:
        return _check(inventory)

    write_text_confined(_OUTPUT_PATH, _dumps(inventory))
    print(f"Wrote {inventory['count']} nodeids to {_OUTPUT_PATH}.")
    problems = _problems(inventory)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
