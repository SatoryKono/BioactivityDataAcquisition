"""Setuptools backend with an explicit source-only quality-tooling closure.

Wheel discovery remains owned by setuptools and restricted to src. The sdist
also supports repository quality imports, path contracts and report generators;
its receipt lists the exact support files instead of borrowing a checkout.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from setuptools import build_meta as _backend

build_wheel = _backend.build_wheel
build_editable = _backend.build_editable
get_requires_for_build_wheel = _backend.get_requires_for_build_wheel
get_requires_for_build_editable = _backend.get_requires_for_build_editable
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _backend.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _backend.prepare_metadata_for_build_editable

_RECEIPT = "quality-tooling-support.json"
_BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bmp",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".parquet",
    ".pdf",
    ".png",
    ".tar",
    ".tgz",
    ".wav",
    ".webm",
    ".webp",
    ".whl",
    ".xz",
    ".zip",
}
_SUPPORT_ROOTS = {
    "src",
    "scripts",
    "configs",
    "docs",
    "tests",
    "grafana",
    ".github",
    ".circleci",
    ".zed",
    ".codex",
    ".junie",
}


def _supported_path(path: str) -> bool:
    candidate = Path(path)
    if (
        not candidate.parts
        or candidate.is_absolute()
        or ".." in candidate.parts
        or any(p.startswith(".env") for p in candidate.parts)
    ):
        return False
    if candidate.parts[:2] == ("docs", "99-archive"):
        return False  # Historical evidence is not an active tooling input.
    if path in {
        "uv.lock",
        ".importlinter",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "Makefile",
        "makefile",
        ".pre-commit-config.yaml",
    }:
        return True
    if candidate.suffix.lower() in _BINARY_SUFFIXES:
        return False
    if candidate.parts[0] in _SUPPORT_ROOTS:
        return True
    if candidate.parts[:2] == ("reports", "observability"):
        return True
    return candidate.parts[:2] == ("reports", "quality") and (
        len(candidate.parts) == 3 or candidate.parts[2] == "quality-move-qm01"
    )


def _git_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }


def _support_paths(root: Path) -> list[str]:
    receipt = root / _RECEIPT
    if receipt.is_file():
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        return sorted(payload["files"])
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        env=_git_environment(),
    )
    return sorted(
        name
        for name in result.stdout.decode("utf-8").split("\0")
        if name and _supported_path(name)
    )


def _canonical_mode(mode: int) -> int:
    """Keep executability without carrying setuid, setgid or sticky bits."""
    return 0o755 if mode & 0o111 else 0o644


def _receipt_modes(
    root: Path, paths: list[str], payload: dict[str, object]
) -> dict[str, int]:
    modes = payload.get("file_modes")
    if modes is None:
        # Legacy receipts lack Git mode metadata; preserve the extracted mode.
        return {name: _canonical_mode((root / name).stat().st_mode) for name in paths}
    if not isinstance(modes, dict):
        raise ValueError("Source-tooling file_modes must be a mapping")
    result = {}
    for name in paths:
        mode = modes.get(name)
        if type(mode) is not int or mode not in {0o644, 0o755}:
            raise ValueError(f"Missing or invalid source-tooling mode: {name}")
        result[name] = mode
    return result


def _support_modes(root: Path, paths: list[str]) -> dict[str, int]:
    receipt = root / _RECEIPT
    if receipt.is_file():
        return _receipt_modes(
            root, paths, json.loads(receipt.read_text(encoding="utf-8"))
        )
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        env=_git_environment(),
    )
    selected = set(paths)
    modes = {}
    for record in result.stdout.decode("utf-8").split("\0"):
        header, _, name = record.partition("\t")
        if name not in selected:
            continue
        mode, _, stage = header.split()
        if mode not in {"100644", "100755"} or stage != "0":
            raise ValueError(f"Unsupported or unmerged source-tooling mode: {name}")
        modes[name] = _canonical_mode(int(mode, 8))
    if set(modes) != selected:
        raise ValueError("Source-tooling Git modes do not cover the selected files")
    return modes


def _add_bytes(
    archive: tarfile.TarFile, name: str, data: bytes, *, mode: int = 0o644
) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = _canonical_mode(mode)
    member.mtime = 0
    archive.addfile(member, io.BytesIO(data))


def _validated_members(archive: tarfile.TarFile) -> tuple[str, list[tarfile.TarInfo]]:
    """Reject escaping paths and links before copying any upstream tar entry."""
    members = archive.getmembers()
    if not members:
        raise ValueError("Empty setuptools sdist")
    first_parts = PurePosixPath(members[0].name).parts
    if not first_parts:
        raise ValueError("Empty sdist member name")
    prefix = first_parts[0]
    for member in members:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in member.name
            or ":" in member.name
            or not path.parts
            or path.parts[0] != prefix
            or not (member.isfile() or member.isdir())
        ):
            raise ValueError(f"Unsafe sdist member: {member.name}")
    return prefix, members


def build_sdist(
    sdist_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    """Include the declared source-tooling closure while keeping wheels clean."""
    root = Path.cwd().resolve()
    paths = _support_paths(root)
    files: dict[str, bytes] = {}
    for name in paths:
        if not _supported_path(name):
            raise ValueError(f"Unsupported source-tooling path: {name}")
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Source-tooling file escapes root: {name}")
        files[name] = path.read_bytes()
    modes = _support_modes(root, paths)
    receipt = {
        "schema_version": 1,
        "support": [
            "quality_cold_imports",
            "quality_root_contracts",
            "quality_report_generators",
            "metric_inventory_cli",
        ],
        "files": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(files.items())
        },
        "file_modes": modes,
    }
    with tempfile.TemporaryDirectory(prefix="bioetl-sdist-") as temporary:
        filename = _backend.build_sdist(temporary, config_settings)
        with tarfile.open(Path(temporary) / filename, "r:gz") as original:
            prefix, members = _validated_members(original)
            target = Path(sdist_directory).resolve() / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            replaced = {f"{prefix}/{name}" for name in files} | {f"{prefix}/{_RECEIPT}"}
            with tarfile.open(target, "w:gz", format=tarfile.PAX_FORMAT) as output:
                for member in members:
                    if member.isfile() and member.name not in replaced:
                        stream = original.extractfile(member.name)
                        if stream is None:
                            raise ValueError(
                                f"Missing sdist member payload: {member.name}"
                            )
                        with stream:
                            _add_bytes(
                                output,
                                PurePosixPath(member.name).as_posix(),
                                stream.read(),
                                mode=member.mode,
                            )
                for name, data in sorted(files.items()):
                    _add_bytes(output, f"{prefix}/{name}", data, mode=modes[name])
                _add_bytes(
                    output,
                    f"{prefix}/{_RECEIPT}",
                    (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(),
                )
    return filename
