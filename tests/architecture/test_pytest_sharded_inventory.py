# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guards for declarative pytest shard inventory."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs/quality/pytest_shards.yaml"
RUNNER_PATH = ROOT / "scripts/engineering/dev/run_pytest_sharded.sh"
ARCHITECTURE_WORKFLOW_PATH = ROOT / ".github/workflows/import-linter.yml"
_BASH_RUNNER_UNSUPPORTED_ON_WINDOWS = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="bash-based sharded runner checks are not reliable on native Windows shells",
)


def _bash_runner_path(path: Path) -> str:
    """Render a bash-friendly script path across Linux and Windows hosts."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        pass

    path_str = path.as_posix()
    if len(path_str) >= 3 and path_str[1:3] == ":/":
        return f"/{path_str[0].lower()}{path_str[2:]}"
    return path_str


def _load_inventory() -> dict[str, object]:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


def _shard_map(inventory: dict[str, object]) -> dict[str, dict[str, object]]:
    shards = inventory["shards"]
    assert isinstance(shards, list)
    return {str(entry["name"]): entry for entry in shards if isinstance(entry, dict)}


def _alias_members(inventory: dict[str, object], alias_name: str) -> set[str]:
    aliases = inventory["aliases"]
    assert isinstance(aliases, dict)
    alias = aliases[alias_name]
    assert isinstance(alias, dict)
    expands_to = alias["expands_to"]
    assert isinstance(expands_to, list)
    return {str(name) for name in expands_to}


def _is_ignored_by_args(path: str, args: list[object]) -> bool:
    for arg in args:
        text = str(arg)
        if text == f"--ignore={path}":
            return True
        if text.startswith("--ignore-glob=") and fnmatch(path, text.split("=", 1)[1]):
            return True
    return False


def _shard_collects_path(shard: dict[str, object], path: str) -> bool:
    declared_paths = [str(item).rstrip("/") for item in shard["paths"]]
    if path in declared_paths:
        return True
    if "tests/architecture" not in declared_paths:
        return False
    args = shard.get("extra_pytest_args", [])
    assert isinstance(args, list)
    return not _is_ignored_by_args(path, args)


def _architecture_path_from_test_id(test_id: str) -> str | None:
    dotted_module = test_id.split("::", maxsplit=1)[0]
    if not dotted_module.startswith("tests.architecture."):
        return None

    parts = dotted_module.split(".")
    while len(parts) >= 3:
        candidate = Path(*parts).with_suffix(".py")
        if (ROOT / candidate).exists():
            return candidate.as_posix()
        parts.pop()
    return None


def _telemetry_hotspot_paths(
    *,
    telemetry: dict[str, object],
    min_duration_s: float,
) -> list[str]:
    rows = telemetry["top_slowest"]
    assert isinstance(rows, list)
    paths: list[str] = []
    for row in rows:
        assert isinstance(row, dict)
        duration_s = float(row["duration_s"])
        if duration_s < min_duration_s:
            continue
        path = _architecture_path_from_test_id(str(row["test"]))
        if path is None or path in paths:
            continue
        paths.append(path)
    return paths


@pytest.mark.architecture
def test_pytest_shard_inventory_declares_canonical_schema_and_aliases() -> None:
    inventory = _load_inventory()

    assert inventory["schema_version"] == 1
    assert inventory["source"] == "configs/quality/pytest_shards.yaml"

    shards = inventory["shards"]
    assert isinstance(shards, list)
    shard_names = [entry["name"] for entry in shards]
    assert shard_names == [
        "S1-domain-core",
        "S1-domain-services",
        "S2-comp-iface",
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a3",
        "S3-app-foundation",
        "S4-app-services",
        "S7-crosscutting-architecture-b",
        "S5-infra-adapters",
        "S6-crosscutting-unit",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-guardrails",
        "S8-crosscutting-governance",
        "S7-crosscutting-architecture-d",
    ]

    aliases = inventory["aliases"]
    assert aliases["S7-crosscutting-architecture"]["expands_to"] == [
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a3",
        "S7-crosscutting-architecture-b",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-d",
    ]
    assert aliases["S7-architecture-fast-boundary"]["expands_to"] == [
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a3",
        "S7-crosscutting-architecture-b",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-d",
    ]
    assert aliases["S7-architecture-slow-governance"]["expands_to"] == [
        "S7-crosscutting-architecture-guardrails",
    ]


@pytest.mark.architecture
def test_architecture_ci_matrix_matches_canonical_physical_shards() -> None:
    inventory = _load_inventory()
    workflow = yaml.safe_load(ARCHITECTURE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    arch_job = workflow["jobs"]["arch-tests"]
    matrix = arch_job["strategy"]["matrix"]["include"]
    expected = [
        *inventory["aliases"]["S7-architecture-fast-boundary"]["expands_to"],
        *inventory["aliases"]["S7-architecture-slow-governance"]["expands_to"],
    ]

    assert arch_job["strategy"]["fail-fast"] is False
    assert [entry["shard"] for entry in matrix] == expected
    assert [
        entry["shard"] for entry in matrix if entry["requires_lfs"]
    ] == ["S7-crosscutting-architecture-d"]

    lfs_step = next(
        step for step in arch_job["steps"] if step["name"].startswith("Fetch Git LFS")
    )
    assert lfs_step["if"] == "${{ matrix.requires_lfs }}"
    assert "import-contracts" in workflow["jobs"]["checks-complete"]["needs"]


@pytest.mark.architecture
def test_architecture_physical_shards_form_exact_file_union() -> None:
    inventory = _load_inventory()
    shards = _shard_map(inventory)
    physical_shards = [
        *inventory["aliases"]["S7-architecture-fast-boundary"]["expands_to"],
        *inventory["aliases"]["S7-architecture-slow-governance"]["expands_to"],
    ]
    test_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests/architecture").rglob("test_*.py")
    )
    owners = {
        path: [
            shard_name
            for shard_name in physical_shards
            if _shard_collects_path(shards[shard_name], path)
        ]
        for path in test_paths
    }

    assert all(len(path_owners) == 1 for path_owners in owners.values()), {
        path: path_owners
        for path, path_owners in owners.items()
        if len(path_owners) != 1
    }


@pytest.mark.architecture
def test_sharded_runner_loads_declarative_inventory_and_documents_path() -> None:
    runner = RUNNER_PATH.read_text(encoding="utf-8")
    guide = (ROOT / "docs/03-guides/testing.md").read_text(encoding="utf-8")
    dev_readme = (ROOT / "scripts/engineering/dev/README.md").read_text(
        encoding="utf-8"
    )

    assert "configs/quality/pytest_shards.yaml" in runner
    assert "load_shard_inventory" in runner
    assert "configs/quality/pytest_shards.yaml" in guide
    assert "configs/quality/pytest_shards.yaml" in dev_readme


@pytest.mark.architecture
def test_application_observability_unit_tests_are_tracked_in_app_shards() -> None:
    inventory = _load_inventory()
    shard_map = _shard_map(inventory)

    foundation_paths = shard_map["S3-app-foundation"]["paths"]

    assert "tests/unit/application/observability" in foundation_paths


@pytest.mark.architecture
def test_subprocess_heavy_architecture_tests_stay_in_slow_governance_shard() -> None:
    """Repo-wide scanner/generator tests must not leak into fast boundary shards."""
    inventory = _load_inventory()
    shards = _shard_map(inventory)
    rebalance = inventory["telemetry_rebalance"]
    assert isinstance(rebalance, dict)
    fast_shards = _alias_members(inventory, "S7-architecture-fast-boundary")
    slow_shards = _alias_members(inventory, "S7-architecture-slow-governance")
    slow_paths = {
        "tests/architecture/test_adr_enforcement_matrix.py",
        "tests/architecture/test_antipatterns.py",
        "tests/architecture/test_checkpoint_runtime_facade_usage.py",
        "tests/architecture/test_cli_command_import_guards.py",
        "tests/architecture/test_code_metrics.py",
        "tests/architecture/test_removed_surface_freeze_guards.py",
        "tests/architecture/test_config_discrepancy_metrics_ratchets.py",
        "tests/architecture/test_config_discrepancy_report_drift.py",
        "tests/architecture/test_config_root_governance.py",
        "tests/architecture/test_config_surface_entity_residual_plateau.py",
        "tests/architecture/test_contract_coverage_matrix_drift.py",
        "tests/architecture/test_layer_dependencies.py",
        "tests/architecture/test_lint_terminology_script.py",
        "tests/architecture/test_module_coverage_inventory_freshness.py",
        "tests/architecture/test_regression_metrics.py",
        "tests/architecture/test_scripts_deprecation_backlog.py",
        "tests/architecture/test_scripts_inventory_manifest.py",
        "tests/architecture/test_scripts_lifecycle_registry.py",
        "tests/architecture/test_test_structural_debt.py",
    }
    slow_paths.update(
        str(path) for path in rebalance["generated_architecture_hotspot_paths"]
    )

    declared_slow_paths: set[str] = set()
    for shard_name in slow_shards:
        paths = shards[shard_name]["paths"]
        assert isinstance(paths, list)
        declared_slow_paths.update(str(path) for path in paths)
    assert slow_paths <= declared_slow_paths

    for shard_name in fast_shards:
        args = shards[shard_name].get("extra_pytest_args", [])
        assert isinstance(args, list)
        missing_ignores = [
            path
            for path in slow_paths
            if not _is_ignored_by_args(path, args)
            and path not in shards[shard_name].get("paths", [])
        ]
        assert not missing_ignores, (
            f"{shard_name} must ignore subprocess-heavy slow governance tests: "
            f"{missing_ignores}"
        )


@pytest.mark.architecture
def test_architecture_shard_rebalance_manifest_matches_slow_test_telemetry() -> None:
    inventory = _load_inventory()
    rebalance = inventory["telemetry_rebalance"]
    assert isinstance(rebalance, dict)
    telemetry_path = ROOT / str(rebalance["source_report"])
    assert telemetry_path.exists()
    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    generated_paths = _telemetry_hotspot_paths(
        telemetry=telemetry,
        min_duration_s=float(rebalance["min_architecture_duration_s"]),
    )

    assert telemetry["profile_scope"] == "targeted_s7_governance_hotspots"
    assert telemetry["total_cases"] > 0
    assert telemetry["source_commit"] == rebalance["source_commit"]
    assert telemetry["source_run_id"] == rebalance["source_run_id"]
    assert telemetry["refreshed_at_utc"] == rebalance["refreshed_at_utc"]
    assert generated_paths == rebalance["generated_architecture_hotspot_paths"]

    shards = _shard_map(inventory)
    slow_shard = shards[str(rebalance["slow_governance_shard"])]
    slow_paths = {str(path) for path in slow_shard["paths"]}
    assert set(generated_paths) <= slow_paths


@pytest.mark.architecture
@_BASH_RUNNER_UNSUPPORTED_ON_WINDOWS
def test_sharded_runner_list_matches_inventory_order() -> None:
    inventory = _load_inventory()
    expected_names = [entry["name"] for entry in inventory["shards"]]

    result = subprocess.run(
        ["bash", _bash_runner_path(RUNNER_PATH), "--list"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    plan_lines = [
        line for line in result.stdout.splitlines() if re.match(r"^S\d-", line)
    ]
    actual_names = [line.split("  ", maxsplit=1)[0] for line in plan_lines]
    assert actual_names == expected_names


@pytest.mark.architecture
@_BASH_RUNNER_UNSUPPORTED_ON_WINDOWS
def test_sharded_runner_dry_run_expands_architecture_alias_from_inventory() -> None:
    inventory = _load_inventory()
    expected_shards = inventory["aliases"]["S7-crosscutting-architecture"]["expands_to"]
    result = subprocess.run(
        [
            "bash",
            _bash_runner_path(RUNNER_PATH),
            "--dry-run",
            "--shard",
            "S7-crosscutting-architecture",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    dry_run_lines = [
        line for line in result.stdout.splitlines() if line.startswith("[dry-run]")
    ]
    assert len(dry_run_lines) == len(expected_shards)
    assert all("run_pytest.sh --narrow" in line for line in dry_run_lines)
    assert all(
        f".coverage.{shard_name}" in line
        for shard_name, line in zip(expected_shards, dry_run_lines, strict=True)
    )
