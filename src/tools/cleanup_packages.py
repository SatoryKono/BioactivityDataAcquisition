import argparse
import ast
import fnmatch
import os
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate_path in [cur, *cur.parents]:
        has_pyproject = (candidate_path / "pyproject.toml").exists()
        has_git = (candidate_path / ".git").exists()
        if has_pyproject or has_git:
            return candidate_path
    return start.resolve().parents[2]


ROOT = _find_project_root(Path(__file__))

try:
    from bioetl.infrastructure.observability.factories import (
        create_logging_port as get_logging_port,
    )
except Exception:
    get_logging_port: Optional[Callable[[], Any]] = None
else:
    get_logging_port = get_logging_port


IGNORED_FILES = {".DS_Store", "Thumbs.db"}


def _is_dunder_py(name: str) -> bool:
    return name.startswith("__") and name.endswith(".py")


def _has_export(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return False
    try:
        tree = ast.parse(src)
    except Exception:
        return False
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)):
        return True
    if any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for n in ast.walk(tree)
    ):
        return True
    assigns: List[ast.AST] = [
        n
        for n in tree.body
        if (
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
        )
        or (
            isinstance(n, ast.AnnAssign)
            and isinstance(n.target, ast.Name)
            and n.target.id == "__all__"
        )
    ]
    for n in assigns:
        value = n.value if isinstance(n, (ast.Assign, ast.AnnAssign)) else None
        if isinstance(value, (ast.List, ast.Tuple)):
            if len(value.elts) > 0:
                return True
        elif value is not None:
            return True
    return False


def _listdir(path: Path) -> Tuple[List[Path], List[Path]]:
    files: List[Path] = []
    dirs: List[Path] = []
    for entry in path.iterdir():
        if entry.name in IGNORED_FILES:
            continue
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            dirs.append(entry)
    return files, dirs


def _is_top_bioetl_package(path: Path) -> bool:
    # Protect immediate subpackages under src/bioetl/*
    parts = path.resolve().parts
    try:
        idx = parts.index("src")
    except ValueError:
        return False
    if idx + 1 < len(parts) and parts[idx + 1] == "bioetl":
        # depth from 'bioetl' root
        depth = len(parts) - (idx + 2)
        return depth <= 1
    return False


def _match_any(path: Path, patterns: List[str]) -> bool:
    path_str = str(path).replace("\\", "/")
    return any(fnmatch.fnmatch(path_str, p) for p in patterns)


def _discover_candidates(
    scope_dirs: List[Path],
    exclude: List[str],
    include_src: bool,
) -> List[Tuple[Path, str]]:
    candidates: List[Tuple[Path, str]] = []
    for base in scope_dirs:
        for dirpath, dirnames, filenames in os.walk(base):
            current_dir = Path(dirpath)
            if _match_any(current_dir, exclude):
                continue
            files = [Path(dirpath) / f for f in filenames if f not in IGNORED_FILES]
            subdirs = [Path(dirpath) / d for d in dirnames]

            if not files and not subdirs:
                candidates.append((current_dir, "empty"))
                continue

            if len(files) == 1 and not subdirs and _is_dunder_py(files[0].name):
                # Skip protected src/bioetl top packages unless include_src=True
                if not include_src and _is_top_bioetl_package(current_dir):
                    continue
                candidates.append((current_dir, "single_dunder_py"))
    return candidates


def _apply(candidates: Iterable[Tuple[Path, str]], aggressive: bool) -> Tuple[int, int]:
    removed = 0
    files_removed = 0
    for path, reason in candidates:
        try:
            files, _ = _listdir(path)
            if reason == "single_dunder_py" and files:
                dunder_file = files[0]
                if aggressive or not _has_export(dunder_file):
                    dunder_file.unlink(missing_ok=True)
                    files_removed += 1
                else:
                    continue
            # Try remove dir if empty
            try:
                path.rmdir()
                removed += 1
            except OSError:
                # Not empty (unexpected) — skip
                pass
        except Exception:
            pass
    return removed, files_removed


def main() -> int:
    arg_parser = argparse.ArgumentParser(
        description="Cleanup empty and dunder-only directories"
    )
    arg_parser.add_argument("--apply", action="store_true")
    arg_parser.add_argument("--include-src", action="store_true")
    arg_parser.add_argument("--aggressive", action="store_true")
    arg_parser.add_argument("--exclude", action="append", default=[])
    args = arg_parser.parse_args()

    logger = None
    if get_logging_port is not None:
        logger = get_logging_port().apply_bind(task="cleanup_packages")

    scope = [ROOT / "tests", ROOT / "docs", ROOT / "src" / "tools"]
    if args.include_src:
        scope.append(ROOT / "src" / "bioetl")
    scope = [p for p in scope if p.exists()]

    candidates = _discover_candidates(scope, args.exclude, include_src=args.include_src)
    if logger:
        logger.info(
            "packages_scan",
            count=len(candidates),
            apply=args.apply,
            include_src=args.include_src,
            exclude_count=len(args.exclude),
        )
        for p, reason in candidates:
            logger.debug("candidate", path=str(p), reason=reason)

    if not args.apply:
        return 0

    removed_dirs, removed_files = _apply(candidates, aggressive=args.aggressive)
    if logger:
        logger.info(
            "packages_cleanup_applied",
            removed_dirs=removed_dirs,
            removed_files=removed_files,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
