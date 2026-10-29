"""Sink DTO projections reject malformed dumps and respect optional fields."""

from types import SimpleNamespace
from pydantic import BaseModel
import pytest

from bioetl.composition.factories.dq._context_resolver_support import (
    project_sink_layer_to_extract_payload,
    extract_single_dq_config_impl,
)

pytestmark = pytest.mark.unit


def test_optional_scalar_union_is_not_treated_as_a_nested_dto():
    class Projection(BaseModel):
        count: None | int = None  # noqa: RUF036 - exercise None-first union inspection.

    sink = SimpleNamespace(model_dump=lambda: {"count": None, "unknown": "dropped"})
    assert project_sink_layer_to_extract_payload(sink, Projection) == {"count": None}


def test_nonmapping_dump_fails_closed():
    class Projection(BaseModel):
        count: int

    with pytest.raises(TypeError, match="must return a mapping"):
        project_sink_layer_to_extract_payload(
            SimpleNamespace(model_dump=lambda: []), Projection
        )


def test_structural_validator_survives_invalid_pydantic_subclass_metadata():
    result = SimpleNamespace(enabled=True)

    class Meta(type):
        def __getattr__(cls, name):
            if name == "__pydantic_decorators__":
                raise TypeError("not Pydantic metadata")
            raise AttributeError(name)

    class Projection(metaclass=Meta):
        @classmethod
        def model_validate(cls, payload):
            assert payload == {"allowed": True}
            return SimpleNamespace(dq_report=result)

    sink = SimpleNamespace(model_dump=lambda: {"allowed": True})
    assert (
        extract_single_dq_config_impl({"silver": sink}, "silver", Projection) is result
    )
