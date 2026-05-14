"""Guardrails for the canonical pytest configuration source."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEGACY_PYTEST_CONFIG_SECTIONS = (
    (ROOT / "setup.cfg", "[tool:pytest]"),
    (ROOT / "tox.ini", "[pytest]"),
)


def test_pyproject_is_the_only_root_pytest_config() -> None:
    """pytest.ini must not shadow the canonical pyproject.toml pytest section."""
    assert not (ROOT / "pytest.ini").exists(), (
        "Keep pytest configuration in pyproject.toml [tool.pytest.ini_options]; "
        "a root pytest.ini overrides pyproject.toml and causes policy drift."
    )


def test_pyproject_declares_required_pytest_policy() -> None:
    """The canonical pytest config must keep strict and replay-safe defaults."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.pytest.ini_options]" in pyproject
    assert '"--strict-markers"' in pyproject
    assert '"--strict-config"' in pyproject
    assert '"--import-mode=importlib"' in pyproject
    assert "timeout = 60" in pyproject


def test_legacy_pytest_config_sections_do_not_shadow_pyproject() -> None:
    """Legacy pytest config files must not reintroduce a second config source."""
    offenders: list[str] = []
    for config_path, section_header in LEGACY_PYTEST_CONFIG_SECTIONS:
        if not config_path.exists():
            continue
        if section_header in config_path.read_text(encoding="utf-8"):
            offenders.append(f"{config_path.name}: {section_header}")

    assert not offenders, (
        "Keep pytest policy in pyproject.toml only; remove legacy config sections:\n"
        + "\n".join(f"  - {offender}" for offender in offenders)
    )
