"""Gates for architecture plan S4–S9 (#9600–#9605)."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa.report_lazy_import_inventory import (
    collect_lazy_imports,
    main as lazy_main,
)
from tests.architecture.quality_artifacts import load_quality_json

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


def test_s4_lazy_import_ratchet_is_shrink_only() -> None:
    config = yaml.safe_load(
        (ROOT / "configs/quality/lazy_import_ratchet.yaml").read_text(encoding="utf-8")
    )
    live = collect_lazy_imports()
    assert len(live) <= int(config["max_count"])
    assert len(live) == int(config["max_count"])
    assert lazy_main(["--check"]) == 0


def test_s6_source_tree_manifest_is_the_pinned_sha() -> None:
    from scripts.engineering.qa.report_source_tree_manifest import (
        build_manifest,
        main as manifest_main,
    )

    live = build_manifest()
    payload = load_quality_json("source-tree-manifest.json")
    assert payload["source_tree_sha256"] == live["source_tree_sha256"]
    assert payload["generated_from_manifest"] is True
    assert manifest_main(["--check"]) == 0
    helper_users = [
        path
        for path in (ROOT / "tests/architecture").rglob("*.py")
        if "quality_artifacts" in path.read_text(encoding="utf-8")
    ]
    assert len(helper_users) >= 15, len(helper_users)


def test_s5_service_access_seams_are_at_most_two() -> None:
    """Enforce the layered registry and composition seam contract from ADR-058."""
    files = sorted((ROOT / "src/bioetl/composition").glob("*service_access.py"))
    names = [path.name for path in files]
    assert names == [
        "control_plane_service_access.py",
        "health_service_access.py",
    ]
    from bioetl.application.ports import HealthServiceProtocol
    from bioetl.composition.entrypoints import resolve, register, registered_ports

    assert callable(resolve) and callable(register)
    assert set(registered_ports()) == {HealthServiceProtocol}
    api_files = sorted((ROOT / "src/bioetl/composition").glob("*_api.py"))
    assert [path.name for path in api_files] == [
        "execution_api.py",
        "health_api.py",
        "maintenance_api.py",
        "registry_api.py",
    ]


def test_s7_package_cohesion_budgets_are_not_exceeded() -> None:
    """Enforce the shrink-only package cohesion budgets from ADR-059."""
    config = yaml.safe_load(
        (ROOT / "configs/quality/package_cohesion_budget.yaml").read_text(
            encoding="utf-8"
        )
    )
    for row in config["packages"]:
        package = ROOT / row["path"]
        py_files = list(package.rglob("*.py"))
        loc = 0
        for path in py_files:
            loc += sum(
                1
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        assert len(py_files) <= int(row["max_modules"]), row["path"]
        assert loc <= int(row["max_package_loc"]), row["path"]


def test_s8_domain_framework_import_ratchet() -> None:
    config = yaml.safe_load(
        (ROOT / "configs/quality/domain_dataframe_zoning.yaml").read_text(
            encoding="utf-8"
        )
    )
    allowed = tuple(config["allowed_libraries"])
    domain = ROOT / "src/bioetl/domain"
    count = 0
    pandas_in_forbidden = []
    forbidden = tuple(config["pandas_forbidden_path_prefixes"])
    for path in domain.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module.split(".", 1)[0])
            for name in names:
                if name not in allowed:
                    continue
                count += 1
                if name == "pandas" and rel.startswith(forbidden):
                    pandas_in_forbidden.append(rel)
    assert count <= int(config["max_framework_imports"])
    assert not pandas_in_forbidden
    inventory = load_quality_json("module-coverage-inventory.json")
    summary = inventory["summary"]
    status = summary["status_counts"]
    doc = (ROOT / "docs/02-architecture/current-state-inventory.md").read_text(
        encoding="utf-8"
    )
    assert f"`{summary['source_module_count']}`" in doc
    assert f"`{status['fully_covered']}` fully covered" in doc
    assert f"`{status['partially_covered']}` partially covered" in doc


def test_s9_assertless_ratchet_and_expiry_dispersion() -> None:
    assertless = yaml.safe_load(
        (ROOT / "configs/quality/assertless_ratchet.yaml").read_text(encoding="utf-8")
    )
    assert int(assertless["max_assertless_tests"]) <= 102
    policy = yaml.safe_load(
        (ROOT / "configs/quality/layered_suffix_policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    dates: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "expires_on" in node:
                dates.append(str(node["expires_on"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(policy)
    counts = Counter(dates)
    assert dates
    assert max(counts.values()) <= 7
    assert len(counts) >= 4
