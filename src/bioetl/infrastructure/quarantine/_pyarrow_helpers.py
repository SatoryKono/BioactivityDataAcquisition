# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""PyArrow compute helpers for quarantine operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    import pyarrow as pa

try:
    import pyarrow.compute as pc
except ImportError:
    pc = None


class _PyArrowComputeModule(Protocol):
    def equal(
        self,
        left: object,
        right: object,
    ) -> pa.Array | pa.ChunkedArray: ...

    def and_(
        self,
        left: object,
        right: object,
    ) -> pa.Array | pa.ChunkedArray: ...


def _require_pyarrow_compute() -> _PyArrowComputeModule:
    """Return ``pyarrow.compute`` or raise a bounded runtime error."""
    if pc is None:
        raise RuntimeError(
            "Quarantine read operations require pyarrow.compute, but it could not "
            "be imported in the current environment"
        )
    return cast(_PyArrowComputeModule, pc)


def equal_mask(left: object, right: object) -> pa.Array | pa.ChunkedArray:
    """Create equality mask for PyArrow arrays."""
    compute = _require_pyarrow_compute()
    return compute.equal(left, right)


def and_mask(left: object, right: object) -> pa.Array | pa.ChunkedArray:
    """Create AND mask for PyArrow arrays."""
    compute = _require_pyarrow_compute()
    return compute.and_(left, right)
