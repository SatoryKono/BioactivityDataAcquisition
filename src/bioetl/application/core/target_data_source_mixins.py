"""Public seam for derived-target data-source wrapper mixins."""

from __future__ import annotations

from bioetl.application.core._target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _yield_plain_wrapped_fetch_records,
    _yield_wrapped_fetch_records,
)

__all__ = [
    "_FallbackFilterableTargetFetchMixin",
    "_FilterableTargetDelegationMixin",
    "_TargetEntityFetchDelegationMixin",
    "_yield_plain_wrapped_fetch_records",
    "_yield_wrapped_fetch_records",
]
