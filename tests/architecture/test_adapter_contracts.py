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

import re
from pathlib import Path

import pytest


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
            "base.py",
            "base_metrics.py",  # Base class for metrics adapters
            "types.py",
            "exceptions.py",
            "client.py",  # HTTP client utility, not a DataSourcePort adapter
            "pagination.py",  # Pagination mixin, not a DataSourcePort adapter
            "rate_limiter.py",  # Rate limiting utility
            "circuit_breaker.py",  # Circuit breaker utility
            "health_monitor.py",  # Health state utility, not a DataSourcePort adapter
        }
        adapter_files = []
        for py_file in adapters_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            if py_file.name in excluded_files:
                continue
            adapter_files.append(py_file)

        missing_health_check = []

        for py_file in adapter_files:
            content = py_file.read_text(encoding="utf-8")

            # Check if file defines a class (likely an adapter)
            if "class " not in content:
                continue

            # Check for health_check method definition OR inheritance from BaseHttpAdapter
            # BaseHttpAdapter provides health_check() via Template Method pattern
            has_health_check = (
                "def health_check" in content
                or "async def health_check" in content
                or "(BaseHttpAdapter)" in content  # Inherits health_check from base
            )

            if not has_health_check:
                # Only flag if it looks like an adapter class
                if "Adapter" in content or "Client" in content or "Fetcher" in content:
                    relative_path = py_file.relative_to(src_dir)
                    missing_health_check.append(str(relative_path))

        assert not missing_health_check, (
            "Adapters must implement health_check() method (REQ-OBS-001).\n"
            "Files missing health_check:\n"
            + "\n".join(f"  - {f}" for f in missing_health_check)
            + "\n\nSee: docs/05-operations/runbooks/observability-checklist.md"
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


class TestStorageWriterContracts:
    """Tests ensuring storage writers follow proper patterns."""

    def test_atomic_write_used_in_writers(self, src_dir: Path) -> None:
        """Verify that storage writers use atomic write patterns.

        REQ-DATA-004: All file writes should be atomic to prevent data corruption.
        """
        storage_path = src_dir / "bioetl" / "infrastructure" / "storage"
        if not storage_path.exists():
            pytest.skip("Storage layer not found")

        # Writers that should use atomic patterns
        writer_files = ["bronze_writer.py", "gold_writer.py"]

        # Patterns indicating atomic writes (should be present)
        atomic_indicators = [
            r"atomic_write",
            r"AtomicWriteGroup",
            r"\.replace\s*\(",
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
