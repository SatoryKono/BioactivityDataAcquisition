"""Portable Windows Zed tasks and explicit pytest feedback modes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import venv
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]
ROOT = Path(__file__).resolve().parents[4]
QUICK_LABEL = "pytest: current test file (quick; project addopts disabled)"
PROJECT_LABEL = "pytest: current test file (project settings)"
TEMPLATE_ROOT = ROOT / "configs/ide/zed"
CACHE_OPTION = "cache_dir=.cache/pytest/windows"
PYTHON_COMMAND = "& (Join-Path $env:ZED_WORKTREE_ROOT '.venv-win\\Scripts\\python.exe')"
QUOTED_FILE = '"$env:ZED_FILE"'
BASE_LABELS = frozenset(
    {
        "Python: active project interpreter",
        "Environment: verify",
        PROJECT_LABEL,
        QUICK_LABEL,
        "Ruff: check current file",
        "Ruff: check formatting of current file",
    }
)


@pytest.fixture(params=("template", "local"))
def zed_config_root(request: pytest.FixtureRequest) -> Path:
    root = TEMPLATE_ROOT if request.param == "template" else ROOT / ".zed"
    for filename in ("settings.json", "tasks.json"):
        if request.param == "local" and not (root / filename).is_file():
            pytest.skip("Optional machine-local Zed settings/tasks are absent")
        assert (root / filename).is_file()
    return root


class ZedTask(TypedDict):
    label: str
    command: str
    args: list[str]
    cwd: str
    save: str
    reveal: str
    hide: str
    allow_concurrent_runs: bool
    env: NotRequired[dict[str, str]]
    tags: NotRequired[list[str]]


def _tasks(zed_root: Path = TEMPLATE_ROOT) -> list[ZedTask]:
    return cast(
        list[ZedTask],
        json.loads((zed_root / "tasks.json").read_text(encoding="utf-8")),
    )


def _powershell() -> str:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is not installed")
    return shell


def _shell_command(task: ZedTask) -> str:
    """Join command and args the way Zed's no-quote task spawn does."""
    return " ".join([task["command"], *task["args"]])


def test_task_commands_are_bound_to_the_current_checkout(zed_config_root: Path) -> None:
    tasks = _tasks(zed_config_root)
    labels = [task["label"] for task in tasks]
    assert len(set(labels)) == len(labels)
    by_label = {task["label"]: task for task in tasks}
    if zed_config_root == TEMPLATE_ROOT:
        assert set(labels) == BASE_LABELS
    else:
        assert BASE_LABELS <= set(labels)
    for label in BASE_LABELS:
        task = by_label[label]
        assert task["command"] == PYTHON_COMMAND
        assert task["cwd"] == "$ZED_WORKTREE_ROOT"
        assert task["allow_concurrent_runs"] is False
        assert task["hide"] == "never"
        assert task["reveal"] == "always"


def test_interpreter_task_preserves_python_code_in_powershell(
    zed_config_root: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("Project Zed tasks target native Windows .venv-win")
    executable = ROOT / ".venv-win/Scripts/python.exe"
    if not executable.is_file():
        pytest.skip("Optional local Windows project environment is absent")
    task = next(
        task
        for task in _tasks(zed_config_root)
        if task["label"] == "Python: active project interpreter"
    )
    env = os.environ.copy()
    env["ZED_WORKTREE_ROOT"] = str(ROOT)
    # Exercise shell parsing, not subprocess argv: semicolons must stay in -c.
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-Command", _shell_command(task)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) >= 2
    assert Path(lines[0]).resolve() == executable.resolve()
    assert "SyntaxError" not in result.stderr


def test_pytest_tasks_distinguish_quick_and_project_settings(
    zed_config_root: Path,
) -> None:
    tasks = {task["label"]: task for task in _tasks(zed_config_root)}
    quick = tasks[QUICK_LABEL]
    project = tasks[PROJECT_LABEL]
    assert quick["args"] == [
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "-p",
        "no:benchmark",
        "-o",
        CACHE_OPTION,
        QUOTED_FILE,
    ]
    assert project["args"] == ["-m", "pytest", "-o", CACHE_OPTION, QUOTED_FILE]
    for task in (quick, project):
        assert task["save"] == "current"
        assert task.get("env") == {
            "VCR_RECORD_MODE": "none",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    tagged = [
        task["label"]
        for task in tasks.values()
        if "python-test" in task.get("tags", [])
    ]
    assert tagged == [PROJECT_LABEL]


def test_ruff_tasks_use_the_project_python_module(zed_config_root: Path) -> None:
    tasks = {task["label"]: task for task in _tasks(zed_config_root)}
    assert tasks["Ruff: check current file"]["args"] == [
        "-m",
        "ruff",
        "check",
        QUOTED_FILE,
    ]
    assert tasks["Ruff: check formatting of current file"]["args"] == [
        "-m",
        "ruff",
        "format",
        "--check",
        QUOTED_FILE,
    ]


def test_lsp_uses_native_discovery_without_machine_paths(zed_config_root: Path) -> None:
    settings = json.loads(
        (zed_config_root / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["languages"]["Python"]["language_servers"] == [
        "basedpyright",
        "ruff",
    ]
    for server in ("basedpyright", "ruff"):
        assert "binary" not in settings.get("lsp", {}).get(server, {})
    assert settings["terminal"]["detect_venv"]["on"]["directories"] == [".venv-win"]
    assert "D:\\\\github" not in json.dumps(settings)


@pytest.fixture
def relocated_checkout(tmp_path: Path) -> Path:
    if os.name != "nt":
        pytest.skip("Project Zed tasks target native Windows .venv-win")
    root = tmp_path / "relocated checkout with spaces"
    venv.EnvBuilder(with_pip=False).create(root / ".venv-win")
    (root / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\n"
        'addopts = ["--strict-markers", "--strict-config", "--import-mode=importlib"]\n'
        'filterwarnings = ["error"]\n',
        encoding="utf-8",
    )
    return root


def _run_task(
    root: Path,
    label: str,
    source: str,
    *,
    autoload_plugins: bool = False,
) -> subprocess.CompletedProcess[str]:
    path = root / "test file with spaces.py"
    path.write_text(source, encoding="utf-8")
    task = next(task for task in _tasks() if task["label"] == label)
    env = os.environ.copy()
    env.update(task.get("env", {}))
    env["ZED_WORKTREE_ROOT"] = str(root)
    env["ZED_FILE"] = str(path)
    # Reuse installed pytest read-only; the disposable venv installs no packages.
    env["PYTHONPATH"] = str(Path(pytest.__file__).resolve().parents[1])
    if autoload_plugins:
        env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    else:
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run(
        [_powershell(), "-NoProfile", "-Command", _shell_command(task)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_project_task_runs_from_a_relocated_checkout(relocated_checkout: Path) -> None:
    result = _run_task(
        relocated_checkout,
        PROJECT_LABEL,
        "def test_settings(pytestconfig):\n"
        "    assert pytestconfig.getoption('strict_markers')\n"
        "    assert pytestconfig.getoption('strict_config')\n"
        "    assert pytestconfig.getoption('importmode') == 'importlib'\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_project_task_preserves_strict_markers(relocated_checkout: Path) -> None:
    result = _run_task(
        relocated_checkout,
        PROJECT_LABEL,
        "import pytest\n@pytest.mark.undeclared_marker\ndef test_marked():\n    assert True\n",
    )
    assert result.returncode != 0
    assert "undeclared_marker" in result.stdout + result.stderr


def test_quick_task_explicitly_disables_project_addopts(
    relocated_checkout: Path,
) -> None:
    result = _run_task(
        relocated_checkout,
        QUICK_LABEL,
        "def test_settings(pytestconfig):\n"
        "    assert not pytestconfig.getoption('strict_markers')\n"
        "    assert not pytestconfig.getoption('strict_config')\n"
        "    assert pytestconfig.getoption('importmode') == 'prepend'\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


@pytest.mark.parametrize("label", [PROJECT_LABEL, QUICK_LABEL])
def test_tasks_write_platform_cache_without_touching_old_cache(
    relocated_checkout: Path,
    label: str,
) -> None:
    old_cache = relocated_checkout / ".pytest_cache"
    old_cache.write_text("untouched cache sentinel", encoding="utf-8")
    result = _run_task(
        relocated_checkout,
        label,
        "def test_cache(pytestconfig):\n"
        "    assert pytestconfig.getini('cache_dir') == '.cache/pytest/windows'\n"
        "    assert pytestconfig.pluginmanager.hasplugin('cacheprovider')\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (relocated_checkout / ".cache/pytest/windows/v/cache/nodeids").is_file()
    assert old_cache.read_text(encoding="utf-8") == "untouched cache sentinel"


@pytest.mark.parametrize("label", [PROJECT_LABEL, QUICK_LABEL])
def test_cache_redirection_keeps_warnings_as_errors(
    relocated_checkout: Path, label: str
) -> None:
    result = _run_task(
        relocated_checkout,
        label,
        "import warnings\ndef test_warning():\n    warnings.warn('cache contract probe')\n",
    )
    assert result.returncode != 0
    assert "UserWarning: cache contract probe" in result.stdout + result.stderr


def test_interpreter_task_runs_when_checkout_contains_an_apostrophe(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("Project Zed tasks target native Windows .venv-win")
    root = tmp_path / "O'Brien checkout"
    venv.EnvBuilder(with_pip=False).create(root / ".venv-win")
    task = next(
        task
        for task in _tasks()
        if task["label"] == "Python: active project interpreter"
    )
    env = os.environ.copy()
    env["ZED_WORKTREE_ROOT"] = str(root)
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-Command", _shell_command(task)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "O'Brien checkout" in result.stdout
    assert "SyntaxError" not in result.stderr


def test_quick_task_keeps_benchmark_plugin_unloaded(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Project Zed tasks target native Windows .venv-win")
    project_python = ROOT / ".venv-win" / "Scripts" / "python.exe"
    if not project_python.is_file():
        pytest.skip("Optional local Windows project environment is absent")
    probe = subprocess.run(
        [
            str(project_python),
            "-c",
            "import importlib.util, sys; "
            "sys.exit(0 if importlib.util.find_spec('pytest_benchmark') else 1)",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if probe.returncode != 0:
        pytest.skip("pytest-benchmark is not installed")
    root = tmp_path / "O'Brien bench checkout"
    root.mkdir()
    link = root / ".venv-win"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(ROOT / ".venv-win")],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        pytest.skip("Could not link the project environment")
    try:
        (root / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\naddopts = []\n",
            encoding="utf-8",
        )
        result = _run_task(
            root,
            QUICK_LABEL,
            "def test_benchmark_stays_disabled(pytestconfig):\n"
            "    assert not pytestconfig.pluginmanager.hasplugin('benchmark')\n",
            autoload_plugins=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        subprocess.run(["cmd", "/c", "rmdir", str(link)], check=False)
