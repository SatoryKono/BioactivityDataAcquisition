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
"""Property tests for composite join key resolution."""

from __future__ import annotations

import pytest

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name

pytestmark = pytest.mark.unit

_LOWER_ALPHA = "abcdefghijklmnopqrstuvwxyz"
_LOWER_ALNUM = f"{_LOWER_ALPHA}0123456789"
_IDENT = st.builds(
    lambda head, tail: head + tail,
    st.sampled_from(tuple(_LOWER_ALPHA)),
    st.text(alphabet=_LOWER_ALNUM, min_size=0, max_size=7),
)
_PROPERTY_TEST_SETTINGS = settings(
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)


def _build_resolver() -> JoinKeyResolverService:
    from bioetl.application.composite.join_key_resolution import ResolverHelper
    from unittest.mock import MagicMock

    # Create resolver helper with normalization policies (new API)
    mock_logger = MagicMock()
    resolver_helper = ResolverHelper(
        logger=mock_logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )

    return JoinKeyResolverService(
        resolver_helper=resolver_helper,
        parse_pipeline_name=parse_pipeline_name,
    )


@_PROPERTY_TEST_SETTINGS
@given(provider=_IDENT, entity=_IDENT, key=_IDENT)
def test_find_join_key_column_prefers_qualified_when_available(
    provider: str,
    entity: str,
    key: str,
) -> None:
    resolver = _build_resolver()
    pipeline = f"{provider}_{entity}"
    qualified = f"{provider}.{entity}.{key}"
    columns = [qualified, key, f"other.namespace.{key}"]

    assert resolver.find_join_key_column(key, columns, pipeline) == qualified


@_PROPERTY_TEST_SETTINGS
@given(key=_IDENT)
def test_find_join_key_column_falls_back_to_unqualified_for_invalid_pipeline(
    key: str,
) -> None:
    resolver = _build_resolver()
    columns = [key, f"other.namespace.{key}"]

    assert resolver.find_join_key_column(key, columns, "invalidpipeline") == key


@_PROPERTY_TEST_SETTINGS
@given(provider=_IDENT, entity=_IDENT, key=_IDENT)
def test_resolve_join_key_names_uses_qualified_seed_when_present(
    provider: str,
    entity: str,
    key: str,
) -> None:
    resolver = _build_resolver()
    pipeline = f"{provider}_{entity}"
    qualified = f"{provider}.{entity}.{key}"

    seed_key, right_key, seed_qualified = resolver.resolve_join_key_names(
        primary_key=key,
        seed_pipeline=pipeline,
        enricher_pipeline=pipeline,
        merged_columns=[qualified],
    )

    assert seed_key == qualified
    assert right_key == qualified
    assert seed_qualified == qualified


@_PROPERTY_TEST_SETTINGS
@given(
    left_provider=_IDENT,
    left_entity=_IDENT,
    right_provider=_IDENT,
    right_entity=_IDENT,
    left_key=_IDENT,
    right_key=_IDENT,
)
def test_resolve_join_key_names_asymmetric_preserves_left_qualification(
    left_provider: str,
    left_entity: str,
    right_provider: str,
    right_entity: str,
    left_key: str,
    right_key: str,
) -> None:
    resolver = _build_resolver()
    left_pipeline = f"{left_provider}_{left_entity}"
    right_pipeline = f"{right_provider}_{right_entity}"
    left_qualified = f"{left_provider}.{left_entity}.{left_key}"

    resolved_left, resolved_right, resolved_left_qualified = (
        resolver.resolve_join_key_names_asymmetric(
            left_key=left_key,
            right_key=right_key,
            left_pipeline=left_pipeline,
            right_pipeline=right_pipeline,
            merged_columns=[left_qualified],
        )
    )

    assert resolved_left == left_qualified
    assert resolved_left_qualified == left_qualified
    assert resolved_right == f"{right_provider}.{right_entity}.{right_key}"


@_PROPERTY_TEST_SETTINGS
@given(
    left_provider=_IDENT,
    left_entity=_IDENT,
    right_provider=_IDENT,
    right_entity=_IDENT,
    join_keys=st.lists(_IDENT, min_size=1, max_size=3, unique=True),
)
def test_resolve_composite_join_keys_preserves_key_cardinality(
    left_provider: str,
    left_entity: str,
    right_provider: str,
    right_entity: str,
    join_keys: list[str],
) -> None:
    resolver = _build_resolver()
    left_pipeline = f"{left_provider}_{left_entity}"
    right_pipeline = f"{right_provider}_{right_entity}"
    merged_columns = [f"{left_provider}.{left_entity}.{key}" for key in join_keys]

    left_keys, right_keys, join_key_set = resolver.resolve_composite_join_keys(
        join_keys_list=join_keys,
        left_pipeline=left_pipeline,
        right_pipeline=right_pipeline,
        merged_columns=merged_columns,
    )

    assert len(left_keys) == len(join_keys)
    assert len(right_keys) == len(join_keys)
    assert set(left_keys).issubset(join_key_set)
    assert set(right_keys).issubset(join_key_set)
