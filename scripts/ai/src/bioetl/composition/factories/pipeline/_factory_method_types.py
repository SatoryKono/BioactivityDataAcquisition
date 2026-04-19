#!/usr/bin/env python3
"""Private type/context helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import DataSourceCreatorProtocol
from bioetl.composition.factories.pipeline.creation_support import _PipelineCreationRequest
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.composition.observability import ObservabilityBundle

if TYPE_CHECKING:
    import pyarrow as pa
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.types import GoldSchemaType