# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture gate: entity configs must declare explicit sink.silver sections."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"


def _standard_entity_configs() -> list[Path]:
    configs: list[Path] = []
    for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
        if path.name.startswith("_"):
            continue
        if path.parent.name == "composite":
            continue
        configs.append(path)
    return configs


@pytest.mark.architecture
@pytest.mark.parametrize(
    "config_path",
    _standard_entity_configs(),
    ids=lambda path: path.relative_to(PROJECT_ROOT).as_posix(),
)
def test_entity_config_declares_explicit_sink_silver_section(
    config_path: Path,
) -> None:
    """Unified entity configs must declare pipeline.sink.silver explicitly."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    provider = str(payload.get("provider", "")).strip()
    entity = str(payload.get("entity", "")).strip()
    assert provider and entity, (
        f"{config_path.as_posix()}: missing provider/entity for effective config loading"
    )
    pipeline = load_pipeline_config_from_root(
        f"{provider}_{entity}",
        configs_root=PROJECT_ROOT / "configs",
    ).model_dump(mode="python")
    sink = pipeline.get("sink")
    assert isinstance(sink, dict), f"{config_path.as_posix()}: missing pipeline.sink"
    silver = sink.get("silver")
    assert isinstance(silver, dict), (
        f"{config_path.as_posix()}: missing explicit pipeline.sink.silver section"
    )
