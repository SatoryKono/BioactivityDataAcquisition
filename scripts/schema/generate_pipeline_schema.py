#!/usr/bin/env python3
"""Generate JSON Schema from Pydantic pipeline configuration models.

Replaces the hand-maintained configs/_schema/pipeline.json and
configs/_schema/composite.json with auto-generated schemas derived
from PipelineYamlConfig and CompositeConfigFileSchema Pydantic models.

Usage:
    python -m scripts.schema generate-pipeline [--check]

Exit codes:
    0 - Schemas generated (or up-to-date with --check)
    1 - Schemas out of date (--check mode only)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
from bioetl.infrastructure.schemas.dq_config import DQConfigFile
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

project_root = Path(__file__).resolve().parents[2]
SCHEMA_DIR = project_root / "configs" / "_schema"

SCHEMAS = {
    "pipeline.json": PipelineYamlConfig,
    "composite.json": CompositeConfigFileSchema,
    "source.json": SourceYamlConfig,
    "dq.json": DQConfigFile,
}


def _normalize_newlines(content: str) -> str:
    """Normalize line endings for cross-platform stable comparisons."""
    return content.replace("\r\n", "\n").replace("\r", "\n")


def generate_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Generate JSON Schema dict from a Pydantic model class."""
    schema = model_cls.model_json_schema()
    # Add JSON Schema meta-fields
    schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
    return schema


def write_schema(path: Path, schema: dict[str, Any]) -> None:
    """Write schema to file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pipeline JSON schemas")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if schemas are up-to-date (exit 1 if stale)",
    )
    args = parser.parse_args()

    stale = False

    for filename, model_cls in SCHEMAS.items():
        schema = generate_schema(model_cls)
        out_path = SCHEMA_DIR / filename
        new_content = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

        if args.check:
            if out_path.exists():
                existing = out_path.read_text(encoding="utf-8")
                if _normalize_newlines(existing) == _normalize_newlines(new_content):
                    sys.stdout.write(f"  OK   {out_path}\n")
                    continue
            sys.stderr.write(f"  STALE {out_path}\n")
            stale = True
        else:
            write_schema(out_path, schema)
            sys.stdout.write(f"  Generated {out_path}\n")

    if args.check and stale:
        sys.stderr.write(
            "\nSchemas are out of date. Run: python -m scripts.schema generate-pipeline\n"
        )
        return 1

    if not args.check:
        sys.stdout.write("\nAll schemas generated from Pydantic models.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
