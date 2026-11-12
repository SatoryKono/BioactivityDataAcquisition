"""Budget guards compare immutable Git evidence and preserve shrink-only policy."""

from __future__ import annotations

import copy

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


@pytest.mark.parametrize("protected", ["budget", "registry"])
@pytest.mark.parametrize("mode", ["120000", "160000"])
def test_non_regular_policy_objects_are_rejected_staged_and_committed(
    policy_repo, protected, mode
):
    """A symlink's JSON-looking target text must never stand in for policy data."""
    root, _, budget = policy_repo
    budget.write_text("{}")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "trusted empty baseline fixture")
    base = _git(root, "rev-parse", "HEAD")
    path = (
        budget.relative_to(root).as_posix() if protected == "budget" else guard.REGISTRY
    )
    if mode == "120000":
        target = budget.parent / "{}"
        target.write_text('{"allowed_errors":99}')
        _git(root, "add", str(target))
        payload = root / ".git/link-text"
        payload.write_text("{}")
        object_id = _git(root, "hash-object", "-w", str(payload))
    else:
        object_id = base
    _git(root, "update-index", "--add", "--cacheinfo", f"{mode},{object_id},{path}")
    staged = guard.check_budget_diff(root, base)
    assert staged["status"] == "FAIL"
    assert {"path": path, "code": "budget.non_regular_policy"} in staged["findings"]
    _git(root, "commit", "-qm", "non-regular candidate fixture")
    committed = guard.check_budget_diff(root, base, tip="HEAD")
    assert committed["status"] == "FAIL"
    assert {"path": path, "code": "budget.non_regular_policy"} in committed["findings"]


@pytest.mark.parametrize(
    "source",
    [
        "configs/quality/private_import_ratchet.yaml",
        "configs/quality/vcr_cassette_size_budget.yaml",
    ],
)
def test_registered_embedded_exemptions_can_retire_but_not_expand(policy_repo, source):
    """Exercise real current document shapes through the immutable Git interface."""
    import yaml

    root, _, _ = policy_repo
    target = root / source
    target.write_bytes((ROOT / source).read_bytes())
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "trusted embedded exemption fixture")
    base = _git(root, "rev-parse", "HEAD")
    previous = yaml.safe_load(target.read_text(encoding="utf-8"))
    proposed = copy.deepcopy(previous)
    if "pairs" in proposed:
        proposed["pairs"].pop()
        proposed["max_count"] -= 1
    else:
        proposed["policy"]["allowlist_oversized"].pop()
    target.write_text(yaml.safe_dump(proposed), encoding="utf-8")
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "PASS"
    expanded = copy.deepcopy(previous)
    records = (
        expanded["pairs"]
        if "pairs" in expanded
        else expanded["policy"]["allowlist_oversized"]
    )
    extra = copy.deepcopy(records[0])
    extra["id" if "pairs" in expanded else "path"] = "new-unreviewed-scope"
    records.append(extra)
    target.write_text(yaml.safe_dump(expanded), encoding="utf-8")
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "FAIL"
    if "max_count" in previous:
        missing_limit = copy.deepcopy(proposed)
        del missing_limit["max_count"]
        target.write_text(yaml.safe_dump(missing_limit), encoding="utf-8")
        _git(root, "add", ".")
        assert guard.check_budget_diff(root, base)["status"] == "FAIL"


def test_line_baseline_uses_producer_set_semantics(policy_repo):
    root, _, _ = policy_repo
    relative = "scripts/engineering/baselines/not_in_nav_baseline.txt"
    target = root / relative
    target.parent.mkdir(parents=True)
    target.write_text("# fixture\ndocs/keep.md\ndocs/retired.md\ndocs/keep.md\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "trusted line baseline fixture")
    base = _git(root, "rev-parse", "HEAD")
    target.write_text("  # comment\n\ndocs/keep.md\n")
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "PASS"
    target.write_text("docs/keep.md\ndocs/new-unreviewed.md\n")
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "FAIL"


def test_only_whole_registry_entries_can_retire(policy_repo):
    import yaml

    root, _, _ = policy_repo
    path = root / "configs/quality/architecture_metric_exemptions.yaml"
    previous = {
        "registries": {
            "file_size_limits": {
                "src/example.py": {"expires_on": "2027-01-31", "scopes": ["size"]}
            }
        }
    }
    path.write_text(yaml.safe_dump(previous))
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "trusted exemption entry fixture")
    base = _git(root, "rev-parse", "HEAD")
    removed_expiry = copy.deepcopy(previous)
    del removed_expiry["registries"]["file_size_limits"]["src/example.py"]["expires_on"]
    path.write_text(yaml.safe_dump(removed_expiry))
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "FAIL"
    retired = copy.deepcopy(previous)
    del retired["registries"]["file_size_limits"]["src/example.py"]
    path.write_text(yaml.safe_dump(retired))
    _git(root, "add", ".")
    assert guard.check_budget_diff(root, base)["status"] == "PASS"


def test_alternate_index_cannot_hide_staged_growth(
    policy_repo: tuple[Path, str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ambient clean index must not conceal increases in the repository index."""
    root, base, budget = policy_repo
    alternate = root.parent / "alternate-index"
    alternate.write_bytes((root / ".git/index").read_bytes())
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    _git(root, "add", ".")
    real_before = (root / ".git/index").read_bytes()
    alternate_before = alternate.read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))

    report = guard.check_budget_diff(root, base)

    assert report["status"] == "FAIL"
    assert any(
        item["code"] == "budget.ceiling_increased" for item in report["findings"]
    )
    assert (root / ".git/index").read_bytes() == real_before
    assert alternate.read_bytes() == alternate_before


@pytest.mark.parametrize(
    "name,keypath",
    [
        ("private_import_ratchet.yaml", ("pairs",)),
        ("vcr_cassette_size_budget.yaml", ("policy", "allowlist_oversized")),
    ],
)
def test_existing_nested_exemptions_can_shrink(
    name: str, keypath: tuple[str, ...]
) -> None:
    """Retire actual private-import/VCR entries without removing budget records."""
    old = guard._load_document((ROOT / "configs/quality" / name).read_text(), ".yaml")
    new = json.loads(json.dumps(old))
    value = new
    for key in keypath[:-1]:
        value = value[key]
    value[keypath[-1]].pop()
    if name == "private_import_ratchet.yaml":
        new["max_count"] -= 1
    descriptors = guard._registry((ROOT / guard.REGISTRY).read_text(encoding="utf-8"))
    descriptor = next(
        item for item in descriptors if item["pattern"] == f"configs/quality/{name}"
    )
    assert guard._compare_registered_documents(old, new, descriptor) == []


def test_retirement_does_not_remove_fields_from_retained_exemptions() -> None:
    old = {
        "registries": {
            "file_size_limits": {
                "src/example.py": {"value": 100, "expires_on": "2026-12-01"},
            }
        }
    }
    new = json.loads(json.dumps(old))
    del new["registries"]["file_size_limits"]["src/example.py"]["expires_on"]
    assert "protected_field_removed" in guard.compare_documents(
        old, new, kind="exemptions"
    )
    assert (
        guard.compare_documents(
            old,
            {"registries": {"file_size_limits": {}}},
            kind="exemptions",
        )
        == []
    )


def test_text_navigation_baseline_shrinks_without_new_exceptions() -> None:
    raw = (ROOT / "scripts/engineering/baselines/not_in_nav_baseline.txt").read_text()
    old = guard._load_document(raw, ".txt")
    lines = [
        line
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    new = guard._load_document("# reviewed removal\n" + "\n".join(lines[1:]), ".txt")
    assert guard._compare_surface_documents(old, new, "line_exemptions") == []
    expanded = guard._load_document(raw + "\nnew/unreviewed.md\n", ".txt")
    assert guard._compare_surface_documents(old, expanded, "line_exemptions") == [
        "exemption_scope_added"
    ]


@pytest.mark.parametrize("committed", [False, True])
def test_policy_symlink_object_cannot_masquerade_as_empty_json(
    policy_repo: tuple[Path, str, Path],
    committed: bool,
) -> None:
    """Reject Git symlink modes even when their link text parses as a valid policy."""
    root, _, budget = policy_repo
    budget.write_text("{}")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture empty policy")
    base = _git(root, "rev-parse", "HEAD")
    payload = root.parent / "link-payload"
    payload.write_text("{}")
    blob = _git(root, "hash-object", "-w", str(payload))
    path = budget.relative_to(root).as_posix()
    _git(root, "update-index", "--cacheinfo", f"120000,{blob},{path}")
    tip = None
    if committed:
        _git(root, "commit", "-qm", "fixture symbolic policy")
        tip = _git(root, "rev-parse", "HEAD")
    assert guard.check_budget_diff(root, base, tip=tip)["status"] == "FAIL"


@pytest.mark.parametrize("field", ["budgets", "pairs"])
def test_budget_record_removal_is_still_rejected(field: str) -> None:
    assert guard.compare_documents(
        {field: [{"id": "required-cap", "max_count": 2}]},
        {field: []},
    ) == ["budget_record_removed"]


def test_git_supplied_commit_index_growth_is_checked_even_when_default_is_clean(
    policy_repo, monkeypatch
):
    """A real Git commit may supply its own index for a selected-path commit."""
    root, base, budget = policy_repo
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    _git(root, "add", ".")
    supplied = root.parent / "git-commit-index"
    supplied.write_bytes((root / ".git/index").read_bytes())
    _git(root, "read-tree", "HEAD")
    default_before = (root / ".git/index").read_bytes()
    supplied_before = supplied.read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(supplied))
    result = guard.check_budget_diff(root, base)
    assert result["status"] == "FAIL"
    assert any(
        item["code"] == "budget.ceiling_increased" for item in result["findings"]
    )
    assert (root / ".git/index").read_bytes() == default_before
    assert supplied.read_bytes() == supplied_before


def test_unstaged_working_budget_growth_is_blocked_without_staging(policy_repo):
    root, base, budget = policy_repo
    index = (root / ".git/index").read_bytes()
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    assert guard.check_budget_diff(root, base)["status"] == "PASS"
    result = guard.check_worktree_budget_diff(root, base)
    assert result["status"] == "FAIL"
    assert any(row["code"] == "budget.ceiling_increased" for row in result["findings"])
    assert (root / ".git/index").read_bytes() == index


@pytest.mark.parametrize("ignored", [False, True])
def test_new_policy_without_trusted_baseline_cannot_pass(policy_repo, ignored):
    root, base, _ = policy_repo
    path = root / "configs/quality/new_budget.json"
    if ignored:
        (root / ".git/info").mkdir(exist_ok=True)
        (root / ".git/info/exclude").write_text("configs/quality/new_budget.json\n")
    path.write_text('{"max_count":99}')
    assert "configs/quality/new_budget.json" in guard.worktree_policy_paths(root, base)
    assert guard.check_worktree_budget_diff(root, base)["status"] == "ERROR"


def test_worktree_guard_ignores_ambient_config_override(policy_repo, monkeypatch):
    root, base, budget = policy_repo
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(root.parent / "absent"))
    assert guard.check_worktree_budget_diff(root, base)["status"] == "FAIL"


def test_scoped_validation_rejects_real_unstaged_budget_increase(policy_repo):
    from scripts.engineering.repo import scoped_checks

    root, base, budget = policy_repo
    _git(root, "update-ref", "refs/remotes/origin/main", base)
    budget.write_text('{"baseline":{"count":99},"max_count":99}')
    result = scoped_checks.validate(root)
    assert result["status"] == "ERROR"
    assert [(row["id"], row["status"]) for row in result["checks"]] == [
        ("tree", "PASS"),
        ("budgets", "PASS"),
        ("budgets-worktree", "FAIL"),
    ]
    assert (
        json.loads(_git(root, "show", ":configs/quality/example_budget.json"))[
            "max_count"
        ]
        == 2
    )
