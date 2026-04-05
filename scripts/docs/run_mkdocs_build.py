#!/usr/bin/env python3
"""Build the MkDocs site with a stable in-repo entrypoint.

This wrapper keeps the docs build path reproducible across local shells and CI.
It also patches the current `mkdocs-material` namespace theme entrypoint so
`mkdocs` can resolve the theme directory consistently.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from mkdocs.commands.build import build
from mkdocs.config import load_config


def _patch_material_theme_namespace() -> None:
    """Give namespace-based material theme modules a synthetic __file__.

    `mkdocs` 1.6 resolves themes through entry points and expects the loaded
    module to expose `__file__`. Recent `mkdocs-material` releases register the
    `material.templates` namespace package, which does not have `__file__` by
    default. Populate it from the package path so MkDocs can derive the theme
    directory reliably.
    """

    module = importlib.import_module("material.templates")
    if getattr(module, "__file__", None):
        return

    paths = list(getattr(module, "__path__", []))
    if not paths:
        return

    module.__file__ = str(Path(paths[0]) / "__init__.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="Enable MkDocs strict mode"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean stale files before build"
    )
    parser.add_argument(
        "--site-dir",
        default=".mkdocs-site",
        help="Output site directory (default: .mkdocs-site)",
    )
    parser.add_argument(
        "--config-file",
        default="mkdocs.yml",
        help="MkDocs config file (default: mkdocs.yml)",
    )
    args = parser.parse_args()

    _patch_material_theme_namespace()
    config = load_config(
        config_file=args.config_file,
        strict=args.strict,
        site_dir=args.site_dir,
    )
    build(config, dirty=not args.clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
