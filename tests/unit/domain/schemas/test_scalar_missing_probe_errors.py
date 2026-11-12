"""An unsupported pandas scalar is not silently accepted as missing."""

from __future__ import annotations

import pytest
from bioetl.domain.schemas import validators

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("error", [TypeError, ValueError])
def test_uninspectable_scalar_is_not_classified_as_null(monkeypatch, error):
    def reject_scalar(*args, **kwargs):
        raise error("synthetic unsupported scalar")

    monkeypatch.setattr(validators.pd, "Series", reject_scalar)
    assert validators._is_scalar_missing(object()) is False
