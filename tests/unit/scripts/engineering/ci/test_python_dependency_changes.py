"""Source-only dependency selection without collecting or running the suite."""

from pathlib import Path

import pytest

from scripts.engineering.ci import _python_dependency_changes as dependencies
from scripts.engineering.ci import pr_lane_results as lane

pytestmark = pytest.mark.unit


def _consumer(root: Path, source: str, imported: str) -> None:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"import {imported}\n", encoding="utf-8")


@pytest.mark.parametrize(
    "package,imported,owner",
    [
        ("httpx", "httpx", "infrastructure"),
        ("polars", "polars", "application"),
        ("pyarrow", "pyarrow", "infrastructure"),
    ],
)
def test_dependency_consumers_reuse_source_routes(
    tmp_path: Path, package: str, imported: str, owner: str
) -> None:
    _consumer(tmp_path, f"src/bioetl/{owner}/consumer.py", imported)
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (tmp_path / f"tests/unit/{owner}").mkdir(parents=True)
    targets = lane.affected_pytest_targets(
        ["uv.lock", "pyproject.toml"],
        repo_root=tmp_path,
        changed_python_dependencies={package},
    )
    assert targets == [f"tests/unit/{owner}"]


def test_transitive_dependency_selects_direct_consumer(tmp_path: Path) -> None:
    _consumer(tmp_path, "src/bioetl/infrastructure/http/client.py", "httpx")
    (tmp_path / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "httpx"\ndependencies = [{name = "httpcore"}]\n',
        encoding="utf-8",
    )
    assert dependencies.dependency_consumers(tmp_path, {"httpcore"}) == [
        "src/bioetl/infrastructure/http/client.py"
    ]


def test_curated_http_owner_tests_are_required(tmp_path: Path) -> None:
    _consumer(tmp_path, "src/bioetl/infrastructure/adapters/http/client.py", "httpx")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    inventory = tmp_path / "configs/quality/source_test_owner_inventory.yaml"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        "modules:\n  - source: src/bioetl/infrastructure/adapters/http/client.py\n    owner_tests: [tests/unit/infrastructure/adapters/http/test_client.py]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="test_client.py"):
        lane.affected_pytest_targets(
            ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"httpx"}
        )
    target = tmp_path / "tests/unit/infrastructure/adapters/http/test_client.py"
    target.parent.mkdir(parents=True)
    target.write_text("def test_client(): pass\n", encoding="utf-8")
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"httpx"}
    ) == [target.relative_to(tmp_path).as_posix()]


def test_unknown_dependency_route_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unconfirmed.*unknown-package"):
        lane.affected_pytest_targets(
            ["uv.lock"],
            repo_root=tmp_path,
            changed_python_dependencies={"unknown-package"},
        )


def test_changed_lock_versions_and_wheels_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "pyproject.toml":
            return {"project": {"dependencies": ["httpx>=0.28"]}}
        return {
            "package": [
                {"name": "httpx", "version": "0.28" if sha == "base" else "0.29"}
            ]
        }

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert dependencies.changed_dependencies(tmp_path, "base", "head") == {"httpx"}


def test_configuration_only_change_is_not_a_dependency_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dependencies, "_read_revision", lambda *args: {})
    with pytest.raises(ValueError, match="own classified route"):
        dependencies.changed_dependencies(tmp_path, "base", "head")
