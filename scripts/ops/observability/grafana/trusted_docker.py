"""Resolve a protected Docker installation without trusting caller PATH."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def _windows_installation() -> Path:
    import winreg

    key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Docker Desktop"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as handle:
        directory, _ = winreg.QueryValueEx(handle, "InstallLocation")
    root = Path(directory)
    if not root.is_absolute():
        raise ValueError("Docker installation must be registered with an absolute path")
    return root


def _windows_signature(candidate: Path) -> dict:
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not 0 < length < len(buffer):
        raise ValueError("Cannot resolve the trusted Windows system directory")
    powershell = Path(buffer.value) / "WindowsPowerShell/v1.0/powershell.exe"
    literal = str(candidate).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop'; "
        "Import-Module ($PSHOME + '\\Modules\\Microsoft.PowerShell.Security\\Microsoft.PowerShell.Security.psd1'); "
        "Import-Module ($PSHOME + '\\Modules\\Microsoft.PowerShell.Utility\\Microsoft.PowerShell.Utility.psd1'); "
        f"$signature=Get-AuthenticodeSignature -LiteralPath '{literal}'; "
        "@{Status=$signature.Status.ToString(); Subject=$signature.SignerCertificate.Subject} "
        "| ConvertTo-Json -Compress"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    # A PowerShell 7 caller may export its module path. Windows PowerShell must
    # use its own protected system modules, never that inherited search path.
    environment = {**os.environ, "PSModulePath": str(powershell.parent / "Modules")}
    return json.loads(
        subprocess.check_output(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ],
            text=True,
            env=environment,
        )
    )


def _windows_docker() -> str:
    installation = _windows_installation().resolve()
    candidate = installation / "resources/bin/docker.exe"
    if not candidate.is_file() or not candidate.resolve().is_relative_to(installation):
        raise ValueError("Registered Docker executable is missing or redirected")
    signature = _windows_signature(candidate)
    if (
        signature.get("Status") != "Valid"
        or re.search(r"(?:^|,\s*)CN=Docker Inc(?:,|$)", signature.get("Subject") or "")
        is None
    ):
        raise ValueError("Docker executable must have a valid Docker Inc signature")
    return str(candidate)


def docker_path() -> str:
    if sys.platform == "win32":
        return _windows_docker()
    for candidate in (Path("/usr/bin/docker"), Path("/usr/local/bin/docker")):
        if candidate.is_file():
            resolved = candidate.resolve()
            for path in (resolved, *resolved.parents):
                info = path.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise ValueError(
                        "Docker executable path must be root-owned and protected"
                    )
            return str(resolved)
    raise ValueError("Docker is absent from the fixed trusted locations")
