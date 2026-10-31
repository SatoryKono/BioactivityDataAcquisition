"""Validate explicitly selected QM artifacts against the source move manifest.

This read-only content gate complements builds and isolated runtime smoke; it
does not assert their success or promote receipt trust.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

from scripts.engineering.common.build_backend import _supported_path, _validated_members

_BUILD_METADATA = {
    "src/bioetl.egg-info/" + name
    for name in (
        "PKG-INFO",
        "SOURCES.txt",
        "dependency_links.txt",
        "entry_points.txt",
        "requires.txt",
        "top_level.txt",
    )
}


def _unique(names: list[str]) -> None:
    if len(names) != len(set(names)):
        raise ValueError("Duplicate archive members")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe archive path")


def _check_wheel(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        _unique(names)
        if archive.testzip() is not None:
            raise ValueError("Corrupt wheel payload")
        for name in names:
            # A .data/{purelib,platlib} payload is installed into site-packages.
            parts = PurePosixPath(name).parts
            installed = (
                "/".join(parts[2:])
                if len(parts) > 2
                and parts[0].endswith(".data")
                and parts[1] in {"purelib", "platlib"}
                else name
            )
            if installed == "scripts.py" or installed.startswith(
                ("scripts/", "bioetl/infrastructure/quality/")
            ):
                raise ValueError("Forbidden runtime wheel namespace")
        if not any(
            name.startswith("bioetl/") and name.endswith(".py") for name in names
        ):
            raise ValueError("Wheel has no runtime package")


def _check_sdist(sdist: Path, expected: set[str], parents: set[str]) -> int:
    with tarfile.open(sdist, "r:gz") as archive:
        top, members = _validated_members(archive)
        _unique([member.name for member in members])
        files = {
            member.name.removeprefix(top + "/"): member
            for member in members
            if member.isfile()
        }
        actual = {
            name
            for name in files
            if name.startswith("scripts/engineering/quality/") and name.endswith(".py")
        }
        if actual != expected or not parents <= files.keys():
            raise ValueError("Sdist quality modules or parent packages differ")
        if any(name.startswith("src/bioetl/infrastructure/quality/") for name in files):
            raise ValueError("Sdist retains the old quality namespace")
        receipt_member = files.get("quality-tooling-support.json")
        if receipt_member is None:
            raise ValueError("Missing support closure receipt")
        stream = archive.extractfile(receipt_member)
        assert stream is not None
        receipt = json.load(stream)
        if receipt["schema_version"] != 1:
            raise ValueError("Unsupported support receipt schema")
        hashes, modes = receipt["files"], receipt["file_modes"]
        declared = set(hashes)
        if not expected | parents <= declared or set(modes) != declared:
            raise ValueError("Incomplete support closure")
        # Receipt cannot omit supported files that are physically present.
        supported = {name for name in files if _supported_path(name)} - _BUILD_METADATA
        supported.discard("quality-tooling-support.json")
        if supported != declared:
            raise ValueError("Support closure inventory differs")
        _verify_support_files(archive, files, hashes, modes)
    return len(declared)


def _verify_support_files(
    archive: tarfile.TarFile,
    files: dict[str, tarfile.TarInfo],
    hashes: dict[str, str],
    modes: dict[str, int],
) -> None:
    if not set(hashes) <= files.keys() or any(
        not _supported_path(name) for name in hashes
    ):
        raise ValueError("Missing or invalid support file")
    # Physical member order avoids repeatedly decompressing a gzip stream.
    for name, member in files.items():
        if name not in hashes:
            continue
        stream = archive.extractfile(member)
        assert stream is not None
        if hashlib.sha256(stream.read()).hexdigest() != hashes[name]:
            raise ValueError("Support file digest differs")
        if member.mode != modes[name]:
            raise ValueError("Support file mode differs")


def validate(wheel: Path, sdist: Path, manifest: Path) -> dict[str, object]:
    """Reject missing, corrupt, poisoned or incomplete distribution content."""
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    targets = [row["target_path"] for row in rows]
    if len(targets) != 30 or len(set(targets)) != 30:
        raise ValueError("Expected exactly 30 unique manifest targets")
    expected = set(targets)
    if any(not name.startswith("scripts/engineering/quality/") for name in expected):
        raise ValueError("Unexpected quality target namespace")
    parents = {"scripts/__init__.py", "scripts/engineering/__init__.py"}
    _check_wheel(wheel)
    support_count = _check_sdist(sdist, expected, parents)
    return {
        "wheel": str(wheel),
        "sdist": str(sdist),
        "quality_modules": len(expected),
        "support_files": support_count,
    }


def main(argv: list[str] | None = None) -> int:
    """Require explicit artifacts; never select the first stale dist glob."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate(args.wheel, args.sdist, args.manifest)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"Distribution content FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
