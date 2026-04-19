"""Compatibility re-export module for metadata coordinator helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "build_bronze_file_output_metadata",
    "build_bronze_source_metadata",
    "create_metadata_bundle",
    "validate_records_present",
]

_IMPL_MODULE = "bioetl.application.services.lineage._metadata_coordinator_helpers"
_IMPL = import_module(_IMPL_MODULE)

build_bronze_file_output_metadata = _IMPL.build_bronze_file_output_metadata
build_bronze_source_metadata = _IMPL.build_bronze_source_metadata
create_metadata_bundle = _IMPL.create_metadata_bundle
validate_records_present = _IMPL.validate_records_present


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(_IMPL, name)


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
