#!/usr/bin/env python3
"""Cross-platform primitives shared by repository setup scripts.

Keep host detection and script-launch policy in one place so callers do not
grow independent ``os.name`` / ``sys.platform`` branches.  The helpers are
deliberately side-effect free except for :func:`ensure_user_executable`.
"""

from __future__ import annotations

import os
import platform as stdlib_platform
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PlatformKind(StrEnum):
    """Supported host families for engineering scripts."""

    WINDOWS = "windows"
    WSL = "wsl"
    LINUX = "linux"
    MACOS = "macos"
    OTHER_POSIX = "other-posix"


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    """Normalized host capabilities used by cross-platform launchers."""

    kind: PlatformKind
    os_name: str
    sys_platform: str
    release: str

    @property
    def is_windows(self) -> bool:
        """Return whether commands execute in a native Windows process."""

        return self.kind is PlatformKind.WINDOWS

    @property
    def is_wsl(self) -> bool:
        """Return whether commands execute in Windows Subsystem for Linux."""

        return self.kind is PlatformKind.WSL

    @property
    def is_posix(self) -> bool:
        """Return whether POSIX shell and permission semantics are available."""

        return not self.is_windows

    @property
    def script_suffix(self) -> str:
        """Return the native repository wrapper suffix."""

        return ".ps1" if self.is_windows else ".sh"

    @property
    def script_shell(self) -> str:
        """Return the native repository wrapper shell."""

        return "powershell" if self.is_windows else "bash"

    @property
    def wrapper_platform(self) -> str:
        """Return the legacy setup-mcp platform key."""

        return "nt" if self.is_windows else "posix"


def detect_platform(
    *,
    os_name: str | None = None,
    sys_platform: str | None = None,
    release: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> PlatformInfo:
    """Detect Windows, WSL, Linux, macOS, or another POSIX host.

    Optional inputs make the decision deterministic in unit tests and in
    platform compatibility probes; production callers normally pass nothing.
    """

    resolved_os_name = os_name if os_name is not None else os.name
    resolved_sys_platform = sys_platform if sys_platform is not None else sys.platform
    resolved_release = release if release is not None else stdlib_platform.release()
    resolved_environ = environ if environ is not None else os.environ

    if resolved_os_name == "nt" or resolved_sys_platform.startswith("win"):
        kind = PlatformKind.WINDOWS
    elif resolved_sys_platform == "darwin":
        kind = PlatformKind.MACOS
    elif resolved_sys_platform.startswith("linux"):
        release_lower = resolved_release.lower()
        is_wsl = (
            "microsoft" in release_lower
            or bool(resolved_environ.get("WSL_DISTRO_NAME"))
            or bool(resolved_environ.get("WSL_INTEROP"))
        )
        kind = PlatformKind.WSL if is_wsl else PlatformKind.LINUX
    else:
        kind = PlatformKind.OTHER_POSIX

    return PlatformInfo(
        kind=kind,
        os_name=resolved_os_name,
        sys_platform=resolved_sys_platform,
        release=resolved_release,
    )


def script_command(path: Path, *, host: PlatformInfo | None = None) -> list[str]:
    """Build a shell invocation for a trusted repository script path."""

    resolved_host = host or detect_platform()
    if resolved_host.is_windows:
        return [
            "powershell",
            "-NoLogo",
            "-NonInteractive",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(path),
        ]
    return ["bash", str(path)]


def ensure_user_executable(
    path: Path, *, host: PlatformInfo | None = None
) -> None:
    """Add only the POSIX owner execute bit; native Windows needs no chmod."""

    resolved_host = host or detect_platform()
    if resolved_host.is_windows:
        return
    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR)
