"""Unit tests for the Zed environment doctor (stdlib-only helper)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEV_SCRIPTS = ROOT / "scripts" / "engineering" / "dev"

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def doctor_module():
    if str(DEV_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(DEV_SCRIPTS))
    from scripts.engineering.dev import zed_env_doctor

    return zed_env_doctor


def test_format_report_healthy(doctor_module) -> None:
    text = doctor_module.format_report([])
    assert "ok" in text
    assert "ModuleNotFoundError" not in text


def test_check_modules_missing(doctor_module) -> None:
    findings = doctor_module.check_modules(["no_such_package_for_zed_doctor_xyz"])
    assert findings[0].code == "missing_module"
    assert "setup_env_windows.ps1" in findings[0].recovery


def test_check_interpreter_missing_venv(doctor_module, tmp_path: Path) -> None:
    findings = doctor_module.check_interpreter(repo_root=tmp_path)
    assert findings[0].code == "missing_venv"


def test_ensure_ready_exits_without_traceback(
    doctor_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "diagnose",
        lambda **_kwargs: [
            doctor_module.Finding(
                code="missing_module",
                message="Required package is not importable: import-linter (importlinter)",
                recovery=r".\scripts\engineering\dev\setup_env_windows.ps1",
            )
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        doctor_module.ensure_ready(modules=("importlinter",))
    assert excinfo.value.code == 2


@pytest.fixture
def locked_tool(doctor_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "mypy"\nversion = "2.4.1"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(doctor_module.metadata, "version", lambda _name: "2.4.1")
    return tmp_path


def test_locked_versions_match(doctor_module, locked_tool: Path) -> None:
    assert doctor_module.check_locked_versions(("mypy",), repo_root=locked_tool) == []


def test_locked_versions_detect_drift(
    doctor_module, locked_tool: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor_module.metadata, "version", lambda _name: "2.4.0")
    findings = doctor_module.check_locked_versions(("mypy",), repo_root=locked_tool)
    assert len(findings) == 1
    assert findings[0].code == "locked_version_mismatch"
    assert "2.4.0" in findings[0].message
    assert "2.4.1" in findings[0].message
    assert "uv.lock" in findings[0].message
    assert "setup_env_windows.ps1" in findings[0].recovery


def test_locked_versions_missing_distribution(
    doctor_module, locked_tool: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(_name: str) -> str:
        raise doctor_module.metadata.PackageNotFoundError(_name)

    monkeypatch.setattr(doctor_module.metadata, "version", missing)
    findings = doctor_module.check_locked_versions(("mypy",), repo_root=locked_tool)
    assert findings[0].code == "missing_distribution"


@pytest.mark.parametrize(
    "contents",
    [
        None,
        "not valid TOML [",
        "version = 1\n",
        'package = "invalid"\n',
        'package = ["invalid"]\n',
        '[[package]]\nname = "mypy"\n',
        '[[package]]\nname = "mypy"\nversion = ["2.4.1"]\n',
        '[[package]]\nname = "mypy"\nversion = "2.4.1"\n'
        '[[package]]\nname = "mypy"\nversion = "2.5.0"\n',
    ],
)
def test_locked_versions_report_unusable_lock(
    doctor_module, tmp_path: Path, contents: str | None
) -> None:
    if contents is not None:
        (tmp_path / "uv.lock").write_text(contents, encoding="utf-8")
    findings = doctor_module.check_locked_versions(("mypy",), repo_root=tmp_path)
    assert len(findings) == 1
    assert findings[0].code == "invalid_lockfile"


def test_default_version_check_covers_ide_and_ci_tools(
    doctor_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = {"ruff", "mypy", "basedpyright", "pyrefly", "ty", "pytest"}
    (tmp_path / "uv.lock").write_text(
        "\n".join(
            f'[[package]]\nname = "{tool}"\nversion = "1.0"' for tool in sorted(tools)
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(doctor_module.metadata, "version", lambda _name: "0.9")
    findings = doctor_module.check_locked_versions(repo_root=tmp_path)
    assert {finding.message.split()[0] for finding in findings} == tools
    assert all(finding.code == "locked_version_mismatch" for finding in findings)


def test_locked_versions_only_inspect_selected_tools(
    doctor_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected(_name: str) -> str:
        pytest.fail("An unrelated module must not trigger version checks")

    monkeypatch.setattr(doctor_module.metadata, "version", unexpected)
    assert (
        doctor_module.check_locked_versions(("custom_module",), repo_root=tmp_path)
        == []
    )


def test_diagnose_includes_locked_version_drift(
    doctor_module, locked_tool: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(locked_tool)
    monkeypatch.setattr(doctor_module, "check_modules", lambda _modules: [])
    monkeypatch.setattr(doctor_module.metadata, "version", lambda _name: "2.4.0")
    findings = doctor_module.diagnose(
        modules=("mypy",), repo_root=locked_tool, skip_interpreter=True
    )
    assert [finding.code for finding in findings] == ["locked_version_mismatch"]
