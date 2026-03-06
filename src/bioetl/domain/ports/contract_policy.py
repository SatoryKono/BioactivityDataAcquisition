"""Backward-compatible re-export for quality contract policy port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.contract_policy import ContractPolicyPort

__all__ = ["ContractPolicyPort"]
