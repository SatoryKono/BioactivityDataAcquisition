#!/usr/bin/env python3
"""
Pipeline Scaffolding Tool.

Generates boilerplate code for new BioETL pipelines following standard patterns.
Creates:
1. Pipeline Configuration (YAML)
2. Pipeline Class (Python)
3. Transformer Class (Python)
4. Unit Test Skeleton (Python)

Usage:
    python src/tools/create_pipeline.py --provider <name> --entity <name> [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path
from string import Template

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Templates
YAML_TEMPLATE = Template(
    """# Unified Entity Configuration for ${provider}/${entity}
version: 1.0.0
provider: ${provider}
entity: ${entity}

pipeline:
  pipeline_name: ${provider}_${entity}
  provider: ${provider}
  entity_type: ${entity}
  description: ${pipeline_description}
  business_primary_keys:
    - ${entity}_id
  silver_table: ${provider}_${entity}
  gold_table: ${provider}_${entity}
  batch_size: 100

schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
    - name: system
      fields:
        - entity_id
        - content_hash
        - _source
        - _index
    - name: business
      fields:
        - ${entity}_id
    - name: dq
      pattern: ^_dq_
  silver:
    include_groups: [system, business, dq]
    exclude_fields: []
  gold:
    include_groups: [system, business]
    exclude_fields: [_dq_*, _index]

quality:
  version: 1.0.0
  provider: ${provider}
  entity: ${entity}
  field_validations:
    - field: ${entity}_id
      type: required
      nullable: false
      error_message: ${entity}_id is required

filters:
  version: 1.0.0
  provider: ${provider}
  entity: ${entity}
  input_filter:
    enabled: false
  extraction_params: {}
  silver_filters:
    columns: {}
    ranges: {}
    drop_nulls: []
  gold_filters:
    required_fields:
      - ${entity}_id
    columns: {}
    ranges: {}
    drop_nulls: []

contracts:
  primary_key:
    - ${entity}_id
  merge_keys:
    - ${entity}_id
  rename_map:
    source: _source
  hash_include: []
  hash_exclude:
    - _dq_error
    - _dq_warn
    - _index
"""
)

PIPELINE_TEMPLATE = Template(
    '''"""${provider_title} ${entity_title} Pipeline.

Defines the pipeline structure for ${provider_title} ${entity_title} data.
Transformation logic is delegated to ${entity_title}Transformer.

Registration: Add a PipelineFactoryConfig entry to
``bioetl.composition.factories.pipeline.registry_manifest`` and call
``register_all_pipelines()`` at application startup.
"""

from __future__ import annotations

from bioetl.application.pipelines.generic import GenericPipeline

# ${provider_title} ${entity_title} uses GenericPipeline via GenericPipelineFactory.
# Register by adding PipelineFactoryConfig to registry_manifest.py.
# See: src/bioetl/composition/factories/pipeline/registry_manifest.py
'''
)

TRANSFORMER_TEMPLATE = Template(
    '''"""${provider_title} ${entity_title} Transformer.

Handles transformation from Bronze (JSON) to Silver (Standardized) format.
"""

from __future__ import annotations

from typing import Any

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.context import PipelineContext


class ${class_prefix}Transformer(BaseTransformer):
    """Transformer for ${provider_title} ${entity_title} records."""

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Transform a single raw record.

        Args:
            context: Pipeline context (run_id, etc.)
            record: Raw dictionary from Bronze layer
            index: Sequential index of the record in the pipeline run.

        Returns:
            Transformed dictionary or None to skip.
        """
        # Implement mapping logic
        # Example:
        # if "id" not in record:
        #     return None

        return {
            "${entity}_id": record.get("id"),
            "ingestion_ts": context.started_at.isoformat(),
            # Add other fields here
        }

    def _get_gold_filter_config(self) -> dict[str, Any]:
        """Get configuration for Gold layer filtering."""
        # If needed, override to provide custom filter config
        return super()._get_gold_filter_config()
'''
)

TEST_TEMPLATE = Template(
    '''"""Unit tests for ${provider_title} ${entity_title} Pipeline."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from bioetl.application.pipelines.${provider}.${entity} import ${class_prefix}Pipeline
from bioetl.application.pipelines.${provider}.transformer import ${class_prefix}Transformer
from bioetl.domain.context import PipelineContext


@pytest.fixture
def transformer():
    return ${class_prefix}Transformer(provider="${provider}")

@pytest.mark.unit
class Test${class_prefix}Transformer:
    """Tests for ${class_prefix}Transformer."""

    @pytest.mark.asyncio
    async def test_transform_record(self, transformer):
        """Test basic record transformation."""
        context = MagicMock(spec=PipelineContext)
        # Setup context.started_at etc.

        raw_record = {"id": "123", "data": "value"}
        result = await transformer._transform_impl(context, raw_record, 0)

        assert result is not None
        assert result["${entity}_id"] == "123"
'''
)


def to_pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def to_title_case(snake_str: str) -> str:
    """Convert snake_case to Title Case."""
    return " ".join(word.capitalize() for word in snake_str.split("_"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BioETL Pipeline Boilerplate")
    parser.add_argument(
        "--provider", required=True, help="Provider name (snake_case, e.g., 'chembl')"
    )
    parser.add_argument(
        "--entity", required=True, help="Entity name (snake_case, e.g., 'activity')"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plans without creating files"
    )

    args = parser.parse_args()

    provider = args.provider.lower()
    entity = args.entity.lower()

    # Validation
    if not provider.replace("_", "").isalnum():
        logger.error(
            "Error: Provider name '%s' must be alphanumeric/snake_case", provider
        )
        return 1
    if not entity.replace("_", "").isalnum():
        logger.error("Error: Entity name '%s' must be alphanumeric/snake_case", entity)
        return 1

    # Derived names
    pipeline_name = f"{provider}_{entity}"
    provider_title = to_title_case(provider)
    entity_title = to_title_case(entity)
    class_prefix = f"{to_pascal_case(provider)}{to_pascal_case(entity)}"

    # Paths
    root_dir = Path("src/bioetl")
    config_dir = Path("configs/entities") / provider
    pipeline_dir = root_dir / "application/pipelines" / provider
    test_dir = Path("tests/unit/pipelines") / provider

    files_to_create = {
        config_dir / f"{entity}.yaml": YAML_TEMPLATE.substitute(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            pipeline_description=(
                f"{provider_title} {entity_title} unified entity pipeline"
            ),
        ),
        pipeline_dir / f"{entity}.py": PIPELINE_TEMPLATE.substitute(
            provider=provider,
            entity=entity,
            provider_title=provider_title,
            entity_title=entity_title,
            pipeline_name=pipeline_name,
            class_prefix=class_prefix,
        ),
        pipeline_dir / "transformer.py": TRANSFORMER_TEMPLATE.substitute(
            provider=provider,
            entity=entity,
            provider_title=provider_title,
            entity_title=entity_title,
            class_prefix=class_prefix,
        ),
        test_dir / f"test_{entity}_pipeline.py": TEST_TEMPLATE.substitute(
            provider=provider,
            entity=entity,
            provider_title=provider_title,
            entity_title=entity_title,
            class_prefix=class_prefix,
        ),
    }

    # Check for existing transformer file to avoid overwrite if multiple entities per provider
    # If transformer.py exists, suggest appending or creating entity_transformer.py
    # For simplicity in this tool, if transformer.py exists, we will use {entity}_transformer.py
    transformer_path = pipeline_dir / "transformer.py"
    if transformer_path.exists() and not args.dry_run:
        new_transformer_path = pipeline_dir / f"{entity}_transformer.py"
        content = files_to_create.pop(transformer_path)
        files_to_create[new_transformer_path] = content
        logger.info(
            "Note: %s exists. Creating %s instead.",
            transformer_path,
            new_transformer_path,
        )

    if args.dry_run:
        logger.info("Dry Run - Files to be created:")
        for path in files_to_create:
            logger.info("- %s", path)
        return 0

    # Create directories and files
    for path, content in files_to_create.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Create __init__.py if missing in parent dir
        init_file = path.parent / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        if path.exists():
            logger.info("Skipping %s: File already exists", path)
            continue

        with path.open("w") as f:
            f.write(content)
        logger.info("Created %s", path)

    logger.info("")
    logger.info("Done! Don't forget to:")
    logger.info("1. Implement transformation logic in transformer.py")
    logger.info(
        "2. Define validation schema in src/bioetl/infrastructure/schemas/gold.py"
    )
    logger.info(
        "3. Register any new factories if needed (though GenericPipelineFactory should handle it)"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
