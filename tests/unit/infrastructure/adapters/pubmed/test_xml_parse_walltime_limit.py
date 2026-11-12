"""Each XML parser callback enforces an already exhausted wall-time budget."""

from __future__ import annotations

import time
import pytest
from bioetl.infrastructure.adapters.pubmed.xml_processor import LimitedParseTarget

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("callback", ["start", "data", "end"])
def test_xml_callback_rejects_an_exhausted_time_budget(callback):
    target = LimitedParseTarget()
    target.start_time = time.monotonic() - target.max_time - 1.0
    arguments = {"start": ("article", {}), "data": ("text",), "end": ("article",)}
    with pytest.raises(ValueError, match="XML time limit exceeded"):
        getattr(target, callback)(*arguments[callback])
