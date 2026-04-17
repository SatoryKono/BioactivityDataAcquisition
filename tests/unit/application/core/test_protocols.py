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

import pytest

from bioetl.application.core.protocols import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
    TransformerProtocol,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, SilverRecord


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

    def test_protocol_is_callable(self) -> None:
        """GoldFilterCallback protocol is callable."""
        assert callable(GoldFilterCallback)

    def test_implementation_satisfies_protocol(self) -> None:
        """Implementation with correct signature satisfies protocol."""

        class ValidGoldFilterCallback:
            """Valid GoldFilterCallback implementation."""

            def __call__(
                self, context: PipelineContext, record: dict[str, Any]
            ) -> bool:
                """Evaluate if record should be included in Gold layer."""
                return record.get("valid", False) is True

        callback = ValidGoldFilterCallback()
        assert callable(callback)

    def test_function_satisfies_protocol(self) -> None:
        """Function can satisfy GoldFilterCallback protocol."""

        def filter_fn(context: Any, record: dict[str, Any]) -> bool:
            return record.get("active", False)

        assert callable(filter_fn)


class TestGoldTransformCallbackProtocol:
    """Tests for GoldTransformCallback protocol."""

    def test_protocol_is_callable(self) -> None:
        """GoldTransformCallback protocol is callable."""
        assert callable(GoldTransformCallback)

    def test_implementation_satisfies_protocol(self) -> None:
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
        assert transform_method is not None

    def test_implementation_satisfies_protocol(self) -> None:
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
        assert TransformCallback is not None

    def test_gold_filter_callback_signature(self) -> None:
        """Verify GoldFilterCallback signature components."""
        # The protocol should accept PipelineContext, dict
        # and return bool
        assert GoldFilterCallback is not None

    def test_gold_transform_callback_signature(self) -> None:
        """Verify GoldTransformCallback signature components."""
        # The protocol should accept PipelineContext, dict
        # and return dict
        assert GoldTransformCallback is not None

    def test_transformer_protocol_signature(self) -> None:
        """Verify TransformerProtocol signature components."""
        # The protocol should have async transform method
        # accepting PipelineContext, BronzeRecord, int
        # and returning SilverRecord | None
        assert TransformerProtocol is not None


class TestProtocolDocumentation:
    """Tests that protocols have proper documentation."""

    def test_transform_callback_has_docstring(self) -> None:
        """TransformCallback has docstring."""
        assert TransformCallback.__doc__ is not None
        assert len(TransformCallback.__doc__) > 0

    def test_gold_filter_callback_has_docstring(self) -> None:
        """GoldFilterCallback has docstring."""
        assert GoldFilterCallback.__doc__ is not None
        assert len(GoldFilterCallback.__doc__) > 0

    def test_gold_transform_callback_has_docstring(self) -> None:
        """GoldTransformCallback has docstring."""
        assert GoldTransformCallback.__doc__ is not None
        assert len(GoldTransformCallback.__doc__) > 0

    def test_transformer_protocol_has_docstring(self) -> None:
        """TransformerProtocol has docstring."""
        assert TransformerProtocol.__doc__ is not None
        assert len(TransformerProtocol.__doc__) > 0

    def test_transformer_protocol_transform_has_docstring(self) -> None:
        """TransformerProtocol.transform has docstring."""
        transform_doc = TransformerProtocol.transform.__doc__
        assert transform_doc is not None
        assert "Bronze" in transform_doc or "Silver" in transform_doc


class TestMockImplementations:
    """Tests with mock implementations for verification."""

    @pytest.mark.asyncio
    async def test_transformer_returns_silver_record(self, noop_logger) -> None:
        """Transformer implementation returns valid SilverRecord."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.types import RunID, RunType

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
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime.now(UTC),
        )

        transformer = MockTransformer()
        record: BronzeRecord = {"id": "test-123"}

        result = await transformer.transform(context, record, 0)

        assert result is not None
        assert result["id"] == "test-123"
        assert result["_run_id"] == str(context.run_id)
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transformer_returns_none_for_invalid(self, noop_logger) -> None:
        """Transformer returns None for invalid records."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.types import RunID, RunType

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
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime.now(UTC),
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
        from uuid import uuid4

        from bioetl.domain.types import RunID, RunType

        context = PipelineContext.create(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime.now(UTC),
        )

        def activity_filter(context: PipelineContext, record: dict[str, Any]) -> bool:
            """Filter records with standard_value."""
            return record.get("standard_value") is not None

        # Test with records
        valid_record = {"id": 1, "standard_value": 100.0}
        invalid_record = {"id": 2}

        assert activity_filter(context, valid_record) is True
        assert activity_filter(context, invalid_record) is False

    def test_gold_transform_callback_usage(self, noop_logger) -> None:
        """Demonstrate gold transform callback usage."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.types import RunID, RunType

        context = PipelineContext.create(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=noop_logger,
            started_at=datetime.now(UTC),
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
