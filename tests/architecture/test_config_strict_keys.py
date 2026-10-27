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
"""Architecture test: pipeline configs must not contain unknown keys.

PipelineYamlConfig uses ``extra="forbid"`` to reject unrecognised YAML
fields at parse time.  This test loads every expected entity pipeline YAML
through the standard loading pipeline and asserts that Pydantic validation
succeeds.

RF-001 (#12566): discovery is **fail-closed**. Unexpected load/resolve
failures on the pinned expected list fail the suite; they must not be
silently skipped via ``ValueError → continue``. An invalid unknown-key
payload must fail (not be skipped).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

pytestmark = pytest.mark.architecture

_ENTITIES_DIR = Path("configs/entities")

# Pinned expected provider_entity pipeline names (runtime entity catalog).
# Disk discovery must match this set exactly; drift = fail.
EXPECTED_ENTITY_PIPELINE_NAMES: frozenset[str] = frozenset(
    {
        "chembl_activity",
        "chembl_assay",
        "chembl_assay_parameters",
        "chembl_cell_line",
        "chembl_compound_record",
        "chembl_molecule",
        "chembl_protein_class",
        "chembl_publication",
        "chembl_publication_similarity",
        "chembl_publication_term",
        "chembl_subcellular_fraction",
        "chembl_target",
        "chembl_target_component",
        "chembl_target_protein_classification",
        "chembl_tissue",
        "composite_activity",
        "composite_assay",
        "composite_molecule",
        "composite_publication",
        "composite_target",
        "crossref_publication",
        "openalex_publication",
        "pubchem_compound",
        "pubmed_publication",
        "semanticscholar_publication",
        "uniprot_idmapping",
        "uniprot_protein",
    }
)


def _has_pipeline_section(config_path: Path) -> bool:
    """Return True only for entity configs that define pipeline mapping."""
    with open(config_path, encoding="utf-8") as handle:
        raw_obj: object = yaml.safe_load(handle)
    if not isinstance(raw_obj, dict):
        return False
    if not all(isinstance(key, str) for key in raw_obj):
        return False
    raw_map: dict[str, object] = dict(raw_obj)
    pipeline_section = raw_map.get("pipeline")
    return isinstance(pipeline_section, dict)


def discover_entity_pipeline_names(entities_dir: Path = _ENTITIES_DIR) -> list[str]:
    """Discover provider_entity names that declare a pipeline section.

    Fail-closed: does **not** call ``load_pipeline_config`` during discovery.
    Load failures are asserted separately so broken configs cannot vanish
    from parametrization via silent skip.
    """
    names: list[str] = []
    for provider_dir in sorted(entities_dir.iterdir()):
        if not provider_dir.is_dir() or provider_dir.name.startswith(("_", ".")):
            continue
        for yaml_file in sorted(provider_dir.glob("*.yaml")):
            if yaml_file.name.startswith("_"):
                continue
            if not _has_pipeline_section(yaml_file):
                continue
            names.append(f"{provider_dir.name}_{yaml_file.stem}")
    return names


def test_entity_pipeline_discovery_matches_expected_list() -> None:
    """Pinned expected list must match disk candidates (no silent drift)."""
    discovered = frozenset(discover_entity_pipeline_names())
    assert discovered == EXPECTED_ENTITY_PIPELINE_NAMES, (
        "Entity pipeline discovery drifted from the pinned expected list.\n"
        f"only_on_disk={sorted(discovered - EXPECTED_ENTITY_PIPELINE_NAMES)}\n"
        f"only_expected={sorted(EXPECTED_ENTITY_PIPELINE_NAMES - discovered)}"
    )


def test_entity_pipeline_configs_load_fail_closed() -> None:
    """Every expected entity pipeline config must load; failures are not skipped."""
    failures: list[str] = []
    for pipeline_name in sorted(EXPECTED_ENTITY_PIPELINE_NAMES):
        try:
            load_pipeline_config(pipeline_name)
        except Exception as exc:  # noqa: BLE001 — surface any resolve/load failure
            failures.append(f"{pipeline_name}: {type(exc).__name__}: {exc}")
    assert failures == [], (
        "Fail-closed discovery: expected pipeline configs failed to load:\n"
        + "\n".join(failures)
    )


@pytest.mark.parametrize(
    "pipeline_name", sorted(EXPECTED_ENTITY_PIPELINE_NAMES)
)
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
            message = (
                f"Pipeline config '{pipeline_name}' contains unknown keys: "
                + f"{extra_fields}.\n"
                + "Either add the field to the Pydantic model or remove it "
                + "from the YAML config."
            )
            pytest.fail(message)
        raise


def test_invalid_pipeline_config_unknown_key_fails() -> None:
    """Negative: unknown keys on PipelineYamlConfig must fail, not be skipped."""
    payload = {
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity_type": "activity",
        "rf001_unknown_key_must_fail": True,
    }
    with pytest.raises(ValidationError) as exc_info:
        PipelineYamlConfig.model_validate(payload)
    extra_fields = [
        error["loc"]
        for error in exc_info.value.errors()
        if error["type"] == "extra_forbidden"
    ]
    assert ("rf001_unknown_key_must_fail",) in extra_fields
