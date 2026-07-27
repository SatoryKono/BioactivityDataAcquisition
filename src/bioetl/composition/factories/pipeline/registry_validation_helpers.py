"""Private helpers for pipeline registry validation (TD-R-05)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig


__all__ = [
]
