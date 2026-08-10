"""Tests for the shared engineering platform abstraction."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from scripts.engineering.common.platform import (
    PlatformInfo,
    PlatformKind,
    detect_platform,
    ensure_user_executable,
    script_command,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("os_name", "sys_platform", "release", "environ", "expected"),
    [
        ("nt", "win32", "10", {}, PlatformKind.WINDOWS),
        ("posix", "linux", "6.8.0", {}, PlatformKind.LINUX),
        ("posix", "linux", "5.15.0-microsoft-standard", {}, PlatformKind.WSL),
        (
            "posix",
            "linux",
            "6.8.0",
            {"WSL_INTEROP": "/run/WSL/1"},
            PlatformKind.WSL,
        ),
        ("posix", "darwin", "24.0", {}, PlatformKind.MACOS),
        ("posix", "freebsd14", "14.0", {}, PlatformKind.OTHER_POSIX),
    ],
)
def test_detect_platform_is_deterministic(
    os_name: str,
    sys_platform: str,
    release: str,
    environ: dict[str, str],
    expected: PlatformKind,
) -> None:
    host = detect_platform(
        os_name=os_name,
        sys_platform=sys_platform,
        release=release,
        environ=environ,
    )
    assert host.kind is expected


def test_script_command_uses_native_shell() -> None:
    path = Path("scripts/example")
    windows = PlatformInfo(PlatformKind.WINDOWS, "nt", "win32", "fixture")
    linux = PlatformInfo(PlatformKind.LINUX, "posix", "linux", "fixture")

    assert script_command(path.with_suffix(".ps1"), host=windows) == [
        "powershell",
        "-NoLogo",
        "-NonInteractive",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(path.with_suffix(".ps1")),
    ]
    assert script_command(path.with_suffix(".sh"), host=linux) == [
        "bash",
        str(path.with_suffix(".sh")),
    ]


def test_ensure_user_executable_changes_only_posix_owner_bit(tmp_path: Path) -> None:
    script = tmp_path / "generated.sh"
    script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    script.chmod(stat.S_IRUSR | stat.S_IWUSR)
    linux = PlatformInfo(PlatformKind.LINUX, "posix", "linux", "fixture")

    ensure_user_executable(script, host=linux)

    assert script.stat().st_mode & stat.S_IXUSR
