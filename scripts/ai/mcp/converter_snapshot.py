"""Snapshot the installed MarkItDown dependency closure without executing .pth files."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import uuid
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    raw = (root / "converter.json").read_bytes()
    manifest = json.loads(raw)
    if root.name != hashlib.sha256(raw).hexdigest() or manifest.get("schema") != 1:
        raise ValueError("Converter snapshot identity mismatch")
    actual = set()
    for current, directories, files in os.walk(root, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if (
                getattr(path.lstat(), "st_file_attributes", 0) & 0x400
                or path.is_symlink()
            ):
                raise ValueError("Converter snapshot contains a reparse point")
        actual.update(
            (Path(current) / name).relative_to(root).as_posix()
            for name in files
            if Path(current) / name != root / "converter.json"
        )
    if actual != set(manifest["files"]):
        raise ValueError("Converter snapshot file set changed")
    for relative, expected in manifest["files"].items():
        if (
            Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or digest(root / relative) != expected
        ):
            raise ValueError("Converter snapshot dependency drift")
    return manifest


def closure(site, extras=()):
    """Resolve only installed, version-compatible dependencies for selected formats."""
    from packaging.requirements import Requirement

    def normalize(name):
        return re.sub(r"[-_.]+", "-", name).lower()

    installed = {
        normalize(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(site)])
    }
    pending = [("markitdown", set(extras))]
    selected = {}
    packages = {}
    while pending:
        name, extras = pending.pop()
        name = normalize(name)
        previous = selected.get(name)
        if previous is not None and extras <= previous:
            continue
        selected[name] = (previous or set()) | extras
        distribution = installed[name]
        packages[name] = distribution.version
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or any(
                requirement.marker.evaluate({"extra": extra})
                for extra in {"", *selected[name]}
            ):
                if normalize(requirement.name) not in installed:
                    raise ValueError(
                        "Converter dependency missing: " + requirement.name
                    )
                if (
                    requirement.specifier
                    and installed[normalize(requirement.name)].version
                    not in requirement.specifier
                ):
                    raise ValueError(
                        "Converter dependency version mismatch: " + requirement.name
                    )
                pending.append((requirement.name, set(requirement.extras)))
    return installed, selected, packages


def build(destination, site, extras=()):
    """Copy the exact installed closure for independently qualified formats."""
    installed, selected, packages = closure(site, extras)
    destination.mkdir(parents=True, exist_ok=True)
    staging = destination / ("building-" + uuid.uuid4().hex)
    staging.mkdir()
    for name in selected:
        for relative in installed[name].files or []:
            source = Path(installed[name].locate_file(relative)).resolve(strict=True)
            if not source.is_relative_to(site):
                continue  # Console entrypoints are replaced by the isolated runner.
            if "__pycache__" in source.parts or source.suffix == ".pyc":
                continue
            if source.name == ".env" or source.name.startswith(".env."):
                raise ValueError("Converter package contains an environment file")
            if source.resolve(strict=True) != source or source.is_symlink():
                raise ValueError("Converter package traverses a reparse path")
            target = staging / "site-packages" / source.relative_to(site)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if digest(source) != digest(target):
                raise ValueError("Converter dependency changed during copying")
    runner = Path(__file__).with_name("converter_runner.py")
    shutil.copyfile(runner, staging / "converter_runner.py")
    manifest = {
        "schema": 1,
        "packages": packages,
        "formats": sorted(extras),
        "files": {
            p.relative_to(staging).as_posix(): digest(p)
            for p in sorted(staging.rglob("*"))
            if p.is_file()
        },
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    (staging / "converter.json").write_bytes(raw)
    target = destination / hashlib.sha256(raw).hexdigest()
    if not target.exists():
        staging.rename(target)
    verify(target)
    return target
