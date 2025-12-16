"""
Template for a Factory.
Location: src/bioetl/infrastructure/factories/<provider>.py
"""
from typing import TYPE_CHECKING

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.factories.clients import create_redis_client, get_aws_credentials
from bioetl.infrastructure.factories.storage import StorageAdapter
# Import specific adapter
# from bioetl.infrastructure.adapters.{{provider}}.client import {{Provider}}Adapter

if TYPE_CHECKING:
    import structlog

class {{Provider}}PipelineFactory:
    """Factory for {{Provider}} pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        **kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""

        # 1. HTTP Client
        http_client = UnifiedHTTPClient(
            TokenBucket(rate=5.0, capacity=10),
            CircuitBreaker(provider="{{provider}}")
        )

        # 2. Data Source Adapter
        # data_source = {{Provider}}Adapter(http_client=http_client)
        data_source = None # Replace with actual adapter

        # 3. Storage & Infrastructure (Standard setup)
        # Reuse standard factory logic or copy from existing factories
        # ...

        return PipelineServices(
            data_source=data_source,
            # storage=storage,
            # lock=lock,
            # checkpoint=checkpoint,
            # quarantine=quarantine,
            # metrics=metrics,
            logger=logger,
        )
