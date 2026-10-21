"""A selected producer may own only rows with a proven stable identity."""

from types import SimpleNamespace

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage import workflow_producer_ownership as ownership
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    filter_current_rows,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "row", [{}, {"entity_id": "e"}, {"entity_id": "", "content_hash": "h"}]
)
def test_missing_technical_identity_is_rejected(row):
    with pytest.raises(ValueError, match="lacks entity/content identity"):
        ownership.entity_hashes([row])


def test_ambiguous_current_entity_cannot_certify_producer_membership():
    with pytest.raises(ValueError, match="ambiguous current entities"):
        ownership.entity_hashes(
            [
                {"entity_id": "e", "content_hash": "a"},
                {"entity_id": "e", "content_hash": "b"},
            ]
        )


@pytest.mark.parametrize("owned", [{"": "h"}, {"e": None}, {1: "h"}])
def test_invalid_saved_membership_never_selects_rows(owned):
    with pytest.raises(ValueError, match="membership is invalid"):
        ownership.filter_owned_entities(
            [], {"ownership": "producer_delta_entities", "owned_entities": owned}
        )


def _stub_table(monkeypatch, rows):
    table = pa.Table.from_pylist(rows)
    monkeypatch.setattr(
        ownership,
        "DeltaTable",
        lambda *args, **kwargs: SimpleNamespace(to_pyarrow_table=lambda: table),
    )


@pytest.mark.asyncio
async def test_capture_requires_run_or_technical_columns(monkeypatch):
    _stub_table(monkeypatch, [{"business_id": "1"}])
    with pytest.raises(ValueError, match="no row run identity or technical identity"):
        await ownership.capture_ownership(
            "unused", "silver", 1, before=True, previous=None, table_id="table"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "previous, message",
    [
        (None, "pre-execution snapshot"),
        ({"version": 1}, "schema changed"),
        ({"entity_hashes": []}, "baseline is invalid"),
    ],
)
async def test_capture_rejects_unproven_preexecution_state(
    monkeypatch, previous, message
):
    _stub_table(monkeypatch, [{"entity_id": "e", "content_hash": "h"}])
    with pytest.raises(ValueError, match=message):
        await ownership.capture_ownership(
            "unused", "silver", 2, before=False, previous=previous, table_id="table"
        )


@pytest.mark.asyncio
async def test_recreated_table_does_not_reuse_old_membership(monkeypatch):
    _stub_table(monkeypatch, [{"entity_id": "e", "content_hash": "h"}])
    result = await ownership.capture_ownership(
        "unused",
        "silver",
        2,
        before=False,
        previous={"table_id": "old", "version": 1, "entity_hashes": {"e": "h"}},
        table_id="new",
    )
    assert result["owned_entities"] == {"e": "h"}
    assert result["producer_input_table_id"] == "old"


@pytest.mark.parametrize(
    "flag, expected",
    [
        (True, True),
        (False, False),
        (None, False),
        (1, True),
        (0, False),
        (" yes ", True),
        ("no", False),
        ([], False),
    ],
)
def test_current_row_filter_obeys_supported_saved_flag_values(flag, expected):
    row = {"entity_id": "e", "is_current": flag}
    assert filter_current_rows([row], current_only=True, layer="silver") == (
        [row] if expected else []
    )


def test_current_filter_preserves_unversioned_rows_and_explicit_opt_out():
    rows = [{"entity_id": "e"}]
    assert filter_current_rows(rows, current_only=True, layer="silver") == rows
    assert filter_current_rows(rows, current_only=False, layer="gold") == rows
    assert filter_current_rows([], current_only=True, layer="silver") == []
