"""Budget guards compare immutable Git evidence and preserve shrink-only policy."""

from __future__ import annotations

from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.engineering.repo import budget_guard as guard

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    "old,new",
    [
        (
            {"baseline": {"count": 2}, "max_count": 2},
            {"baseline": {"count": 3}, "max_count": 3},
        ),
        ({"max_count": 0}, {"max_count": True}),
        ({"max_count": 2}, {}),
        ({"mode": "block"}, {"mode": "warn"}),
        ({"min_coverage": 85}, {"min_coverage": 84}),
        ({"baseline_throughput_rps": 100}, {"baseline_throughput_rps": 90}),
    ],
)
def test_policy_cannot_be_weakened(old: object, new: object) -> None:
    """Moving a baseline together with a cap cannot turn growth into success."""
    assert guard.compare_documents(old, new)


def test_shrinking_limits_and_strengthening_floors_are_allowed() -> None:
    """Stronger numerical policy must not be confused with additional debt."""
    assert not guard.compare_documents(
        {"max_count": 3, "min_coverage": 85}, {"max_count": 2, "min_coverage": 86}
    )


def test_exemptions_may_retire_but_cannot_expand_or_extend() -> None:
    """Removal is shrink-only; new identities and later expiry are not."""
    old = {
        "path_entries": [{"path": "src/a", "expiry": "2026-11-15", "scopes": ["xenon"]}]
    }
    assert not guard.compare_documents(old, {"path_entries": []}, kind="exemptions")
    extended = {
        "path_entries": [{"path": "src/a", "expiry": "2027-11-15", "scopes": ["xenon"]}]
    }
    assert guard.compare_documents(old, extended, kind="exemptions")
    expanded = {"path_entries": [*old["path_entries"], {"path": "src/b"}]}
    assert guard.compare_documents(old, expanded, kind="exemptions")


def test_unknown_policy_lists_do_not_silently_drop_requirements() -> None:
    """A list of required modules cannot be mistaken for an allowlist."""
    assert guard.compare_documents(
        {"required_modules": ["a", "b"]}, {"required_modules": ["a"]}
    )


def test_telemetry_measurements_are_not_limits() -> None:
    """Coverage observations may change while the floor and age cap stay fixed."""
    old = {
        "version": 1,
        "policy_scope": "test_telemetry_baseline",
        "freshness_guard": {"max_age_days": 45, "timestamp_field": "refreshed_at_utc"},
        "coverage": {"threshold_percent": 85, "actual_percent": 90},
    }
    new = json.loads(json.dumps(old))
    new["coverage"]["actual_percent"] = 99
    assert not guard._compare_surface_documents(old, new, "telemetry")
    new["coverage"]["threshold_percent"] = 84
    assert guard._compare_surface_documents(old, new, "telemetry")


def test_registry_covers_current_budget_like_policy_files() -> None:
    """New unregistered policy surfaces must have an explicit review signal."""
    surfaces = guard._registry((ROOT / guard.REGISTRY).read_text(encoding="utf-8"))
    roots = (
        ROOT / "configs/quality",
        ROOT / "scripts/engineering/baselines",
        ROOT / "tests/performance",
    )
    candidates = [
        p.relative_to(ROOT).as_posix()
        for folder in roots
        for p in folder.rglob("*")
        if p.is_file()
    ]
    uncovered = [
        p
        for p in candidates
        if p != guard.REGISTRY
        and guard.is_budget_candidate(p)
        and not any(fnmatchcase(p, item["pattern"]) for item in surfaces)
    ]
    assert uncovered == []
    assert not guard.is_budget_candidate("tests/performance/test_hotspot_budgets.py")


def _git(root: Path, *args: str) -> str:
    """Use private fixture history without any installed host hooks."""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=" + str(root / "empty-hooks"),
            "-c",
            "user.name=Guard Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-C",
            str(root),
            *args,
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.strip()


@pytest.fixture
def policy_repo(tmp_path: Path) -> tuple[Path, str, Path]:
    """Create a tiny local test repository, never a BioETL checkout."""
    root = tmp_path / "fixture"
    root.mkdir()
    _git(root, "-c", "init.templateDir=", "init", "-q")
    registry = root / guard.REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / guard.REGISTRY).read_bytes())
    budget = registry.parent / "example_budget.json"
    budget.write_text('{"baseline":{"count":2},"max_count":2}')
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture baseline")
    return root, _git(root, "rev-parse", "HEAD"), budget


def test_staged_growth_cannot_be_hidden_by_worktree(
    policy_repo: tuple[Path, str, Path],
) -> None:
    """A later unstaged repair cannot hide the actually staged increase."""
    root, base, budget = policy_repo
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    _git(root, "add", ".")
    budget.write_text('{"baseline":{"count":1},"max_count":1}')
    index_before = (root / ".git/index").read_bytes()
    report = guard.check_budget_diff(root, base)
    assert report["status"] == "FAIL"
    assert any(
        item["code"] == "budget.ceiling_increased" for item in report["findings"]
    )
    assert (root / ".git/index").read_bytes() == index_before
    assert json.loads(budget.read_text())["max_count"] == 1


def test_immutable_tip_and_missing_base(policy_repo: tuple[Path, str, Path]) -> None:
    """CI can inspect a tip object; missing baseline evidence is never PASS."""
    root, base, budget = policy_repo
    budget.write_text('{"baseline":{"count":1},"max_count":1}')
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture shrink")
    assert guard.check_budget_diff(root, base, tip="HEAD")["status"] == "PASS"
    assert guard.check_budget_diff(root, "missing-branch")["status"] == "ERROR"


def test_staged_registry_cannot_exclude_its_own_budget(
    policy_repo: tuple[Path, str, Path],
) -> None:
    """The proposed registry cannot redefine the trusted base's scope."""
    root, base, budget = policy_repo
    registry = root / guard.REGISTRY
    data = json.loads(registry.read_text())
    data["surfaces"] = [{"pattern": "elsewhere/*", "kind": "budget"}]
    registry.write_text(json.dumps(data))
    budget.write_text('{"baseline":{"count":9},"max_count":9}')
    _git(root, "add", ".")
    report = guard.check_budget_diff(root, base)
    assert report["status"] == "FAIL"
    assert {x["code"] for x in report["findings"]} >= {
        "budget.registry_change_requires_review",
        "budget.ceiling_increased",
    }


def test_malformed_policy_does_not_echo_values(
    policy_repo: tuple[Path, str, Path],
) -> None:
    """Invalid input yields an explicit error, not a parser traceback or leak."""
    root, base, budget = policy_repo
    budget.write_text("private-input-not-for-output")
    _git(root, "add", ".")
    report = guard.check_budget_diff(root, base)
    assert report["status"] == "ERROR"
    assert "private-input" not in json.dumps(report)


@pytest.mark.parametrize(
    "captured,replacement,expected", [(99, 1, "FAIL"), (1, 99, "PASS")]
)
def test_index_replacement_cannot_mix_candidate_objects(
    policy_repo: tuple[Path, str, Path],
    monkeypatch: pytest.MonkeyPatch,
    captured: int,
    replacement: int,
    expected: str,
) -> None:
    """All comparisons use the blob IDs captured before another agent stages."""
    root, base, budget = policy_repo
    budget.write_text(
        json.dumps({"baseline": {"count": captured}, "max_count": captured})
    )
    _git(root, "add", ".")
    original = guard._check_surface

    def replace_then_compare(*args: object, **kwargs: object) -> list[dict[str, str]]:
        budget.write_text(
            json.dumps({"baseline": {"count": replacement}, "max_count": replacement})
        )
        _git(root, "add", ".")
        return original(*args, **kwargs)

    monkeypatch.setattr(guard, "_check_surface", replace_then_compare)
    assert guard.check_budget_diff(root, base)["status"] == expected


def test_unmerged_index_is_error(
    policy_repo: tuple[Path, str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unmerged raw records never become a successful empty comparison."""
    root, base, _ = policy_repo
    original = guard._git

    def raw_conflict(path: Path, *args: str) -> str:
        if args[0] == "diff":
            return (
                ":000000 100644 "
                + "0" * 40
                + " "
                + "1" * 40
                + " U\x00configs/quality/example_budget.json\x00"
            )
        return original(path, *args)

    monkeypatch.setattr(guard, "_git", raw_conflict)
    assert guard.check_budget_diff(root, base)["status"] == "ERROR"


@pytest.mark.parametrize("suffix", [".toml", ".ini", ".cfg", ".dat"])
def test_unknown_budget_formats_do_not_silently_skip(suffix: str) -> None:
    """Unknown policy formats still require review in the declared scope."""
    assert guard.is_budget_candidate("configs/quality/new_budget" + suffix)


def test_deleted_budget_fails_closed(policy_repo: tuple[Path, str, Path]) -> None:
    """Removing a protected budget cannot erase the baseline check."""
    root, base, budget = policy_repo
    budget.unlink()
    _git(root, "add", "-u")
    assert guard.check_budget_diff(root, base)["status"] == "ERROR"


@pytest.mark.parametrize(
    "name", ["confirming_clean_snapshots_required", "coverage_floor", "floor_percent"]
)
def test_required_evidence_and_floor_counts_cannot_shrink(name: str) -> None:
    """Required clean snapshots are a floor, not a debt ceiling."""
    assert guard.compare_documents({name: 2}, {name: 1}) == ["minimum_weakened"]
    assert guard.compare_documents({name: 2}, {name: 3}) == []


@pytest.mark.parametrize("new", [0, 2, True, "1"])
def test_policy_version_is_not_a_reducible_budget(new: object) -> None:
    """Changing schema version requires review even if the number decreases."""
    assert guard.compare_documents({"version": 1}, {"version": new}) == [
        "policy_schema_changed"
    ]


def test_replace_refs_cannot_substitute_trusted_policy_objects(
    policy_repo: tuple[Path, str, Path],
) -> None:
    """Local replace refs must not turn the protected ceiling into a fake base."""
    root, base, budget = policy_repo
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    _git(root, "add", ".")
    tree = _git(root, "write-tree")
    replacement = _git(root, "commit-tree", tree, "-m", "replacement fixture")
    _git(root, "replace", base, replacement)
    path = budget.relative_to(root).as_posix()
    assert json.loads(_git(root, "show", f"{base}:{path}"))["max_count"] == 99
    budget.write_text('{"baseline":{"count":9},"max_count":9}')
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "FAIL"
