"""Sink DTO projections reject malformed dumps and respect optional fields."""

from __future__ import annotations

from types import SimpleNamespace
from pydantic import BaseModel
import pytest

from bioetl.composition.factories.dq._context_resolver_support import (
    project_sink_layer_to_extract_payload,
    extract_single_dq_config_impl,
)

pytestmark = pytest.mark.unit


def test_optional_scalar_union_is_not_treated_as_a_nested_dto():
    class NestedProjection(BaseModel):
        enabled: bool

    class Projection(BaseModel):
        count: None | int = None  # noqa: RUF036 - exercise None-first union inspection.
        dq_report: NestedProjection | None = None

    Projection.model_rebuild(_types_namespace={"NestedProjection": NestedProjection})

    sink = SimpleNamespace(
        model_dump=lambda: {
            "count": None,
            "unknown": "dropped",
            "dq_report": {"enabled": True, "unknown": "dropped"},
        }
    )
    assert project_sink_layer_to_extract_payload(sink, Projection) == {
        "count": None,
        "dq_report": {"enabled": True},
    }


def test_nonmapping_dump_fails_closed():
    class Projection(BaseModel):
        count: int

    with pytest.raises(TypeError, match="must return a mapping"):
        project_sink_layer_to_extract_payload(
            SimpleNamespace(model_dump=lambda: []), Projection
        )


def test_structural_validator_survives_invalid_pydantic_subclass_metadata():
    result = SimpleNamespace(enabled=True)
    inspected = []

    class Projection:
        @classmethod
        def model_validate(cls, payload):
            assert payload == {"allowed": True}
            return SimpleNamespace(dq_report=result)

    sink = SimpleNamespace(model_dump=lambda: {"allowed": True})
    from bioetl.composition.factories.dq import _context_resolver_support as support

    def invalid_subclass_metadata(candidate, base):
        inspected.append((candidate, base))
        raise TypeError("not Pydantic metadata")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(support, "issubclass", invalid_subclass_metadata, raising=False)
        assert (
            extract_single_dq_config_impl({"silver": sink}, "silver", Projection)
            is result
        )
    assert inspected == [(Projection, BaseModel)]
