# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Bootstrap unit suite fixtures with optional immutable metadata reuse (T-04).

Session-scoped payloads are limited to immutable pipeline/provider catalog
metadata (see ``tests/helpers/bootstrap_cache.py``). Mutable services, ports,
and observability exporters are never cached.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapMetadataCache,
    CachedBootstrapMetadata,
    clone_pipeline_registry,
    clone_provider_registry,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIGS_ROOT = _REPO_ROOT / "configs"


@pytest.fixture(scope="session")
def bootstrap_metadata_cache() -> BootstrapMetadataCache:
    """Session-scoped fingerprint cache for immutable bootstrap catalogs."""
    return BootstrapMetadataCache()


@pytest.fixture(scope="session")
def cached_bootstrap_metadata(
    bootstrap_metadata_cache: BootstrapMetadataCache,
) -> CachedBootstrapMetadata:
    """Immutable pipeline/provider catalog for the current configs fingerprint."""
    return bootstrap_metadata_cache.get_or_build(configs_root=_CONFIGS_ROOT)


@pytest.fixture
def fresh_pipeline_registry(cached_bootstrap_metadata: CachedBootstrapMetadata):
    """Per-test pipeline registry clone rebuilt from immutable metadata."""
    return clone_pipeline_registry(cached_bootstrap_metadata)


@pytest.fixture
def fresh_provider_registry(cached_bootstrap_metadata: CachedBootstrapMetadata):
    """Per-test provider registry clone rebuilt from immutable metadata."""
    return clone_provider_registry(cached_bootstrap_metadata)
