"""Source-only dependency selection without collecting or running the suite."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.ci import _python_dependency_changes as dependencies
from scripts.engineering.ci import pr_lane_results as lane

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _distribution_owners(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use deterministic package ownership metadata, never name guessing."""
    monkeypatch.setattr(
        dependencies,
        "packages_distributions",
        lambda: {
            "httpx": ["httpx"],
            "polars": ["polars"],
            "pyarrow": ["pyarrow"],
            "syrupy": ["syrupy"],
        },
    )
    monkeypatch.setattr(
        dependencies, "distribution", lambda name: SimpleNamespace(entry_points=[])
    )


def test_pytest_helper_uses_canonical_all_tests_lane(tmp_path: Path) -> None:
    _consumer(tmp_path, "tests/helpers/publication_fixtures.py", "pytest")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"pytest"}
    ) == ["tests"]


@pytest.mark.parametrize(
    "plugin", ["pytest-cov", "pytest-xdist", "pytest-timeout", "pytest-recording"]
)
def test_entrypoint_plugin_uses_canonical_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plugin: str
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        dependencies,
        "distribution",
        lambda name: SimpleNamespace(entry_points=[SimpleNamespace(group="pytest11")]),
    )
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={plugin}
    ) == ["tests"]


@pytest.mark.parametrize("dependency_changed", [False, True])
def test_pytest_config_change_retains_required_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dependency_changed: bool,
) -> None:
    (tmp_path / "tests").mkdir()

    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "uv.lock":
            return {}
        spec = "httpx>=0.29" if dependency_changed and sha == "head" else "httpx>=0.28"
        return {
            "project": {"dependencies": [spec]},
            "tool": {
                "pytest": {
                    "ini_options": {"addopts": "-q" if sha == "base" else "-q -ra"}
                }
            },
        }

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert (
        lane.main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                "pyproject.toml",
                "--base-sha",
                "base",
                "--head-sha",
                "head",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines() == ["tests"]


def test_unknown_mixed_configuration_does_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "uv.lock":
            return {}
        return {
            "project": {
                "dependencies": ["httpx>=0.28" if sha == "base" else "httpx>=0.29"]
            },
            "tool": {"ruff": {"line-length": 88 if sha == "base" else 100}},
        }

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert (
        lane.main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                "pyproject.toml",
                "--base-sha",
                "base",
                "--head-sha",
                "head",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "tool.ruff.line-length" in captured.err
    assert not captured.out


def test_uv_constraint_dependencies_select_the_pytest_family_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "uv.lock").write_text(
        "\n".join(
            (
                "version = 1",
                "[[package]]",
                'name = "pytest"',
                'dependencies = [{name = "packaging"}]',
                "[[package]]",
                'name = "packaging"',
                'version = "26.3"',
                "",
            )
        ),
        encoding="utf-8",
    )

    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "uv.lock":
            version = "26.2" if sha == "base" else "26.3"
            return {
                "package": [
                    {"name": "pytest", "dependencies": [{"name": "packaging"}]},
                    {"name": "packaging", "version": version},
                ]
            }
        document: dict = {"project": {"dependencies": []}}
        if sha == "head":
            document["tool"] = {
                "uv": {"constraint-dependencies": ["virtualenv>=21.14.7"]}
            }
        return document

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert (
        lane.main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                "pyproject.toml",
                "--changed-file",
                "uv.lock",
                "--base-sha",
                "base",
                "--head-sha",
                "head",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines() == ["tests"]


def test_malformed_uv_constraint_stays_unconfirmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "uv.lock":
            return {}
        if sha == "base":
            return {"project": {"dependencies": ["httpx>=0.28"]}}
        return {
            "project": {"dependencies": ["httpx>=0.28"]},
            "tool": {"uv": {"constraint-dependencies": {"virtualenv": ">=21.14.7"}}},
        }

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert (
        lane.main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                "pyproject.toml",
                "--base-sha",
                "base",
                "--head-sha",
                "head",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "tool.uv.constraint-dependencies" in captured.err
    assert not captured.out


def test_uv_constraint_without_lock_delta_is_still_a_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "uv.lock":
            return {"package": [{"name": "virtualenv", "version": "21.14.12"}]}
        document: dict = {"project": {"dependencies": []}}
        if sha == "head":
            document["tool"] = {
                "uv": {"constraint-dependencies": ["virtualenv>=21.14.7"]}
            }
        return document

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert dependencies.changed_dependencies(tmp_path, "base", "head") == {"virtualenv"}


def test_removed_package_without_head_metadata_gets_broad_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tests").mkdir()

    def revision(root: Path, sha: str, name: str) -> dict:
        if name == "pyproject.toml":
            return {}
        return (
            {"package": [{"name": "removed-distribution", "version": "1"}]}
            if sha == "base"
            else {}
        )

    monkeypatch.setattr(dependencies, "_read_revision", revision)
    assert (
        lane.main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                "uv.lock",
                "--base-sha",
                "base",
                "--head-sha",
                "head",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines() == ["tests"]


def _consumer(root: Path, source: str, imported: str) -> None:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"import {imported}\n", encoding="utf-8")


def _optional_distribution(root: Path, adapter: str) -> None:
    script = root / "scripts/ai/agent_tools/__main__.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(adapter, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "\n".join(
            (
                "[project]",
                'name = "bioetl"',
                "dependencies = []",
                "[project.optional-dependencies]",
                'proofagent = ["proofagent-harness==0.13.0"]',
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "uv.lock").write_text(
        "\n".join(
            (
                "version = 1",
                "[[package]]",
                'name = "proofagent-harness"',
                'dependencies = [{name = "litellm"}]',
                "[[package]]",
                'name = "litellm"',
                'dependencies = [{name = "aiohttp"}]',
                "[[package]]",
                'name = "aiohttp"',
                'dependencies = [{name = "yarl"}]',
                "[[package]]",
                'name = "yarl"',
                'version = "1.25.1"',
                "",
            )
        ),
        encoding="utf-8",
    )


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


def test_transitive_optional_dependency_uses_declared_reference(
    tmp_path: Path,
) -> None:
    _optional_distribution(tmp_path, 'Adapter(distribution="proofagent-harness")\n')
    _consumer(
        tmp_path,
        "tests/unit/scripts/ai/agent_tools/test_cli.py",
        "scripts.ai.agent_tools.__main__",
    )
    assert dependencies.dependency_consumers(tmp_path, {"aiohttp", "yarl"}) == [
        "scripts/ai/agent_tools/__main__.py"
    ]
    assert lane.affected_pytest_targets(
        ["uv.lock"],
        repo_root=tmp_path,
        changed_python_dependencies={"aiohttp", "yarl"},
    ) == ["tests/unit/scripts/ai/agent_tools/test_cli.py"]


@pytest.mark.parametrize("package", ["aiohttp", "yarl"])
def test_import_and_declared_reference_consumers_are_combined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, package: str
) -> None:
    _optional_distribution(tmp_path, 'Adapter(distribution="proofagent-harness")\n')
    _consumer(tmp_path, "src/bioetl/infrastructure/client.py", "aiohttp")
    _consumer(
        tmp_path,
        "tests/unit/scripts/ai/agent_tools/test_cli.py",
        "scripts.ai.agent_tools.__main__",
    )
    (tmp_path / "tests/unit/infrastructure").mkdir(parents=True)
    monkeypatch.setattr(
        dependencies, "packages_distributions", lambda: {"aiohttp": ["aiohttp"]}
    )

    assert dependencies.dependency_consumers(tmp_path, {package}) == [
        "scripts/ai/agent_tools/__main__.py",
        "src/bioetl/infrastructure/client.py",
    ]
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={package}
    ) == [
        "tests/unit/scripts/ai/agent_tools/test_cli.py",
        "tests/unit/infrastructure",
    ]


@pytest.mark.parametrize(
    "adapter",
    [
        '"""proofagent-harness"""\n',
        'DISTRIBUTION = "proofagent-harness"\n',
        'Adapter("proofagent-harness")\n',
        'Adapter(name="proofagent-harness")\n',
        "Adapter(distribution=42)\n",
        'Adapter(distribution="aiohttp")\n',
    ],
)
def test_unconfirmed_distribution_reference_fails_closed(
    tmp_path: Path, adapter: str
) -> None:
    _optional_distribution(tmp_path, adapter)
    _consumer(
        tmp_path,
        "tests/unit/scripts/ai/agent_tools/test_cli.py",
        "scripts.ai.agent_tools.__main__",
    )
    with pytest.raises(ValueError, match="Unconfirmed.*aiohttp"):
        lane.affected_pytest_targets(
            ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"aiohttp"}
        )


def test_transitive_name_mention_without_declared_parent_fails_closed(
    tmp_path: Path,
) -> None:
    _optional_distribution(tmp_path, 'CLIENT = "aiohttp"\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "bioetl"\ndependencies = []\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unconfirmed.*aiohttp"):
        dependencies.dependency_consumers(tmp_path, {"aiohttp"})


def test_declared_distribution_without_source_reference_fails_closed(
    tmp_path: Path,
) -> None:
    _optional_distribution(tmp_path, "EXECUTABLE = 'proof'\n")
    with pytest.raises(ValueError, match="Unconfirmed.*aiohttp"):
        dependencies.dependency_consumers(tmp_path, {"aiohttp"})


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


def test_test_only_dependency_selects_its_consumers(tmp_path: Path) -> None:
    _consumer(tmp_path, "tests/unit/test_snapshot.py", "syrupy")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"syrupy"}
    ) == ["tests/unit/test_snapshot.py"]


def test_import_name_is_not_assumed_to_equal_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _consumer(tmp_path, "src/bioetl/infrastructure/consumer.py", "unknown_package")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unconfirmed.*unknown-package"):
        lane.affected_pytest_targets(
            ["uv.lock"],
            repo_root=tmp_path,
            changed_python_dependencies={"unknown-package"},
        )


@pytest.mark.parametrize("command", ["ruff", "mypy", "twine", "pip-audit", "bandit"])
def test_repository_console_tool_uses_canonical_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    workflow = tmp_path / ".github/workflows/owner.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        f"jobs:\n  owner:\n    steps:\n      - run: uv run --frozen {command} --version\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dependencies,
        "distribution",
        lambda name: SimpleNamespace(
            entry_points=[SimpleNamespace(group="console_scripts", name=command)]
        ),
    )
    assert lane.affected_pytest_targets(
        ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={command}
    ) == ["tests"]


def test_console_entrypoint_without_workflow_owner_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        dependencies,
        "distribution",
        lambda name: SimpleNamespace(
            entry_points=[
                SimpleNamespace(group="console_scripts", name="unowned-command")
            ]
        ),
    )
    with pytest.raises(
        ValueError, match="Unconfirmed Python dependency consumer route: unowned"
    ):
        lane.affected_pytest_targets(
            ["uv.lock"], repo_root=tmp_path, changed_python_dependencies={"unowned"}
        )


@pytest.mark.parametrize(
    "helper,suite",
    [
        ("tests/helpers/control_plane_replay.py", "tests"),
        ("tests/contract/_provider_contract_replay.py", "tests/contract"),
    ],
)
def test_shared_dependency_helper_uses_complete_owner_suite(
    tmp_path: Path, helper: str, suite: str
) -> None:
    _consumer(tmp_path, helper, "yaml")
    test = tmp_path / (
        "tests/unit/test_consumer.py"
        if suite == "tests"
        else "tests/contract/test_consumer.py"
    )
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_text("def test_consumer(): pass\n", encoding="utf-8")
    assert lane._consumer_targets(helper, tmp_path, {}) == [suite]


def test_shared_helper_without_any_tests_fails_closed(tmp_path: Path) -> None:
    _consumer(tmp_path, "tests/helpers/control_plane_replay.py", "yaml")
    with pytest.raises(ValueError, match="test-helper owner route"):
        lane._consumer_targets("tests/helpers/control_plane_replay.py", tmp_path, {})


def test_native_cli_record_uses_workflow_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = tmp_path / ".github/workflows/owner.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  owner:\n    steps:\n      - run: uv run --frozen ruff check src\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dependencies,
        "distribution",
        lambda name: SimpleNamespace(
            entry_points=[], files=[Path("../../../bin/ruff")]
        ),
    )
    assert dependencies.repository_cli_affected(tmp_path, {"ruff"})
