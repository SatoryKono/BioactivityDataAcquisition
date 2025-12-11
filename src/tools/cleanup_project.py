import argparse
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable, List, Tuple


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate_path in [cur, *cur.parents]:
        has_pyproject = (candidate_path / "pyproject.toml").exists()
        has_git = (candidate_path / ".git").exists()
        if has_pyproject or has_git:
            return candidate_path
    # Fallback for typical layout: src/tools/* -> project root two levels up
    return start.resolve().parents[2]


THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _find_project_root(THIS_FILE)
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _whitelist_patterns() -> List[str]:
    return [
        "**/__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        ".coverage*",
        "coverage.xml",
        "htmlcov",
        "build",
        "dist",
        "**/*.egg-info",
        "**/*.log",
        "**/*.tmp",
        "**/*report*.txt",
        "full_log.txt",
        "final_report*.txt",
        "project_rules_failures.txt",
        ".idea/workspace.xml",
        ".DS_Store",
        "Thumbs.db",
        ".ipynb_checkpoints",
        ".vercel/cache",
        "node_modules",
    ]


def _is_dir_pattern(pat: str) -> bool:
    base = Path(pat).name
    return not any(ch in base for ch in ["*", "?"]) and not base.startswith(".")


def _is_log_like(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".log") or name.endswith(".tmp"):
        return True
    return "report" in name and name.endswith(".txt")


def _iter_candidates(root: Path, patterns: Iterable[str]) -> List[Path]:
    found: List[Path] = []
    for pat in patterns:
        if pat.startswith("**/") or pat.startswith("**\\") or pat.startswith("**"):
            for candidate_path in root.rglob(pat.replace("**/", "")):
                found.append(candidate_path)
        else:
            for candidate_path in (
                (root / pat).glob("**/*") if _is_dir_pattern(pat) else root.glob(pat)
            ):
                if candidate_path.exists():
                    found.append(candidate_path)
    uniq = []
    seen = set()
    for candidate_path in found:
        resolved_path = candidate_path.resolve()
        if resolved_path not in seen:
            seen.add(resolved_path)
            uniq.append(resolved_path)
    return uniq


def _size_bytes(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _, filenames in os.walk(path, onerror=lambda e: None):
        for f in filenames:
            file_path = Path(dirpath) / f
            try:
                total += file_path.stat().st_size
            except OSError:
                pass
    return total


def _archive_logs(paths: Iterable[Path], root: Path) -> Tuple[int, int]:
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)
    moved = 0
    bytes_moved = 0
    for current_path in paths:
        if current_path.is_file() and _is_log_like(current_path):
            if current_path.resolve().parent == reports_dir.resolve():
                continue
            target = reports_dir / current_path.name
            if target.exists() and target.resolve() != current_path.resolve():
                target.unlink()
            shutil.move(str(current_path), str(target))
            moved += 1
            bytes_moved += _size_bytes(target)
    return moved, bytes_moved


def _delete(paths: Iterable[Path]) -> Tuple[int, int]:
    deleted = 0
    bytes_deleted = 0
    for current_path in paths:
        try:
            size = _size_bytes(current_path)
            if current_path.is_dir():
                shutil.rmtree(current_path, ignore_errors=True)
            else:
                current_path.unlink(missing_ok=True)
            deleted += 1
            bytes_deleted += size
        except Exception:
            pass
    return deleted, bytes_deleted


def main() -> int:
    from bioetl.infrastructure.observability.factories import create_logging_port

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--apply", action="store_true")
    arg_parser.add_argument("--archive-logs", action="store_true")
    arg_parser.add_argument("--purge-logs", action="store_true")
    args = arg_parser.parse_args()

    logger = create_logging_port().apply_bind(task="cleanup_project")
    root = PROJECT_ROOT
    patterns = _whitelist_patterns()
    candidates = _iter_candidates(root, patterns)
    candidates.sort(key=lambda p: str(p).lower())

    total_size = sum(_size_bytes(p) for p in candidates)
    logger.info("cleanup_dry_run", count=len(candidates), bytes=total_size)

    for p in candidates:
        logger.debug("candidate", path=str(p), bytes=_size_bytes(p))

    if not args.apply:
        return 0

    to_process = list(candidates)
    if args.archive_logs and not args.purge_logs:
        moved, moved_bytes = _archive_logs(to_process, root)
        logger.info("logs_archived", count=moved, bytes=moved_bytes)

    deleted, deleted_bytes = _delete(to_process)
    logger.info("cleanup_applied", deleted=deleted, bytes=deleted_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
