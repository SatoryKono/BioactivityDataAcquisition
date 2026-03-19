"""Architecture test: pipeline configs must not contain unknown keys.

PipelineYamlConfig uses ``extra="forbid"`` to reject unrecognised YAML
fields at parse time.  This test loads every pipeline YAML through the
standard loading pipeline and asserts that Pydantic validation succeeds.

If a new key is added to a YAML file without a corresponding model field,
this test will fail with a ``ValidationError`` listing the unknown key.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.config import load_pipeline_config

# Discover all unified entity configs (provider/entity.yaml → provider_entity)
_ENTITIES_DIR = Path("configs/entities")

_PIPELINE_NAMES: list[str] = []
for provider_dir in sorted(_ENTITIES_DIR.iterdir()):
    if not provider_dir.is_dir() or provider_dir.name.startswith(("_", ".")):
        continue
    for yaml_file in sorted(provider_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        pipeline_name = f"{provider_dir.name}_{yaml_file.stem}"
        _PIPELINE_NAMES.append(pipeline_name)


@pytest.mark.parametrize("pipeline_name", _PIPELINE_NAMES)
def test_pipeline_config_no_unknown_keys(pipeline_name: str) -> None:
    """Loading a pipeline config must not raise ValidationError for extra keys.

    This test acts as a CI gate: if someone adds a typo or an unrecognised
    field to a pipeline YAML, Pydantic ``extra="forbid"`` will reject it.
    """
    try:
        load_pipeline_config(pipeline_name)
    except ValidationError as exc:
        extra_fields = [
            e["loc"] for e in exc.errors() if e["type"] == "extra_forbidden"
        ]
        if extra_fields:
            pytest.fail(
                f"Pipeline config '{pipeline_name}' contains unknown keys: "
                f"{extra_fields}.\n"
                f"Either add the field to the Pydantic model or remove it "
                f"from the YAML config."
            )
        raise  # Re-raise non-extra validation errors
