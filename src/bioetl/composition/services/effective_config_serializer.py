"""Composition facade. Implementation lives in `bioetl.domain.config.effective_config_serializer` (#11241)."""

from __future__ import annotations

from bioetl.domain.config.effective_config_serializer import (
    EffectiveConfigSerializer,
    create_effective_config_serializer,
)

__all__ = ['EffectiveConfigSerializer', 'create_effective_config_serializer']
