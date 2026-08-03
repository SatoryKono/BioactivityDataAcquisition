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
"""Unit tests for protocols — structural shape verification."""

from __future__ import annotations

import pytest

from bioetl.application.composite.protocols import (
    DependencyJoinerProtocol,
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)


@pytest.mark.unit
class TestJoinKeyResolverProtocol:
    """Verify JoinKeyResolverProtocol defines expected methods."""

    def test_has_find_join_key_column(self) -> None:
        assert hasattr(JoinKeyResolverProtocol, "find_join_key_column")

    def test_has_normalize_join_key_columns(self) -> None:
        assert hasattr(JoinKeyResolverProtocol, "normalize_join_key_columns")

    def test_has_resolve_join_key_names(self) -> None:
        assert hasattr(JoinKeyResolverProtocol, "resolve_join_key_names")

    def test_has_resolve_join_key_names_asymmetric(self) -> None:
        assert hasattr(JoinKeyResolverProtocol, "resolve_join_key_names_asymmetric")

    def test_has_resolve_composite_join_keys(self) -> None:
        assert hasattr(JoinKeyResolverProtocol, "resolve_composite_join_keys")

    def test_is_runtime_checkable(self) -> None:
        assert isinstance(JoinKeyResolverProtocol, type)

        # runtime_checkable means we can use isinstance() checks
        # A conforming class should pass isinstance check
        class _Impl:
            def find_join_key_column(self, key, columns, pipeline=None):
                return None

            def normalize_join_key_columns(self, df, join_keys, pipeline=None):
                return None

            def resolve_join_key_names(
                self, primary_key, seed_pipeline, enricher_pipeline, merged_columns
            ):
                return None

            def resolve_join_key_names_asymmetric(
                self, left_key, right_key, left_pipeline, right_pipeline, merged_columns
            ):
                return None

            def resolve_composite_join_keys(
                self, join_keys_list, left_pipeline, right_pipeline, merged_columns
            ):
                return None

        assert isinstance(_Impl(), JoinKeyResolverProtocol)


@pytest.mark.unit
class TestJoinExecutorProtocol:
    """Verify JoinExecutorProtocol defines expected methods."""

    def test_has_execute_polars_join(self) -> None:
        assert hasattr(JoinExecutorProtocol, "execute_polars_join")

    def test_has_execute_composite_key_join(self) -> None:
        assert hasattr(JoinExecutorProtocol, "execute_composite_key_join")

    def test_has_get_polars_join_type(self) -> None:
        assert hasattr(JoinExecutorProtocol, "get_polars_join_type")

    def test_join_executor_protocol__is_runtime_checkable__bec146d2(self) -> None:
        class _Impl:
            def execute_polars_join(
                self, left_df, right_df, left_key, right_key, pipeline_name
            ):
                return None

            def execute_composite_key_join(
                self, left_df, right_df, left_keys, right_keys, pipeline_name
            ):
                return None

            def get_polars_join_type(self):
                return None

        assert isinstance(_Impl(), JoinExecutorProtocol)


@pytest.mark.unit
class TestDependencyJoinerProtocol:
    """Verify DependencyJoinerProtocol defines expected methods."""

    def test_has_apply_dependency_joins(self) -> None:
        assert hasattr(DependencyJoinerProtocol, "apply_dependency_joins")

    def test_has_apply_composite_key_dependency_join(self) -> None:
        assert hasattr(DependencyJoinerProtocol, "apply_composite_key_dependency_join")

    def test_has_drop_system_columns(self) -> None:
        assert hasattr(DependencyJoinerProtocol, "drop_system_columns")

    def test_joiner_protocol__is_runtime_checkable__e8453357(self) -> None:
        class _Impl:
            def apply_dependency_joins(
                self, *, merged_df, dependency_dfs, dependencies, seed_pipeline=None
            ):
                return None

            def apply_composite_key_dependency_join(
                self, *, merged_df, dep_df, dep, seed_pipeline=None
            ):
                return None

            def drop_system_columns(self, df):
                return None

        assert isinstance(_Impl(), DependencyJoinerProtocol)

    def test_non_conforming_class_fails(self) -> None:
        class _Bad:
            pass

        assert not isinstance(_Bad(), DependencyJoinerProtocol)
