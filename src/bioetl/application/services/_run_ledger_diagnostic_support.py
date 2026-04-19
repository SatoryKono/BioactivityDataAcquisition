"""Compatibility re-export module for run-ledger diagnostic helpers."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "LEDGER_DIAGNOSTIC_CONTRACT_VERSION",
    "_RunLedgerDefaultsHost",
    "build_run_ledger_diagnostic_details",
    "sync_manifest_contract_defaults",
    "sync_manifest_runtime_defaults",
]

_IMPL_MODULE = (
    "bioetl.application.services.control_plane._run_ledger_diagnostic_support"
)
_IMPL = import_module(_IMPL_MODULE)

LEDGER_DIAGNOSTIC_CONTRACT_VERSION = _IMPL.LEDGER_DIAGNOSTIC_CONTRACT_VERSION
_RunLedgerDefaultsHost = _IMPL._RunLedgerDefaultsHost
build_run_ledger_diagnostic_details = _IMPL.build_run_ledger_diagnostic_details
sync_manifest_contract_defaults = _IMPL.sync_manifest_contract_defaults
sync_manifest_runtime_defaults = _IMPL.sync_manifest_runtime_defaults


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(_IMPL, name)


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
