#!/usr/bin/env python3
"""Shared first-party import graph helpers for QA inventory reports."""

from __future__ import annotations

import ast
import hashlib
import os
import pickle
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from scripts.engineering.qa.file_discovery import discover_files

_MIN_PARALLEL_READ_FILES = 64
_DEFAULT_READ_WORKERS = 8
# Windows GDrive/cloud mounts are latency-bound; a small worker pool hides
# round-trips better than pure serial reads without thrashing the client.
_DEFAULT_WINDOWS_READ_WORKERS = 2
_MAX_READ_WORKERS = 16
_MAX_SOURCE_BYTES = 512_000
_READ_WORKERS_ENV = "BIOETL_IMPORT_GRAPH_READ_WORKERS"
_PARSED_CACHE_VERSION = 2
_PARSED_CACHE_ENV = "BIOETL_IMPORT_GRAPH_CACHE_DIR"
_INIT_PY = "__init__.py"
_INIT_PYI = "__init__.pyi"
_BIOETL_MODULE_PREFIX = "bioetl."


@dataclass(frozen=True)
class PackageScan:
    """One first-party package tree to scan."""

    label: str
    root: Path
    module_prefix: str


@dataclass(frozen=True)
class ParsedModule:
    """Parsed first-party Python module ready for repeated import-graph scans."""

    scan_label: str
    rel_path: str
    candidate_targets: tuple[str, ...]
    exact_import_usage: tuple[tuple[str, tuple[str, ...]], ...]


def _read_worker_count(total_files: int, *, os_name: str = os.name) -> int:
    """Return a conservative worker count for mounted-worktree file reads."""
    configured = os.getenv(_READ_WORKERS_ENV, "").strip()
    if configured:
        try:
            return max(1, min(int(configured), _MAX_READ_WORKERS, max(total_files, 1)))
        except ValueError:
            pass
    if total_files < _MIN_PARALLEL_READ_FILES:
        return 1
    if os_name == "nt":
        return min(total_files, _DEFAULT_WINDOWS_READ_WORKERS)
    cpu_count = os.cpu_count() or _DEFAULT_READ_WORKERS
    return min(total_files, _MAX_READ_WORKERS, max(_DEFAULT_READ_WORKERS, cpu_count))


def _read_module_source(item: tuple[str, Path]) -> tuple[str, Path, str | None]:
    """Read one Python module source payload for import-graph parsing.

    Uses a single bounded read (no pre-stat) so cloud-synced trees pay one
    open/read round-trip per file instead of stat+read.
    """
    module_name, py_file = item
    try:
        with py_file.open("rb") as stream:
            source_bytes = stream.read(_MAX_SOURCE_BYTES + 1)
        if len(source_bytes) > _MAX_SOURCE_BYTES:
            return module_name, py_file, None
        return module_name, py_file, source_bytes.decode("utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return module_name, py_file, None


def _read_module_sources(
    modules: list[tuple[str, Path]],
) -> list[tuple[str, Path, str]]:
    """Read module sources with bounded parallelism before single-thread parsing."""
    max_workers = _read_worker_count(len(modules))
    rows: list[tuple[str, Path, str]] = []

    if max_workers == 1:
        for module in modules:
            module_name, py_file, text = _read_module_source(module)
            if text is not None:
                rows.append((module_name, py_file, text))
        return rows

    # map() preserves order; chunking keeps memory bounded for large trees.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for module_name, py_file, text in executor.map(
            _read_module_source, modules, chunksize=32
        ):
            if text is not None:
                rows.append((module_name, py_file, text))
    return rows


def default_scan_roots(repo_root: Path) -> tuple[PackageScan, ...]:
    """Return the canonical first-party scan roots."""
    return (
        PackageScan("src", repo_root / "src" / "bioetl", "bioetl"),
        PackageScan("tests", repo_root / "tests", "tests"),
    )


def _iter_python_modules(scan: PackageScan) -> list[tuple[str, Path]]:
    return list(
        _iter_python_modules_cached(
            str(scan.root.resolve()),
            scan.module_prefix,
        )
    )


def _iter_import_sources(scan: PackageScan) -> list[tuple[str, Path]]:
    """Return runtime modules and type stubs that can declare imports."""
    return list(
        _iter_import_sources_cached(
            str(scan.root.resolve()),
            scan.module_prefix,
        )
    )


@cache
def _iter_python_modules_cached(
    root_str: str,
    module_prefix: str,
) -> tuple[tuple[str, Path], ...]:
    return _iter_module_sources_cached(root_str, module_prefix, (".py",))


@cache
def _iter_import_sources_cached(
    root_str: str,
    module_prefix: str,
) -> tuple[tuple[str, Path], ...]:
    return _iter_module_sources_cached(root_str, module_prefix, (".py", ".pyi"))


@cache
def _iter_module_sources_cached(
    root_str: str,
    module_prefix: str,
    suffixes: tuple[str, ...],
) -> tuple[tuple[str, Path], ...]:
    root = Path(root_str)
    if not root.exists():
        return ()

    modules: list[tuple[str, Path]] = []
    for suffix in suffixes:
        for relative_path in discover_files(root_str, suffix):
            source_file = root / relative_path
            rel_path = source_file.relative_to(root)
            if source_file.name in {_INIT_PY, _INIT_PYI}:
                rel_parts = rel_path.parent.parts
            else:
                rel_parts = rel_path.with_suffix("").parts
            module_name = ".".join(
                [module_prefix, *rel_parts] if rel_parts else [module_prefix]
            )
            modules.append((module_name, source_file))
    return tuple(sorted(modules, key=lambda item: item[1].as_posix()))


def _collect_existing_modules(scan: PackageScan) -> frozenset[str]:
    return frozenset(module_name for module_name, _ in _iter_python_modules(scan))


def _parsed_modules_cache_dir(repo_root: Path) -> Path:
    """Prefer a local non-network cache dir when available (Windows GDrive)."""
    configured = os.getenv(_PARSED_CACHE_ENV, "").strip()
    if configured:
        return Path(configured)
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        repo_key = hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()[
            :16
        ]
        return Path(local_app_data) / "bioetl-import-graph-cache" / repo_key
    return repo_root / ".cache" / "import-graph"


def _import_sources_fingerprint(modules: list[tuple[str, Path]]) -> str:
    """Fingerprint import sources by path + size + mtime (no content read)."""

    def _stat_one(item: tuple[str, Path]) -> tuple[str, str]:
        module_name, path = item
        try:
            stat_result = path.stat()
            return module_name, f"{stat_result.st_size}\0{stat_result.st_mtime_ns}"
        except OSError:
            return module_name, "missing"

    workers = _read_worker_count(len(modules))
    if workers == 1:
        rows = [_stat_one(item) for item in modules]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(_stat_one, modules, chunksize=64))

    digest = hashlib.sha256()
    digest.update(f"v{_PARSED_CACHE_VERSION}".encode())
    for module_name, signature in rows:
        digest.update(module_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(signature.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _load_parsed_modules_disk_cache(
    cache_path: Path,
) -> tuple[ParsedModule, ...] | None:
    try:
        with cache_path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError):
        return None
    if not isinstance(payload, tuple):
        return None
    if not all(isinstance(item, ParsedModule) for item in payload):
        return None
    return payload


def _store_parsed_modules_disk_cache(
    cache_path: Path,
    parsed_modules: tuple[ParsedModule, ...],
) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        with temp_path.open("wb") as handle:
            pickle.dump(parsed_modules, handle, protocol=pickle.HIGHEST_PROTOCOL)
        temp_path.replace(cache_path)
    except OSError:
        # Cache is best-effort; inventory correctness must not depend on it.
        return


def _record_exact_import_usage(
    node: ast.AST,
    *,
    importer_module: str,
    importer_is_package: bool,
    exact_import_usage: dict[str, set[str]],
) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name.startswith(_BIOETL_MODULE_PREFIX):
                exact_import_usage[alias.name].add("<module>")
        return
    if not isinstance(node, ast.ImportFrom):
        return
    base_module = _resolve_relative_module(
        importer_module=importer_module,
        importer_is_package=importer_is_package,
        module=node.module,
        level=node.level,
    )
    if not base_module or not base_module.startswith(_BIOETL_MODULE_PREFIX):
        return
    for alias in node.names:
        exact_import_usage[base_module].add(alias.name)


def _parse_module_import_graph(
    *,
    tree: ast.AST,
    existing_modules: frozenset[str],
    importer_module: str,
    importer_is_package: bool,
) -> tuple[set[str], dict[str, set[str]]]:
    candidate_targets: set[str] = set()
    exact_import_usage: dict[str, set[str]] = defaultdict(set)
    # Only Import/ImportFrom matter for the inventory; avoid paying for
    # every AST node type on multi-thousand-file trees.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for target_module in _iter_candidate_import_targets(
            existing_modules=existing_modules,
            importer_module=importer_module,
            importer_is_package=importer_is_package,
            node=node,
        ):
            candidate_targets.add(target_module)
        _record_exact_import_usage(
            node,
            importer_module=importer_module,
            importer_is_package=importer_is_package,
            exact_import_usage=exact_import_usage,
        )
    return candidate_targets, exact_import_usage


def _build_parsed_module(
    *,
    scan_label: str,
    repo_root: Path,
    py_file: Path,
    importer_module: str,
    source_text: str,
    existing_modules: frozenset[str],
) -> ParsedModule | None:
    importer_is_package = py_file.name in {_INIT_PY, _INIT_PYI}
    try:
        tree = ast.parse(source_text, filename=str(py_file), mode="exec")
    except SyntaxError:
        return None
    candidate_targets, exact_import_usage = _parse_module_import_graph(
        tree=tree,
        existing_modules=existing_modules,
        importer_module=importer_module,
        importer_is_package=importer_is_package,
    )
    return ParsedModule(
        scan_label=scan_label,
        rel_path=py_file.relative_to(repo_root).as_posix(),
        candidate_targets=tuple(sorted(candidate_targets)),
        exact_import_usage=tuple(
            (module_name, tuple(sorted(imported_names)))
            for module_name, imported_names in sorted(exact_import_usage.items())
        ),
    )


@cache
def _collect_parsed_modules(repo_root_str: str) -> tuple[ParsedModule, ...]:
    """Parse first-party Python modules once per repo path for reuse across checks."""
    repo_root = Path(repo_root_str)
    scans = default_scan_roots(repo_root)
    existing_modules = _collect_existing_modules(scans[0])
    import_sources: list[tuple[str, Path]] = []
    for scan in scans:
        import_sources.extend(_iter_import_sources(scan))

    fingerprint = _import_sources_fingerprint(import_sources)
    cache_path = (
        _parsed_modules_cache_dir(repo_root)
        / f"parsed-v{_PARSED_CACHE_VERSION}-{fingerprint[:24]}.pkl"
    )
    cached = _load_parsed_modules_disk_cache(cache_path)
    if cached is not None:
        return cached

    parsed_modules: list[ParsedModule] = []
    # Preserve scan-label grouping: read each scan separately so ParsedModule
    # labels remain src/tests even though fingerprint covers both trees.
    for scan in scans:
        for importer_module, py_file, source_text in _read_module_sources(
            _iter_import_sources(scan)
        ):
            parsed = _build_parsed_module(
                scan_label=scan.label,
                repo_root=repo_root,
                py_file=py_file,
                importer_module=importer_module,
                source_text=source_text,
                existing_modules=existing_modules,
            )
            if parsed is not None:
                parsed_modules.append(parsed)

    result = tuple(parsed_modules)
    _store_parsed_modules_disk_cache(cache_path, result)
    return result


def _resolve_relative_module(
    *,
    importer_module: str,
    importer_is_package: bool,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return module

    base_parts = (
        importer_module.split(".")
        if importer_is_package
        else importer_module.split(".")[:-1]
    )
    if level > len(base_parts):
        return None

    resolved_base_parts = base_parts[: len(base_parts) - level + 1]
    if module:
        return ".".join([*resolved_base_parts, module])
    return ".".join(resolved_base_parts)


def _iter_candidate_import_targets(
    *,
    existing_modules: frozenset[str],
    importer_module: str,
    importer_is_package: bool,
    node: ast.AST,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name.startswith(_BIOETL_MODULE_PREFIX)]

    if not isinstance(node, ast.ImportFrom):
        return []

    base_module = _resolve_relative_module(
        importer_module=importer_module,
        importer_is_package=importer_is_package,
        module=node.module,
        level=node.level,
    )
    if not base_module or not base_module.startswith(_BIOETL_MODULE_PREFIX):
        return []

    candidates = [base_module]
    for alias in node.names:
        if alias.name == "*":
            continue
        nested_module = f"{base_module}.{alias.name}"
        if nested_module in existing_modules:
            candidates.append(nested_module)
    return candidates


def collect_bioetl_importers(
    repo_root: Path,
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Collect first-party importers for every ``bioetl.*`` module."""
    scans = default_scan_roots(repo_root)
    src_scan = scans[0]
    existing_modules = _collect_existing_modules(src_scan)
    importers: dict[str, dict[str, set[str]]] = {
        module_name: {"src": set(), "tests": set()} for module_name in existing_modules
    }

    for parsed_module in _collect_parsed_modules(str(repo_root.resolve())):
        for target_module in parsed_module.candidate_targets:
            if target_module in importers:
                importers[target_module][parsed_module.scan_label].add(
                    parsed_module.rel_path
                )

    return {
        module_name: {
            "src": tuple(sorted(paths["src"])),
            "tests": tuple(sorted(paths["tests"])),
        }
        for module_name, paths in sorted(importers.items())
    }


def collect_exact_module_import_usage(
    repo_root: Path, target_module: str
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Collect exact first-party import usage for one target module.

    The returned mapping is keyed first by scan label (`src` / `tests`) and then
    by importer path. Each importer path maps to the tuple of imported names used
    from the target module. Direct ``import <module>`` statements are recorded as
    ``"<module>"``.
    """

    scans = default_scan_roots(repo_root)
    usage: dict[str, dict[str, set[str]]] = {
        scan.label: defaultdict(set) for scan in scans
    }

    for parsed_module in _collect_parsed_modules(str(repo_root.resolve())):
        exact_usage = dict(parsed_module.exact_import_usage)
        if target_module not in exact_usage:
            continue
        for imported_name in exact_usage[target_module]:
            usage[parsed_module.scan_label][parsed_module.rel_path].add(imported_name)

    return {
        label: {
            rel_path: tuple(sorted(imported_names))
            for rel_path, imported_names in sorted(path_map.items())
        }
        for label, path_map in usage.items()
    }


def find_public_private_twin_modules(repo_root: Path) -> list[dict[str, str]]:
    """Return sibling ``_private.py``/``public.py`` first-party module pairs."""
    repo_root = repo_root.resolve()
    src_root = repo_root / "src" / "bioetl"
    src_scan = PackageScan("src", src_root, "bioetl")
    module_name_by_path = {
        path: module_name for module_name, path in _iter_python_modules(src_scan)
    }
    pairs: list[dict[str, str]] = []

    for relative_path in discover_files(str(src_root.resolve()), ".py", "_"):
        py_file = src_root / relative_path
        if py_file.name == _INIT_PY:
            continue
        public_file = py_file.with_name(py_file.name[1:])
        if not public_file.exists():
            continue
        private_module = module_name_by_path.get(py_file)
        public_module = module_name_by_path.get(public_file)
        if private_module is None or public_module is None:
            continue
        pairs.append(
            {
                "private_path": py_file.relative_to(repo_root).as_posix(),
                "public_path": public_file.relative_to(repo_root).as_posix(),
                "private_module": private_module,
                "public_module": public_module,
            }
        )

    return pairs


def collect_zero_import_bioetl_modules(repo_root: Path) -> list[dict[str, object]]:
    """Return repo-wide ``bioetl`` modules with zero first-party static importers."""
    scans = default_scan_roots(repo_root)
    src_scan = scans[0]
    importer_map = collect_bioetl_importers(repo_root)
    zero_import_modules: list[dict[str, object]] = []

    for module_name, py_file in _iter_python_modules(src_scan):
        if py_file.name == _INIT_PY:
            continue
        importer_entry = importer_map.get(module_name, {"src": (), "tests": ()})
        src_importers = tuple(importer_entry.get("src", ()))
        test_importers = tuple(importer_entry.get("tests", ()))
        if src_importers or test_importers:
            continue
        zero_import_modules.append(
            {
                "module_name": module_name,
                "path": py_file.relative_to(repo_root).as_posix(),
                "is_private_module": py_file.name.startswith("_"),
                "src_importer_count": 0,
                "test_importer_count": 0,
            }
        )

    return zero_import_modules
