# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for strict metadata sidecar and lineage-fragment publication guards."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.infrastructure.storage.bronze.side_effects_mixin import (
    BronzeWriterSideEffectsMixin,
)
from bioetl.infrastructure.storage.gold.metadata_operations import (
    _GoldMetadataWriteRequest,
    _PreparedGoldMetadataWrite,
    _persist_gold_metadata_write,
)
from bioetl.infrastructure.storage.lineage_persistence import (
    lineage_fragment_publication_required,
    persist_lineage_fragment_if_present,
)
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_prepared_silver_metadata_write_operation,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverMetadataWriteOperation,
)
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)


def _strict_coordinator() -> SimpleNamespace:
    return SimpleNamespace(
        run_context=SimpleNamespace(
            exact_replay=False,
            required_persistence_profile="replay_ready",
        )
    )


@pytest.mark.unit
def test_lineage_publication_required_for_strict_profile() -> None:
    assert lineage_fragment_publication_required(_strict_coordinator()) is True


@pytest.mark.unit
def test_lineage_publication_not_required_for_unset_magicmock_context() -> None:
    assert lineage_fragment_publication_required(MagicMock()) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_required_lineage_publication_fails_without_store() -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="silver:strict-fragment",
        layer="silver",
        logical_name="chembl.activity",
    )

    with pytest.raises(RuntimeError, match="requires a lineage store"):
        await persist_lineage_fragment_if_present(
            lineage_store=None,
            lineage_fragment=fragment,
            pipeline_name="chembl_activity",
            layer="silver",
            required=True,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_required_lineage_publication_fails_without_fragment() -> None:
    with pytest.raises(RuntimeError, match="requires a lineage fragment"):
        await persist_lineage_fragment_if_present(
            lineage_store=MagicMock(),
            lineage_fragment=None,
            pipeline_name="chembl_activity",
            layer="silver",
            required=True,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bronze_strict_metadata_write_requires_lineage_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="bronze:strict-fragment",
        layer="bronze",
        logical_name="chembl.activity",
    )

    class _Host(BronzeWriterSideEffectsMixin):
        pass

    host = _Host()
    host._metadata_writer = SimpleNamespace(write_bronze_metadata=AsyncMock())
    host._metadata_coordinator = _strict_coordinator()
    host._lineage_store = None
    host._metrics = None
    host._flat_structure = False
    host.base_path = tmp_path
    host.logger = MagicMock()

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.side_effects_mixin.prepare_bronze_metadata_write",
        lambda _host, _request: SimpleNamespace(
            metadata_base_path=tmp_path,
            metadata=object(),
            lineage_fragment=fragment,
        ),
    )

    with pytest.raises(RuntimeError, match="requires a lineage store"):
        await host._maybe_write_bronze_metadata(
            run_id="run-1",
            run_type=SimpleNamespace(value="backfill"),
            provider="chembl",
            entity="activity",
            batch_id="batch-1",
            record_count=1,
            compressed_size=10,
            relative_path="chembl/activity/file.jsonl.zst",
            ingestion_ts=object(),
            duration=1.0,
            source_metadata=None,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_silver_strict_metadata_write_requires_lineage_store() -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="silver:strict-fragment",
        layer="silver",
        logical_name="chembl.activity",
    )
    host = AsyncMock()
    host._metadata_coordinator = _strict_coordinator()
    host._lineage_store = None
    host._metrics = None
    host._write_silver_metadata_file = AsyncMock()
    prepared = _PreparedSilverMetadataWriteOperation(
        request=_SilverMetadataWriteRequest(
            table_path="/tmp/silver/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        ),
        provider_name="chembl",
        entity_name="activity",
        metadata=MagicMock(),
        lineage_fragment=fragment,
    )

    with pytest.raises(RuntimeError, match="requires a lineage store"):
        await _execute_prepared_silver_metadata_write_operation(host, prepared)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gold_strict_metadata_write_requires_lineage_store() -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="gold:strict-fragment",
        layer="gold",
        logical_name="chembl.compound",
    )
    host = AsyncMock()
    host._metadata_coordinator = _strict_coordinator()
    host._lineage_store = None
    host._metrics = None
    host._write_gold_metadata_file = AsyncMock()
    prepared = _PreparedGoldMetadataWrite(
        request=_GoldMetadataWriteRequest(
            table_path="/tmp/gold/chembl/compound",
            table_name="chembl.compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        ),
        provider_name="chembl",
        entity_name="compound",
        metadata=MagicMock(),
        lineage_fragment=fragment,
    )

    with pytest.raises(RuntimeError, match="requires a lineage store"):
        await _persist_gold_metadata_write(host, prepared)
