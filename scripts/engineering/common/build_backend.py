"""Setuptools backend with an explicit source-only quality-tooling closure.

Wheel discovery remains owned by setuptools and restricted to src. The sdist
also supports repository quality imports, path contracts and report generators;
its receipt lists the exact support files instead of borrowing a checkout.
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
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
_TEXT_SUFFIXES = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".csv",
    ".toml",
    ".sh",
    ".ps1",
    ".txt",
}
_SUPPORT_ROOTS = {"src", "scripts", "configs", "docs", "tests", "grafana", ".github"}


def _supported_path(path: str) -> bool:
    candidate = Path(path)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or any(p.startswith(".env") for p in candidate.parts)
    ):
        return False
    if path in {
        "uv.lock",
        ".importlinter",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "pyproject.toml",
        "README.md",
        "LICENSE",
    }:
        return True
    if candidate.suffix not in _TEXT_SUFFIXES:
        return False
    if candidate.parts[0] in _SUPPORT_ROOTS:
        return True
    if candidate.parts[:2] == ("reports", "observability"):
        return True
    return candidate.parts[:2] == ("reports", "quality") and (
        len(candidate.parts) == 3 or candidate.parts[2] == "quality-move-qm01"
    )


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
    )
    return sorted(
        name
        for name in result.stdout.decode("utf-8").split("\0")
        if name and _supported_path(name)
    )


def _add_bytes(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = 0o644
    member.mtime = 0
    archive.addfile(member, io.BytesIO(data))


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
    }
    with tempfile.TemporaryDirectory(prefix="bioetl-sdist-") as temporary:
        filename = _backend.build_sdist(temporary, config_settings)
        with tarfile.open(Path(temporary) / filename, "r:gz") as original:
            members = original.getmembers()
            prefix = members[0].name.split("/")[0]
            target = Path(sdist_directory).resolve() / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            replaced = {f"{prefix}/{name}" for name in files} | {f"{prefix}/{_RECEIPT}"}
            with tarfile.open(target, "w:gz", format=tarfile.PAX_FORMAT) as output:
                for member in members:
                    if member.name not in replaced:
                        output.addfile(
                            member,
                            original.extractfile(member) if member.isfile() else None,
                        )
                for name, data in sorted(files.items()):
                    _add_bytes(output, f"{prefix}/{name}", data)
                _add_bytes(
                    output,
                    f"{prefix}/{_RECEIPT}",
                    (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(),
                )
    return filename
