"""Architecture tests: Infrastructure adapter contracts.

These tests verify that infrastructure adapters:
- Implement required port methods (health_check, etc.)
- Follow proper Protocol patterns
- Use atomic write patterns for storage

REQ-OBS-001: Adapters must provide health check for monitoring.
REQ-ARCH-025: Filterable adapters must implement FilterableDataSourcePort.
REQ-DATA-004: All file writes should be atomic.

See CLAUDE.md §7 Technology Stack and §14 Creating Components.
"""

from __future__ import annotations

import ast
import inspect
import re
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.ports import FilterableDataSourcePort

ADAPTER_MIXIN_CANONICAL_FILES = frozenset(
    {
        "chembl/fetch_adapter_mixin.py",
        "openalex/client_helpers_adapter_mixin.py",
        "uniprot/metadata_adapter_mixin.py",
    }
)

REMOVED_ADAPTER_MIXIN_SHIMS = frozenset(
    {
        "chembl/fetch_mixin.py",
        "openalex/client_helpers_mixin.py",
        "uniprot/metadata_mixin.py",
    }
)

REMOVED_SHIM_IMPORT_PATHS = frozenset(
    {
        "bioetl.infrastructure.adapters.chembl.fetch_mixin",
        "bioetl.infrastructure.adapters.openalex.client_helpers_mixin",
        "bioetl.infrastructure.adapters.uniprot.metadata_mixin",
    }
)

LEGACY_SHIM_SYMBOLS = frozenset(
    {
        "ChemblFetchMixin",
        "_OpenAlexAdapterHelpersMixin",
        "_UniProtAdapterMetadataMixin",
    }
)


def _rel_adapter_path(adapters_path: Path, py_file: Path) -> str:
    """Return adapter path normalized to POSIX separators."""
    return py_file.relative_to(adapters_path).as_posix()


def _adapter_entrypoint_files(adapters_path: Path) -> list[Path]:
    excluded_files = {
        "base.py",
        "sync_base.py",
        "health_check_mixin.py",
        "base_metrics.py",
        "types.py",
        "exceptions.py",
        "client.py",
        "pagination.py",
        "rate_limiter.py",
        "circuit_breaker.py",
        "health.py",
        "health_monitor.py",
        "error_handling.py",
        "fallback.py",
        "base_title_fallback.py",
    }
    adapter_files: list[Path] = []
    for py_file in adapters_path.rglob("*.py"):
        rel_path = _rel_adapter_path(adapters_path, py_file)
        if py_file.name.startswith("_"):
            continue
        if py_file.name in excluded_files:
            continue
        if rel_path in ADAPTER_MIXIN_CANONICAL_FILES:
            continue
        if py_file.name.endswith("_mixin.py") or py_file.name.endswith("_helpers.py"):
            continue
        adapter_files.append(py_file)
    return adapter_files


def _has_health_check_contract(content: str) -> bool:
    has_method = "def health_check" in content or "async def health_check" in content
    inherits_base = re.search(
        r"class\s+\w+\s*\([^)]*Base(Http|Sync)Adapter",
        content,
        re.MULTILINE | re.DOTALL,
    )
    has_mixin = "HealthCheckProviderMixin" in content
    return bool(has_method or inherits_base or has_mixin)


def _iter_cached_modules(
    ast_caches: tuple[dict[Path, ast.Module], ...],
) -> list[tuple[Path, ast.Module]]:
    modules: list[tuple[Path, ast.Module]] = []
    for ast_cache in ast_caches:
        modules.extend(sorted(ast_cache.items()))
    return modules


def _legacy_import_from_violation(
    rel_path: str,
    node: ast.ImportFrom,
) -> str | None:
    if node.module not in REMOVED_SHIM_IMPORT_PATHS:
        return None
    return f"{rel_path}:{node.lineno} imports removed module '{node.module}'"


def _legacy_import_violations(
    rel_path: str,
    node: ast.Import,
) -> list[str]:
    return [
        f"{rel_path}:{node.lineno} imports removed module '{alias.name}'"
        for alias in node.names
        if alias.name in REMOVED_SHIM_IMPORT_PATHS
    ]


def _legacy_module_violations_for_tree(rel_path: str, tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            violation = _legacy_import_from_violation(rel_path, node)
            if violation is not None:
                violations.append(violation)
            continue
        if isinstance(node, ast.Import):
            violations.extend(_legacy_import_violations(rel_path, node))
    return violations


def _legacy_module_import_violations(
    root: Path,
    ast_caches: tuple[dict[Path, ast.Module], ...],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in _iter_cached_modules(ast_caches):
        rel_path = py_file.relative_to(root).as_posix()
        violations.extend(_legacy_module_violations_for_tree(rel_path, tree))
    return violations


def _expected_root_import_name(
    node: ast.ImportFrom,
    disallowed_modules: dict[str, str],
) -> str | None:
    if node.module is None:
        return None
    expected_name = disallowed_modules.get(node.module)
    if expected_name is None:
        return None
    if not any(alias.name == expected_name for alias in node.names):
        return None
    return expected_name


def _package_root_violation(
    root: Path,
    py_file: Path,
    node: ast.ImportFrom,
    expected_name: str,
) -> str:
    return (
        f"{py_file.relative_to(root)}:{node.lineno} imports "
        f"{expected_name} from {node.module}; use the provider "
        "package root instead"
    )


def _package_root_violations_for_tree(
    root: Path,
    py_file: Path,
    tree: ast.Module,
    disallowed_modules: dict[str, str],
) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        expected_name = _expected_root_import_name(node, disallowed_modules)
        if expected_name is None:
            continue
        violations.append(_package_root_violation(root, py_file, node, expected_name))
    return violations


def _package_root_import_violations(
    root: Path,
    allowed_files: set[Path],
    disallowed_modules: dict[str, str],
    ast_caches: tuple[dict[Path, ast.Module], ...],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in _iter_cached_modules(ast_caches):
        if py_file in allowed_files:
            continue
        violations.extend(
            _package_root_violations_for_tree(root, py_file, tree, disallowed_modules)
        )
    return violations


class TestAdapterHealthCheck:
    """Tests ensuring adapters have proper health check methods."""

    def test_adapters_have_health_check(self, src_dir: Path) -> None:
        """All adapters MUST implement health_check() method.

        REQ-OBS-001: Adapters must provide health check for provider monitoring.
        See docs/05-operations/runbooks/observability-checklist.md.
        """
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        missing_health_check = []
        for py_file in _adapter_entrypoint_files(adapters_path):
            content = py_file.read_text(encoding="utf-8")
            adapter_like_class = re.search(
                r"class\s+\w{0,128}(?:Adapter|Client|Fetcher)\w{0,128}\s*\(",
                content,
                re.MULTILINE,
            )
            if adapter_like_class is None:
                continue
            if not _has_health_check_contract(content):
                relative_path = py_file.relative_to(src_dir)
                missing_health_check.append(str(relative_path))

        assert not missing_health_check, (
            "Adapters must implement health_check() method (REQ-OBS-001).\n"
            "Files missing health_check:\n"
            + "\n".join(f"  - {f}" for f in missing_health_check)
            + "\n\nSee: docs/05-operations/runbooks/observability-checklist.md"
        )


class TestAdapterMixinPolicy:
    """Tests ensuring explicit adapter mixin naming and shim contract."""

    def test_adapter_mixins_use_canonical_naming(self, src_dir: Path) -> None:
        """Adapter mixins must live in explicit *_adapter_mixin.py modules."""
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        missing = [
            rel
            for rel in sorted(ADAPTER_MIXIN_CANONICAL_FILES)
            if not (adapters_path / rel).exists()
        ]

        assert not missing, "Missing canonical adapter mixin modules:\n" + "\n".join(
            f"  - {m}" for m in missing
        )

    def test_adapter_mixins_do_not_implement_health_check(self, src_dir: Path) -> None:
        """Adapter mixins should not duplicate HealthCheckProviderMixin logic."""
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        violations: list[str] = []
        for rel in sorted(ADAPTER_MIXIN_CANONICAL_FILES):
            file_path = adapters_path / rel
            content = file_path.read_text(encoding="utf-8")
            if "def health_check" in content or "async def health_check" in content:
                violations.append(rel)

        assert not violations, (
            "Adapter mixins must not implement health_check() directly. "
            "Use BaseHttpAdapter/BaseSyncAdapter with HealthCheckProviderMixin.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_removed_legacy_mixin_shims_are_absent(self, src_dir: Path) -> None:
        """Removed legacy mixin shim modules must stay deleted."""
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        lingering = [
            rel
            for rel in sorted(REMOVED_ADAPTER_MIXIN_SHIMS)
            if (adapters_path / rel).exists()
        ]

        assert not lingering, (
            "Removed legacy adapter-mixin shims must stay deleted.\n"
            + "\n".join(f"  - {rel}" for rel in lingering)
        )

    def test_src_does_not_import_legacy_adapter_mixin_modules(
        self,
        src_dir: Path,
        source_ast_cache: dict[Path, ast.Module],
        test_ast_cache: dict[Path, ast.Module],
    ) -> None:
        """Removed legacy adapter-mixin module paths must stay absent everywhere."""
        violations: list[str] = []
        root = src_dir.parent
        violations = _legacy_module_import_violations(
            root,
            (source_ast_cache, test_ast_cache),
        )

        assert not violations, (
            "Removed legacy adapter-mixin module imports are forbidden.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_src_does_not_use_legacy_adapter_mixin_symbols(
        self,
        src_dir: Path,
        source_content_cache: dict[Path, str],
    ) -> None:
        """Production source must not reference legacy shim symbol names."""
        violations: list[str] = []
        for py_file, content in sorted(source_content_cache.items()):
            rel_path = py_file.relative_to(src_dir).as_posix()
            for symbol in LEGACY_SHIM_SYMBOLS:
                if re.search(rf"\b{re.escape(symbol)}\b", content):
                    violations.append(
                        f"{rel_path}: references legacy symbol '{symbol}'"
                    )

        assert not violations, (
            "Legacy adapter-mixin symbols are forbidden in src.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestAdapterPortCompliance:
    """Tests ensuring adapters properly implement domain ports."""

    def test_infrastructure_imports_domain_ports(self, src_dir: Path) -> None:
        """Infrastructure adapters should import from domain layer.

        REQ-ARCH-006: Infrastructure implementations should implement domain ports.
        """
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        found_domain_import = False
        for py_file in adapters_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            with py_file.open(encoding="utf-8") as f:
                content = f.read()
            if "bioetl.domain" in content:
                found_domain_import = True
                break

        assert found_domain_import, (
            "Infrastructure adapters should import from domain layer "
            "(e.g., to implement ports)"
        )

    def test_filterable_adapters_implement_protocol(self, src_dir: Path) -> None:
        """Adapters with fetch_filtered MUST implement FilterableDataSourcePort.

        REQ-ARCH-025: Replace duck-typing with explicit Protocol for adapters
        that support filtering at API level. This ensures type safety and
        enables isinstance() checks instead of hasattr().
        """
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        violations = []

        for py_file in adapters_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # Check if file defines fetch_filtered method
            has_fetch_filtered = (
                "def fetch_filtered" in content or "async def fetch_filtered" in content
            )

            if has_fetch_filtered:
                # Should reference FilterableDataSourcePort in docstring
                has_protocol_ref = "FilterableDataSourcePort" in content

                if not has_protocol_ref:
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(
                        f"{relative_path}: defines fetch_filtered but doesn't "
                        "reference FilterableDataSourcePort"
                    )

        assert not violations, (
            "Adapters with fetch_filtered must implement FilterableDataSourcePort.\n"
            "Update class/method docstrings to reference the Protocol:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    @pytest.mark.parametrize(
        ("module_path", "class_name"),
        [
            (
                "bioetl.infrastructure.adapters.chembl.client",
                "ChemblAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.crossref.client",
                "CrossRefAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.openalex.client",
                "OpenAlexAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.pubmed.client",
                "PubMedAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.pubchem.client",
                "PubChemAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.semanticscholar.client",
                "SemanticScholarAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.uniprot.client",
                "UniProtAdapter",
            ),
        ],
    )
    def test_filterable_adapters_runtime_isinstance_protocol(
        self,
        module_path: str,
        class_name: str,
    ) -> None:
        """Filterable adapters MUST satisfy runtime isinstance() Protocol checks."""
        adapter_cls = getattr(import_module(module_path), class_name)
        init_kwargs, thread_pool = _build_runtime_init_kwargs(adapter_cls)
        adapter = adapter_cls(**init_kwargs)
        try:
            assert isinstance(adapter, FilterableDataSourcePort), (
                f"{module_path}.{class_name} must satisfy "
                "runtime FilterableDataSourcePort contract"
            )
        finally:
            if thread_pool is not None:
                thread_pool.shutdown(wait=False)

    def test_filtered_data_source_uses_isinstance(self, src_dir: Path) -> None:
        """FilteredDataSource MUST use isinstance() for Protocol check.

        REQ-ARCH-026: Replace hasattr() duck-typing with isinstance() check
        for FilterableDataSourcePort. This enables proper type checking and
        IDE support.
        """
        filtered_source = (
            src_dir / "bioetl" / "application" / "core" / "filtered_data_source.py"
        )
        if not filtered_source.exists():
            pytest.skip("FilteredDataSource not found")

        content = filtered_source.read_text(encoding="utf-8")

        # Should NOT use hasattr for fetch_filtered
        uses_hasattr = "hasattr" in content and "fetch_filtered" in content
        assert not uses_hasattr, (
            "FilteredDataSource should not use hasattr() for fetch_filtered check. "
            "Use isinstance(adapter, FilterableDataSourcePort) instead."
        )

        # Should use isinstance with FilterableDataSourcePort
        uses_isinstance = (
            "isinstance" in content and "FilterableDataSourcePort" in content
        )
        assert uses_isinstance, (
            "FilteredDataSource must use isinstance(adapter, FilterableDataSourcePort) "
            "for type-safe Protocol check."
        )

    def test_primary_adapter_classes_use_package_root_imports(
        self,
        src_dir: Path,
        source_ast_cache: dict[Path, ast.Module],
        test_ast_cache: dict[Path, ast.Module],
    ) -> None:
        """Primary adapter classes should be imported from provider package roots."""
        disallowed_modules = {
            "bioetl.infrastructure.adapters.chembl.client": "ChemblAdapter",
            "bioetl.infrastructure.adapters.crossref.client": "CrossRefAdapter",
            "bioetl.infrastructure.adapters.openalex.client": "OpenAlexAdapter",
            "bioetl.infrastructure.adapters.pubchem.client": "PubChemAdapter",
            "bioetl.infrastructure.adapters.pubmed.client": "PubMedAdapter",
            "bioetl.infrastructure.adapters.pubmed.pubmed_client": "PubMedAdapter",
            "bioetl.infrastructure.adapters.semanticscholar.client": "SemanticScholarAdapter",
            "bioetl.infrastructure.adapters.semanticscholar.adapter": "SemanticScholarAdapter",
            "bioetl.infrastructure.adapters.uniprot.client": "UniProtAdapter",
        }
        allowed_files = {
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "chembl"
            / "__init__.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "crossref"
            / "__init__.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "openalex"
            / "__init__.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "pubchem"
            / "__init__.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "pubmed"
            / "__init__.py",
            src_dir / "bioetl" / "infrastructure" / "adapters" / "pubmed" / "client.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "semanticscholar"
            / "__init__.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "semanticscholar"
            / "client.py",
            src_dir
            / "bioetl"
            / "infrastructure"
            / "adapters"
            / "uniprot"
            / "__init__.py",
            src_dir.parent
            / "tests"
            / "unit"
            / "infrastructure"
            / "adapters"
            / "crossref"
            / "test_compatibility.py",
        }

        violations = _package_root_import_violations(
            src_dir.parent,
            allowed_files,
            disallowed_modules,
            (source_ast_cache, test_ast_cache),
        )

        assert not violations, (
            "Primary adapter classes must be imported from package-root facades.\n"
            + "\n".join(f"  - {item}" for item in violations)
        )


def _build_runtime_init_kwargs(
    adapter_cls: type,
) -> tuple[dict[str, object], ThreadPoolExecutor | None]:
    """Create minimal constructor kwargs for runtime Protocol checks."""
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import (
        PubChemEntityMapper,
    )

    signature = inspect.signature(adapter_cls)
    kwargs: dict[str, object] = {}
    thread_pool: ThreadPoolExecutor | None = None
    http_client = _create_http_client_mock()
    logger = MagicMock()
    rate_limiter = MagicMock()
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.return_value = "closed"
    circuit_breaker.get_failure_count.return_value = 0
    error_handler = MagicMock()

    value_by_name: dict[str, object] = {
        "http_client": http_client,
        "logger": logger,
        "mailto": "bioetl-tests@example.org",
        "email": "bioetl-tests@example.org",
        "rate_limiter": rate_limiter,
        "circuit_breaker": circuit_breaker,
        "error_handler": error_handler,
        "request_collector": APIRequestCollector(),
        "entity_mapper": PubChemEntityMapper(),
        "fetch_strategies": MagicMock(),
        "fallback_fetch_service": MagicMock(),
        "query_builder": MagicMock(),
        "response_mapper": MagicMock(),
        "batch_fetcher": MagicMock(),
        "search_paginator": MagicMock(),
        "title_fallback_handler": MagicMock(),
    }

    for parameter in signature.parameters.values():
        if parameter.name == "self":
            continue
        if parameter.default is not inspect._empty:
            continue

        if parameter.name == "thread_pool":
            thread_pool = ThreadPoolExecutor(max_workers=1)
            kwargs["thread_pool"] = thread_pool
            continue

        value = value_by_name.get(parameter.name)
        if value is None:
            raise AssertionError(
                "Unhandled required constructor parameter for runtime protocol test: "
                f"{adapter_cls.__module__}.{adapter_cls.__name__}.{parameter.name}"
            )
        kwargs[parameter.name] = value

    if (
        adapter_cls.__module__ == "bioetl.infrastructure.adapters.crossref.client"
        and adapter_cls.__name__ == "CrossRefAdapter"
    ):
        for name in (
            "query_builder",
            "response_mapper",
            "batch_fetcher",
            "search_paginator",
            "title_fallback_handler",
        ):
            kwargs.setdefault(name, value_by_name[name])

    return kwargs, thread_pool


def _create_http_client_mock() -> AsyncMock:
    """Create minimal HTTP client mock satisfying adapter constructor contracts."""
    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    http_client.circuit_breaker = MagicMock()
    http_client.circuit_breaker.get_state.return_value = "closed"
    http_client.circuit_breaker.get_failure_count.return_value = 0
    return http_client


class TestStorageWriterContracts:
    """Tests ensuring storage writers follow proper patterns."""

    def test_atomic_write_used_in_writers(self, src_dir: Path) -> None:
        """Verify that storage writers use atomic write patterns.

        REQ-DATA-004: All file writes should be atomic to prevent data corruption.

        Note: Delta Lake writers (silver_writer.py, gold_writer.py) get atomicity
        from Delta Lake's transaction log, not temp file + rename. Only bronze_writer
        needs explicit atomic patterns since it writes JSONL files directly.
        """
        storage_path = src_dir / "bioetl" / "infrastructure" / "storage"
        if not storage_path.exists():
            pytest.skip("Storage layer not found")

        # Writers that should use explicit atomic patterns (non-Delta file writers)
        # Delta writers (silver, gold) get atomicity from Delta Lake's transaction log
        writer_files = ["bronze_writer.py"]

        # Patterns indicating atomic writes (should be present)
        atomic_indicators = [
            r"atomic_write",
            r"AtomicWriteGroup",
            r"tempfile\.mkstemp",
        ]

        findings = []

        for writer_file in writer_files:
            file_path = storage_path / writer_file
            if not file_path.exists():
                continue

            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            # Check for atomic indicators
            has_atomic = any(re.search(p, content) for p in atomic_indicators)

            if not has_atomic:
                findings.append(f"{writer_file} - No atomic write patterns detected")

        assert not findings, (
            "Storage writers should use atomic write patterns (temp file + rename).\n"
            "Files missing atomic patterns:\n" + "\n".join(f"  - {f}" for f in findings)
        )
