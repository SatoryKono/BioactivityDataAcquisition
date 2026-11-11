"""Compare protected policy documents to trusted Git objects, not self-baselines."""

from __future__ import annotations

import argparse
from datetime import date
from fnmatch import fnmatchcase
import json
import math
import os
from pathlib import Path
import re
import subprocess
from typing import Any

REGISTRY = "configs/quality/agent_guard_budget_surfaces.json"
_OBJECT_ID_PATTERN = r"[0-9a-f]{40}(?:[0-9a-f]{24})?"
METADATA = frozenset(
    {
        "owner",
        "rationale",
        "reason",
        "description",
        "next_step",
        "removal_step",
        "progress_note",
        "linked_issue",
        "linked_rf",
        "source_report",
        "recorded_on",
        "snapshot_date",
        "generator",
        "artifact",
        "linked_issues",
        "reviewed_on",
        "notes",
    }
)
EXPIRY = frozenset({"expiry", "expires_on", "expires", "review_by"})


def _number(value: Any) -> bool:
    """Booleans must not masquerade as numeric limits."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric_change(old: Any, new: Any, path: tuple[str, ...]) -> list[str]:
    """Maxima shrink; explicit minimum floors may only strengthen."""
    if not _number(new) or new < 0:
        return ["invalid_numeric_limit"]
    try:
        finite = math.isfinite(old) and math.isfinite(new)
    except OverflowError:
        finite = False
    if not finite:
        return ["invalid_baseline_limit"]
    if path and (
        path[-1].startswith(("min_", "minimum_", "floor_"))
        or path[-1].endswith(("_min", "_floor", "_required"))
        or path[-1] == "baseline_throughput_rps"
    ):
        return ["minimum_weakened"] if new < old else []
    return ["ceiling_increased"] if new > old else []


def _identity(item: Any) -> tuple[str, str] | None:
    """Match exemption records independently of their list order."""
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("path"), str) and isinstance(item.get("function"), str):
        return "function", item["path"] + "\x00" + item["function"]
    for key in ("id", "path", "function", "name", "metric", "quarter"):
        if isinstance(item.get(key), str):
            return key, item[key]
    return None


def _list_changes(
    old: list[Any], new: list[Any], path: tuple[str, ...], kind: str
) -> list[str]:
    """Allow retiring exemptions, not inserting new records or wider scopes."""
    if old == new:
        return []
    if all(isinstance(item, str) for item in [*old, *new]):
        return _string_list_changes(old, new, path)
    return _record_list_changes(old, new, path, kind)


def _string_list_changes(
    old: list[str], new: list[str], path: tuple[str, ...]
) -> list[str]:
    """Only explicitly understood allowlists and requirements may change."""
    if not path or path[-1] not in {
        "required_fields",
        "scopes",
        "allowlist",
        "whitelist",
        "allowed_tools",
        "allowed_paths",
    }:
        return ["unsupported_policy_list_change"]
    acceptable = (
        set(old) <= set(new) if path[-1] == "required_fields" else set(new) <= set(old)
    )
    return [] if acceptable else ["policy_list_expanded"]


def _record_list_changes(
    old: list[Any], new: list[Any], path: tuple[str, ...], kind: str
) -> list[str]:
    """Compare stable record identities while allowing exemption retirement."""
    old_map = {_identity(item): item for item in old}
    new_map = {_identity(item): item for item in new}
    if (
        None in old_map
        or None in new_map
        or len(old_map) != len(old)
        or len(new_map) != len(new)
    ):
        return ["unsupported_or_duplicate_record_identity"]
    if not set(new_map) <= set(old_map):
        return ["new_policy_record"]
    retirable = kind == "exemptions" or path in {
        ("pairs",),
        ("policy", "allowlist_oversized"),
    }
    if not retirable and set(new_map) != set(old_map):
        return ["budget_record_removed"]
    return [
        error
        for key in new_map
        for error in compare_documents(old_map[key], new_map[key], path=path, kind=kind)
    ]


def _mapping_changes(
    old: dict[str, Any], new: dict[str, Any], path: tuple[str, ...], kind: str
) -> list[str]:
    """Reject schema escapes and changes to both a cap and its baseline."""
    errors = []
    if not all(isinstance(key, str) for key in [*old, *new]):
        return ["unsupported_policy_keys"]
    for key, previous in old.items():
        if key in METADATA:
            continue
        errors.extend(_mapping_field_changes(key, previous, new, path, kind))
    if set(new) - set(old) - METADATA:
        errors.append("unreviewed_policy_field")
    return errors


def _mapping_field_changes(
    key: str, previous: Any, new: dict[str, Any], path: tuple[str, ...], kind: str
) -> list[str]:
    """Separate schema identity and exemption retirement from numeric limits."""
    if key in {"version", "schema_version"} and (
        type(new.get(key)) is not type(previous) or new.get(key) != previous
    ):
        return ["policy_schema_changed"]
    if key not in new:
        retired = kind == "exemptions" and len(path) == 2 and path[0] == "registries"
        return [] if retired else ["protected_field_removed"]
    return compare_documents(previous, new[key], path=(*path, key), kind=kind)


def compare_documents(
    old: Any, new: Any, *, path: tuple[str, ...] = (), kind: str = "budget"
) -> list[str]:
    """Return reason codes only; never echo values from untrusted documents."""
    if _number(old):
        return _numeric_change(old, new, path)
    if isinstance(old, dict) and isinstance(new, dict):
        return _mapping_changes(old, new, path, kind)
    if isinstance(old, list) and isinstance(new, list):
        return _list_changes(old, new, path, kind)
    if path and path[-1] in EXPIRY:
        return _expiry_change(old, new)
    return (
        [] if type(old) is type(new) and old == new else ["unsupported_policy_change"]
    )


def _expiry_change(old: Any, new: Any) -> list[str]:
    """An exemption's lifetime cannot be extended through a string edit."""
    try:
        previous, proposed = date.fromisoformat(str(old)), date.fromisoformat(str(new))
    except ValueError:
        return ["invalid_policy_expiry"]
    return ["policy_expiry_extended"] if proposed > previous else []


def _git(root: Path, *args: str) -> str:
    """Read Git metadata with a deadline and no ambient repository override."""
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(name, None)
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            *args,
        ],
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )
    if result.returncode:
        raise ValueError("Git object query unavailable")
    return result.stdout


def _revision(root: Path, value: str) -> str:
    """Resolve a commit before interpolating it into an object specifier."""
    if (
        not value
        or value.startswith("-")
        or not re.fullmatch(r"[A-Za-z0-9_./@^{}~+-]+", value)
    ):
        raise ValueError("invalid revision")
    sha = _git(
        root, "rev-parse", "--verify", "--end-of-options", value + "^{commit}"
    ).strip()
    if not re.fullmatch(_OBJECT_ID_PATTERN, sha):
        raise ValueError("unverified revision")
    return sha


def _git_document(root: Path, object_spec: str) -> str:
    """Pin an immutable blob before checking size, avoiding index-swap races."""
    sha = _git(root, "rev-parse", "--verify", "--end-of-options", object_spec).strip()
    if not re.fullmatch(_OBJECT_ID_PATTERN, sha):
        raise ValueError("unverified policy object")
    size = int(_git(root, "cat-file", "-s", sha).strip())
    if size < 0 or size > 2 * 1024 * 1024:
        raise ValueError("policy exceeds size limit")
    return _git(root, "cat-file", "blob", sha)


def _load_document(raw: str, suffix: str) -> Any:
    """Safe-load structured policy without executing YAML constructors."""
    if len(raw.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("policy exceeds size limit")
    if suffix == ".json":
        return json.loads(raw)
    if suffix == ".txt":
        return {
            "allowlist": sorted(
                {
                    line.strip()
                    for line in raw.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                }
            )
        }
    import yaml

    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        raise ValueError("invalid policy document") from None


def _registry(raw: str) -> list[dict[str, str]]:
    """Only the base commit may define the protected surface inventory."""
    data = json.loads(raw)
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or not isinstance(data.get("owner"), str)
    ):
        raise ValueError("unknown registry schema")
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("empty surface registry")
    for item in surfaces:
        if (
            not isinstance(item, dict)
            or set(item) != {"pattern", "kind"}
            or item["kind"] not in {"budget", "exemptions", "telemetry", "contract"}
            or not isinstance(item["pattern"], str)
        ):
            raise ValueError("unknown surface descriptor")
    return surfaces


def is_budget_candidate(path: str) -> bool:
    """Unregistered budget-like files require review instead of a silent skip."""
    in_scope = path.startswith(
        ("configs/quality/", "scripts/engineering/baselines/", "tests/performance/")
    )
    return (
        in_scope
        and Path(path).suffix.lower() not in {".py", ".pyc", ".md"}
        and bool(
            re.search(
                r"budget|ratchet|exemption|scorecard|limits|baseline", Path(path).name
            )
        )
    )


def check_budget_diff(
    root: Path, base: str, *, tip: str | None = None
) -> dict[str, Any]:
    """Compare index or immutable tip to a trusted base, including deletions."""
    try:
        base_sha = _revision(root, base)
        tip_sha = _revision(root, tip) if tip else None
        surfaces = _registry(_git_document(root, f"{base_sha}:{REGISTRY}"))
        diff_args = [base_sha, tip_sha] if tip_sha else ["--cached", base_sha]
        changed = _changed_objects(root, diff_args)
        findings = []
        for path, blob, mode in changed:
            findings.extend(_check_surface(root, path, base_sha, blob, surfaces, mode))
        return {
            "status": "FAIL" if findings else "PASS",
            "base_sha": base_sha,
            "tip_sha": tip_sha,
            "findings": findings,
        }
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        subprocess.SubprocessError,
        ImportError,
    ):
        return {
            "status": "ERROR",
            "findings": [{"code": "budget.evidence_unavailable"}],
        }


def _changed_objects(root: Path, diff_args: list[str]) -> list[tuple[str, str, str]]:
    """Capture immutable candidate blob IDs from a single index read.

    Reading :path separately for each file could mix states from concurrent
    index replacements. Raw diff captures the complete comparison in one Git
    process; subsequent reads never consult the mutable index again.
    """
    fields = _git(
        root,
        "diff",
        *diff_args,
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--raw",
        "--no-abbrev",
        "-z",
        "--",
    ).split("\x00")
    if fields.pop() != "" or len(fields) % 2:
        raise ValueError("invalid raw diff")
    result = []
    for metadata, path in zip(fields[::2], fields[1::2], strict=True):
        tokens = metadata.split()
        if len(tokens) != 5 or tokens[-1] not in {"A", "M", "D", "T"}:
            raise ValueError("unresolved or unsupported index state")
        blob = tokens[3]
        if not re.fullmatch(_OBJECT_ID_PATTERN, blob):
            raise ValueError("invalid candidate object")
        result.append((path, blob, tokens[1]))
    return result


def _check_surface(
    root: Path,
    path: str,
    base: str,
    blob: str,
    surfaces: list[dict[str, str]],
    mode: str = "100644",
) -> list[dict[str, str]]:
    """Classify a changed path before loading any policy values."""
    matches = [item for item in surfaces if fnmatchcase(path, item["pattern"])]
    if (path == REGISTRY or matches) and mode not in {"100644", "100755", "000000"}:
        return [{"path": path, "code": "budget.non_regular_policy_object"}]
    if path == REGISTRY:
        old = _git_document(root, f"{base}:{path}")
        new = _git_document(root, blob)
        return (
            []
            if json.loads(old) == json.loads(new)
            else [{"path": path, "code": "budget.registry_change_requires_review"}]
        )
    if not matches:
        return (
            [{"path": path, "code": "budget.unregistered_surface"}]
            if is_budget_candidate(path)
            else []
        )
    old = _load_document(_git_document(root, f"{base}:{path}"), Path(path).suffix)
    new = _load_document(_git_document(root, blob), Path(path).suffix)
    codes = set(_compare_surface_documents(old, new, matches[0]["kind"]))
    return [{"path": path, "code": "budget." + code} for code in sorted(codes)]


def _compare_surface_documents(old: Any, new: Any, kind: str) -> list[str]:
    """Keep operational thresholds separate from measured telemetry values."""
    if kind == "telemetry":
        return compare_documents(_telemetry_limits(old), _telemetry_limits(new))
    if kind == "contract":
        # Architecture acceptance text is delegated to its architecture tests.
        if _numeric_paths(old) != {("version",)} or _numeric_paths(new) != {
            ("version",)
        }:
            return ["unknown_contract_numeric_field"]
        return (
            []
            if old["version"] == new["version"] == 1
            else ["unknown_contract_version"]
        )
    if not isinstance(old, dict) and not _number(old):
        raise ValueError("unknown policy document shape")
    return compare_documents(old, new, kind=kind)


def _telemetry_limits(data: Any) -> dict[str, Any]:
    """Protect the existing age ceiling and coverage floor, not observations."""
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or data.get("policy_scope") != "test_telemetry_baseline"
    ):
        raise ValueError("unknown telemetry schema")
    return {
        "freshness_guard": data["freshness_guard"],
        "min_coverage_threshold": data["coverage"]["threshold_percent"],
    }


def _numeric_paths(data: Any, path: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Find unregistered numerical controls in delegated contract documents."""
    if _number(data):
        return {path}
    if isinstance(data, dict):
        return {
            p
            for key, value in data.items()
            for p in _numeric_paths(value, (*path, str(key)))
        }
    if isinstance(data, list):
        return {
            p
            for i, value in enumerate(data)
            for p in _numeric_paths(value, (*path, str(i)))
        }
    return set()


def main(argv: list[str] | None = None) -> int:
    """Emit a non-secret-bearing report without refreshing or staging files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--tip")
    args = parser.parse_args(argv)
    result = check_budget_diff(args.repo_root.resolve(), args.base, tip=args.tip)
    print(json.dumps(result))
    return {"PASS": 0, "FAIL": 1, "ERROR": 2}[result["status"]]
