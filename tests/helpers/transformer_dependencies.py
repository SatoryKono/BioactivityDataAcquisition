"""Test helper for explicit transformer collaborator wiring."""

from __future__ import annotations

import dataclasses
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
    dependencies = build_test_transformer_dependencies()

    # Route context-specific kwargs to the dependency bundle
    context_keys = {
        "tracer",
        "metrics",
        "identity_service",
        "pii_hasher",
        "data_normalizer",
        "contract_policy",
        "structural_policy",
    }
    context_kwargs = {k: v for k, v in kwargs.items() if k in context_keys}
    for k in context_kwargs:
        kwargs.pop(k)

    if context_kwargs:
        dependencies = dataclasses.replace(dependencies, **context_kwargs)

    return transformer_class(
        dependencies=dependencies,
        **kwargs,
    )
