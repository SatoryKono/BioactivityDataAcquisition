"""Verify the hash-locked package closure before importing any Fetch code.

The owning CLI emits measurement originals and accepts individually reviewed
profiles. Normal startup never learns, updates or falls back from these pins.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import secrets
import stat
import sys

HERE = Path(__file__).resolve().parent
LOCK = HERE / "public-fetch-requirements.txt"
PROFILES = HERE / "public-fetch-runtime-profiles.json"
_DLL_HANDLES: list[object] = []


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_directory() -> Path:
    root = Path(sys.executable).absolute().parent.parent
    if not (root / "pyvenv.cfg").is_file():
        raise RuntimeError("Use the isolated Fetch environment")
    site = root / (
        "Lib/site-packages" if os.name == "nt" else "lib/python3.13/site-packages"
    )
    if site.resolve(strict=True) != site:
        raise RuntimeError("Linked Fetch package directory refused")
    return site


def package_file_sha(path: Path) -> str | None:
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError("Non-regular Fetch package file refused")
    if path.suffix in {".pyc", ".pyo"}:
        raise RuntimeError("Sourceless Fetch bytecode refused")
    if path.parent.name.endswith(".dist-info") and path.name in {
        "RECORD",
        "INSTALLER",
        "REQUESTED",
        "direct_url.json",
    }:
        # These installer receipts are not loaded and contain local paths.
        return None
    return _sha(path)


def package_files(site: Path) -> dict[str, str]:
    """Measure only regular package files, rejecting linked or executable caches."""
    files: dict[str, str] = {}
    for current, directories, names in os.walk(site, followlinks=False):
        directory = Path(current)
        for name in directories:
            child = directory / name
            if child.is_symlink() or child.is_junction():
                raise RuntimeError("Linked Fetch package subtree refused")
        directories[:] = sorted(name for name in directories if name != "__pycache__")
        for name in sorted(names):
            path = directory / name
            digest = package_file_sha(path)
            if digest is not None:
                files[path.relative_to(site).as_posix()] = digest
    return files


def package_versions(site: Path) -> dict[str, str]:
    packages: dict[str, str] = {}
    for distribution in importlib.metadata.distributions(path=[str(site)]):
        name = distribution.metadata["Name"].lower().replace("_", "-")
        if name in packages:
            raise RuntimeError("Duplicate Fetch distribution")
        packages[name] = distribution.version
    if (
        packages.get("mcp-server-fetch") != "2026.11.4"
        or packages.get("mcp") != "2.3.0"
    ):
        raise RuntimeError("Pinned Fetch distributions missing")
    return dict(sorted(packages.items()))


def measure_runtime(*, include_files: bool = False) -> dict[str, object]:
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("Fetch requires Python 3.13")
    architecture = platform.machine().lower()
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(
        architecture, architecture
    )
    key = sys.platform + "-" + architecture
    if key not in {"win32-x86_64", "linux-x86_64", "linux-aarch64"}:
        raise RuntimeError("Unqualified Fetch platform")
    site = package_directory()
    files = package_files(site)
    packages = package_versions(site)
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    result: dict[str, object] = {
        "platform": key,
        "python_minor": "3.13",
        "requirements_sha256": _sha(LOCK),
        "file_count": len(files),
        "files_sha256": hashlib.sha256(canonical).hexdigest(),
        "packages": dict(sorted(packages.items())),
    }
    if include_files:
        result["files"] = dict(sorted(files.items()))
    return result


def bootstrap() -> None:
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError("Use pinned Python with -I -S -B")
    actual = measure_runtime()
    expected = json.loads(PROFILES.read_text(encoding="utf-8"))
    if expected.get("schema_version") != 1 or expected.get(
        "requirements_sha256"
    ) != _sha(LOCK):
        raise RuntimeError("Fetch runtime profile lock changed")
    if expected.get("profiles", {}).get(actual["platform"]) != actual:
        raise RuntimeError("Fetch package closure changed or has no reviewed profile")
    site = package_directory()
    # -B prevents writes, but ordinarily still reads cached bytecode. A fresh
    # unused prefix disables those reads too, without deleting any cache files.
    sys.pycache_prefix = str(site.parent / "unused-bytecode" / secrets.token_hex(16))
    sys.path.append(str(site))
    if os.name == "nt":
        # Only for native qualification; the production launcher stays Linux-only.
        for relative in ("win32", "win32/lib"):
            path = site / relative
            if path.is_dir():
                sys.path.append(str(path))
        dlls = site / "pywin32_system32"
        if dlls.is_dir():
            _DLL_HANDLES.append(os.add_dll_directory(str(dlls)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--emit-profile", type=Path)
    actions.add_argument("--accept-profile", type=Path)
    args = parser.parse_args()
    if args.emit_profile:
        with args.emit_profile.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(
                measure_runtime(include_files=True), output, indent=2, sort_keys=True
            )
            output.write("\n")
    else:
        original = json.loads(args.accept_profile.read_text(encoding="utf-8"))
        if original.get("requirements_sha256") != _sha(LOCK):
            raise RuntimeError("Review profile from the current requirements lock")
        files = original.pop("files")
        encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        if (
            hashlib.sha256(encoded).hexdigest() != original["files_sha256"]
            or len(files) != original["file_count"]
        ):
            raise RuntimeError("Runtime profile original is inconsistent")
        payload = (
            (json.loads(PROFILES.read_text(encoding="utf-8")))
            if PROFILES.exists()
            else {
                "schema_version": 1,
                "requirements_sha256": _sha(LOCK),
                "profiles": {},
            }
        )
        if payload["requirements_sha256"] != _sha(LOCK):
            raise RuntimeError("Requalify all profiles after dependency changes")
        payload["profiles"][original["platform"]] = original
        with PROFILES.open("w", encoding="utf-8", newline="\n") as output:
            json.dump(payload, output, indent=2, sort_keys=True)
            output.write("\n")


if __name__ == "__main__":
    main()
