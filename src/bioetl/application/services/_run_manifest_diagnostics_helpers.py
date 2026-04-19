"""Compatibility re-export module for run-manifest diagnostics helpers."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "DQDetailsSummary",
    "collect_dq_values",
    "extract_cross_validation_sets",
    "extract_diagnostic_context",
    "extract_dq_details",
    "has_dq_signal",
    "load_str_collection",
    "update_correlation_anchor_gaps",
]

_IMPL_MODULE = (
    "bioetl.application.services.control_plane._run_manifest_diagnostics_helpers"
)
_IMPL = import_module(_IMPL_MODULE)

DQDetailsSummary = _IMPL.DQDetailsSummary
collect_dq_values = _IMPL.collect_dq_values
extract_cross_validation_sets = _IMPL.extract_cross_validation_sets
extract_diagnostic_context = _IMPL.extract_diagnostic_context
extract_dq_details = _IMPL.extract_dq_details
has_dq_signal = _IMPL.has_dq_signal
load_str_collection = _IMPL.load_str_collection
update_correlation_anchor_gaps = _IMPL.update_correlation_anchor_gaps


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(_IMPL, name)


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
