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

ADAPTER_MIXIN_LEGACY_SHIMS: dict[str, str] = {
    "chembl/fetch_mixin.py": "fetch_adapter_mixin",
    "openalex/client_helpers_mixin.py": "client_helpers_adapter_mixin",
    "uniprot/metadata_mixin.py": "metadata_adapter_mixin",
}

LEGACY_SHIM_IMPORT_PATHS = frozenset(
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

        # Files that define adapter classes (not __init__.py or base classes)
        # Exclude HTTP infrastructure utilities that are not DataSourcePort adapters
        excluded_files = {
            "base.py",  # BaseHttpAdapter - base class providing health_check
            "sync_base.py",  # BaseSyncAdapter - base class providing health_check
            "health_check_mixin.py",  # HealthCheckProviderMixin - provides health_check
            "base_metrics.py",  # Base class for metrics adapters
            "types.py",
            "exceptions.py",
            "client.py",  # HTTP client utility, not a DataSourcePort adapter
            "pagination.py",  # Pagination mixin, not a DataSourcePort adapter
            "rate_limiter.py",  # Rate limiting utility
            "circuit_breaker.py",  # Circuit breaker utility
            "health.py",  # Health check mixin, not a DataSourcePort adapter
            "health_monitor.py",  # Health state utility, not a DataSourcePort adapter
            "error_handling.py",  # Error handling utility, not a DataSourcePort adapter
            "fallback.py",  # Title fallback handler utility, not a DataSourcePort adapter
            "base_title_fallback.py",  # Base class for title fallback handlers
        }
        adapter_files = []
        for py_file in adapters_path.rglob("*.py"):
            rel_path = _rel_adapter_path(adapters_path, py_file)
            if py_file.name.startswith("_"):
                continue
            if py_file.name in excluded_files:
                continue
            if rel_path in ADAPTER_MIXIN_CANONICAL_FILES:
                # Adapter mixins are behavioral fragments, not entrypoints.
                continue
            if rel_path in ADAPTER_MIXIN_LEGACY_SHIMS:
                # Legacy shim modules are compatibility re-exports only.
                continue
            if py_file.name.endswith("_mixin.py"):
                # Mixins are behavioral fragments, not full DataSourcePort adapters.
                continue
            if py_file.name.endswith("_helpers.py"):
                # Helper modules are not adapter entrypoints.
                continue
            adapter_files.append(py_file)

        missing_health_check = []

        for py_file in adapter_files:
            content = py_file.read_text(encoding="utf-8")

            # Only scan files that define adapter-like classes.
            adapter_like_class = re.search(
                r"class\s+\w*(Adapter|Client|Fetcher)\w*\s*\(",
                content,
                re.MULTILINE,
            )
            if adapter_like_class is None:
                continue

            # Check for health_check method definition OR inheritance from base adapters
            # BaseHttpAdapter and BaseSyncAdapter provide health_check()
            # via HealthCheckProviderMixin (Template Method pattern).
            # We use regex to handle multi-line inheritance lists.
            has_method = (
                "def health_check" in content or "async def health_check" in content
            )
            inherits_base = re.search(
                r"class\s+\w+\s*\([^)]*Base(Http|Sync)Adapter",
                content,
                re.MULTILINE | re.DOTALL,
            )
            has_mixin = "HealthCheckProviderMixin" in content

            has_health_check = has_method or inherits_base or has_mixin

            if not has_health_check:
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

    def test_legacy_mixin_shims_are_reexport_only(self, src_dir: Path) -> None:
        """Legacy mixin modules must remain thin compatibility shims."""
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        violations: list[str] = []
        for rel, expected_import in ADAPTER_MIXIN_LEGACY_SHIMS.items():
            file_path = adapters_path / rel
            if not file_path.exists():
                violations.append(f"{rel}: missing legacy shim")
                continue

            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            has_runtime_defs = any(
                isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                for node in tree.body
            )
            if has_runtime_defs:
                violations.append(
                    f"{rel}: must not define classes/functions (re-export only)"
                )

            if expected_import not in content:
                violations.append(
                    f"{rel}: must import canonical module '{expected_import}'"
                )

        assert not violations, "Legacy adapter-mixin shim violations:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_src_does_not_import_legacy_adapter_mixin_modules(
        self, src_dir: Path
    ) -> None:
        """Production source must import canonical *_adapter_mixin modules only."""
        src_root = src_dir / "bioetl"
        if not src_root.exists():
            pytest.skip("bioetl source not found")

        violations: list[str] = []
        for py_file in src_root.rglob("*.py"):
            rel_path = py_file.relative_to(src_dir).as_posix()
            if rel_path.endswith("/__init__.py"):
                continue
            if rel_path.startswith(
                "bioetl/infrastructure/adapters/"
            ) and rel_path.split("bioetl/infrastructure/adapters/", 1)[1] in {
                *ADAPTER_MIXIN_LEGACY_SHIMS.keys()
            }:
                # Skip legacy shim modules themselves.
                continue

            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=rel_path)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module in LEGACY_SHIM_IMPORT_PATHS
                ):
                    violations.append(
                        f"{rel_path}:{node.lineno} imports legacy module '{node.module}'"
                    )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in LEGACY_SHIM_IMPORT_PATHS:
                            violations.append(
                                f"{rel_path}:{node.lineno} imports legacy module '{alias.name}'"
                            )

        assert not violations, (
            "Legacy adapter-mixin module imports are forbidden in src.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_src_does_not_use_legacy_adapter_mixin_symbols(self, src_dir: Path) -> None:
        """Production source must not reference legacy shim symbol names."""
        src_root = src_dir / "bioetl"
        if not src_root.exists():
            pytest.skip("bioetl source not found")

        violations: list[str] = []
        for py_file in src_root.rglob("*.py"):
            rel_path = py_file.relative_to(src_dir).as_posix()
            if rel_path.startswith(
                "bioetl/infrastructure/adapters/"
            ) and rel_path.split("bioetl/infrastructure/adapters/", 1)[1] in {
                *ADAPTER_MIXIN_LEGACY_SHIMS.keys()
            }:
                # Legacy shim files define the aliases intentionally.
                continue

            content = py_file.read_text(encoding="utf-8")
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
                "bioetl.infrastructure.adapters.pubmed.pubmed_client",
                "PubMedAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.pubchem.client",
                "PubChemAdapter",
            ),
            (
                "bioetl.infrastructure.adapters.semanticscholar.adapter",
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


def _build_runtime_init_kwargs(
    adapter_cls: type,
) -> tuple[dict[str, object], ThreadPoolExecutor | None]:
    """Create minimal constructor kwargs for runtime Protocol checks."""
    signature = inspect.signature(adapter_cls)
    kwargs: dict[str, object] = {}
    thread_pool: ThreadPoolExecutor | None = None
    http_client = _create_http_client_mock()
    logger = MagicMock()
    rate_limiter = MagicMock()
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.return_value = "closed"
    circuit_breaker.get_failure_count.return_value = 0

    value_by_name: dict[str, object] = {
        "http_client": http_client,
        "logger": logger,
        "mailto": "bioetl-tests@example.org",
        "email": "bioetl-tests@example.org",
        "rate_limiter": rate_limiter,
        "circuit_breaker": circuit_breaker,
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
