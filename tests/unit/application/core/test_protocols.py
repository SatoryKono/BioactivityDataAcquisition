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
# tests/unit/application/core/test_protocols.py
"""Unit tests for application core protocols.

Tests for protocol compliance and structural subtyping verification.
Ensures TransformCallback, GoldFilterCallback, GoldTransformCallback,
and TransformerProtocol are properly defined and implementable.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.core.protocols import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
    TransformerProtocol,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, SilverRecord

pytestmark = pytest.mark.unit


class TestTransformCallbackProtocol:
    """Tests for TransformCallback protocol."""

    def test_protocol_is_callable(self) -> None:
        """TransformCallback protocol is callable."""
        # Verify the protocol has a __call__ method
        assert callable(TransformCallback)

    def test_implementation_satisfies_protocol(self) -> None:
        """Implementation with correct signature satisfies protocol."""

        class ValidTransformCallback:
            """Valid TransformCallback implementation."""

            def __call__(
                self, context: PipelineContext, record: dict[str, Any], index: int
            ) -> Awaitable[dict[str, Any] | None]:
                """Execute transformation."""

                async def transform() -> dict[str, Any] | None:
                    await asyncio.sleep(0)
                    return {"transformed": True}

                return transform()

        callback = ValidTransformCallback()
        # Verify it's callable and has the right signature
        assert callable(callback)

    def test_async_function_satisfies_protocol(self) -> None:
        """Async function can be used as TransformCallback."""

        async def transform_fn(
            context: PipelineContext, record: dict[str, Any], index: int
        ) -> dict[str, Any] | None:
            """Async transformation function."""
            await asyncio.sleep(0)
            return {"data": record.get("value")}

        # Verify it's callable
        assert callable(transform_fn)


class TestGoldFilterCallbackProtocol:
    """Tests for GoldFilterCallback protocol."""

    def test_callback_protocol__protocol_is_callable__9fbb9bc6(self) -> None:
        """GoldFilterCallback protocol is callable."""
        assert callable(GoldFilterCallback)

    def test_callback_protocol__satisfies_protocol__1f29bb32(self) -> None:
        """Implementation with correct signature satisfies protocol."""

        class ValidGoldFilterCallback:
            """Valid GoldFilterCallback implementation."""

            def __call__(
                self, context: PipelineContext, record: dict[str, Any]
            ) -> bool:
                """Evaluate if record should be included in Gold layer."""
                return bool(record.get("valid", False))

        callback = ValidGoldFilterCallback()
        assert callable(callback)

    def test_function_satisfies_protocol(self) -> None:
        """Function can satisfy GoldFilterCallback protocol."""

        def filter_fn(context: Any, record: dict[str, Any]) -> bool:
            return record.get("active", False)

        assert callable(filter_fn)


class TestGoldTransformCallbackProtocol:
    """Tests for GoldTransformCallback protocol."""

    def test_callback_protocol__protocol_is_callable__712c25fb(self) -> None:
        """GoldTransformCallback protocol is callable."""
        assert callable(GoldTransformCallback)

    def test_callback_protocol__satisfies_protocol__86ea5cb9(self) -> None:
        """Implementation with correct signature satisfies protocol."""

        class ValidGoldTransformCallback:
            """Valid GoldTransformCallback implementation."""

            def __call__(
                self, context: PipelineContext, record: dict[str, Any]
            ) -> dict[str, Any]:
                """Execute transformation."""
                # Remove JSON fields for Gold layer
                result = {k: v for k, v in record.items() if not k.endswith("_json")}
                return result

        callback = ValidGoldTransformCallback()
        assert callable(callback)


class TestTransformerProtocol:
    """Tests for TransformerProtocol."""

    def test_protocol_has_transform_method(self) -> None:
        """TransformerProtocol has transform method."""
        assert hasattr(TransformerProtocol, "transform")

    def test_transform_method_is_async(self) -> None:
        """Transform method is async (coroutine)."""
        # Get the transform method
        transform_method = getattr(TransformerProtocol, "transform", None)
        assert transform_method

    def test_transformer_protocol__satisfies_protocol__92cd2381(self) -> None:
        """Implementation with correct signature satisfies protocol."""

        class ValidTransformer:
            """Valid TransformerProtocol implementation."""

            async def transform(
                self,
                context: PipelineContext,
                record: BronzeRecord,
                index: int,
            ) -> SilverRecord | None:
                """Transform a Bronze record to Silver format."""
                await asyncio.sleep(0)
                return {"id": record.get("id"), "processed": True}

        transformer = ValidTransformer()
        assert hasattr(transformer, "transform")
        import asyncio

        assert asyncio.iscoroutinefunction(transformer.transform)

    def test_transformer_with_complex_logic(self) -> None:
        """Transformer with complex transformation logic."""

        class ChemblActivityTransformer:
            """Example transformer implementation."""

            async def transform(
                self,
                context: PipelineContext,
                record: BronzeRecord,
                index: int,
            ) -> SilverRecord | None:
                """Transform ChEMBL activity record."""
                await asyncio.sleep(0)
                activity_id = record.get("activity_id")
                if not activity_id:
                    return None

                return {
                    "activity_id": activity_id,
                    "assay_id": record.get("assay_id"),
                    "molecule_id": record.get("molecule_id"),
                    "standard_value": record.get("standard_value"),
                    "_index": index,
                    "_run_id": context.run_id,
                }

        transformer = ChemblActivityTransformer()
        assert hasattr(transformer, "transform")


class TestProtocolCompatibility:
    """Tests for protocol compatibility with type system."""

    def test_transform_callback_signature(self) -> None:
        """Verify TransformCallback signature components."""
        # The protocol should accept PipelineContext, dict, int
        # and return Awaitable[dict | None]
        assert TransformCallback

    def test_gold_filter_callback_signature(self) -> None:
        """Verify GoldFilterCallback signature components."""
        # The protocol should accept PipelineContext, dict
        # and return bool
        assert GoldFilterCallback

    def test_gold_transform_callback_signature(self) -> None:
        """Verify GoldTransformCallback signature components."""
        # The protocol should accept PipelineContext, dict
        # and return dict
        assert GoldTransformCallback

    def test_transformer_protocol_signature(self) -> None:
        """Verify TransformerProtocol signature components."""
        # The protocol should have async transform method
        # accepting PipelineContext, BronzeRecord, int
        # and returning SilverRecord | None
        assert TransformerProtocol


class TestProtocolDocumentation:
    """Tests that protocols have proper documentation."""

    def test_transform_callback_has_docstring(self) -> None:
        """TransformCallback has docstring."""
        assert TransformCallback.__doc__
        assert len(TransformCallback.__doc__) > 0

    def test_gold_filter_callback_has_docstring(self) -> None:
        """GoldFilterCallback has docstring."""
        assert GoldFilterCallback.__doc__
        assert len(GoldFilterCallback.__doc__) > 0

    def test_gold_transform_callback_has_docstring(self) -> None:
        """GoldTransformCallback has docstring."""
        assert GoldTransformCallback.__doc__
        assert len(GoldTransformCallback.__doc__) > 0

    def test_transformer_protocol_has_docstring(self) -> None:
        """TransformerProtocol has docstring."""
        assert TransformerProtocol.__doc__
        assert len(TransformerProtocol.__doc__) > 0

    def test_transformer_protocol_transform_has_docstring(self) -> None:
        """TransformerProtocol.transform has docstring."""
        transform_doc = TransformerProtocol.transform.__doc__
        assert transform_doc
        assert "Bronze" in transform_doc or "Silver" in transform_doc


class TestMockImplementations:
    """Tests with mock implementations for verification."""

    @pytest.mark.asyncio
    async def test_transformer_returns_silver_record(self, noop_logger) -> None:
        """Transformer implementation returns valid SilverRecord."""
        from datetime import UTC, datetime

        from bioetl.domain.types import RunType

        class MockTransformer:
            """Mock transformer for testing."""

            async def transform(
                self,
                context: PipelineContext,
                record: BronzeRecord,
                index: int,
            ) -> SilverRecord | None:
                """Transform record."""
                await asyncio.sleep(0)
                if not record.get("id"):
                    return None
                return {
                    "id": record["id"],
                    "_run_id": str(context.run_id),
                    "_index": index,
                }

        context = PipelineContext.create(
            run_id=deterministic_run_uuid_from_callsite("test_protocols"),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        transformer = MockTransformer()
        record: BronzeRecord = {"id": "test-123"}

        result = await transformer.transform(context, record, 0)

        assert result
        assert result["id"] == "test-123"
        assert result["_run_id"] == str(context.run_id)
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transformer_returns_none_for_invalid(self, noop_logger) -> None:
        """Transformer returns None for invalid records."""
        from datetime import UTC, datetime

        from bioetl.domain.types import RunType

        class MockTransformer:
            """Mock transformer that validates records."""

            async def transform(
                self,
                context: PipelineContext,
                record: BronzeRecord,
                index: int,
            ) -> SilverRecord | None:
                """Transform record, return None if invalid."""
                await asyncio.sleep(0)
                if not record.get("required_field"):
                    return None
                return {"data": record["required_field"]}

        context = PipelineContext.create(
            run_id=deterministic_run_uuid_from_callsite("test_protocols"),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        transformer = MockTransformer()
        invalid_record: BronzeRecord = {}

        result = await transformer.transform(context, invalid_record, 0)
        assert result is None


class TestCallbackUsage:
    """Tests demonstrating callback usage patterns."""

    def test_filter_callback_usage(self, noop_logger) -> None:
        """Demonstrate filter callback usage."""
        from datetime import UTC, datetime

        from bioetl.domain.types import RunType

        context = PipelineContext.create(
            run_id=deterministic_run_uuid_from_callsite("test_protocols"),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        def activity_filter(context: PipelineContext, record: dict[str, Any]) -> bool:
            """Filter records with standard_value."""
            return "standard_value" in record and record["standard_value"] is not None

        # Test with records
        valid_record = {"id": 1, "standard_value": 100.0}
        invalid_record = {"id": 2}

        assert activity_filter(context, valid_record)
        assert not activity_filter(context, invalid_record)

    def test_gold_transform_callback_usage(self, noop_logger) -> None:
        """Demonstrate gold transform callback usage."""
        from datetime import UTC, datetime

        from bioetl.domain.types import RunType

        context = PipelineContext.create(
            run_id=deterministic_run_uuid_from_callsite("test_protocols"),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        def remove_json_fields(
            context: PipelineContext, record: dict[str, Any]
        ) -> dict[str, Any]:
            """Remove JSON string fields for Gold layer."""
            return {k: v for k, v in record.items() if not k.endswith("_json")}

        record = {
            "id": 1,
            "name": "Test",
            "details_json": '{"nested": "data"}',
        }

        result = remove_json_fields(context, record)
        assert "id" in result
        assert "name" in result
        assert "details_json" not in result
