"""Config alignment tests for non-ChEMBL root hash_policy sections."""

from __future__ import annotations

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.normalization.profiles.registry import (
    resolve_normalization_profile,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from tests.unit.application.core.test_non_chembl_normalization_hash_golden import (
    RAW_CASES,
    _load_golden,
)

NON_CHEMBL_PIPELINE_NAMES = sorted(RAW_CASES)


@pytest.mark.integration
@pytest.mark.parametrize("pipeline_name", NON_CHEMBL_PIPELINE_NAMES)
def test_non_chembl_root_hash_policy_matches_profile_and_golden_hash(
    pipeline_name: str,
) -> None:
    """Root hash_policy must mirror profile fields and preserve golden content hashes."""
    provider, entity_type, raw = RAW_CASES[pipeline_name]
    profile = resolve_normalization_profile(provider, entity_type)
    assert profile is not None

    load_pipeline_config.cache_clear()
    loaded = load_pipeline_config(pipeline_name)
    policy = loaded.content_hash_policy
    assert policy is not None

    assert frozenset(policy.include_fields) == profile.hash_included_fields
    assert policy.provider == provider
    assert policy.entity == entity_type

    processor = RecordNormalizationProcessor(
        provider=provider,
        entity_type=entity_type,
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset(policy.include_fields),
        content_hash_exclude_fields=frozenset(policy.exclude_fields),
    )
    golden = _load_golden(pipeline_name)
    normalized = processor.normalize_business_data(dict(raw))

    assert normalized == golden["normalized"]
    assert processor.compute_content_hash(normalized) == golden["content_hash"]
