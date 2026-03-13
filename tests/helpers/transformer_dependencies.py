"""Test helper for explicit transformer collaborator wiring."""

from __future__ import annotations

from typing import Any, TypeVar

from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies as build_test_transformer_dependencies,
)

TTransformer = TypeVar("TTransformer")

__all__ = [
    "build_test_transformer_dependencies",
    "instantiate_test_transformer",
]


def instantiate_test_transformer(
    transformer_class: type[TTransformer],
    /,
    **kwargs: Any,
) -> TTransformer:
    """Instantiate a transformer using composition-owned default collaborators."""
    return transformer_class(
        dependencies=build_test_transformer_dependencies(),
        **kwargs,
    )
