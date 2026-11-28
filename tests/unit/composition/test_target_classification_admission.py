"""Admission of the shipped IUPHAR profile at the three target writer entry points."""

from pathlib import Path
from shutil import copytree
from types import SimpleNamespace

import pytest

from bioetl.composition.bootstrap.assembly import storage, target_classification_runtime
from bioetl.composition.bootstrap.assembly.target_classification_identity import (
    load_target_aware_pipeline_config,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from bioetl.infrastructure.config.config_root import resolve_repo_relative_path
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.target_classification_config import (
    TargetClassificationYamlConfig,
)

pytestmark = pytest.mark.unit


def test_shipped_profile_loads_from_only_versioned_configuration(tmp_path):
    config = load_pipeline_config("chembl_target")
    classification = config.target_classification
    assert classification.mode == "enrich"
    assert classification.table_contract == "3.1.0"
    assert classification.snapshot_manifest_sha256 == (
        "b02152d8cce606caa43915f9039c2275b99a098861e52acf47643a128640dd15"
    )
    reference = Path(classification.snapshot_manifest)
    assert reference.parts[0] == "configs"
    isolated = tmp_path / reference
    copytree(resolve_repo_relative_path(str(reference)).parent, isolated.parent)
    profile = storage.load_target_runtime_profile(config, dependency_root=tmp_path)
    assert profile.profile_uri == isolated.as_uri()
    assert profile.profile_sha256 == classification.snapshot_manifest_sha256
    assert profile.acceptance_sha256 is not None


@pytest.mark.parametrize("entry", ["direct", "workflow", "composite"])
@pytest.mark.parametrize(
    ("fault", "error", "message"),
    [
        ("off", ValueError, "off requires exact replay"),
        ("missing", FileNotFoundError, "profile.json"),
        ("digest", ValueError, "digest mismatch"),
    ],
)
def test_invalid_target_run_stops_before_outputs(
    tmp_path, monkeypatch, entry, fault, error, message
):
    config = load_pipeline_config("chembl_target")
    profile_path = tmp_path / "profile.json"
    if fault == "off":
        classification = TargetClassificationYamlConfig(mode="off")
    else:
        if fault == "digest":
            profile_path.write_bytes(b"{}")
        classification = config.target_classification.model_copy(
            update={"snapshot_manifest": str(profile_path)}
        )
    config = config.model_copy(update={"target_classification": classification})
    settings = Settings(test_mode=True, data_dir=tmp_path / "data", _env_file=None)

    def load_config(name):
        assert name == "chembl_target"
        return config

    monkeypatch.setattr(storage, "load_pipeline_config", load_config)
    monkeypatch.setattr(
        target_classification_runtime, "load_pipeline_config", load_config
    )
    with pytest.raises(error, match=message):
        if entry == "direct":
            resolved = load_target_aware_pipeline_config(
                "chembl_target", load_config, lambda _: None
            )
            target_classification_runtime.validate_target_runtime_dependency(resolved)
        elif entry == "workflow":
            workflow = WorkflowConfig(
                "target", steps=(WorkflowStepConfig("target", "chembl_target"),)
            )
            storage.preflight_workflow_target_dependencies(
                workflow, {}, settings=settings
            )
        else:
            target_classification_runtime.build_composite_target_classification_stage(
                SimpleNamespace(name="composite_target"), settings=settings
            )
    for layer in ("silver", "gold"):
        assert not (tmp_path / "data" / "output" / layer).exists()
