"""BioETL Pipeline Scaffolder.

Automates the creation of new data adapters and pipelines following
the project's Hexagonal Architecture (Ports & Adapters).
"""

import os
from pathlib import Path

import click

# Templates for new files
CLIENT_TEMPLATE = '''"""{source_title} Adapter.

Implements DataSourcePort for {source_title}.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator

from bioetl.infrastructure.adapters.base import AsyncHttpDataSource

if TYPE_CHECKING:
    from bioetl.domain.models import PipelineContext

class {source_title}Adapter(AsyncHttpDataSource):
    """Adapter for {source_title} API."""

    async def fetch_incremental(
        self, context: PipelineContext, checkpoint: Any = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from {source_title} incrementally."""
        # TODO: Implement API call
        yield {{}}
'''

PIPELINE_TEMPLATE = '''"""{source_title} {entity_title} Pipeline.

Orchestrates data flow from {source_title} to Delta Lake.
"""

from bioetl.application.pipelines.base import BasePipeline

class {source_title}{entity_title}Pipeline(BasePipeline):
    """Pipeline for {source_title} {entity_title} data."""

    def transform(self, df):
        """Clean and normalize data."""
        # TODO: Implement transformation
        return df
'''

CONFIG_TEMPLATE = """# {source}_{entity} pipeline configuration
name: "{source}_{entity}"
source: "{source}"
entity: "{entity}"
batch_size: 100
"""


@click.command()
@click.option("--source", required=True, help="Source name (e.g., chembl)")
@click.option("--entity", required=True, help="Entity name (e.g., activity)")
def scaffold(source, entity):
    """Scaffold a new BioETL adapter and pipeline."""
    source_title = source.capitalize()
    entity_title = entity.capitalize()

    # 1. Create Infrastructure Adapter
    adapter_dir = Path(f"src/bioetl/infrastructure/adapters/{source}")
    adapter_dir.mkdir(parents=True, exist_ok=True)

    (adapter_dir / "client.py").write_text(
        CLIENT_TEMPLATE.format(source_title=source_title)
    )
    (adapter_dir / "__init__.py").write_text(
        f"from .client import {source_title}Adapter"
    )
    (adapter_dir / "models.py").write_text("# Pydantic models for API responses")

    # 2. Create Application Pipeline
    pipeline_file = Path(f"src/bioetl/application/pipelines/{source}_{entity}.py")
    pipeline_file.write_text(
        PIPELINE_TEMPLATE.format(source_title=source_title, entity_title=entity_title)
    )

    # 3. Create Config
    config_file = Path(f"configs/pipelines/{source}_{entity}.yaml")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(CONFIG_TEMPLATE.format(source=source, entity=entity))

    click.echo(f"Successfully scaffolded {source}_{entity} pipeline!")
    click.echo(f"Created adapter: {adapter_dir}")
    click.echo(f"Created pipeline: {pipeline_file}")
    click.echo(f"Created config: {config_file}")


if __name__ == "__main__":
    scaffold()
