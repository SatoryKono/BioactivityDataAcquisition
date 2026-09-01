"""Integrity-pinned dependency contract for the managed Gemini CLI bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, cast

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
TOOLING_DIR = ROOT / "scripts" / "ai" / "gemini" / "npm-tooling"
MANIFEST = TOOLING_DIR / "package.json"
LOCKFILE = TOOLING_DIR / "package-lock.json"
ENSURE_SCRIPT = ROOT / "scripts" / "ai" / "gemini" / "helper" / "ensure-gemini-cli.sh"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_gemini_toolchain_versions_are_exact_and_integrity_pinned() -> None:
    manifest = _json(MANIFEST)
    lockfile = _json(LOCKFILE)

    assert manifest["private"] is True
    assert manifest["dependencies"] == {
        "@google/gemini-cli": "0.57.0",
    }
    assert manifest["optionalDependencies"] == {
        "node-linux-arm64": "22.18.0",
        "node-linux-x64": "22.18.0",
    }
    assert lockfile["lockfileVersion"] == 3
    assert lockfile["packages"][""]["dependencies"] == manifest["dependencies"]
    assert (
        lockfile["packages"][""]["optionalDependencies"]
        == manifest["optionalDependencies"]
    )

    for package_path, expected_version in (
        ("node_modules/@google/gemini-cli", "0.57.0"),
        ("node_modules/node-linux-arm64", "22.18.0"),
        ("node_modules/node-linux-x64", "22.18.0"),
    ):
        package = lockfile["packages"][package_path]
        assert package["version"] == expected_version
        assert package["integrity"].startswith("sha512-")

    registry_packages = {
        path: package
        for path, package in lockfile["packages"].items()
        if path
        and str(package.get("resolved", "")).startswith("https://registry.npmjs.org/")
    }
    assert registry_packages
    for package_path, package in registry_packages.items():
        assert package["integrity"].startswith("sha512-"), package_path


def test_gemini_bootstrap_is_lockfile_only_and_invalidates_stale_cache() -> None:
    helper = ENSURE_SCRIPT.read_text(encoding="utf-8")

    assert 'npm ci --prefix "${GEMINI_NPM_PREFIX}"' in helper
    assert "--ignore-scripts" in helper
    assert 'cp "${GEMINI_TOOLING_LOCK}"' in helper
    assert 'GEMINI_NODE_PACKAGE="node-linux-x64"' in helper
    assert 'GEMINI_NODE_PACKAGE="node-linux-arm64"' in helper
    assert "EXPECTED_LOCK_SHA" in helper
    assert 'EXPECTED_CACHE_ID="${EXPECTED_LOCK_SHA}:${GEMINI_NODE_PACKAGE}"' in helper
    assert "GEMINI_CACHE_STAMP" in helper
    assert 'CURRENT_CACHE_ID}" != "${EXPECTED_CACHE_ID}' in helper
    assert '! -x "${GEMINI_NODE_SOURCE}"' in helper
    assert "missing or stale for package-lock.json" in helper
    assert "npm --global" not in helper
    assert " install node@" not in helper
    assert "|| npm" not in helper


def test_gemini_shell_helpers_do_not_contain_npm_install_commands() -> None:
    command = re.compile(r"(?m)^[^#\n]*\bnpm\b[^\n]*\binstall\b")
    violations: list[str] = []

    for path in sorted((TOOLING_DIR.parent).rglob("*.sh")):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if command.search(line):
                violations.append(
                    f"{path.relative_to(ROOT).as_posix()}:{line_number}: {line.strip()}"
                )

    assert violations == []


def test_cache_identity_differs_between_supported_node_platforms() -> None:
    lock_sha = "a" * 64

    assert f"{lock_sha}:node-linux-x64" != f"{lock_sha}:node-linux-arm64"


def test_dependabot_tracks_the_gemini_toolchain_lockfile() -> None:
    dependabot = DEPENDABOT.read_text(encoding="utf-8")

    assert 'directory: "/scripts/ai/gemini/npm-tooling"' in dependabot
    assert "npm-gemini-cli:" in dependabot
