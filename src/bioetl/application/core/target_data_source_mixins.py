"""Public seam for derived-target data-source wrapper mixins."""

from __future__ import annotations

from bioetl.application.core._target_data_source_fetch_support import (
    yield_plain_wrapped_fetch_records as _yield_plain_wrapped_fetch_records,
)
from bioetl.application.core._target_data_source_fetch_support import (
    yield_wrapped_fetch_records as _yield_wrapped_fetch_records,
)
from bioetl.application.core._target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)

__all__ = [
    "_FallbackFilterableTargetFetchMixin",
    "_FilterableTargetDelegationMixin",
    "_TargetEntityFetchDelegationMixin",
    "_yield_plain_wrapped_fetch_records",
    "_yield_wrapped_fetch_records",
]
