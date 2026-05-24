#!/usr/bin/env python3
"""Build the MkDocs site through the packaged ``scripts.docs`` route."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SITE_DIR = _REPO_ROOT / "docs" / "site"
_LEGACY_SITE_DIR = _REPO_ROOT / "site"


def _site_dir_explicit(argv: Sequence[str]) -> bool:
    for arg in argv:
        if arg in {"--site-dir", "-d"}:
            return True
        if arg.startswith("--site-dir="):
            return True
        if arg.startswith("-d") and arg != "-d":
            return True
    return False


def _mkdocs_build(argv: Sequence[str]) -> int:
    command = [sys.executable, "-m", "mkdocs", "build", *argv]
    result = subprocess.run(command, check=False)
    return result.returncode


def _replace_site_dir(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def _cleanup_legacy_site_dir() -> None:
    if _LEGACY_SITE_DIR.exists() and _LEGACY_SITE_DIR != _DEFAULT_SITE_DIR:
        shutil.rmtree(_LEGACY_SITE_DIR)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if any(arg in {"-h", "--help"} for arg in args):
        return _mkdocs_build(args)
    if _site_dir_explicit(args):
        return _mkdocs_build(args)

    with tempfile.TemporaryDirectory(prefix="bioetl-mkdocs-site-") as temp_root:
        staged_site_dir = Path(temp_root) / "site"
        exit_code = _mkdocs_build([*args, "--site-dir", str(staged_site_dir)])
        if exit_code != 0:
            return exit_code
        _replace_site_dir(staged_site_dir, _DEFAULT_SITE_DIR)
        _cleanup_legacy_site_dir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
