"""Canonical pipeline assembly module.

Provides the generic pipeline factory and runner assembly entrypoints.
The legacy ``assembler`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)

__all__ = ["GenericPipelineFactory", "assemble_runner", "create_pipeline_factory"]
