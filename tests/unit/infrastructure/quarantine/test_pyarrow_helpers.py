"""Tests for quarantine PyArrow compute helper seams."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quarantine import _pyarrow_helpers

pytestmark = pytest.mark.unit


class _FakePyArrowCompute:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def equal(self, left: object, right: object) -> str:
        self.calls.append(("equal", left, right))
        return "equal-mask"

    def and_(self, left: object, right: object) -> str:
        self.calls.append(("and", left, right))
        return "and-mask"


def test_equal_and_and_masks_delegate_to_pyarrow_compute(monkeypatch) -> None:
    compute = _FakePyArrowCompute()
    monkeypatch.setattr(_pyarrow_helpers, "pc", compute)

    assert _pyarrow_helpers.equal_mask("left", "right") == "equal-mask"
    assert _pyarrow_helpers.and_mask("first", "second") == "and-mask"
    assert compute.calls == [
        ("equal", "left", "right"),
        ("and", "first", "second"),
    ]


def test_require_pyarrow_compute_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(_pyarrow_helpers, "pc", None)

    with pytest.raises(RuntimeError, match=r"require pyarrow\.compute"):
        _pyarrow_helpers._require_pyarrow_compute()
