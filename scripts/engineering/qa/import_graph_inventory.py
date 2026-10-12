#!/usr/bin/env python3
"""Shared first-party import graph helpers for QA inventory reports.

Census helpers keep their historical static ``Import`` / ``ImportFrom`` view.
``collect_import_graph`` records edges and five projections without executing
imports. ``src/memory`` is an optional wider scan root only; five-layer
``bioetl`` import rules do not apply to that package.
"""

from __future__ import annotations

import ast
import hashlib
import os
import pickle
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import cast

from scripts.engineering.qa.file_discovery import discover_files

_MIN_PARALLEL_READ_FILES = 64
_DEFAULT_READ_WORKERS = 8
# Windows GDrive/cloud mounts are latency-bound; a small worker pool hides
# round-trips better than pure serial reads without thrashing the client.
_DEFAULT_WINDOWS_READ_WORKERS = 2
_MAX_READ_WORKERS = 16
_MAX_SOURCE_BYTES = 512_000
_READ_WORKERS_ENV = "BIOETL_IMPORT_GRAPH_READ_WORKERS"
# v3 stores ImportEdge rows plus read/parse failures on the scan cache.
_PARSED_CACHE_VERSION = 4
_PARSED_CACHE_ENV = "BIOETL_IMPORT_GRAPH_CACHE_DIR"
_INIT_PY = "__init__.py"
_INIT_PYI = "__init__.pyi"
_BIOETL_MODULE_PREFIX = "bioetl."
_TYPING_MODULES = frozenset({"typing", "typing_extensions"})

SYNTAX_IMPORT = "import"
SYNTAX_IMPORT_FROM = "import_from"
SYNTAX_IMPORT_MODULE = "import_module"
SYNTAX_DUNDER_IMPORT = "dunder_import"
_STATIC_SYNTAX = frozenset({SYNTAX_IMPORT, SYNTAX_IMPORT_FROM})
_DYNAMIC_SYNTAX = frozenset({SYNTAX_IMPORT_MODULE, SYNTAX_DUNDER_IMPORT})

RESOLUTION_RESOLVED = "resolved"
RESOLUTION_UNRESOLVED = "unresolved"
RESOLUTION_SYMBOL_NOT_MODULE = "symbol_not_module"

TIMING_MODULE_IMPORT_TIME = "module_import_time"
TIMING_DEFERRED = "deferred"
TIMING_TYPE_CHECKING = "type_checking"
_OWNERSHIP_TIMING = frozenset({TIMING_MODULE_IMPORT_TIME, TIMING_DEFERRED})

FAILURE_PARSE_ERROR = "parse_error"
FAILURE_UNREADABLE = "unreadable"
FAILURE_OVERSIZE = "oversize"

NON_CONSTANT_IMPORT_TARGET = "<non-constant>"
INVALID_RELATIVE_IMPORT_TARGET = "<invalid-relative>"

PROJECTION_IMPORT_TIME_RUNTIME = "import_time_runtime"
PROJECTION_OWNERSHIP = "ownership"
PROJECTION_TYPE_ONLY = "type_only"
PROJECTION_DYNAMIC_RESOLVED = "dynamic_resolved"
PROJECTION_DYNAMIC_UNRESOLVED = "dynamic_unresolved"
PROJECTION_NAMES = (
    PROJECTION_IMPORT_TIME_RUNTIME,
    PROJECTION_OWNERSHIP,
    PROJECTION_TYPE_ONLY,
    PROJECTION_DYNAMIC_RESOLVED,
    PROJECTION_DYNAMIC_UNRESOLVED,
)
PROJECTION_LABELS = {
    PROJECTION_IMPORT_TIME_RUNTIME: "import-time runtime",
    PROJECTION_OWNERSHIP: "ownership",
    PROJECTION_TYPE_ONLY: "type-only",
    PROJECTION_DYNAMIC_RESOLVED: "dynamic resolved",
    PROJECTION_DYNAMIC_UNRESOLVED: "dynamic unresolved",
}


@dataclass(frozen=True)
class PackageScan:
    """One first-party package tree to scan."""

    label: str
    root: Path
    module_prefix: str


@dataclass(frozen=True)
class ImportEdge:
    """One statically observed import edge. Imports are never executed."""

    source: str
    target: str
    file: str
    line: int
    syntax: str
    resolution: str
    timing: str


@dataclass(frozen=True)
class ImportGraphFailure:
    """A source that could not be read or parsed. Not a clean PASS."""

    file: str
    reason: str
    detail: str


@dataclass(frozen=True)
class ImportGraphProjections:
    """The five architecture projections, each a filtered edge tuple."""

    import_time_runtime: tuple[ImportEdge, ...]
    ownership: tuple[ImportEdge, ...]
    type_only: tuple[ImportEdge, ...]
    dynamic_resolved: tuple[ImportEdge, ...]
    dynamic_unresolved: tuple[ImportEdge, ...]


@dataclass(frozen=True)
class ImportGraphReport:
    """Full edge list, failures, and projections for one scan."""

    edges: tuple[ImportEdge, ...]
    failures: tuple[ImportGraphFailure, ...]
    projections: ImportGraphProjections

    @property
    def passed(self) -> bool:
        """False when any source was unreadable, oversize, or unparsable."""

        return not self.failures


@dataclass(frozen=True)
class ImportCycle:
    """One reproducible cycle path and the edges that close it."""

    projection: str
    path: tuple[str, ...]
    edges: tuple[ImportEdge, ...]


@dataclass(frozen=True)
class ParsedModule:
    """Parsed first-party Python module ready for repeated import-graph scans."""

    scan_label: str
    rel_path: str
    candidate_targets: tuple[str, ...]
    exact_import_usage: tuple[tuple[str, tuple[str, ...]], ...]
    edges: tuple[ImportEdge, ...] = ()


@dataclass(frozen=True)
class _ScanCache:
    version: int
    modules: tuple[ParsedModule, ...]
    failures: tuple[ImportGraphFailure, ...]


@dataclass(frozen=True)
class _SourceRead:
    module_name: str
    path: Path
    text: str | None
    failure_reason: str | None = None
    failure_detail: str = ""


@dataclass(frozen=True)
class _BindState:
    """Names that change TYPE_CHECKING and dynamic-import classification."""

    flag_names: frozenset[str] = frozenset({"TYPE_CHECKING"})
    typing_modules: frozenset[str] = frozenset()
    import_module_names: frozenset[str] = frozenset()
    importlib_modules: frozenset[str] = frozenset()
    dunder_import_bound: bool = True


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


def _read_module_source(item: tuple[str, Path]) -> _SourceRead:
    """Read one Python module source payload for import-graph parsing.

    Uses a single bounded read (no pre-stat) so cloud-synced trees pay one
    open/read round-trip per file instead of stat+read. Oversize and
    unreadable files are failures; they are not dropped.
    """
    module_name, py_file = item
    try:
        with py_file.open("rb") as stream:
            source_bytes = stream.read(_MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        return _SourceRead(
            module_name,
            py_file,
            None,
            FAILURE_UNREADABLE,
            exc.__class__.__name__,
        )
    if len(source_bytes) > _MAX_SOURCE_BYTES:
        return _SourceRead(
            module_name,
            py_file,
            None,
            FAILURE_OVERSIZE,
            f"source exceeds {_MAX_SOURCE_BYTES} bytes",
        )
    return _SourceRead(
        module_name,
        py_file,
        source_bytes.decode("utf-8", errors="replace"),
    )


def _read_module_sources(modules: list[tuple[str, Path]]) -> list[_SourceRead]:
    """Read module sources with bounded parallelism before single-thread parsing."""
    max_workers = _read_worker_count(len(modules))
    if max_workers == 1:
        return [_read_module_source(module) for module in modules]

    # map() preserves order; chunking keeps memory bounded for large trees.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_read_module_source, modules, chunksize=32))


def default_scan_roots(repo_root: Path) -> tuple[PackageScan, ...]:
    """Return the canonical first-party scan roots."""
    return (
        PackageScan("src", repo_root / "src" / "bioetl", "bioetl"),
        PackageScan("tests", repo_root / "tests", "tests"),
    )


def scan_roots(
    repo_root: Path,
    *,
    include_memory: bool = False,
) -> tuple[PackageScan, ...]:
    """Return import-graph scan roots.

    ``include_memory=False`` matches :func:`default_scan_roots`.
    ``include_memory=True`` is the wider root and also scans ``src/memory``.
    Memory edges are recorded only; five-layer ``bioetl`` rules do not apply.
    """
    roots = default_scan_roots(repo_root)
    if not include_memory:
        return roots
    return (
        *roots,
        PackageScan("memory", repo_root / "src" / "memory", "memory"),
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


def _roots_cache_key(
    roots: tuple[PackageScan, ...],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (scan.label, str(scan.root.resolve()), scan.module_prefix) for scan in roots
    )


def _import_sources_fingerprint(
    modules: list[tuple[str, Path]],
    *,
    roots_key: tuple[tuple[str, str, str], ...],
) -> str:
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
    for label, root, prefix in roots_key:
        digest.update(label.encode())
        digest.update(b"\0")
        digest.update(root.encode())
        digest.update(b"\0")
        digest.update(prefix.encode())
        digest.update(b"\0")
    for module_name, signature in rows:
        digest.update(module_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(signature.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _load_scan_cache(cache_path: Path) -> _ScanCache | None:
    try:
        with cache_path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError, AttributeError):
        return None
    if not isinstance(payload, _ScanCache):
        return None
    if payload.version != _PARSED_CACHE_VERSION:
        return None
    if not all(isinstance(item, ParsedModule) for item in payload.modules):
        return None
    if not all(isinstance(item, ImportGraphFailure) for item in payload.failures):
        return None
    return payload


def _store_scan_cache(cache_path: Path, payload: _ScanCache) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        with temp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
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


def _relative_posix(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


def _edge_sort_key(edge: ImportEdge) -> tuple[object, ...]:
    return (
        edge.source,
        edge.target,
        edge.file,
        edge.line,
        edge.syntax,
        edge.resolution,
        edge.timing,
    )


def _failure_sort_key(failure: ImportGraphFailure) -> tuple[str, str, str]:
    return (failure.file, failure.reason, failure.detail)


def _build_parsed_module(
    *,
    scan_label: str,
    repo_root: Path,
    py_file: Path,
    importer_module: str,
    source_text: str,
    existing_modules: frozenset[str],
    graph_modules: frozenset[str],
    prefixes: frozenset[str],
) -> tuple[ParsedModule | None, ImportGraphFailure | None]:
    rel_path = _relative_posix(repo_root, py_file)
    importer_is_package = py_file.name in {_INIT_PY, _INIT_PYI}
    try:
        tree = ast.parse(source_text, filename=str(py_file), mode="exec")
    except SyntaxError as exc:
        return None, ImportGraphFailure(
            file=rel_path,
            reason=FAILURE_PARSE_ERROR,
            detail=f"{exc.msg} (line {exc.lineno or 0})",
        )
    candidate_targets, exact_import_usage = _parse_module_import_graph(
        tree=tree,
        existing_modules=existing_modules,
        importer_module=importer_module,
        importer_is_package=importer_is_package,
    )
    edges = _collect_module_edges(
        tree,
        source=importer_module,
        file=rel_path,
        is_package=importer_is_package,
        is_stub=py_file.suffix == ".pyi",
        existing=graph_modules,
        prefixes=prefixes,
    )
    return (
        ParsedModule(
            scan_label=scan_label,
            rel_path=rel_path,
            candidate_targets=tuple(sorted(candidate_targets)),
            exact_import_usage=tuple(
                (module_name, tuple(sorted(imported_names)))
                for module_name, imported_names in sorted(exact_import_usage.items())
            ),
            edges=tuple(sorted(edges, key=_edge_sort_key)),
        ),
        None,
    )


def _append_parsed_source(
    *,
    scan: PackageScan,
    source: _SourceRead,
    repo_root: Path,
    census_modules: frozenset[str],
    graph_modules: frozenset[str],
    prefixes: frozenset[str],
    parsed_modules: list[ParsedModule],
    failures: list[ImportGraphFailure],
) -> None:
    if source.text is None:
        failures.append(
            ImportGraphFailure(
                file=_relative_posix(repo_root, source.path),
                reason=source.failure_reason or FAILURE_UNREADABLE,
                detail=source.failure_detail,
            )
        )
        return
    parsed, failure = _build_parsed_module(
        scan_label=scan.label,
        repo_root=repo_root,
        py_file=source.path,
        importer_module=source.module_name,
        source_text=source.text,
        existing_modules=census_modules,
        graph_modules=graph_modules,
        prefixes=prefixes,
    )
    if failure is not None:
        failures.append(failure)
    if parsed is not None:
        parsed_modules.append(parsed)


def _parse_scan_modules(
    *,
    scans: tuple[PackageScan, ...],
    repo_root: Path,
    census_modules: frozenset[str],
    graph_modules: frozenset[str],
    prefixes: frozenset[str],
) -> tuple[list[ParsedModule], list[ImportGraphFailure]]:
    """Read each scan separately so labels stay src/tests."""
    parsed_modules: list[ParsedModule] = []
    failures: list[ImportGraphFailure] = []
    for scan in scans:
        for source in _read_module_sources(_iter_import_sources(scan)):
            _append_parsed_source(
                scan=scan,
                source=source,
                repo_root=repo_root,
                census_modules=census_modules,
                graph_modules=graph_modules,
                prefixes=prefixes,
                parsed_modules=parsed_modules,
                failures=failures,
            )
    return parsed_modules, failures


def _collect_parsed_modules(repo_root_str: str) -> tuple[ParsedModule, ...]:
    """Parse default scan roots once per repo path for reuse across checks."""
    roots_key = _roots_cache_key(default_scan_roots(Path(repo_root_str)))
    return _collect_import_scan(repo_root_str, roots_key).modules


@cache
def _collect_import_scan(
    repo_root_str: str,
    roots_key: tuple[tuple[str, str, str], ...],
) -> _ScanCache:
    """Parse one root set, keeping read and parse failures with the modules."""
    repo_root = Path(repo_root_str)
    scans = tuple(
        PackageScan(label, Path(root), prefix) for label, root, prefix in roots_key
    )
    census_scan = next((scan for scan in scans if scan.module_prefix == "bioetl"), None)
    census_modules = (
        _collect_existing_modules(census_scan)
        if census_scan is not None
        else frozenset()
    )
    graph_modules: set[str] = set()
    for scan in scans:
        graph_modules.update(_collect_existing_modules(scan))
    prefixes = frozenset(scan.module_prefix for scan in scans)
    import_sources: list[tuple[str, Path]] = []
    for scan in scans:
        import_sources.extend(_iter_import_sources(scan))

    fingerprint = _import_sources_fingerprint(import_sources, roots_key=roots_key)
    cache_path = (
        _parsed_modules_cache_dir(repo_root)
        / f"parsed-v{_PARSED_CACHE_VERSION}-{fingerprint[:24]}.pkl"
    )
    cached = _load_scan_cache(cache_path)
    if cached is not None:
        return cached

    # Preserve scan-label grouping: read each scan separately so ParsedModule
    # labels remain src/tests even though the fingerprint covers every root.
    parsed_modules, failures = _parse_scan_modules(
        scans=scans,
        repo_root=repo_root,
        census_modules=census_modules,
        graph_modules=frozenset(graph_modules),
        prefixes=prefixes,
    )

    result = _ScanCache(
        version=_PARSED_CACHE_VERSION,
        modules=tuple(parsed_modules),
        failures=tuple(sorted(failures, key=_failure_sort_key)),
    )
    _store_scan_cache(cache_path, result)
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
        return [
            alias.name
            for alias in node.names
            if alias.name.startswith(_BIOETL_MODULE_PREFIX)
        ]

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


def _in_scan(module_name: str, prefixes: frozenset[str]) -> bool:
    return module_name.split(".", 1)[0] in prefixes


def _clear_name(state: _BindState, name: str) -> _BindState:
    return cast(
        _BindState,
        replace(
            state,
            flag_names=state.flag_names - {name},
            typing_modules=state.typing_modules - {name},
            import_module_names=state.import_module_names - {name},
            importlib_modules=state.importlib_modules - {name},
            dunder_import_bound=state.dunder_import_bound and name != "__import__",
        ),
    )


def _add_kind(state: _BindState, name: str, kind: str) -> _BindState:
    if kind == "flag":
        return cast(_BindState, replace(state, flag_names=state.flag_names | {name}))
    if kind == "typing_module":
        return cast(
            _BindState, replace(state, typing_modules=state.typing_modules | {name})
        )
    if kind == "importlib_module":
        return cast(
            _BindState,
            replace(state, importlib_modules=state.importlib_modules | {name}),
        )
    if kind == "import_module":
        return cast(
            _BindState,
            replace(state, import_module_names=state.import_module_names | {name}),
        )
    return state


def _iter_target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for elt in target.elts:
            names.extend(_iter_target_names(elt))
        return names
    if isinstance(target, ast.Starred):
        return _iter_target_names(target.value)
    return []


def _bound_name_kind(name: str, state: _BindState) -> str | None:
    if name in state.flag_names:
        return "flag"
    if name in state.typing_modules:
        return "typing_module"
    if name in state.importlib_modules:
        return "importlib_module"
    if name in state.import_module_names:
        return "import_module"
    return None


def _attribute_kind(expr: ast.Attribute, state: _BindState) -> str | None:
    if not isinstance(expr.value, ast.Name):
        return None
    if expr.attr == "TYPE_CHECKING" and expr.value.id in state.typing_modules:
        return "flag"
    if expr.attr == "import_module" and expr.value.id in state.importlib_modules:
        return "import_module"
    return None


def _expr_kind(expr: ast.AST, state: _BindState) -> str | None:
    if isinstance(expr, ast.Name):
        return _bound_name_kind(expr.id, state)
    if isinstance(expr, ast.Attribute):
        return _attribute_kind(expr, state)
    return None


def _bind_assignment(
    state: _BindState,
    target: ast.AST,
    value: ast.AST | None,
) -> _BindState:
    names = _iter_target_names(target)
    if len(names) == 1 and isinstance(target, ast.Name) and value is not None:
        kind = _expr_kind(value, state)
        state = _clear_name(state, names[0])
        if kind is not None:
            state = _add_kind(state, names[0], kind)
        return state
    for name in names:
        state = _clear_name(state, name)
    return state


def _bind_import_alias(state: _BindState, alias: ast.alias) -> _BindState:
    bound = alias.asname or alias.name.split(".", 1)[0]
    state = _clear_name(state, bound)
    top = alias.name.split(".", 1)[0]
    binds_package = alias.asname is None or alias.name == top
    if top in _TYPING_MODULES and binds_package:
        state = _add_kind(state, bound, "typing_module")
    if top == "importlib" and (alias.asname is None or alias.name == "importlib"):
        state = _add_kind(state, bound, "importlib_module")
    return state


def _bind_from_alias(
    state: _BindState,
    node: ast.ImportFrom,
    alias: ast.alias,
) -> _BindState:
    if alias.name == "*":
        return state
    bound = alias.asname or alias.name
    state = _clear_name(state, bound)
    if node.level != 0:
        return state
    if node.module in _TYPING_MODULES and alias.name == "TYPE_CHECKING":
        return _add_kind(state, bound, "flag")
    if node.module == "importlib" and alias.name == "import_module":
        return _add_kind(state, bound, "import_module")
    return state


def _named_type_checking(expr: ast.AST, state: _BindState) -> bool:
    if isinstance(expr, ast.Name) and expr.id in state.flag_names:
        return True
    return (
        isinstance(expr, ast.Attribute)
        and expr.attr == "TYPE_CHECKING"
        and isinstance(expr.value, ast.Name)
        and expr.value.id in state.typing_modules
    )


def _and_type_checking(values: list[bool | None]) -> bool:
    if not any(value is True for value in values):
        return False
    return all(value is True or value is None for value in values)


def _or_type_checking(values: list[bool | None]) -> bool:
    return bool(values) and all(value is True for value in values)


def _bool_type_checking(expr: ast.BoolOp, state: _BindState) -> bool | None:
    values = [_type_checking_polarity(value, state) for value in expr.values]
    if isinstance(expr.op, ast.And) and _and_type_checking(values):
        return True
    if isinstance(expr.op, ast.Or) and _or_type_checking(values):
        return True
    return None


def _type_checking_polarity(expr: ast.AST, state: _BindState) -> bool | None:
    """True when the branch is type-checker-only, False for its negation."""
    if _named_type_checking(expr, state):
        return True
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        inner = _type_checking_polarity(expr.operand, state)
        if inner is None:
            return None
        return not inner
    if isinstance(expr, ast.BoolOp):
        return _bool_type_checking(expr, state)
    return None


def _constant_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _constant_int(node: ast.AST | None) -> int | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return node.value
    return None


def _call_arg(node: ast.Call, index: int, keyword: str) -> ast.AST | None:
    if len(node.args) > index:
        return node.args[index]
    for item in node.keywords:
        if item.arg == keyword:
            return item.value
    return None


def _resolve_dynamic_relative(name: str, package: str) -> str | None:
    level = len(name) - len(name.lstrip("."))
    rest = name[level:] or None
    return _resolve_relative_module(
        importer_module=package,
        importer_is_package=True,
        module=rest,
        level=level,
    )


def _dynamic_syntax(func: ast.AST, state: _BindState) -> str | None:
    if isinstance(func, ast.Name):
        if func.id in state.import_module_names:
            return SYNTAX_IMPORT_MODULE
        if func.id == "__import__" and state.dunder_import_bound:
            return SYNTAX_DUNDER_IMPORT
        return None
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id in state.importlib_modules
    ):
        return SYNTAX_IMPORT_MODULE
    return None


class _EdgeCollector(ast.NodeVisitor):
    """Collect import edges with syntax, resolution, and timing."""

    def __init__(
        self,
        *,
        source: str,
        file: str,
        is_package: bool,
        existing: frozenset[str],
        prefixes: frozenset[str],
        type_checking: bool,
    ) -> None:
        self.source = source
        self.file = file
        self.is_package = is_package
        self.existing = existing
        self.prefixes = prefixes
        self.type_checking = type_checking
        self.deferred = False
        self.state = _BindState()
        self.edges: set[ImportEdge] = set()

    def _timing(self) -> str:
        if self.type_checking:
            return TIMING_TYPE_CHECKING
        if self.deferred:
            return TIMING_DEFERRED
        return TIMING_MODULE_IMPORT_TIME

    def _add(
        self,
        *,
        target: str,
        syntax: str,
        resolution: str,
        lineno: int | None,
    ) -> None:
        self.edges.add(
            ImportEdge(
                source=self.source,
                target=target,
                file=self.file,
                line=int(lineno or 0),
                syntax=syntax,
                resolution=resolution,
                timing=self._timing(),
            )
        )

    def _visit_isolated(
        self,
        statements: list[ast.stmt],
        *,
        type_checking: bool,
    ) -> None:
        saved_state = self.state
        saved_deferred = self.deferred
        saved_type_checking = self.type_checking
        self.type_checking = type_checking
        for stmt in statements:
            self.visit(stmt)
        self.state = saved_state
        self.deferred = saved_deferred
        self.type_checking = saved_type_checking

    def _visit_argument_defaults(self, args: ast.arguments) -> None:
        for default in args.defaults:
            self.visit(default)
        for default in args.kw_defaults:
            if default is not None:
                self.visit(default)

    def _visit_deferred_body(
        self,
        body: list[ast.stmt],
        *,
        name: str,
        args: ast.arguments | None,
    ) -> None:
        # Class bodies execute while the class statement runs, but DEP-004
        # classifies both function-body and class-body imports as deferred.
        saved_state = self.state
        saved_deferred = self.deferred
        saved_type_checking = self.type_checking
        self.state = self.state if args is None else _shadow_arguments(self.state, args)
        self.deferred = True
        for stmt in body:
            self.visit(stmt)
        self.state = _clear_name(saved_state, name)
        self.deferred = saved_deferred
        self.type_checking = saved_type_checking

    def _record_import(self, node: ast.Import) -> None:
        for alias in node.names:
            if not _in_scan(alias.name, self.prefixes):
                continue
            resolution = (
                RESOLUTION_RESOLVED
                if alias.name in self.existing
                else RESOLUTION_UNRESOLVED
            )
            self._add(
                target=alias.name,
                syntax=SYNTAX_IMPORT,
                resolution=resolution,
                lineno=node.lineno,
            )

    def _child_modules(self, base: str, imported_names: list[str]) -> list[str]:
        return [name for name in imported_names if f"{base}.{name}" in self.existing]

    def _skip_package_edge(
        self,
        node: ast.ImportFrom,
        base: str,
        imported_names: list[str],
    ) -> bool:
        # `from . import child` names the child module. Also recording the
        # parent package closes a cycle with every package __init__ that
        # imports that child. `from . import TOKEN` still depends on the package.
        child_modules = self._child_modules(base, imported_names)
        return (
            node.module is None
            and node.level > 0
            and bool(imported_names)
            and len(child_modules) == len(imported_names)
        )

    def _record_from_package(self, node: ast.ImportFrom, base: str) -> bool:
        """Record the package edge. False means the caller must stop."""
        if base == self.source:
            return base in self.existing
        resolution = (
            RESOLUTION_RESOLVED if base in self.existing else RESOLUTION_UNRESOLVED
        )
        self._add(
            target=base,
            syntax=SYNTAX_IMPORT_FROM,
            resolution=resolution,
            lineno=node.lineno,
        )
        return base in self.existing

    def _record_from_names(self, node: ast.ImportFrom, base: str) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            nested = f"{base}.{alias.name}"
            if nested == self.source:
                continue
            resolution = (
                RESOLUTION_RESOLVED
                if nested in self.existing
                else RESOLUTION_SYMBOL_NOT_MODULE
            )
            self._add(
                target=nested,
                syntax=SYNTAX_IMPORT_FROM,
                resolution=resolution,
                lineno=node.lineno,
            )

    def _record_import_from(self, node: ast.ImportFrom) -> None:
        base = _resolve_relative_module(
            importer_module=self.source,
            importer_is_package=self.is_package,
            module=node.module,
            level=node.level,
        )
        if base is None:
            self._add(
                target=INVALID_RELATIVE_IMPORT_TARGET,
                syntax=SYNTAX_IMPORT_FROM,
                resolution=RESOLUTION_UNRESOLVED,
                lineno=node.lineno,
            )
            return
        if not _in_scan(base, self.prefixes):
            return
        imported_names = [alias.name for alias in node.names if alias.name != "*"]
        if not self._skip_package_edge(node, base, imported_names):
            if not self._record_from_package(node, base):
                return
        self._record_from_names(node, base)

    def _record_unresolved_dynamic(
        self,
        node: ast.Call,
        syntax: str,
        *,
        target: str,
    ) -> None:
        self._add(
            target=target,
            syntax=syntax,
            resolution=RESOLUTION_UNRESOLVED,
            lineno=node.lineno,
        )

    def _relative_import_module_target(
        self,
        node: ast.Call,
        syntax: str,
        name: str,
    ) -> str | None:
        package = _constant_str(_call_arg(node, 1, "package"))
        target = None if package is None else _resolve_dynamic_relative(name, package)
        if target is not None:
            return target
        self._record_unresolved_dynamic(
            node,
            syntax,
            target=INVALID_RELATIVE_IMPORT_TARGET,
        )
        return None

    def _dunder_level(self, node: ast.Call, syntax: str) -> int | None:
        level_node = _call_arg(node, 4, "level")
        if level_node is None:
            return 0
        level = _constant_int(level_node)
        if level is not None:
            return level
        self._record_unresolved_dynamic(
            node,
            syntax,
            target=NON_CONSTANT_IMPORT_TARGET,
        )
        return None

    def _dunder_import_target(
        self,
        node: ast.Call,
        syntax: str,
        name: str,
    ) -> str | None:
        level = self._dunder_level(node, syntax)
        if level is None:
            return None
        if not level:
            return name
        target = _resolve_relative_module(
            importer_module=self.source,
            importer_is_package=self.is_package,
            module=name,
            level=level,
        )
        if target is not None:
            return target
        self._record_unresolved_dynamic(
            node,
            syntax,
            target=INVALID_RELATIVE_IMPORT_TARGET,
        )
        return None

    def _dynamic_target(
        self,
        node: ast.Call,
        syntax: str,
        name: str,
    ) -> str | None:
        if syntax == SYNTAX_IMPORT_MODULE and name.startswith("."):
            return self._relative_import_module_target(node, syntax, name)
        if syntax == SYNTAX_DUNDER_IMPORT:
            return self._dunder_import_target(node, syntax, name)
        return name

    def _record_dynamic(self, node: ast.Call, syntax: str) -> None:
        name = _constant_str(_call_arg(node, 0, "name"))
        if name is None:
            self._record_unresolved_dynamic(
                node,
                syntax,
                target=NON_CONSTANT_IMPORT_TARGET,
            )
            return
        target = self._dynamic_target(node, syntax, name)
        if target is None or not _in_scan(target, self.prefixes):
            return
        resolution = (
            RESOLUTION_RESOLVED if target in self.existing else RESOLUTION_UNRESOLVED
        )
        self._add(
            target=target,
            syntax=syntax,
            resolution=resolution,
            lineno=node.lineno,
        )

    def visit_Import(self, node: ast.Import) -> None:
        self._record_import(node)
        for alias in node.names:
            self.state = _bind_import_alias(self.state, alias)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._record_import_from(node)
        for alias in node.names:
            self.state = _bind_from_alias(self.state, node, alias)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.state = _bind_assignment(self.state, target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
        self.state = _bind_assignment(self.state, node.target, node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        for name in _iter_target_names(node.target):
            self.state = _clear_name(self.state, name)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self.state = _bind_assignment(self.state, node.target, node.value)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            for name in _iter_target_names(target):
                self.state = _clear_name(self.state, name)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        if self.type_checking:
            self._visit_isolated(node.body, type_checking=True)
            self._visit_isolated(node.orelse, type_checking=True)
            return
        polarity = _type_checking_polarity(node.test, self.state)
        if polarity is True:
            self._visit_isolated(node.body, type_checking=True)
            for stmt in node.orelse:
                self.visit(stmt)
            return
        if polarity is False:
            for stmt in node.body:
                self.visit(stmt)
            self._visit_isolated(node.orelse, type_checking=True)
            return
        self._visit_isolated(node.body, type_checking=False)
        self._visit_isolated(node.orelse, type_checking=False)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node)

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_argument_defaults(node.args)
        self._visit_deferred_body(node.body, name=node.name, args=node.args)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_argument_defaults(node.args)
        saved_deferred = self.deferred
        self.deferred = True
        self.visit(node.body)
        self.deferred = saved_deferred

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self._visit_deferred_body(node.body, name=node.name, args=None)

    def visit_Call(self, node: ast.Call) -> None:
        syntax = _dynamic_syntax(node.func, self.state)
        if syntax is not None:
            self._record_dynamic(node, syntax)
        self.generic_visit(node)


def _shadow_arguments(state: _BindState, args: ast.arguments) -> _BindState:
    names = [arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if args.vararg is not None:
        names.append(args.vararg.arg)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    for name in names:
        state = _clear_name(state, name)
    return state


def _collect_module_edges(
    tree: ast.AST,
    *,
    source: str,
    file: str,
    is_package: bool,
    is_stub: bool,
    existing: frozenset[str],
    prefixes: frozenset[str],
) -> set[ImportEdge]:
    collector = _EdgeCollector(
        source=source,
        file=file,
        is_package=is_package,
        existing=existing,
        prefixes=prefixes,
        type_checking=is_stub,
    )
    collector.visit(tree)
    return collector.edges


def project_import_edges(edges: Iterable[ImportEdge]) -> ImportGraphProjections:
    """Split edges into the five architecture projections.

    import-time runtime is resolved static imports executed while the module
    loads. Ownership is resolved import-time plus deferred edges, including
    resolved dynamic imports, and excludes type-only edges. Type-only is every
    ``TYPE_CHECKING`` or stub edge. Dynamic projections count literal and
    non-constant ``importlib.import_module`` / ``__import__`` calls.
    """
    materialized = tuple(edges)
    return ImportGraphProjections(
        import_time_runtime=tuple(
            edge
            for edge in materialized
            if edge.timing == TIMING_MODULE_IMPORT_TIME
            and edge.resolution == RESOLUTION_RESOLVED
            and edge.syntax in _STATIC_SYNTAX
        ),
        ownership=tuple(
            edge
            for edge in materialized
            if edge.timing in _OWNERSHIP_TIMING
            and edge.resolution == RESOLUTION_RESOLVED
        ),
        type_only=tuple(
            edge for edge in materialized if edge.timing == TIMING_TYPE_CHECKING
        ),
        dynamic_resolved=tuple(
            edge
            for edge in materialized
            if edge.syntax in _DYNAMIC_SYNTAX and edge.resolution == RESOLUTION_RESOLVED
        ),
        dynamic_unresolved=tuple(
            edge
            for edge in materialized
            if edge.syntax in _DYNAMIC_SYNTAX
            and edge.resolution == RESOLUTION_UNRESOLVED
        ),
    )


def collect_import_graph(
    repo_root: Path,
    *,
    include_memory: bool = False,
    roots: tuple[PackageScan, ...] | None = None,
) -> ImportGraphReport:
    """Collect edges, failures, and projections for ``roots``.

    ``roots=None`` uses :func:`scan_roots`. Pass ``include_memory=True`` or an
    explicit ``roots`` value from :func:`scan_roots` to add ``src/memory``.
    Memory is not judged by the five-layer ``bioetl`` rules. Parse, oversize,
    and unreadable files stay in ``failures`` so the report cannot PASS.
    """
    if roots is not None and include_memory:
        raise ValueError("pass either roots or include_memory, not both")
    resolved = repo_root.resolve()
    selected = (
        roots
        if roots is not None
        else scan_roots(resolved, include_memory=include_memory)
    )
    cached = _collect_import_scan(str(resolved), _roots_cache_key(selected))
    edges = tuple(
        sorted(
            (edge for module in cached.modules for edge in module.edges),
            key=_edge_sort_key,
        )
    )
    return ImportGraphReport(
        edges=edges,
        failures=cached.failures,
        projections=project_import_edges(edges),
    )


def _rotate_cycle(path: tuple[str, ...]) -> tuple[str, ...]:
    if len(path) <= 1:
        return path
    start = min(range(len(path)), key=path.__getitem__)
    return path[start:] + path[:start]


class _Tarjan:
    """Iterative-free Tarjan SCC. Methods stay under the cognitive-complexity cap."""

    def __init__(self, outgoing: dict[str, set[str]]) -> None:
        self.outgoing = outgoing
        self.index = 0
        self.stack: list[str] = []
        self.on_stack: set[str] = set()
        self.indices: dict[str, int] = {}
        self.low_links: dict[str, int] = {}
        self.components: list[frozenset[str]] = []

    def components_of(self) -> list[frozenset[str]]:
        for node in sorted(self.outgoing):
            if node not in self.indices:
                self._connect(node)
        return self.components

    def _connect(self, node: str) -> None:
        self.indices[node] = self.index
        self.low_links[node] = self.index
        self.index += 1
        self.stack.append(node)
        self.on_stack.add(node)
        self._visit_targets(node)
        if self.low_links[node] != self.indices[node]:
            return
        self.components.append(frozenset(self._pop_component(node)))

    def _visit_targets(self, node: str) -> None:
        for target in sorted(self.outgoing.get(node, ())):
            if target not in self.indices:
                self._connect(target)
                self.low_links[node] = min(self.low_links[node], self.low_links[target])
            elif target in self.on_stack:
                self.low_links[node] = min(self.low_links[node], self.indices[target])

    def _pop_component(self, node: str) -> list[str]:
        component: list[str] = []
        while self.stack:
            member = self.stack.pop()
            self.on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        return component


def _strongly_connected(outgoing: dict[str, set[str]]) -> list[frozenset[str]]:
    return _Tarjan(outgoing).components_of()


def _walk_cycle(
    node: str,
    path: list[str],
    seen: set[str],
    *,
    neighbors: dict[str, tuple[str, ...]],
    visited: set[str],
) -> tuple[str, ...] | None:
    visited.add(node)
    path.append(node)
    seen.add(node)
    for nxt in neighbors.get(node, ()):
        if nxt in seen:
            start = path.index(nxt)
            return tuple(path[start:])
        if nxt not in visited:
            found = _walk_cycle(nxt, path, seen, neighbors=neighbors, visited=visited)
            if found is not None:
                return found
    path.pop()
    seen.remove(node)
    return None


def _cycle_path(
    component: frozenset[str],
    outgoing: dict[str, set[str]],
) -> tuple[str, ...] | None:
    neighbors = {
        node: tuple(sorted(dst for dst in outgoing.get(node, ()) if dst in component))
        for node in component
    }
    visited: set[str] = set()
    for start in sorted(component):
        if start in visited:
            continue
        found = _walk_cycle(start, [], set(), neighbors=neighbors, visited=visited)
        if found is not None:
            return _rotate_cycle(found)
    return None


def _resolved_graph(
    edges: Iterable[ImportEdge],
) -> tuple[dict[tuple[str, str], list[ImportEdge]], dict[str, set[str]]]:
    pair_edges: dict[tuple[str, str], list[ImportEdge]] = defaultdict(list)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.resolution != RESOLUTION_RESOLVED:
            continue
        pair_edges[(edge.source, edge.target)].append(edge)
        outgoing[edge.source].add(edge.target)
        outgoing.setdefault(edge.target, set())
    return pair_edges, outgoing


def _trivial_component(
    component: frozenset[str],
    outgoing: dict[str, set[str]],
) -> bool:
    if len(component) != 1:
        return False
    node = next(iter(component))
    return node not in outgoing.get(node, ())


def _edges_along_path(
    path: tuple[str, ...],
    pair_edges: dict[tuple[str, str], list[ImportEdge]],
) -> tuple[ImportEdge, ...] | None:
    cycle_edges: list[ImportEdge] = []
    for index, source in enumerate(path):
        target = path[(index + 1) % len(path)]
        choices = pair_edges.get((source, target))
        if not choices:
            return None
        cycle_edges.append(min(choices, key=_edge_sort_key))
    if len(cycle_edges) != len(path):
        return None
    return tuple(cycle_edges)


def find_import_cycles(
    edges: Iterable[ImportEdge],
    *,
    projection: str,
) -> tuple[ImportCycle, ...]:
    """Return one reproducible cycle per SCC, with edge provenance.

    Only ``resolved`` edges are followed. The path is rotated so the
    lexicographically smallest node is first. Each hop keeps the lowest
    ``(file, line, syntax, resolution, timing)`` edge.
    """
    if projection not in PROJECTION_NAMES:
        raise ValueError(f"unknown import-graph projection: {projection}")
    pair_edges, outgoing = _resolved_graph(edges)
    cycles: list[ImportCycle] = []
    for component in _strongly_connected(outgoing):
        if _trivial_component(component, outgoing):
            continue
        path = _cycle_path(component, outgoing)
        if path is None:
            continue
        cycle_edges = _edges_along_path(path, pair_edges)
        if cycle_edges is None:
            continue
        cycles.append(
            ImportCycle(
                projection=projection,
                path=path,
                edges=cycle_edges,
            )
        )
    cycles.sort(
        key=lambda cycle: (
            cycle.path,
            tuple(_edge_sort_key(edge) for edge in cycle.edges),
        )
    )
    return tuple(cycles)
