#!/usr/bin/env python3
"""Build a pytest nodeid inventory with one canonical lane owner per node.

Collection uses pytest's own session, not a text scan for ``::``. Lane
membership comes from ``configs/quality/test_matrix.yaml`` path prefixes,
``--ignore`` entries, and marker expressions. Sharded lanes use the shard
paths and ignores selected by ``runner_options``, not the lane's broad
``paths`` list. The output path is fixed so CLI arguments cannot choose a
filesystem sink.

``source_commit`` records the HEAD used at ``--update`` time. ``--check``
does not require that field to equal the current HEAD: the committed file
cannot contain the SHA of the commit that adds it. Freshness is the
collected document with ``source_commit`` removed.
"""

from __future__ import annotations

import argparse
import fnmatch
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
_SHARDS_PATH: Final[str] = "configs/quality/pytest_shards.yaml"
_OUTPUT_PATH: Final[str] = "reports/quality/pytest-nodeid-inventory.json"
_COLLECT_ROOTS: Final[tuple[str, ...]] = ("tests",)
_RESIDUAL_LANE: Final[str] = "full-only-residual"
_CHECK_IGNORED_FIELDS: Final[frozenset[str]] = frozenset({"source_commit"})
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
class ShardScope:
    """Paths and ignores for one concrete pytest shard."""

    prefixes: tuple[str, ...]
    ignores: tuple[str, ...]
    ignore_globs: tuple[str, ...]


@dataclass(frozen=True)
class LaneRule:
    """One test-matrix lane reduced to the fields the inventory matches on."""

    name: str
    prefixes: tuple[str, ...]
    ignores: tuple[str, ...]
    marker_expression: str
    shard_scopes: tuple[ShardScope, ...] = ()


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


def _normalize_token(prefix: str) -> str:
    return prefix.replace("\\", "/").lstrip("./")


def glob_match(path: str, pattern: str) -> bool:
    """Match a repo-relative path with the same ``fnmatch`` rules pytest uses."""

    return fnmatch.fnmatchcase(_normalize_token(path), _normalize_token(pattern))


def _path_token_matches(file_name: str, raw: str) -> bool:
    needle = _normalize_token(raw)
    if any(char in needle for char in "*?["):
        return glob_match(file_name, needle)
    if needle.endswith(".py"):
        return file_name == needle
    directory = needle if needle.endswith("/") else f"{needle}/"
    return file_name == directory.rstrip("/") or file_name.startswith(directory)


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
    return any(_path_token_matches(file_name, ignore) for ignore in ignores)


def _glob_ignored(file_name: str, patterns: tuple[str, ...]) -> bool:
    return any(glob_match(file_name, pattern) for pattern in patterns)


def _prefix_matches(file_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(_path_token_matches(file_name, prefix) for prefix in prefixes)


def _scope_matches(scope: ShardScope, file_name: str) -> bool:
    if _ignored(file_name, scope.ignores) or _glob_ignored(
        file_name, scope.ignore_globs
    ):
        return False
    return _prefix_matches(file_name, scope.prefixes)


def lane_matches(rule: LaneRule, file_name: str, markers: set[str]) -> bool:
    """Return whether one collected file belongs to ``rule``."""

    if not marker_expression_matches(markers, rule.marker_expression):
        return False
    if rule.shard_scopes:
        return any(_scope_matches(scope, file_name) for scope in rule.shard_scopes)
    if _ignored(file_name, rule.ignores):
        return False
    return _prefix_matches(file_name, rule.prefixes)


def load_lane_rules(
    matrix: Mapping[str, object],
    shards: Mapping[str, object] | None = None,
) -> tuple[LaneRule, ...]:
    """Read lane path, ignore, and marker rules from the test matrix.

    Sharded lanes replace ``paths`` with the concrete shard scopes named by
    ``runner_options``. ``coverage-verify`` stays an umbrella and is not
    expanded.
    """

    test_lanes = matrix.get("test_lanes")
    if not isinstance(test_lanes, Mapping):
        raise ValueError("test_matrix.yaml is missing test_lanes")
    lanes = test_lanes.get("lanes")
    if not isinstance(lanes, Mapping):
        raise ValueError("test_matrix.yaml is missing test_lanes.lanes")
    aliases: dict[str, tuple[str, ...]] = {}
    scopes: dict[str, ShardScope] = {}
    if shards is not None:
        aliases, scopes = load_shard_catalog(shards)
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
                shard_scopes=_shard_scopes_for_lane(
                    name,
                    info,
                    aliases=aliases,
                    scopes=scopes,
                    catalog_loaded=shards is not None,
                ),
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


def _ignore_glob_args(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    patterns: list[str] = []
    tokens = [str(item) for item in value]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--ignore-glob="):
            patterns.append(token.split("=", 1)[1])
        elif token == "--ignore-glob" and index + 1 < len(tokens):
            index += 1
            patterns.append(tokens[index])
        index += 1
    return tuple(patterns)


def _option_values(value: object, flag: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    tokens = [str(item) for item in value]
    names: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] == flag and index + 1 < len(tokens):
            index += 1
            names.append(tokens[index])
        index += 1
    return tuple(names)


def load_shard_catalog(
    payload: Mapping[str, object],
) -> tuple[dict[str, tuple[str, ...]], dict[str, ShardScope]]:
    """Read alias expansion and concrete shard scopes."""

    raw_aliases = payload.get("aliases")
    aliases: dict[str, tuple[str, ...]] = {}
    if isinstance(raw_aliases, Mapping):
        for name, info in raw_aliases.items():
            if not isinstance(name, str) or not isinstance(info, Mapping):
                raise ValueError(f"invalid shard alias: {name!r}")
            aliases[name] = _string_tuple(info.get("expands_to"))
    raw_shards = payload.get("shards")
    if not isinstance(raw_shards, Sequence) or isinstance(raw_shards, str):
        raise ValueError("pytest_shards.yaml is missing shards")
    scopes: dict[str, ShardScope] = {}
    for entry in raw_shards:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid shard entry")
        name = entry.get("name")
        if not isinstance(name, str):
            raise ValueError("shard name must be a string")
        extra = entry.get("extra_pytest_args")
        scopes[name] = ShardScope(
            prefixes=_string_tuple(entry.get("paths")),
            ignores=_ignore_args(extra),
            ignore_globs=_ignore_glob_args(extra),
        )
    return aliases, scopes


def expand_shard_names(
    names: Sequence[str],
    aliases: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    """Expand alias names to concrete shard names, preserving first-seen order."""

    resolved: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def walk(name: str) -> None:
        if name in seen or name in visiting:
            if name in visiting:
                raise ValueError(f"shard alias cycle: {name}")
            return
        children = aliases.get(name)
        if children:
            visiting.add(name)
            for child in children:
                walk(str(child))
            visiting.remove(name)
            seen.add(name)
            return
        seen.add(name)
        resolved.append(name)

    for name in names:
        walk(name)
    return tuple(resolved)


def _shard_scopes_for_lane(
    name: str,
    info: Mapping[str, object],
    *,
    aliases: Mapping[str, Sequence[str]],
    scopes: Mapping[str, ShardScope],
    catalog_loaded: bool,
) -> tuple[ShardScope, ...]:
    if info.get("runner_backend") != "run_pytest_sharded":
        return ()
    selected = _option_values(info.get("runner_options"), "--shard")
    if not selected:
        if name in _UMBRELLA_LANES:
            return ()
        raise ValueError(f"sharded lane {name} has no --shard selection")
    if not catalog_loaded:
        raise ValueError(f"sharded lane {name} requires the pytest shard catalog")
    expanded = expand_shard_names(selected, aliases)
    missing = [item for item in expanded if item not in scopes]
    if missing:
        raise ValueError(f"unknown shards for {name}: {missing}")
    return tuple(scopes[item] for item in expanded)


def decide_owner(lane_names: Sequence[str]) -> OwnerDecision:
    """Pick one canonical owner. Smoke overlap is the only allowed duplicate."""

    substantive = tuple(name for name in lane_names if name not in _UMBRELLA_LANES)
    if not substantive:
        return OwnerDecision(
            "FullOnly",
            "outside configured lanes",
            (_RESIDUAL_LANE,),
        )
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

    decision = decide_owner(matching_lanes(rules, node.file, set(node.markers)))
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


def collect_pytest_args(paths: Sequence[str] = _COLLECT_ROOTS) -> list[str]:
    """Return the fixed pytest invocation used for a complete inventory."""

    return [
        "--collect-only",
        "-p",
        "no:cacheprovider",
        "--artifact-selection=all",
        *paths,
    ]


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
                collect_pytest_args(paths),
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
    nodeids = [str(record["nodeid"]) for record in records]
    counts = Counter(nodeids)
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


def comparable_inventory(payload: Mapping[str, object]) -> dict[str, object]:
    """Return the manifest fields that must match across commits."""

    return {
        key: value for key, value in payload.items() if key not in _CHECK_IGNORED_FIELDS
    }


def _problems(payload: Mapping[str, object]) -> list[str]:
    problems: list[str] = []
    duplicates = payload.get("duplicate_nodeids")
    if isinstance(duplicates, list) and duplicates:
        problems.append(f"duplicate nodeids: {len(duplicates)}")
    unowned = payload.get("unowned_count")
    if unowned != 0:
        problems.append(f"unowned nodeids: {unowned}")
    return problems


def _check_payloads(
    existing: Mapping[str, object],
    expected: Mapping[str, object],
) -> int:
    if comparable_inventory(existing) != comparable_inventory(expected):
        print("inventory differs from the committed manifest", file=sys.stderr)
        return 1
    problems = _problems(existing)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"Inventory matches {_OUTPUT_PATH}.")
    return 0


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
    return _check_payloads(existing, expected)


def _load_mapping(path: str) -> dict[str, object]:
    loaded = yaml.safe_load(read_text_confined(path))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must be a mapping")
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

    rules = load_lane_rules(_load_mapping(_MATRIX_PATH), _load_mapping(_SHARDS_PATH))
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
