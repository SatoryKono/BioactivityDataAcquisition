"""Cached Bronze binding preserves type, identity, and explicit refusal behavior."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders._cached_bronze_binding import (
    bind_cached_bronze_context,
)
from bioetl.domain.context import CachedBronzeContext

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class FrozenContext:
    name: str = "retained"
    cached_bronze: CachedBronzeContext | None = None


def test_equal_binding_retains_context_identity():
    cached = CachedBronzeContext.disabled()
    context = FrozenContext(cached_bronze=cached)
    assert bind_cached_bronze_context(context, cached) is context


def test_frozen_context_is_replaced_without_mutating_original():
    context = FrozenContext()
    cached = CachedBronzeContext.disabled()
    result = bind_cached_bronze_context(context, cached)
    assert isinstance(result, FrozenContext)
    assert result.cached_bronze is cached
    assert result.name == context.name
    assert context.cached_bronze is None


def test_dataclass_type_is_rejected_instead_of_being_mutated():
    with pytest.raises(TypeError, match="dataclass instance"):
        bind_cached_bronze_context(FrozenContext, CachedBronzeContext.disabled())
    assert FrozenContext.cached_bronze is None


def test_mutable_context_keeps_identity_and_receives_binding():
    context = SimpleNamespace(name="retained")
    cached = CachedBronzeContext.disabled()
    result = bind_cached_bronze_context(context, cached)
    assert result is context
    assert result.cached_bronze is cached
    assert result.name == "retained"


def test_host_setter_can_supply_binding_when_descriptor_has_no_setter():
    class Host:
        @property
        def cached_bronze(self):
            return self.__dict__.get("bound")

        def __setattr__(self, name, value):
            if name != "cached_bronze":
                raise AttributeError(name)
            self.__dict__["bound"] = value

    context = Host()
    cached = CachedBronzeContext.disabled()
    assert bind_cached_bronze_context(context, cached) is context
    assert context.cached_bronze is cached


def test_immutable_host_fails_with_actionable_type_error():
    class Host:
        __slots__ = ()

    with pytest.raises(
        TypeError, match="does not support cached_bronze binding"
    ) as error:
        bind_cached_bronze_context(Host(), CachedBronzeContext.disabled())
    assert isinstance(error.value.__cause__, AttributeError)
