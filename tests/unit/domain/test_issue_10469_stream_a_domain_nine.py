"""Stream A remaining domain coverage (#10469): control-plane, entities, locking, silver port."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest

import bioetl.domain.entities as entities
from bioetl.domain.control_plane.reproducibility_profiles import (
    published_production_reproducibility_families,
    published_supported_reproducibility_families,
)
from bioetl.domain.control_plane.run_ledger_replay import _float_value, _int_value
from bioetl.domain.locking import LockContext, LockContextHolder
from bioetl.domain.ports.storage.silver_port import (
    SilverWriteRequest,
    coerce_silver_write_request,
)
from bioetl.domain.types import ArrowSchema, RunID

pytestmark = pytest.mark.unit

_RUN = RunID(UUID("00000000-0000-4000-8000-000000000009"))


def test_published_reproducibility_family_inventories_are_lists() -> None:
    supported = published_supported_reproducibility_families()
    production = published_production_reproducibility_families()
    assert isinstance(supported, list)
    assert isinstance(production, list)
    assert all(isinstance(item, str) for item in supported)
    assert all(isinstance(item, str) for item in production)


def test_run_ledger_replay_numeric_helpers_treat_empty_text_as_zero() -> None:
    assert _int_value({"count": ""}, "count") == 0
    assert _int_value({"count": None}, "count") == 0
    assert _float_value({"duration": ""}, "duration") == 0.0
    assert _float_value({"duration": None}, "duration") == 0.0


def test_entities_dir_populates_lazy_all_when_empty() -> None:
    entities.__all__.clear()
    names = entities.__dir__()
    assert names == sorted(set(names))
    assert entities.__all__
    assert set(entities.__all__).issubset(set(names))


def test_lock_context_holder_clear_drops_held_context() -> None:
    holder = LockContextHolder()
    context = LockContext.create("chembl", "activity", _RUN)
    holder.set(context)
    assert holder.get() is context
    holder.clear()
    assert holder.get() is None


def test_coerce_silver_write_request_returns_typed_request_unchanged() -> None:
    request = SilverWriteRequest(
        table_name="chembl.activity",
        records=[],
        primary_keys=["activity_id"],
        schema=cast(ArrowSchema, object()),
    )
    assert coerce_silver_write_request(request) is request
