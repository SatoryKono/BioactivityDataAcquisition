"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.interfaces.factories.chembl_activity import (
    ChEMBLActivityPipelineFactory,
)
from bioetl.interfaces.factories.pubchem_compound import (
    PubChemCompoundPipelineFactory,
)
from bioetl.interfaces.factories.uniprot_protein import (
    UniProtProteinPipelineFactory,
)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

# Explicit exports for test mocking
__all__ = [
    "bootstrap_logger",
    "bootstrap_pipeline",
    "ChemblAdapter",
    "UnifiedHTTPClient",
    "S3Checkpoint",
    "ChEMBLActivityPipelineFactory",
    "create_redis_client",
    "get_aws_credentials",
    "StorageAdapter",
    "RedisDistributedLock",
    "PrometheusMetrics",
    "UnifiedQuarantine",
    "BronzeWriter",
    "DeltaWriter",
    "GoldWriter",
    "bootstrap_quarantine",
    "bootstrap_checkpoint",
]

if TYPE_CHECKING:
    import structlog
    from bioetl.domain.types import RunType
    from bioetl.domain.ports import QuarantinePort, CheckpointPort


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine service for CLI inspection."""
    settings = get_settings()
    return UnifiedQuarantine(
        s3_bucket=settings.s3.bucket_bronze,  # Using bronze bucket for quarantine dumps by default
        fs_impl=None  # Use default S3FileSystem
    )


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint service for CLI inspection."""
    settings = get_settings()
    return S3Checkpoint(
        bucket=settings.s3.bucket_checkpoints,
        pipeline_name=pipeline_name,
        endpoint_url=settings.aws.endpoint_url
    )


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


def bootstrap_pipeline(
    pipeline_name: str,
    run_id: UUID,
    run_type: RunType,
    resume: bool,
    limit: int | None,
) -> BasePipeline:
    """
    Composition Root: Assembles and returns a fully configured pipeline instance.
    """
    settings = get_settings()
    logger = bootstrap_logger(pipeline=pipeline_name, run_id=run_id)

    runtime_config = PipelineRuntimeConfig(
        run_type=run_type, resume=resume, limit=limit
    )

    if pipeline_name == "chembl_activity":
        pipeline = ChEMBLActivityPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
    elif pipeline_name == "pubchem_compound":
        pipeline = PubChemCompoundPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
    elif pipeline_name == "uniprot_protein":
        pipeline = UniProtProteinPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
    else:
        raise ValueError(f"Unknown pipeline name: {pipeline_name}")

    return pipeline
