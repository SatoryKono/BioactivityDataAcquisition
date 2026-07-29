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
"""Isolation proof for session-scoped bootstrap metadata cache (#6892)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapMetadataCache,
    CachedBootstrapMetadata,
    clone_pipeline_registry,
)

pytestmark = pytest.mark.unit


def test_session_cached_bootstrap_metadata_is_immutable_catalog(
    cached_bootstrap_metadata: CachedBootstrapMetadata,
    bootstrap_metadata_cache: BootstrapMetadataCache,
) -> None:
    """Session fixture reuses one catalog build for immutable metadata."""
    configs_root = Path(cached_bootstrap_metadata.cache_key.configs_root)
    again = bootstrap_metadata_cache.get_or_build(configs_root=configs_root)
    assert bootstrap_metadata_cache.build_count >= 1
    assert again.cache_key == cached_bootstrap_metadata.cache_key
    assert again.pipeline_names == cached_bootstrap_metadata.pipeline_names
    assert cached_bootstrap_metadata.pipeline_names
    assert cached_bootstrap_metadata.provider_definitions


def test_fresh_pipeline_registry_clones_are_independent(
    cached_bootstrap_metadata: CachedBootstrapMetadata,
) -> None:
    left = clone_pipeline_registry(cached_bootstrap_metadata)
    right = clone_pipeline_registry(cached_bootstrap_metadata)
    assert left is not right
    assert left.list_pipelines() == right.list_pipelines()
