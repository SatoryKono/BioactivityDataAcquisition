import argparse
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable, List, Tuple


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
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
            for p in root.rglob(pat.replace("**/", "")):
                found.append(p)
        else:
            for p in (
                (root / pat).glob("**/*") if _is_dir_pattern(pat) else root.glob(pat)
            ):
                if p.exists():
                    found.append(p)
    uniq = []
    seen = set()
    for p in found:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(rp)
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
            fp = Path(dirpath) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def _archive_logs(paths: Iterable[Path], root: Path) -> Tuple[int, int]:
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)
    moved = 0
    bytes_moved = 0
    for p in paths:
        if p.is_file() and _is_log_like(p):
            if p.resolve().parent == reports_dir.resolve():
                continue
            target = reports_dir / p.name
            if target.exists() and target.resolve() != p.resolve():
                target.unlink()
            shutil.move(str(p), str(target))
            moved += 1
            bytes_moved += _size_bytes(target)
    return moved, bytes_moved


def _delete(paths: Iterable[Path]) -> Tuple[int, int]:
    deleted = 0
    bytes_deleted = 0
    for p in paths:
        try:
            size = _size_bytes(p)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
            deleted += 1
            bytes_deleted += size
        except Exception:
            pass
    return deleted, bytes_deleted


def main() -> int:
    from bioetl.infrastructure.observability.factories import create_logging_port

    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--archive-logs", action="store_true")
    ap.add_argument("--purge-logs", action="store_true")
    args = ap.parse_args()

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
