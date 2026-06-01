"""Backward-compatible re-export for `bioetl.application.core.target_data_source_mixins`."""

from __future__ import annotations

from bioetl.application.core import target_data_source_mixins as _public

_FallbackFilterableTargetFetchMixin = _public._FallbackFilterableTargetFetchMixin
_FilterableTargetDelegationMixin = _public._FilterableTargetDelegationMixin
_TargetEntityFetchDelegationMixin = _public._TargetEntityFetchDelegationMixin

__all__ = [
    "_FallbackFilterableTargetFetchMixin",
    "_FilterableTargetDelegationMixin",
    "_TargetEntityFetchDelegationMixin",
]
