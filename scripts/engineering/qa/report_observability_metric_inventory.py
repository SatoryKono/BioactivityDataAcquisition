#!/usr/bin/env python3
"""Report registry/runtime/docs drift for public observability metric families.

Usage:
    python -m scripts.engineering.qa report-observability-metric-inventory [--json]

The report is intentionally static and repo-local. It reconciles:
- registered public metric families
- runtime metric emitters in ``src/bioetl``
- documentation/dashboard references
- Prometheus rule references
- non-canonical alias candidates used in metric API calls
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from bioetl.domain.events import (  # noqa: E402
    ORDINARY_PIPELINE_STAGE_NAMES,
    PipelineEvent,
)
from bioetl.domain.runtime_observability_publication_contract import (  # noqa: E402
    get_runtime_observability_publication_contract,
)
from bioetl.infrastructure.observability import (  # noqa: E402
    metrics_definitions as _metric_defs,
)
from bioetl.infrastructure.observability.metrics_export_names import (  # noqa: E402
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (  # noqa: E402
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

_CANONICAL_METRIC_RE = re.compile(r"\bbioetl_[a-z0-9_]+\b")
_PROMETHEUS_METRIC_NAME_RE = re.compile(r"^[A-Za-z_:][A-Za-z0-9_:]*$")

_RUNTIME_SCAN_ROOT = Path("src/bioetl")
_REGISTERED_SCAN_ROOT = Path("src/bioetl/infrastructure/observability")
_DOC_SCAN_ROOTS = (
    Path("docs/02-architecture"),
    Path("docs/03-guides"),
    Path("docs/04-reference"),
    Path("docs/05-operations"),
    Path("grafana/dashboards"),
    Path("grafana/README.md"),
)
_RULE_SCAN_ROOT = Path("grafana/prometheus-rules")
_DEFAULT_DRIFT_ALLOWLIST = Path(
    "configs/quality/observability_metric_inventory_allowlist.yaml"
)
_DEFAULT_DECLARED_METRIC_DEFINITIONS = Path(
    "configs/quality/observability_metric_declarations.yaml"
)
_DEFAULT_OBSERVABILITY_GOVERNANCE = Path(
    "configs/quality/observability_metric_governance.yaml"
)
_RUNTIME_EXCLUDE_PARTS = (
    "src/bioetl/infrastructure/observability",
    "src/bioetl/domain",
)
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml"}
_TEXT_FILE_DISCOVERY_CACHE: dict[str, tuple[Path, ...]] = {}
_METRIC_INVENTORY_CACHE: dict[str, dict[str, object]] = {}
_TEXT_DISCOVERY_TIMEOUT_SECONDS: Final[float] = 20.0
_METRIC_MENTION_GREP_TIMEOUT_SECONDS: Final[float] = 20.0
_METRIC_MENTION_GREP_CHUNK_SIZE: Final[int] = 128
_PROMETHEUS_QUERY_TIMEOUT_SECONDS: Final[float] = 5.0
_PROMETHEUS_BASE_URL_ENV_VAR: Final[str] = "BIOETL_OBSERVABILITY_PROMETHEUS_URL"
_PROMETHEUS_BEARER_TOKEN_ENV_VAR: Final[str] = "BIOETL_OBSERVABILITY_PROMETHEUS_TOKEN"
_RUNTIME_METRIC_METHODS = frozenset(
    {"increment_counter", "observe_histogram", "set_gauge"}
)
_RUNTIME_METRIC_NAME_KEYWORDS = frozenset(
    {
        "metric_name",
        "phase_duration_metric",
        "phase_events_metric",
        "state_metric_name",
        "trip_metric_name",
    }
)
_RUNTIME_SCAN_MARKERS: Final[tuple[str, ...]] = (
    "bioetl_",
    "increment_counter",
    "observe_histogram",
    "set_gauge",
    ".inc(",
    ".observe(",
    ".set(",
    ".labels(",
    "metric_name",
    "phase_duration_metric",
    "phase_events_metric",
    "state_metric_name",
    "trip_metric_name",
)
_STATIC_RUNTIME_EMITTERS: Final[dict[str, tuple[str, ...]]] = {
    # This family is emitted through a prometheus_client Counter collector in the
    # metrics server rather than through the MetricsPort helper methods scanned
    # below. Keep it explicit so registry declarations remain tied to a concrete
    # runtime path without treating all registry modules as emitters.
    "bioetl_metrics_publication_events_total": (
        "src/bioetl/infrastructure/observability/server.py",
    ),
}
_PROMETHEUS_FAMILY_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "_bytes",
        "_count",
        "_enabled",
        "_ms",
        "_passed",
        "_rate",
        "_records",
        "_score",
        "_seconds",
        "_size",
        "_state",
        "_status",
        "_total",
        "_validated",
    }
)
_PROMETHEUS_ALIAS_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "_bytes",
        "_seconds",
        "_total",
    }
)
_RUNTIME_EVENT_SCAN_MARKERS: Final[tuple[str, ...]] = (
    "emit_event(",
    "emit_domain_event(",
    "PipelineEvent.",
)
_NON_METRIC_ALIAS_PREFIXES: Final[tuple[str, ...]] = (
    "get_",
    "set_",
    "track_",
    "resolve_",
    "build_",
    "collect_",
    "render_",
    "validate_",
    "latest_",
    "missing_",
    "degraded_",
    "run_manifest_",
    "run_ledger_",
)
_IGNORED_DOC_METRIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        "bioetl_alerts",
        "bioetl_observability",
        "bioetl_pipeline",
    }
)
_CHECK_DRIFT_KEYS: Final[tuple[str, ...]] = (
    "registered_without_runtime",
    "runtime_without_registry",
    "dead_metrics",
    "documented_without_registry",
    "rules_without_registry",
    "runtime_cardinality_review_required",
    "declared_risky_label_review_required",
    "runtime_label_contract_violations",
    "runtime_label_contract_unresolved",
    "runtime_cardinality_threshold_violations",
)
_ALLOWLIST_METADATA_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "runtime_cardinality_review_required",
        "declared_risky_label_review_required",
    }
)
_CARDINALITY_RISK_LABEL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "endpoint",
        "field",
        "pipeline_context",
        "provider_context",
        "run_type_context",
        "table",
    }
)
_DIRECT_COLLECTOR_TERMINAL_METHODS: Final[frozenset[str]] = frozenset(
    {"inc", "observe", "set"}
)
_METRIC_OBJECT_NAME_BY_ID: Final[dict[int, str]] = {
    id(metric): metric_name
    for registry in (COUNTERS, GAUGES, HISTOGRAMS)
    for metric_name, metric in registry.items()
}
_EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS: Final[dict[str, str]] = {
    export_name: metric_name
    for export_name in METRICS_DEFINITION_EXPORT_NAMES
    if isinstance(
        metric_name := _METRIC_OBJECT_NAME_BY_ID.get(
            id(getattr(_metric_defs, export_name))
        ),
        str,
    )
}


def _iter_text_files(root: Path) -> list[Path]:
    cache_key = root.as_posix()
    cached = _TEXT_FILE_DISCOVERY_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    discovered = _iter_text_files_with_git_ls_files(root)
    if discovered is not None:
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(discovered)
        return discovered
    if not root.exists():
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = ()
        return []
    if root.is_file():
        paths = [root] if root.suffix in _TEXT_SUFFIXES else []
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(paths)
        return paths
    discovered = _iter_text_files_with_rg(root)
    if discovered:
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(discovered)
        return discovered
    fallback_paths: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            if path.suffix in _TEXT_SUFFIXES:
                fallback_paths.append(path)
    fallback_paths = sorted(fallback_paths)
    _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(fallback_paths)
    return fallback_paths


def _iter_text_files_with_rg(root: Path) -> list[Path]:
    globs = [
        pattern for suffix in sorted(_TEXT_SUFFIXES) for pattern in ("-g", f"*{suffix}")
    ]
    try:
        result, stdout = _run_text_discovery_command(
            ["rg", "--files", root.as_posix(), *globs],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode not in {0, 1}:
        return []
    return sorted(
        Path(line)
        for line in stdout.splitlines()
        if line and Path(line).suffix in _TEXT_SUFFIXES
    )


def _iter_text_files_with_git_ls_files(root: Path) -> list[Path] | None:
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None
    try:
        result, stdout = _run_text_discovery_command(
            [
                "git",
                "-C",
                _REPO_ROOT.as_posix(),
                "ls-files",
                "--",
                pathspec,
            ],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return sorted(
        _REPO_ROOT / line
        for line in stdout.splitlines()
        if line and Path(line).suffix in _TEXT_SUFFIXES
    )


def _run_text_discovery_command(
    command: list[str],
    *,
    timeout: float,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Capture small discovery output without Windows pipe reader threads."""
    output_path = _temporary_text_discovery_output_path()
    try:
        with output_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
            result = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout,
                **_hidden_windows_subprocess_kwargs(),
            )
        stdout = output_path.read_text(encoding="utf-8", errors="replace")
    finally:
        output_path.unlink(missing_ok=True)
    return result, stdout


def _temporary_text_discovery_output_path() -> Path:
    handle = tempfile.NamedTemporaryFile(
        prefix="observability_metric_inventory_",
        suffix=".txt",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _hidden_windows_subprocess_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: object = subprocess,
) -> dict[str, object]:
    if os_name != "nt":
        return {}

    kwargs: dict[str, object] = {}
    create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window

    startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
    if callable(startupinfo_factory):
        startupinfo = startupinfo_factory()
        startf_use_show_window = int(
            getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
        )
        if startf_use_show_window:
            startupinfo.dwFlags = (
                int(getattr(startupinfo, "dwFlags", 0)) | startf_use_show_window
            )
        if hasattr(subprocess_module, "SW_HIDE"):
            startupinfo.wShowWindow = int(getattr(subprocess_module, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _repo_relative_pathspec(path: Path) -> str | None:
    try:
        common_path = os.path.commonpath(
            [
                os.path.abspath(os.fspath(_REPO_ROOT)),
                os.path.abspath(os.fspath(path)),
            ]
        )
    except ValueError:
        return None
    if os.path.normcase(common_path) != os.path.normcase(
        os.path.abspath(os.fspath(_REPO_ROOT))
    ):
        return None
    relative = os.path.relpath(
        os.path.abspath(os.fspath(path)),
        os.path.abspath(os.fspath(_REPO_ROOT)),
    )
    return "." if relative == "." else relative.replace(os.sep, "/")


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_canonical_metric_mentions(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]]:
    grep_mentions = _scan_canonical_metric_mentions_with_git_grep(paths, repo_root)
    if grep_mentions is not None:
        return grep_mentions

    mentions: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
            mentions[metric_name].append(_as_repo_relative(path, repo_root))
    return _normalize_mapping_lists(mentions)


def _scan_canonical_metric_mentions_with_git_grep(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]] | None:
    """Scan tracked text files without blocking Python on file reads.

    Windows/GDrive checkouts can stall indefinitely on ``Path.read_text`` for
    hydrated or locked documentation files. In real checkouts prefer bounded
    ``git grep`` and keep direct reads only for temporary unit-test trees.
    """
    if not (repo_root / ".git").exists():
        return None

    relative_paths: list[str] = []
    for path in paths:
        try:
            relative_paths.append(path.relative_to(repo_root).as_posix())
        except ValueError:
            return None
    if not relative_paths:
        return {}

    mentions: dict[str, list[str]] = defaultdict(list)
    for index in range(0, len(relative_paths), _METRIC_MENTION_GREP_CHUNK_SIZE):
        chunk = relative_paths[index : index + _METRIC_MENTION_GREP_CHUNK_SIZE]
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    repo_root.as_posix(),
                    "grep",
                    "-I",
                    "-n",
                    "--no-color",
                    "bioetl_",
                    "--",
                    *chunk,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=_METRIC_MENTION_GREP_TIMEOUT_SECONDS,
                **_hidden_windows_subprocess_kwargs(),
            )
        except OSError:
            return None
        except subprocess.TimeoutExpired:
            return _normalize_mapping_lists(mentions)
        if result.returncode == 1:
            continue
        if result.returncode != 0:
            return None

        for line in (result.stdout or "").splitlines():
            path_text, separator, remainder = line.partition(":")
            if not separator:
                continue
            _line_number, separator, text = remainder.partition(":")
            if not separator:
                continue
            for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
                mentions[metric_name].append(path_text)
    return _normalize_mapping_lists(mentions)


def _normalize_mapping_lists(
    mapping: dict[str, list[str]] | defaultdict[str, list[str]],
) -> dict[str, list[str]]:
    """Return a mapping with deterministically sorted unique list values."""
    return {key: sorted(set(values)) for key, values in sorted(mapping.items())}


def _read_runtime_candidate_text(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not any(marker in text for marker in _RUNTIME_SCAN_MARKERS):
        return None
    return text


def _module_path_from_import(module_name: str, repo_root: Path) -> Path | None:
    if not module_name.startswith("bioetl."):
        return None
    module_rel = module_name.replace(".", "/")
    module_path = repo_root / "src" / f"{module_rel}.py"
    if module_path.exists():
        return module_path
    package_init = repo_root / "src" / module_rel / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _collect_module_string_bindings(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError, TimeoutError):
        return {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    bindings: dict[str, str] = {}
    for node in tree.body:
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value_node.value
    return bindings


def _iter_string_assignments(tree: ast.AST) -> list[tuple[list[ast.expr], str]]:
    assignments: list[tuple[list[ast.expr], str]] = []
    for node in ast.walk(tree):
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        assignments.append((targets, value_node.value))
    return assignments


def _resolve_imported_string_bindings(
    tree: ast.AST,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]] | None = None,
) -> dict[str, str]:
    resolved_cache = cache if cache is not None else {}
    bindings: dict[str, str] = {}
    for node in _import_from_nodes(tree):
        relevant_aliases = _imported_string_constant_aliases(node.names)
        if not relevant_aliases:
            continue
        module_bindings = _module_string_bindings(
            node.module,
            repo_root=repo_root,
            cache=resolved_cache,
        )
        if module_bindings is None:
            continue
        _merge_imported_string_aliases(bindings, module_bindings, relevant_aliases)
    return bindings


def _collect_class_attribute_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for class_node in _class_nodes(tree):
        bindings.update(_class_attribute_string_bindings(class_node))
    return bindings


def _collect_repo_class_attribute_bindings(repo_root: Path) -> dict[str, str]:
    """Collect string-valued class attributes across runtime scan roots.

    This lets helper modules resolve ``self.METRIC_*`` style references even when
    the concrete string constant is declared on a subclass in another file.
    """
    bindings: dict[str, str] = {}
    for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT):
        path_str = path.as_posix()
        if any(excluded in path_str for excluded in _RUNTIME_EXCLUDE_PARTS):
            continue
        text = _read_runtime_candidate_text(path)
        if text is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        bindings.update(_collect_class_attribute_bindings(tree))
    return bindings


def _resolve_metric_name_expr(
    node: ast.expr,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return string_bindings.get(node.id) or metric_bindings.get(node.id)
    if isinstance(node, ast.Attribute):
        return attribute_bindings.get(node.attr) or metric_bindings.get(node.attr)
    return None


def _collect_local_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for targets, value in _iter_string_assignments(tree):
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _call_method_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _helper_metric_candidates(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
    call_method_name: str | None,
) -> set[str]:
    candidates: set[str] = set()
    if call_method_name == "emit_metric":
        for arg in node.args:
            metric_name = _resolve_metric_name_expr(
                arg,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            )
            if metric_name is not None:
                candidates.add(metric_name)
    for keyword in node.keywords:
        if keyword.value is None:
            continue
        metric_name = _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None:
            continue
        if keyword.arg in _RUNTIME_METRIC_NAME_KEYWORDS or metric_name.startswith(
            "bioetl_"
        ):
            candidates.add(metric_name)
    return candidates


def _scan_metric_names_in_tree(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[set[str], set[str], set[str]]:
    direct_metric_names: set[str] = set()
    helper_metric_names: set[str] = set()
    alias_metric_names: set[str] = set()

    for call_node in _call_nodes(tree):
        direct_metric_name, helper_candidates = _metric_names_for_call(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if direct_metric_name is not None:
            direct_metric_names.add(direct_metric_name)
            continue
        _partition_helper_metric_candidates(
            helper_candidates,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )

    return direct_metric_names, helper_metric_names, alias_metric_names


def _import_from_nodes(tree: ast.AST) -> list[ast.ImportFrom]:
    """Return import-from nodes with concrete module names."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]


def _looks_like_imported_string_constant_name(name: str) -> bool:
    """Return whether an imported name looks like a UPPER_SNAKE_CASE constant."""
    return any(ch.isalpha() for ch in name) and name.upper() == name


def _imported_string_constant_aliases(aliases: list[ast.alias]) -> list[ast.alias]:
    """Keep only aliases worth resolving as imported string constants."""
    return [
        alias
        for alias in aliases
        if alias.name != "*" and _looks_like_imported_string_constant_name(alias.name)
    ]


def _module_string_bindings(
    module_name: str | None,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]],
) -> dict[str, str] | None:
    """Load cached string bindings for one imported module."""
    if module_name is None:
        return None
    module_path = _module_path_from_import(module_name, repo_root)
    if module_path is None:
        return None
    if module_path not in cache:
        try:
            cache[module_path] = _collect_module_string_bindings(module_path)
        except (UnicodeDecodeError, OSError, TimeoutError):
            cache[module_path] = {}
    return cache[module_path]


def _merge_imported_string_aliases(
    bindings: dict[str, str],
    module_bindings: dict[str, str],
    aliases: list[ast.alias],
) -> None:
    """Merge imported string constants into the local binding map."""
    for alias in aliases:
        if alias.name == "*":
            continue
        resolved = module_bindings.get(alias.name)
        if resolved is not None:
            bindings[alias.asname or alias.name] = resolved


def _class_nodes(tree: ast.AST) -> list[ast.ClassDef]:
    """Return all class definitions in the tree."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _class_attribute_string_bindings(class_node: ast.ClassDef) -> dict[str, str]:
    """Collect string-valued class attribute bindings for one class."""
    bindings: dict[str, str] = {}
    for body_node in class_node.body:
        for targets, value in _iter_string_assignments(body_node):
            for target in targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = value
    return bindings


def _call_nodes(tree: ast.AST) -> list[ast.Call]:
    """Return all call nodes from the AST."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def _metric_names_for_call(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[str | None, set[str]]:
    """Return direct runtime metric name or helper candidates for one call."""
    method_name = _call_method_name(node)
    if method_name in _RUNTIME_METRIC_METHODS:
        return (
            _direct_metric_name(
                node,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            ),
            set(),
        )
    collector_metric_name = _direct_collector_metric_name(
        node,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    if collector_metric_name is not None:
        return (collector_metric_name, set())
    return (
        None,
        _helper_metric_candidates(
            node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
            call_method_name=method_name,
        ),
    )


def _direct_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    """Resolve the direct runtime metric name from a runtime metrics call."""
    if node.args:
        return _resolve_metric_name_expr(
            node.args[0],
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    for keyword in node.keywords:
        if keyword.arg != "name" or keyword.value is None:
            continue
        return _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    return None


def _collector_base_metric_expr(node: ast.Call) -> ast.expr | None:
    func = node.func
    if (
        not isinstance(func, ast.Attribute)
        or func.attr not in _DIRECT_COLLECTOR_TERMINAL_METHODS
    ):
        return None
    if isinstance(func.value, ast.Call):
        labels_call = func.value
        labels_func = labels_call.func
        if isinstance(labels_func, ast.Attribute) and labels_func.attr == "labels":
            return labels_func.value
        return None
    return func.value


def _direct_collector_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    metric_expr = _collector_base_metric_expr(node)
    if metric_expr is None:
        return None
    return _resolve_metric_name_expr(
        metric_expr,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )


def _dict_literal_string_keys(node: ast.expr) -> frozenset[str] | None:
    """Return literal string keys when *node* is a dict literal."""
    if not isinstance(node, ast.Dict):
        return None
    keys: set[str] = set()
    for key_node in node.keys:
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            return None
        keys.add(key_node.value)
    return frozenset(keys)


def _direct_metric_label_keys(node: ast.Call) -> frozenset[str] | None:
    """Resolve statically declared label keys from one direct metric call."""
    for keyword in node.keywords:
        if keyword.arg == "labels" and keyword.value is not None:
            return _dict_literal_string_keys(keyword.value)
    if len(node.args) >= 3:
        return _dict_literal_string_keys(node.args[2])
    return frozenset()


def _scan_direct_metric_label_shapes(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> list[tuple[str, frozenset[str] | None, int]]:
    """Return direct metric label shapes resolved from literal label dictionaries."""
    shapes: list[tuple[str, frozenset[str] | None, int]] = []
    for call_node in _call_nodes(tree):
        if _call_method_name(call_node) not in _RUNTIME_METRIC_METHODS:
            continue
        metric_name = _direct_metric_name(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None or not metric_name.startswith("bioetl_"):
            continue
        shapes.append(
            (
                metric_name,
                _direct_metric_label_keys(call_node),
                getattr(call_node, "lineno", 0),
            )
        )
    return shapes


def _record_label_contract_violations(
    *,
    label_contract_violations: list[str],
    label_contract_unresolved: list[str],
    relative_path: str,
    label_shapes: list[tuple[str, frozenset[str] | None, int]],
) -> None:
    """Compare direct emitter label keys against declared registry contracts."""
    for metric_name, emitted_labels, lineno in label_shapes:
        declared_labels = REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name)
        if declared_labels is None:
            continue
        location = f"{relative_path}:{lineno}"
        if emitted_labels is None:
            label_contract_unresolved.append(f"{metric_name} @ {location}")
            continue
        missing = sorted(declared_labels - emitted_labels)
        extra = sorted(emitted_labels - declared_labels)
        if missing or extra:
            emitted = sorted(emitted_labels)
            declared = sorted(declared_labels)
            label_contract_violations.append(
                f"{metric_name} @ {location} missing={missing} extra={extra} "
                f"emitted={emitted} declared={declared}"
            )


def _partition_helper_metric_candidates(
    metric_names: set[str],
    *,
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    """Partition helper candidate names into canonical and alias buckets."""
    for metric_name in metric_names:
        if metric_name.startswith("bioetl_"):
            helper_metric_names.add(metric_name)
        elif _is_metric_like_alias_name(metric_name):
            alias_metric_names.add(metric_name)


def _is_metric_like_alias_name(metric_name: str) -> bool:
    """Return True only for plausible Prometheus-style alias metric names."""
    normalized = metric_name.strip()
    if not normalized:
        return False
    if not _PROMETHEUS_METRIC_NAME_RE.fullmatch(normalized):
        return False
    if "_" not in normalized:
        return False
    if normalized.startswith(_NON_METRIC_ALIAS_PREFIXES):
        return False
    return normalized.endswith(tuple(_PROMETHEUS_ALIAS_SUFFIXES))


def _record_runtime_mentions(
    *,
    canonical_mentions: dict[str, list[str]],
    helper_backed_mentions: dict[str, list[str]],
    alias_mentions: dict[str, list[str]],
    relative_path: str,
    direct_metric_names: set[str],
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    for metric_name in sorted(direct_metric_names):
        if metric_name.startswith("bioetl_"):
            canonical_mentions[metric_name].append(relative_path)
            continue
        if _is_metric_like_alias_name(metric_name):
            alias_mentions[metric_name].append(relative_path)
    for metric_name in sorted(helper_metric_names - direct_metric_names):
        helper_backed_mentions[metric_name].append(relative_path)
    for metric_name in sorted(alias_metric_names):
        alias_mentions[metric_name].append(relative_path)


def _scan_runtime_metric_file(
    path: Path,
    *,
    repo_root: Path,
    import_binding_cache: dict[Path, dict[str, str]],
    repo_attribute_bindings: dict[str, str] | None = None,
    preloaded_text: str | None = None,
) -> (
    tuple[
        str,
        set[str],
        set[str],
        set[str],
        list[tuple[str, frozenset[str] | None, int]],
    ]
    | None
):
    text = (
        preloaded_text
        if preloaded_text is not None
        else _read_runtime_candidate_text(path)
    )
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    string_bindings = _resolve_imported_string_bindings(
        tree,
        repo_root=repo_root,
        cache=import_binding_cache,
    )
    string_bindings.update(_collect_local_string_bindings(tree))
    metric_bindings = _resolve_imported_metric_bindings(tree)
    attribute_bindings = dict(repo_attribute_bindings or {})
    attribute_bindings.update(_collect_class_attribute_bindings(tree))
    direct_metric_names, helper_metric_names, alias_metric_names = (
        _scan_metric_names_in_tree(
            tree,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    )
    label_shapes = _scan_direct_metric_label_shapes(
        tree,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    return (
        _as_repo_relative(path, repo_root),
        direct_metric_names,
        helper_metric_names,
        alias_metric_names,
        label_shapes,
    )


def _scan_runtime_metric_calls(
    repo_root: Path,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    list[str],
    list[str],
]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
    helper_backed_mentions: dict[str, list[str]] = defaultdict(list)
    alias_mentions: dict[str, list[str]] = defaultdict(list)
    label_contract_violations: list[str] = []
    label_contract_unresolved: list[str] = []
    import_binding_cache: dict[Path, dict[str, str]] = {}
    repo_attribute_bindings = _collect_repo_class_attribute_bindings(repo_root)
    for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT):
        path_str = path.as_posix()
        if any(excluded in path_str for excluded in _RUNTIME_EXCLUDE_PARTS):
            continue
        scan_result = _scan_runtime_metric_file(
            path,
            repo_root=repo_root,
            import_binding_cache=import_binding_cache,
            repo_attribute_bindings=repo_attribute_bindings,
        )
        if scan_result is None:
            continue
        (
            relative_path,
            direct_metric_names,
            helper_metric_names,
            alias_metric_names,
            label_shapes,
        ) = scan_result
        _record_runtime_mentions(
            canonical_mentions=canonical_mentions,
            helper_backed_mentions=helper_backed_mentions,
            alias_mentions=alias_mentions,
            relative_path=relative_path,
            direct_metric_names=direct_metric_names,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )
        _record_label_contract_violations(
            label_contract_violations=label_contract_violations,
            label_contract_unresolved=label_contract_unresolved,
            relative_path=relative_path,
            label_shapes=label_shapes,
        )
    _record_static_runtime_emitters(repo_root, canonical_mentions)
    return (
        _normalize_mapping_lists(canonical_mentions),
        _normalize_mapping_lists(helper_backed_mentions),
        _normalize_mapping_lists(alias_mentions),
        sorted(label_contract_violations),
        sorted(label_contract_unresolved),
    )


def _record_static_runtime_emitters(
    repo_root: Path,
    canonical_mentions: dict[str, list[str]],
) -> None:
    """Record runtime emitters that use direct Prometheus collectors."""
    for metric_name, relative_paths in _STATIC_RUNTIME_EMITTERS.items():
        for relative_path in relative_paths:
            if (repo_root / relative_path).exists():
                canonical_mentions[metric_name].append(relative_path)


def _scan_registered_metric_names(repo_root: Path) -> frozenset[str]:
    metric_names: set[str] = set()
    for path in sorted((repo_root / _REGISTERED_SCAN_ROOT).glob("_metrics_defs_*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        metric_names.update(_CANONICAL_METRIC_RE.findall(text))
    return frozenset(metric_names)


def _load_declared_metric_definitions(repo_root: Path) -> dict[str, set[str]]:
    path = repo_root / _DEFAULT_DECLARED_METRIC_DEFINITIONS
    if not path.exists():
        return {
            "recording_rule_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    try:
        import yaml
    except ImportError:
        return {
            "recording_rule_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {
            "recording_rule_metrics": set(),
            "declared_label_contract_metrics": set(),
        }

    definitions: dict[str, set[str]] = {}
    for field in ("recording_rule_metrics", "declared_label_contract_metrics"):
        raw_metrics = payload.get(field, [])
        if not isinstance(raw_metrics, list):
            definitions[field] = set()
            continue
        definitions[field] = {
            value
            for value in raw_metrics
            if isinstance(value, str) and value.startswith("bioetl_")
        }
    return definitions


def _filter_declared_label_contract_metrics(
    unresolved_rows: list[str],
    declared_metric_names: set[str],
) -> list[str]:
    return [
        row
        for row in unresolved_rows
        if _drift_allowlist_token("runtime_label_contract_unresolved", row)
        not in declared_metric_names
    ]


def _resolve_imported_metric_bindings(tree: ast.AST) -> dict[str, str]:
    bindings = dict(_EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS)
    for node in _import_from_nodes(tree):
        for alias in node.names:
            if alias.name == "*":
                continue
            metric_name = _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS.get(alias.name)
            if metric_name is not None:
                bindings[alias.asname or alias.name] = metric_name
    return bindings


REGISTERED_PROMETHEUS_METRIC_NAMES = _scan_registered_metric_names(_REPO_ROOT)
REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {
    name: frozenset(metric._labelnames)
    for registry in (COUNTERS, GAUGES, HISTOGRAMS)
    for name, metric in registry.items()
}


def _looks_like_metric_family_name(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in _PROMETHEUS_FAMILY_SUFFIXES)


def _is_generated_prometheus_series(
    metric_name: str,
    registered_metrics: frozenset[str] | set[str],
) -> bool:
    histogram_suffixes = ("_bucket", "_sum", "_count")
    for suffix in histogram_suffixes:
        if metric_name.endswith(suffix):
            return metric_name[: -len(suffix)] in registered_metrics
    if metric_name.endswith("_created"):
        base = metric_name.removesuffix("_created")
        return base in registered_metrics or f"{base}_total" in registered_metrics
    return False


def _filter_documented_metric_mentions(
    mentions: dict[str, list[str]],
    *,
    registered_metrics: frozenset[str] | set[str],
) -> dict[str, list[str]]:
    filtered: dict[str, list[str]] = {}
    for metric_name, paths in mentions.items():
        if metric_name in _IGNORED_DOC_METRIC_NAMES:
            continue
        if metric_name.endswith("_"):
            continue
        if _is_generated_prometheus_series(metric_name, registered_metrics):
            continue
        if metric_name not in registered_metrics and not _looks_like_metric_family_name(
            metric_name
        ):
            continue
        filtered[metric_name] = paths
    return _normalize_mapping_lists(filtered)


def _scan_rule_metric_mentions(repo_root: Path) -> dict[str, list[str]]:
    try:
        import yaml
    except ImportError:
        return _scan_canonical_metric_mentions(
            _iter_text_files(repo_root / _RULE_SCAN_ROOT),
            repo_root,
        )

    mentions: dict[str, list[str]] = defaultdict(list)
    for path in _iter_text_files(repo_root / _RULE_SCAN_ROOT):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(payload, dict):
            continue
        rel_path = _as_repo_relative(path, repo_root)
        groups = payload.get("groups", [])
        if not isinstance(groups, list):
            continue
        for metric_name in _extract_rule_metric_names(groups):
            mentions[metric_name].append(rel_path)
    return _normalize_mapping_lists(mentions)


def _extract_rule_metric_names(groups: list[object]) -> list[str]:
    metric_names: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        rules = group.get("rules", [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            expr = rule.get("expr")
            if isinstance(expr, str):
                metric_names.update(_CANONICAL_METRIC_RE.findall(expr))
    return sorted(metric_names)


def _declared_pipeline_event_names() -> set[str]:
    declared: set[str] = set()
    for attribute_name in dir(PipelineEvent):
        if not attribute_name.isupper():
            continue
        value = getattr(PipelineEvent, attribute_name, None)
        if isinstance(value, str):
            declared.add(value)
    for stage_name in ORDINARY_PIPELINE_STAGE_NAMES:
        declared.add(PipelineEvent.phase_started(stage_name))
        declared.add(PipelineEvent.phase_completed(stage_name))
    return declared


def _load_retired_observability_event_names(repo_root: Path) -> set[str]:
    path = repo_root / _DEFAULT_OBSERVABILITY_GOVERNANCE
    if not path.exists():
        return set()
    try:
        import yaml
    except ImportError:
        return set()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return set()
    event_governance = payload.get("event_signal_governance", {})
    if not isinstance(event_governance, dict):
        return set()
    retired_entries = event_governance.get("retired_declared_events", [])
    if not isinstance(retired_entries, list):
        return set()
    retired: set[str] = set()
    for entry in retired_entries:
        if not isinstance(entry, dict):
            continue
        event_name = entry.get("event_name")
        action = entry.get("action")
        if isinstance(event_name, str) and action == "retire":
            retired.add(event_name)
    return retired


def _resolve_observability_event_expr(node: ast.expr) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "PipelineEvent"
    ):
        resolved = getattr(PipelineEvent, node.attr, None)
        return {resolved} if isinstance(resolved, str) else set()
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "PipelineEvent"
        and node.func.attr in {"phase_started", "phase_completed"}
    ):
        resolver = (
            PipelineEvent.phase_started
            if node.func.attr == "phase_started"
            else PipelineEvent.phase_completed
        )
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return {resolver(node.args[0].value)}
        return {resolver(stage_name) for stage_name in ORDINARY_PIPELINE_STAGE_NAMES}
    return set()


def _scan_domain_mapping_observability_events(
    repo_root: Path,
) -> tuple[set[str], dict[str, list[str]]]:
    mapping_path = repo_root / "src/bioetl/domain/observability_event_mapping.py"
    try:
        tree = ast.parse(mapping_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set(), {}

    event_names: set[str] = set()
    emitters: dict[str, list[str]] = defaultdict(list)
    relative_path = _as_repo_relative(mapping_path, repo_root)
    for node in _call_nodes(tree):
        if not isinstance(node.func, ast.Name) or node.func.id != "_build_envelope":
            continue
        for keyword in node.keywords:
            if keyword.arg != "event_name" or keyword.value is None:
                continue
            for event_name in _resolve_observability_event_expr(keyword.value):
                event_names.add(event_name)
                emitters[event_name].append(relative_path)
    return event_names, _normalize_mapping_lists(emitters)


def _scan_runtime_observability_event_calls(
    repo_root: Path,
) -> tuple[dict[str, list[str]], list[str]]:
    direct_emitters: dict[str, list[str]] = defaultdict(list)
    domain_event_emitters: list[str] = []
    for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT):
        relative_path = _as_repo_relative(path, repo_root)
        path_str = path.as_posix()
        if "src/bioetl/infrastructure" in path_str:
            continue
        text = _read_runtime_candidate_text(path)
        if text is None or not any(marker in text for marker in _RUNTIME_EVENT_SCAN_MARKERS):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in _call_nodes(tree):
            method_name = _call_method_name(node)
            if method_name == "emit_event" and node.args:
                for event_name in _resolve_observability_event_expr(node.args[0]):
                    direct_emitters[event_name].append(relative_path)
            if method_name == "emit_domain_event":
                domain_event_emitters.append(relative_path)
    return _normalize_mapping_lists(direct_emitters), sorted(set(domain_event_emitters))


def _load_runtime_cardinality_thresholds(repo_root: Path) -> dict[str, int]:
    """Load approved runtime-cardinality thresholds from governed allowlist."""
    allowlist_path = repo_root / _DEFAULT_DRIFT_ALLOWLIST
    if not allowlist_path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    payload = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    allowed = payload.get("allowed", {})
    if not isinstance(allowed, dict):
        return {}
    thresholds: dict[str, int] = {}
    for entry in allowed.get("runtime_cardinality_review_required", []):
        if not isinstance(entry, dict):
            continue
        metric = entry.get("metric")
        approved_max = entry.get("approved_max_series")
        if isinstance(metric, str) and isinstance(approved_max, int):
            thresholds[metric] = approved_max
    return thresholds


def _observed_runtime_series_counts() -> dict[str, int]:
    """Return current-process observed series counts from registered collectors."""
    counts: dict[str, int] = {}
    for registry in (COUNTERS, GAUGES, HISTOGRAMS):
        for metric_name, metric in registry.items():
            observed_labelsets: set[tuple[tuple[str, str], ...]] = set()
            for family in metric.collect():
                for sample in family.samples:
                    sample_name = str(sample.name)
                    if not (
                        sample_name == metric_name
                        or sample_name.startswith(f"{metric_name}_")
                    ):
                        continue
                    observed_labelsets.add(
                        tuple(
                            sorted((str(k), str(v)) for k, v in sample.labels.items())
                        )
                    )
            counts[metric_name] = len(observed_labelsets)
    return counts


def _runtime_cardinality_evidence_rows(
    *,
    metric_names: list[str],
    combined_emitters: dict[str, list[str]],
    observed_series_counts: dict[str, int],
    thresholds: dict[str, int],
) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    for metric_name in metric_names:
        labels = sorted(REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name, ()))
        rows = [
            f"observed_series_count={observed_series_counts.get(metric_name, 0)}",
            f"approved_max_series={thresholds.get(metric_name, 0)}",
            f"runtime_emitter_count={len(set(combined_emitters.get(metric_name, [])))}",
            "label_keys=" + ",".join(labels),
        ]
        evidence[metric_name] = rows
    return evidence


def _runtime_cardinality_threshold_violations(
    *,
    observed_series_counts: dict[str, int],
    thresholds: dict[str, int],
) -> list[str]:
    violations: list[str] = []
    for metric_name, approved_max in sorted(thresholds.items()):
        observed = observed_series_counts.get(metric_name, 0)
        if observed > approved_max:
            violations.append(
                f"{metric_name} observed_series_count={observed} approved_max_series={approved_max}"
            )
    return violations


def _resolve_prometheus_base_url(
    explicit_base_url: str | None,
) -> tuple[str | None, str]:
    if explicit_base_url and explicit_base_url.strip():
        return explicit_base_url.strip().rstrip("/"), "cli"
    env_base_url = os.getenv(_PROMETHEUS_BASE_URL_ENV_VAR, "").strip()
    if env_base_url:
        return env_base_url.rstrip("/"), "env"
    return None, "unconfigured"


def _prometheus_metric_family_matcher(metric_name: str) -> str:
    escaped = re.escape(metric_name)
    return f"^{escaped}(?:_bucket|_sum|_count|_created)?$"


def _prometheus_cardinality_query(
    metric_name: str,
    *,
    label_names: frozenset[str],
) -> str:
    selector = (
        "{__name__=~" + json.dumps(_prometheus_metric_family_matcher(metric_name)) + "}"
    )
    if label_names:
        labels_expr = ", ".join(sorted(label_names))
        return f"count(count by ({labels_expr}) ({selector}))"

    ignored_labels = ["__name__"]
    if metric_name in HISTOGRAMS:
        ignored_labels.append("le")
    ignored_expr = ", ".join(sorted(ignored_labels))
    return f"count(count without ({ignored_expr}) ({selector}))"


def _query_prometheus_scalar(
    *,
    prometheus_base_url: str,
    query: str,
    bearer_token: str,
) -> int:
    request = Request(
        url=prometheus_base_url.rstrip("/")
        + "/api/v1/query?"
        + urlencode({"query": query}),
        headers={"Accept": "application/json"},
    )
    if bearer_token:
        request.add_header("Authorization", f"Bearer {bearer_token}")

    try:
        with urlopen(request, timeout=_PROMETHEUS_QUERY_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:  # pragma: no cover - exercised via mocked failure paths
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except URLError as exc:  # pragma: no cover - exercised via mocked failure paths
        raise RuntimeError(str(exc.reason)) from exc

    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeError("unexpected Prometheus API response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("missing Prometheus API data payload")

    result_type = data.get("resultType")
    result = data.get("result")
    if result_type == "scalar" and isinstance(result, list) and len(result) == 2:
        return int(float(result[1]))
    if result_type == "vector" and isinstance(result, list) and len(result) == 1:
        vector_item = result[0]
        if isinstance(vector_item, dict):
            value = vector_item.get("value")
            if isinstance(value, list) and len(value) == 2:
                return int(float(value[1]))
    raise RuntimeError("Prometheus query did not return a single scalar result")


RuntimeCardinalityReviewSummary = dict[str, object]


def _local_observed_series_counts(report: MetricInventoryReport) -> dict[str, int]:
    raw_local_observed_series = report.get("runtime_cardinality_observed_series", {})
    if not isinstance(raw_local_observed_series, dict):
        return {}
    counts: dict[str, int] = {}
    for metric_name, raw_value in raw_local_observed_series.items():
        if not isinstance(metric_name, str):
            continue
        if isinstance(raw_value, int):
            counts[metric_name] = raw_value
            continue
        if not isinstance(raw_value, list):
            continue
        for row in raw_value:
            if not isinstance(row, str):
                continue
            prefix = "observed_series_count="
            if row.startswith(prefix):
                try:
                    counts[metric_name] = int(row.removeprefix(prefix))
                except ValueError:
                    pass
                break
    return counts


def _build_runtime_cardinality_review_summary(
    report: MetricInventoryReport,
    *,
    repo_root: Path,
    prometheus_base_url: str | None,
    allow_local_cardinality_fallback: bool = False,
) -> RuntimeCardinalityReviewSummary:
    reviewed_metrics = sorted(
        str(metric_name)
        for metric_name in report.get("runtime_cardinality_reviewed", [])
        if isinstance(metric_name, str)
    )
    review_required = sorted(
        str(metric_name)
        for metric_name in report.get("runtime_cardinality_review_required", [])
        if isinstance(metric_name, str)
    )
    static_threshold_violations = sorted(
        str(row)
        for row in report.get("runtime_cardinality_threshold_violations", [])
        if isinstance(row, str)
    )
    thresholds = _load_runtime_cardinality_thresholds(repo_root)
    resolved_base_url, url_source = _resolve_prometheus_base_url(prometheus_base_url)
    query_results: dict[str, int] = {}
    query_errors: dict[str, str] = {}
    degraded_reasons: list[str] = []
    live_threshold_violations: list[str] = []
    local_observed_series = _local_observed_series_counts(report)
    local_threshold_violations: list[str] = []

    summary: RuntimeCardinalityReviewSummary = {
        "generated_at": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source_command": (
            "python -m scripts.engineering.qa.report_observability_metric_inventory "
            "--check --write-evidence reports/observability/runtime_cardinality_inventory.json "
            "--review-json-out reports/observability/runtime_cardinality_review.json "
            '--summary-out "$GITHUB_STEP_SUMMARY" '
            "--fail-on-degraded-live-review"
        ),
        "status": "passed",
        "mode": "static_only",
        "prometheus_base_url": resolved_base_url,
        "prometheus_base_url_source": url_source,
        "prometheus_url_env_var": _PROMETHEUS_BASE_URL_ENV_VAR,
        "prometheus_token_env_var": _PROMETHEUS_BEARER_TOKEN_ENV_VAR,
        "local_cardinality_fallback_allowed": allow_local_cardinality_fallback,
        "reviewed_metrics": reviewed_metrics,
        "review_required_metrics": review_required,
        "static_threshold_violations": static_threshold_violations,
        "approved_thresholds": {
            metric_name: thresholds[metric_name]
            for metric_name in reviewed_metrics
            if metric_name in thresholds
        },
        "local_observed_series": {
            metric_name: local_observed_series[metric_name]
            for metric_name in reviewed_metrics
            if metric_name in local_observed_series
        },
        "local_threshold_violations": local_threshold_violations,
        "live_observed_series": query_results,
        "live_threshold_violations": live_threshold_violations,
        "degraded_reasons": degraded_reasons,
        "query_errors": query_errors,
    }
    if not reviewed_metrics:
        summary["mode"] = "no_reviewed_metrics"
        degraded_reasons.append(
            "no reviewed runtime-cardinality metrics require live evidence"
        )
        return summary

    missing_thresholds = [
        metric_name for metric_name in reviewed_metrics if metric_name not in thresholds
    ]
    if missing_thresholds:
        degraded_reasons.append(
            "missing approved_max_series for reviewed metrics: "
            + ", ".join(missing_thresholds)
        )

    if resolved_base_url is None:
        if allow_local_cardinality_fallback and not missing_thresholds:
            missing_local_observations = [
                metric_name
                for metric_name in reviewed_metrics
                if metric_name not in local_observed_series
            ]
            if not missing_local_observations:
                summary["mode"] = "local_cardinality_fallback"
                for metric_name in reviewed_metrics:
                    approved_max_series = thresholds[metric_name]
                    observed_series_count = local_observed_series[metric_name]
                    if observed_series_count > approved_max_series:
                        local_threshold_violations.append(
                            f"{metric_name} "
                            f"observed_series_count={observed_series_count} "
                            f"approved_max_series={approved_max_series}"
                        )
                if local_threshold_violations or static_threshold_violations:
                    summary["status"] = "failed"
                return summary
            degraded_reasons.append(
                "missing local cardinality observations for reviewed metrics: "
                + ", ".join(missing_local_observations)
            )
        summary["status"] = "degraded"
        degraded_reasons.append(
            f"missing {_PROMETHEUS_BASE_URL_ENV_VAR}; falling back to static cardinality evidence only"
        )
        return summary

    bearer_token = os.getenv(_PROMETHEUS_BEARER_TOKEN_ENV_VAR, "").strip()
    for metric_name in reviewed_metrics:
        query = _prometheus_cardinality_query(
            metric_name,
            label_names=REGISTERED_PROMETHEUS_METRIC_LABELS.get(
                metric_name,
                frozenset(),
            ),
        )
        try:
            query_results[metric_name] = _query_prometheus_scalar(
                prometheus_base_url=resolved_base_url,
                query=query,
                bearer_token=bearer_token,
            )
        except RuntimeError as exc:
            query_errors[metric_name] = str(exc)

    if query_errors or degraded_reasons:
        summary["status"] = "degraded"
        summary["mode"] = "live_review_unavailable"
        if query_errors:
            degraded_reasons.append(
                "live Prometheus review failed for: " + ", ".join(sorted(query_errors))
            )
        return summary

    summary["mode"] = "live_review"
    for metric_name, approved_max_series in sorted(thresholds.items()):
        if metric_name not in query_results:
            continue
        observed_series_count = query_results[metric_name]
        if observed_series_count > approved_max_series:
            live_threshold_violations.append(
                f"{metric_name} observed_series_count={observed_series_count} approved_max_series={approved_max_series}"
            )
    if live_threshold_violations:
        summary["status"] = "failed"
    return summary


def collect_metric_inventory(
    repo_root: Path,
) -> dict[str, list[str] | dict[str, list[str]]]:
    repo_root = repo_root.resolve()
    cache_key = repo_root.as_posix()
    cached = _METRIC_INVENTORY_CACHE.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    declared_metric_definitions = _load_declared_metric_definitions(repo_root)
    declared_rule_metrics = declared_metric_definitions["recording_rule_metrics"]
    declared_label_contract_metrics = declared_metric_definitions[
        "declared_label_contract_metrics"
    ]
    runtime_registered_set = set(REGISTERED_PROMETHEUS_METRIC_NAMES)
    declared_set = runtime_registered_set | declared_rule_metrics
    registered = sorted(declared_set)
    (
        runtime_mentions,
        helper_backed_mentions,
        alias_mentions,
        label_contract_violations,
        label_contract_unresolved,
    ) = _scan_runtime_metric_calls(repo_root)
    label_contract_unresolved = _filter_declared_label_contract_metrics(
        label_contract_unresolved,
        declared_label_contract_metrics,
    )

    doc_paths: list[Path] = []
    for root in _DOC_SCAN_ROOTS:
        doc_paths.extend(_iter_text_files(repo_root / root))
    docs_mentions = _filter_documented_metric_mentions(
        _scan_canonical_metric_mentions(doc_paths, repo_root),
        registered_metrics=declared_set,
    )
    rules_mentions = _filter_documented_metric_mentions(
        _scan_rule_metric_mentions(repo_root),
        registered_metrics=declared_set,
    )
    declared_pipeline_events = _declared_pipeline_event_names()
    mapped_observability_events, mapped_event_emitters = (
        _scan_domain_mapping_observability_events(repo_root)
    )
    direct_observability_event_emitters, domain_event_emitters = (
        _scan_runtime_observability_event_calls(repo_root)
    )
    raw_declared_observability_events = (
        declared_pipeline_events | mapped_observability_events
    )
    retired_declared_observability_events = sorted(
        raw_declared_observability_events
        & _load_retired_observability_event_names(repo_root)
    )
    declared_observability_events = sorted(
        raw_declared_observability_events - set(retired_declared_observability_events)
    )
    direct_emitted_observability_events = set(direct_observability_event_emitters)
    emitted_observability_events = sorted(
        direct_emitted_observability_events | mapped_observability_events
    )
    retired_declared_observability_events_emitted = sorted(
        set(retired_declared_observability_events) & set(emitted_observability_events)
    )
    unused_declared_observability_events = sorted(
        set(declared_observability_events) - set(emitted_observability_events)
    )
    emitted_observability_events_without_contract = sorted(
        set(emitted_observability_events) - set(declared_observability_events)
    )
    observability_event_emitters = _combine_metric_emitters(
        direct_observability_event_emitters,
        mapped_event_emitters,
    )
    runtime_observability_contract = get_runtime_observability_publication_contract()

    registered_set = set(registered)
    direct_runtime_set = set(runtime_mentions)
    helper_runtime_set = set(helper_backed_mentions)
    runtime_set = direct_runtime_set | helper_runtime_set
    docs_set = set(docs_mentions)
    rules_set = set(rules_mentions)
    registry_only_metrics = runtime_registered_set - runtime_set
    runtime_without_registry = runtime_set - registered_set
    dead_metrics = registry_only_metrics - docs_set - rules_set
    documented_without_runtime = (docs_set & runtime_registered_set) - runtime_set
    ruled_without_runtime = (rules_set & runtime_registered_set) - runtime_set
    combined_emitters = _combine_metric_emitters(
        runtime_mentions, helper_backed_mentions
    )
    observed_series_counts = _observed_runtime_series_counts()
    cardinality_thresholds = _load_runtime_cardinality_thresholds(repo_root)
    drift_allowlist = _load_drift_allowlist(repo_root / _DEFAULT_DRIFT_ALLOWLIST)
    reviewed_runtime_cardinality = drift_allowlist.get(
        "runtime_cardinality_review_required", set()
    ) | set(cardinality_thresholds)
    runtime_cardinality_candidates = sorted(
        metric_name
        for metric_name, emitter_paths in combined_emitters.items()
        if len(set(emitter_paths)) >= 3
    )
    runtime_cardinality_reviewed = sorted(
        set(runtime_cardinality_candidates) & reviewed_runtime_cardinality
    )
    runtime_cardinality_review_required = [
        metric_name
        for metric_name in runtime_cardinality_candidates
        if metric_name not in reviewed_runtime_cardinality
    ]
    runtime_cardinality_evidence = _runtime_cardinality_evidence_rows(
        metric_names=runtime_cardinality_candidates,
        combined_emitters=combined_emitters,
        observed_series_counts=observed_series_counts,
        thresholds=cardinality_thresholds,
    )
    runtime_cardinality_threshold_violations = (
        _runtime_cardinality_threshold_violations(
            observed_series_counts=observed_series_counts,
            thresholds=cardinality_thresholds,
        )
    )
    declared_risky_label_candidates = sorted(
        metric_name
        for metric_name, label_names in REGISTERED_PROMETHEUS_METRIC_LABELS.items()
        if metric_name in declared_set
        and bool(set(label_names) & _CARDINALITY_RISK_LABEL_NAMES)
    )
    contract_bounded_risky_labels = (
        set(declared_risky_label_candidates) & declared_label_contract_metrics
    )
    reviewed_risky_labels = drift_allowlist.get(
        "declared_risky_label_review_required",
        set(),
    )
    declared_risky_label_reviewed = sorted(
        (set(declared_risky_label_candidates) & reviewed_risky_labels)
        | contract_bounded_risky_labels
    )
    declared_risky_label_review_required = [
        metric_name
        for metric_name in declared_risky_label_candidates
        if metric_name not in reviewed_risky_labels
        and metric_name not in contract_bounded_risky_labels
    ]

    report: dict[str, list[str] | dict[str, list[str]]] = {
        "declared_metrics": registered,
        "emitted_metrics": sorted(registered_set & runtime_set),
        "declared_observability_events": declared_observability_events,
        "emitted_observability_events": emitted_observability_events,
        "unused_declared_observability_events": (
            unused_declared_observability_events
        ),
        "retired_declared_observability_events": (
            retired_declared_observability_events
        ),
        "retired_declared_observability_events_emitted": (
            retired_declared_observability_events_emitted
        ),
        "emitted_observability_events_without_contract": (
            emitted_observability_events_without_contract
        ),
        "dashboarded_metrics": sorted(docs_set & registered_set),
        "alerted_metrics": sorted(rules_set & registered_set),
        "unused_declared_metrics": sorted(registry_only_metrics),
        "emitted_without_declaration": sorted(runtime_without_registry),
        "dashboarded_without_declaration": sorted(docs_set - registered_set),
        "alerted_without_declaration": sorted(rules_set - registered_set),
        "dashboarded_without_emission": sorted(documented_without_runtime),
        "alerted_without_emission": sorted(ruled_without_runtime),
        "runtime_cardinality_review_candidates": runtime_cardinality_candidates,
        "runtime_cardinality_reviewed": runtime_cardinality_reviewed,
        "runtime_cardinality_review_required": runtime_cardinality_review_required,
        "runtime_cardinality_evidence": runtime_cardinality_evidence,
        "runtime_cardinality_observed_series": {
            metric_name: [f"observed_series_count={count}"]
            for metric_name, count in sorted(observed_series_counts.items())
        },
        "runtime_cardinality_threshold_violations": (
            runtime_cardinality_threshold_violations
        ),
        "declared_risky_label_review_candidates": declared_risky_label_candidates,
        "declared_risky_label_contract_reviewed": sorted(
            contract_bounded_risky_labels
        ),
        "declared_risky_label_reviewed": declared_risky_label_reviewed,
        "declared_risky_label_review_required": (declared_risky_label_review_required),
        "declared_label_contract_metrics": sorted(declared_label_contract_metrics),
        "runtime_label_contract_violations": label_contract_violations,
        "runtime_label_contract_unresolved": label_contract_unresolved,
        "registered_metrics": registered,
        "live_metrics": sorted(registered_set & runtime_set),
        "direct_live_metrics": sorted(registered_set & direct_runtime_set),
        "helper_backed_live_metrics": sorted(registered_set & helper_runtime_set),
        "registered_without_runtime": sorted(registry_only_metrics),
        "runtime_without_registry": sorted(runtime_without_registry),
        "registry_only_metrics": sorted(registry_only_metrics),
        "dead_metrics": sorted(dead_metrics),
        "documented_without_registry": sorted(docs_set - registered_set),
        "rules_without_registry": sorted(rules_set - registered_set),
        "documented_without_runtime": sorted(documented_without_runtime),
        "documented_only_metrics": sorted(documented_without_runtime),
        "ruled_without_runtime": sorted(ruled_without_runtime),
        "compatibility_alias_candidates": sorted(alias_mentions),
        "runtime_emitters": runtime_mentions,
        "helper_backed_emitters": helper_backed_mentions,
        "observability_event_emitters": observability_event_emitters,
        "domain_event_emitters": domain_event_emitters,
        "canonical_runtime_observability_emitters": sorted(
            runtime_observability_contract.canonical_emitters
        ),
        "docs_mentions": docs_mentions,
        "rules_mentions": rules_mentions,
        "alias_emitters": alias_mentions,
    }
    _METRIC_INVENTORY_CACHE[cache_key] = report
    return report


def _combine_metric_emitters(
    runtime_emitters: dict[str, list[str]],
    helper_backed_emitters: dict[str, list[str]],
) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = defaultdict(list)
    for source in (runtime_emitters, helper_backed_emitters):
        for metric_name, emitter_paths in source.items():
            combined[metric_name].extend(emitter_paths)
    return dict(combined)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when metric registry/runtime/docs drift exceeds the allowlist",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=_DEFAULT_DRIFT_ALLOWLIST,
        help="YAML file with allowed drift entries for --check",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to scan",
    )
    parser.add_argument(
        "--write-evidence",
        type=Path,
        help="Write collected inventory JSON to a replayable evidence artifact path",
    )
    parser.add_argument(
        "--review-json-out",
        type=Path,
        help="Write runtime cardinality live-review summary JSON to this path",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        help="Append a markdown runtime cardinality review summary to this path",
    )
    parser.add_argument(
        "--prometheus-base-url",
        help=(
            "Prometheus HTTP API base URL for live runtime-cardinality review. "
            f"Defaults to ${_PROMETHEUS_BASE_URL_ENV_VAR} when unset."
        ),
    )
    parser.add_argument(
        "--fail-on-degraded-live-review",
        action="store_true",
        help=(
            "Fail when the runtime-cardinality live review is degraded. "
            "Release gates should enable this so missing Prometheus evidence "
            "does not silently pass."
        ),
    )
    parser.add_argument(
        "--allow-local-cardinality-fallback",
        action="store_true",
        help=(
            "Allow PR/local gates to satisfy runtime-cardinality review from "
            "deterministic repo-local observed-series evidence when Prometheus is "
            "unconfigured. Release gates should keep using "
            "--fail-on-degraded-live-review without this flag."
        ),
    )
    return parser


def _parse_allowlist_metric_name(
    key: str, item: object
) -> str | None:  # pragma: no cover - exercised through _load_drift_allowlist
    if isinstance(item, str):
        if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
            raise ValueError(
                f"{key} entries must be mappings with metric/owner/reason/review_date"
            )
        return item
    if not isinstance(item, dict):
        raise ValueError(f"{key} entries must be strings or mappings")

    metric_name = item.get("metric")
    if not isinstance(metric_name, str) or not metric_name:
        raise ValueError(f"{key} mapping entries must declare a non-empty metric")

    if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
        for field_name in ("owner", "reason", "review_date"):
            field_value = item.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(
                    f"{key} metric {metric_name!r} is missing required {field_name}"
                )
        _validate_allowlist_review_date(
            key=key,
            metric_name=metric_name,
            raw_review_date=str(item["review_date"]),
        )
    return metric_name


def _validate_allowlist_review_date(
    *,
    key: str,
    metric_name: str,
    raw_review_date: str,
) -> None:
    try:
        review_date = date.fromisoformat(raw_review_date)
    except ValueError as exc:
        raise ValueError(
            f"{key} metric {metric_name!r} has invalid review_date "
            f"{raw_review_date!r}; expected ISO YYYY-MM-DD"
        ) from exc
    if review_date < date.today():
        raise ValueError(
            f"{key} metric {metric_name!r} has expired review_date "
            f"{raw_review_date}; refresh or remove this lifecycle exception"
        )


def _load_drift_allowlist(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    raw_allowed = payload.get("allowed", payload)
    if not isinstance(raw_allowed, dict):
        return {}
    allowlist: dict[str, set[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = raw_allowed.get(key, [])
        if not isinstance(values, list):
            continue
        allowlist[key] = {
            metric_name
            for metric_name in (
                _parse_allowlist_metric_name(key, value) for value in values
            )
            if metric_name
        }
    return allowlist


def validate_metric_inventory(
    report: dict[str, list[str] | dict[str, list[str]]],
    *,
    allowlist: dict[str, set[str]] | None = None,
) -> dict[str, list[str]]:
    """Return unallowed metric drift grouped by deterministic check category."""
    allowed = allowlist or {}
    violations: dict[str, list[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = report.get(key, [])
        if not isinstance(values, list):
            continue
        allowed_values = allowed.get(key, set())
        unallowed = sorted(
            {
                value
                for value in values
                if _drift_allowlist_token(key, value) not in allowed_values
            }
        )
        if unallowed:
            violations[key] = unallowed
    return violations


def _drift_allowlist_token(key: str, value: str) -> str:
    """Normalize drift rows for allowlist comparison."""
    if key == "runtime_label_contract_unresolved":
        return value.split(" @ ", 1)[0]
    return value


def _render_text(report: dict[str, list[str] | dict[str, list[str]]]) -> str:
    lines = ["Observability metric inventory"]
    for key in (
        "declared_metrics",
        "emitted_metrics",
        "declared_observability_events",
        "emitted_observability_events",
        "unused_declared_observability_events",
        "retired_declared_observability_events",
        "retired_declared_observability_events_emitted",
        "emitted_observability_events_without_contract",
        "dashboarded_metrics",
        "alerted_metrics",
        "unused_declared_metrics",
        "emitted_without_declaration",
        "dashboarded_without_declaration",
        "alerted_without_declaration",
        "dashboarded_without_emission",
        "alerted_without_emission",
        "runtime_cardinality_review_candidates",
        "runtime_cardinality_reviewed",
        "runtime_cardinality_review_required",
        "declared_risky_label_review_candidates",
        "declared_risky_label_reviewed",
        "declared_risky_label_review_required",
        "runtime_label_contract_violations",
        "runtime_label_contract_unresolved",
        "runtime_cardinality_threshold_violations",
        "live_metrics",
        "direct_live_metrics",
        "helper_backed_live_metrics",
        "registered_without_runtime",
        "runtime_without_registry",
        "dead_metrics",
        "documented_without_registry",
        "rules_without_registry",
        "documented_without_runtime",
        "ruled_without_runtime",
        "compatibility_alias_candidates",
    ):
        values = report.get(key, [])
        assert isinstance(values, list)
        lines.append(f"\n{key} ({len(values)}):")
        if not values:
            lines.append("  - <none>")
            continue
        lines.extend(f"  - {value}" for value in values)
    return "\n".join(lines)


MetricInventoryReport = dict[str, list[str] | dict[str, list[str]]]


def _write_evidence_report(
    report: MetricInventoryReport, *, repo_root: Path, evidence_path: Path | None
) -> None:
    if evidence_path is None:
        return
    resolved_path = (
        evidence_path if evidence_path.is_absolute() else repo_root / evidence_path
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolved_allowlist_path(repo_root: Path, allowlist_path: Path) -> Path:
    return (
        allowlist_path if allowlist_path.is_absolute() else repo_root / allowlist_path
    )


def _metric_inventory_violations(
    report: MetricInventoryReport, *, args: argparse.Namespace
) -> dict[str, list[str]]:
    if not args.check:
        return {}
    return validate_metric_inventory(
        report,
        allowlist=_load_drift_allowlist(
            _resolved_allowlist_path(args.repo_root, args.allowlist)
        ),
    )


def _emit_json_report(
    report: MetricInventoryReport, *, violations: dict[str, list[str]]
) -> int:
    if violations:
        report["check_violations"] = violations
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if violations else 0


def _emit_text_report(
    report: MetricInventoryReport, *, violations: dict[str, list[str]]
) -> int:
    print(_render_text(report))
    if not violations:
        return 0
    print("\nMetric inventory drift check failed:", file=sys.stderr)
    for key, values in violations.items():
        print(f"{key} ({len(values)}):", file=sys.stderr)
        for value in values:
            print(f"  - {value}", file=sys.stderr)
    return 1


def _write_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
    *,
    repo_root: Path,
    output_path: Path | None,
) -> None:
    if output_path is None:
        return
    resolved_path = (
        output_path if output_path.is_absolute() else repo_root / output_path
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
) -> str:
    lines = [
        "## Observability Runtime Cardinality Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Mode: `{summary['mode']}`",
        f"- Prometheus source: `{summary['prometheus_base_url_source']}`",
        f"- Reviewed metrics: `{len(summary['reviewed_metrics'])}`",
        f"- Review-required metrics: `{len(summary['review_required_metrics'])}`",
    ]

    degraded_reasons = summary.get("degraded_reasons", [])
    if isinstance(degraded_reasons, list) and degraded_reasons:
        lines.append("- Degraded reasons:")
        lines.extend(f"  - `{reason}`" for reason in degraded_reasons)

    live_threshold_violations = summary.get("live_threshold_violations", [])
    if isinstance(live_threshold_violations, list) and live_threshold_violations:
        lines.append("- Live threshold violations:")
        lines.extend(f"  - `{row}`" for row in live_threshold_violations)

    query_errors = summary.get("query_errors", {})
    if isinstance(query_errors, dict) and query_errors:
        lines.append("- Query errors:")
        lines.extend(
            f"  - `{metric_name}`: `{message}`"
            for metric_name, message in sorted(query_errors.items())
        )
    return "\n".join(lines) + "\n"


def _append_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
    *,
    repo_root: Path,
    summary_out: Path | None,
) -> None:
    if summary_out is None:
        return
    resolved_path = (
        summary_out if summary_out.is_absolute() else repo_root / summary_out
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if resolved_path.exists() and resolved_path.stat().st_size > 0:
        prefix = "\n"
    with resolved_path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + _render_runtime_cardinality_review_summary(summary))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = collect_metric_inventory(args.repo_root)
    _write_evidence_report(
        report,
        repo_root=args.repo_root,
        evidence_path=args.write_evidence,
    )
    review_summary = _build_runtime_cardinality_review_summary(
        report,
        repo_root=args.repo_root,
        prometheus_base_url=args.prometheus_base_url,
        allow_local_cardinality_fallback=args.allow_local_cardinality_fallback,
    )
    _write_runtime_cardinality_review_summary(
        review_summary,
        repo_root=args.repo_root,
        output_path=args.review_json_out,
    )
    _append_runtime_cardinality_review_summary(
        review_summary,
        repo_root=args.repo_root,
        summary_out=args.summary_out,
    )
    violations = _metric_inventory_violations(report, args=args)
    live_review_failed = review_summary["status"] == "failed"
    live_review_degraded = (
        args.fail_on_degraded_live_review and review_summary["status"] == "degraded"
    )
    if args.json:
        exit_code = _emit_json_report(report, violations=violations)
    else:
        exit_code = _emit_text_report(report, violations=violations)
    if live_review_failed or live_review_degraded:
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
