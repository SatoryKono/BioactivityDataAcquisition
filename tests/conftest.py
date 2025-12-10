"""
Pytest configuration and shared fixtures.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

# CRITICAL: Clean sys.path and PYTHONPATH BEFORE importing any packages
# to avoid conflicts with source directories (e.g., numpy source tree)

# Ensure src is on sys.path even if pytest pythonpath is ignored by runners
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

# RADICAL FIX: Completely rebuild sys.path with only safe paths
# This prevents numpy source directory import errors
_original_sys_path = list(sys.path)
_clean_sys_path = []

# Only keep site-packages, dist-packages, and standard library paths
# EXCLUDE paths to old projects (bioactivity_data_acquisition1)
for p in _original_sys_path:
    if not p:
        continue
    p_lower = p.lower()
    # Exclude old project paths
    if "bioactivity_data_acquisition1" in p_lower:
        continue
    # Keep installed packages
    if "site-packages" in p_lower or "dist-packages" in p_lower:
        _clean_sys_path.append(p)
    # Keep standard library
    elif "lib" in p_lower and "python" in p_lower:
        _clean_sys_path.append(p)

# Add our src path first
_clean_sys_path.insert(0, str(SRC_PATH))

# Replace sys.path immediately
sys.path = _clean_sys_path

# Completely clear PYTHONPATH to prevent any contamination
# Especially remove paths to old projects
if "PYTHONPATH" in os.environ:
    pythonpath_parts = os.environ["PYTHONPATH"].split(os.pathsep)
    filtered = [
        p
        for p in pythonpath_parts
        if p and "bioactivity_data_acquisition1" not in p.lower()
    ]
    if filtered:
        os.environ["PYTHONPATH"] = os.pathsep.join(filtered)
    else:
        del os.environ["PYTHONPATH"]

# Also check if current working directory contains numpy source
try:
    cwd = Path.cwd()
    if (cwd / "numpy" / "__init__.py").exists() and (cwd / "setup.py").exists():
        # We're in a numpy source directory - change to project root
        os.chdir(PROJECT_ROOT)
except (OSError, ValueError):
    pass

# Check if project itself is in a numpy source tree
# (should not happen, but safety check)
if (PROJECT_ROOT.parent / "numpy" / "__init__.py").exists() and (
    PROJECT_ROOT.parent / "setup.py"
).exists():
    raise RuntimeError(
        f"Project is located inside numpy source tree at {PROJECT_ROOT.parent}. "
        "Please move the project to a different location."
    )


def _contains_numpy_source(path_str: str) -> bool:
    """Check if path contains numpy source tree."""
    if not path_str:
        return False
    try:
        path = Path(path_str).resolve()
        if not path.exists():
            return False
        # Check if this path or any parent contains numpy source
        current = path
        for _ in range(5):  # Check up to 5 levels up
            if (current / "numpy" / "__init__.py").exists():
                # Check if it's a source tree (has setup.py)
                if (current / "setup.py").exists() or (
                    current / "numpy" / "setup.py"
                ).exists():
                    return True
            if current == current.parent:
                break
            current = current.parent
        return False
    except (OSError, ValueError):
        return False


# PYTHONPATH already cleared above, but double-check
if "PYTHONPATH" in os.environ:
    del os.environ["PYTHONPATH"]

# Also check and clean other environment variables that might affect imports
for env_var in ["PYTHONHOME"]:
    if env_var in os.environ:
        value = os.environ[env_var]
        if _contains_numpy_source(value):
            del os.environ[env_var]


# Aggressively clean sys.path to remove source directories
def _is_source_directory(path_str: str) -> bool:
    """Check if path points to a source directory (not installed package)."""
    if not path_str:
        return False

    # Never treat site-packages as source
    path_lower = path_str.lower()
    if "site-packages" in path_lower or "dist-packages" in path_lower:
        return False

    try:
        path = Path(path_str).resolve()
        if not path.exists():
            return False

        # Check for numpy source tree indicators
        if _contains_numpy_source(path_str):
            return True

        # Check for pandas source tree indicators
        pandas_indicators = [
            path / "pandas" / "__init__.py",
            path / "pandas" / "setup.py",
        ]
        if any(ind.exists() for ind in pandas_indicators):
            # Check if it's a source tree (has setup.py in parent or pandas dir)
            if (path / "setup.py").exists() or (path / "pandas" / "setup.py").exists():
                return True

        # Check if path itself is a numpy/pandas directory
        if path.name.lower() in ("numpy", "pandas"):
            if (path / "setup.py").exists() or (path / "pyproject.toml").exists():
                return True

        # Check parent directories for source trees
        for parent in [path.parent, path.parent.parent]:
            if (parent / "numpy" / "__init__.py").exists() or (
                parent / "pandas" / "__init__.py"
            ).exists():
                if (parent / "setup.py").exists():
                    return True

        return False
    except (OSError, ValueError):
        return False


def _should_exclude_path(path_str: str) -> bool:
    """Check if path should be excluded from sys.path."""
    if not path_str:
        return True

    path_lower = path_str.lower()

    # Always keep site-packages and dist-packages (installed packages)
    if "site-packages" in path_lower or "dist-packages" in path_lower:
        return False

    # Exclude known problematic patterns
    if "bioactivity_data_acquisition1" in path_lower:
        return True

    # Exclude if it's a source directory (but not if it's in site-packages)
    if _is_source_directory(path_str):
        return True

    # Exclude paths that are clearly source trees (not installed packages)
    # Check if path contains numpy/pandas but is NOT in site-packages
    if any(
        marker in path_lower
        for marker in [
            "/numpy/",
            "\\numpy\\",
            "/pandas/",
            "\\pandas\\",
        ]
    ):
        # Only exclude if it's NOT in site-packages
        if "site-packages" not in path_lower and "dist-packages" not in path_lower:
            return True

    return False


# sys.path already cleaned at the top of the file - no need to do it again
# Just ensure src is first
src_str = str(SRC_PATH)
if src_str in sys.path:
    sys.path.remove(src_str)
sys.path.insert(0, src_str)

# CRITICAL: Check if numpy in site-packages is actually source tree
# Diagnostic showed site-packages has numpy source instead of installed package
try:
    # Find numpy in site-packages and check if it's source
    numpy_source_path = None
    for path_str in sys.path:
        is_site_packages = (
            "site-packages" in path_str.lower() or "dist-packages" in path_str.lower()
        )
        if is_site_packages:
            site_packages_path = Path(path_str)
            numpy_path = site_packages_path / "numpy" / "__init__.py"
            if numpy_path.exists():
                # Check if this is a source tree (has setup.py in parent or numpy dir)
                if (site_packages_path / "setup.py").exists():
                    # This site-packages directory contains a source tree!
                    numpy_source_path = site_packages_path
                    break
                # Check if numpy itself has setup.py (it's a source tree)
                if (site_packages_path / "numpy" / "setup.py").exists():
                    numpy_source_path = site_packages_path / "numpy"
                    break

    # If we found numpy source in site-packages, we need to remove that path
    # This is the root cause: numpy source tree is in site-packages
    if numpy_source_path:
        source_str = str(numpy_source_path)
        if source_str in sys.path:
            sys.path.remove(source_str)
        # Also check parent if it's not site-packages
        parent_str = str(numpy_source_path.parent)
        if parent_str in sys.path and "site-packages" not in parent_str.lower():
            sys.path.remove(parent_str)

        # Now try to import - if it still fails, numpy needs to be reinstalled
        import numpy

        # Verify numpy location
        numpy_file = getattr(numpy, "__file__", None)
        if numpy_file:
            numpy_path = Path(numpy_file).resolve()
            # Check if it's still from a source tree
            check_dir = numpy_path.parent
            for _ in range(6):
                if (check_dir / "setup.py").exists() and (
                    check_dir / "numpy" / "__init__.py"
                ).exists():
                    raise RuntimeError(
                        f"numpy source tree detected in site-packages at: {check_dir}. "
                        "Please reinstall numpy:\n"
                        "  pip uninstall numpy\n"
                        "  pip install numpy"
                    )
                if check_dir == check_dir.parent:
                    break
                check_dir = check_dir.parent
    else:
        # No source tree found, try normal import
        import numpy
except ImportError as e:
    error_msg = str(e)
    if "source directory" in error_msg.lower():
        # Provide helpful error message with fix script
        fix_script = PROJECT_ROOT / "scripts" / "fix_numpy_import.py"
        raise RuntimeError(
            "numpy source tree detected in Python path.\n\n"
            "QUICK FIX:\n"
            f"  python {fix_script}\n\n"
            "OR MANUAL FIX:\n"
            "1. Clear PYTHONPATH: $env:PYTHONPATH = $null (PowerShell)\n"
            "2. Remove numpy source from site-packages if present\n"
            "3. Reinstall numpy: pip uninstall numpy && pip install numpy\n\n"
            f"Original error: {error_msg}"
        ) from e
    raise RuntimeError(f"Cannot import numpy: {e}. Please install numpy.") from e
except Exception as e:
    # Log but continue - might work anyway
    import warnings

    warnings.warn(f"Error checking numpy import: {e}", RuntimeWarning)

# Now safe to import packages
import pandas as pd  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402
import pytest  # noqa: E402

from bioetl.domain.configs import (  # noqa: E402
    ChemblSourceConfig,
    ClientConfig,
    HashingConfig,
    LoggingConfig,
    PipelineConfig,
    StorageConfig,
)
from bioetl.domain.models import RunContext  # noqa: E402
from bioetl.domain.observability.contracts import LoggingPortABC  # noqa: E402
from bioetl.domain.validation.service import ValidationService  # noqa: E402

# Workaround for Hypothesis issue with Python 3.13 and SimpleNamespace modules
# Hypothesis tries to create a set from sys.modules.values(), but some modules
# are SimpleNamespace objects which are not hashable.
# This patch is applied early via pytest_configure hook.


def pytest_configure(config):
    """Apply patches for removed modules and Hypothesis compatibility."""

    # Apply Hypothesis compatibility patch for Python 3.13
    try:
        # Import and patch before Hypothesis is used
        from hypothesis.internal.conjecture import providers as hypothesis_providers

        _original_get_local_constants = hypothesis_providers._get_local_constants

        def _patched_get_local_constants():
            """Patched version that filters out unhashable modules."""
            try:
                return _original_get_local_constants()
            except TypeError as e:
                if "unhashable type" in str(e):
                    # Filter out SimpleNamespace modules before creating set
                    # This is a workaround for Python 3.13 compatibility
                    import sys
                    from types import SimpleNamespace

                    # Create filtered modules dict
                    filtered_modules = {
                        k: v
                        for k, v in sys.modules.items()
                        if not isinstance(v, SimpleNamespace)
                    }

                    # Temporarily replace sys.modules
                    original_modules = dict(sys.modules)
                    try:
                        sys.modules.clear()
                        sys.modules.update(filtered_modules)
                        return _original_get_local_constants()
                    finally:
                        # Restore original
                        sys.modules.clear()
                        sys.modules.update(original_modules)
                raise

        hypothesis_providers._get_local_constants = _patched_get_local_constants
    except (ImportError, AttributeError):
        # Hypothesis not available or structure changed, skip patch
        pass


@pytest.fixture
def mock_config():
    """Create a mock pipeline configuration."""
    return PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        input_mode="auto_detect",
        input_path=None,
        output_path="./test_out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url=cast(AnyHttpUrl, "https://www.ebi.ac.uk/chembl/api/data"),
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path="./test_out"),
        hashing=HashingConfig(business_key_fields=["id"]),
        pipeline={},
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock(spec=LoggingPortABC)
    logger.apply_bind.return_value = logger
    return logger


@pytest.fixture
def mock_validation_service():
    """Create a mock validation service."""
    service = MagicMock(spec=ValidationService)
    # Default behavior: return df as is
    service.validate.side_effect = lambda df, **kwargs: df
    service.get_schema_columns.return_value = []
    return service


@pytest.fixture
def mock_loader():
    """Create a mock loader compatible with LoaderABC."""
    from pathlib import Path

    from bioetl.domain.clients.base.output.contracts import WriteResult
    from bioetl.domain.pipelines.contracts import LoaderABC

    loader = MagicMock(spec=LoaderABC)
    loader.load.return_value = WriteResult(
        path=Path("/tmp/test_output.csv"),
        row_count=2,  # Default for most tests
        duration_sec=0.1,
        checksum=None,
    )
    return loader


@pytest.fixture
def mock_metadata_builder():
    """Create a mock metadata builder compatible with RunMetadataBuilderProtocol."""
    return SimpleNamespace(
        build_run_metadata=lambda context, write_result: {
            "run_id": getattr(context, "run_id", None),
            "row_count": getattr(write_result, "row_count", 0),
            "provider": getattr(context, "provider", None),
            "entity": getattr(context, "entity_name", None),
        },
        build_dry_run_metadata=lambda context, row_count: {
            "run_id": getattr(context, "run_id", None),
            "row_count": row_count,
            "dry_run": True,
            "provider": getattr(context, "provider", None),
            "entity": getattr(context, "entity_name", None),
        },
    )


@pytest.fixture
def sample_df():
    """Create a sample DataFrame."""
    return pd.DataFrame({"id": [1, 2, 3], "value": ["a", "b", "c"]})


@pytest.fixture
def run_context_factory():
    """Factory fixture to build RunContext with optional overrides."""

    def _factory(
        run_id: str = "test-run",
        entity_name: str = "test_entity",
        provider: str = "chembl",
        started_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> RunContext:
        return RunContext(
            run_id=run_id,
            entity_name=entity_name,
            provider=provider,
            started_at=started_at
            or datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            metadata=metadata or {},
            config=config or {},
            dry_run=dry_run,
        )

    return _factory


@pytest.fixture
def pipeline_test_config(tmp_path_factory: pytest.TempPathFactory) -> PipelineConfig:
    """Pipeline config for integration-style unit tests."""
    output_dir = tmp_path_factory.mktemp("pipeline_output")
    return PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        input_mode="auto_detect",
        input_path=None,
        output_path=str(output_dir),
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url=cast(AnyHttpUrl, "https://www.ebi.ac.uk/chembl/api/data"),
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path=str(output_dir)),
        hashing=HashingConfig(business_key_fields=["id"]),
        pipeline={},
    )


@pytest.fixture
def small_pipeline_df() -> pd.DataFrame:
    """Tiny dataset used for pipeline dry-run tests."""
    return pd.DataFrame(
        {
            "id": [101, 202],
            "value": ["alpha", "beta"],
        }
    )


@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch, request):
    """Block network access unless marked with 'network' or 'integration'."""
    if request.node.get_closest_marker("network") or request.node.get_closest_marker(
        "integration"
    ):
        return

    def guard(*_args, **_kwargs):
        raise RuntimeError(
            "Network access disabled. Use @pytest.mark.network or "
            "@pytest.mark.integration to enable. "
            f"Test: {request.node.name}"
        )

    class GuardedSocket:
        """Mock socket that raises error on instantiation."""

        def __init__(self, *_args, **_kwargs):
            guard()

    monkeypatch.setattr(socket, "socket", GuardedSocket)
    monkeypatch.setattr(socket, "create_connection", guard)


# End of conftest


@pytest.fixture(autouse=True)
def init_provider_registry():
    """Initialize the provider registry for all tests."""
    from bioetl.domain.provider_registry import set_provider_registry
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

    registry = InMemoryProviderRegistry()
    set_provider_registry(registry)

