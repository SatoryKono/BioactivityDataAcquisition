"""Deployment admission uses real YAML loading and real writer destinations."""

from pathlib import Path
from dataclasses import replace
from shutil import copytree, ignore_patterns
from types import SimpleNamespace

import pytest
import yaml

from bioetl.composition.bootstrap import (
    target_migration_binding as migration,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
)
from iuphar_target_class.stage0.io import sha256_file


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    copytree(
        root / "configs", tmp_path / "configs", ignore=ignore_patterns(".env*", "*.env")
    )
    canonical = tmp_path / "configs/entities/chembl/target.yaml"
    document = yaml.safe_load(canonical.read_bytes())
    document["pipeline"]["target_classification"] = {
        "mode": "enrich",
        "snapshot_manifest": str(tmp_path / "profile.json"),
        "snapshot_manifest_sha256": "a" * 64,
    }
    candidate = tmp_path / "deployment.yaml"
    candidate.write_text(yaml.safe_dump(document), encoding="utf-8")
    settings = Settings(_env_file=None, test_mode=True, data_dir=tmp_path / "data")
    paths = TargetMigrationPaths(
        tmp_path,
        settings.silver_path / "chembl/target",
        settings.gold_path / "chembl/target",
        settings.gold_path / "chembl/assay",
        canonical,
        tmp_path / "candidate-silver",
        tmp_path / "candidate-gold",
        candidate,
        tmp_path / "backup",
    )
    # Profile admission has its own source/receipt integration suite. This fixture
    # isolates the actual public config loader and writer-path resolution.
    monkeypatch.setattr(
        migration,
        "load_target_runtime_profile",
        lambda _: SimpleNamespace(profile_sha256="a" * 64),
    )
    return paths, settings, document


def test_real_loader_binds_canonical_destinations(deployment):
    paths, settings, _ = deployment
    binding = migration.bind_target_deployment(
        paths, settings=settings, configs_root=paths.workspace / "configs"
    )
    assert binding.silver_path == str(paths.silver.resolve())
    assert binding.gold_path == str(paths.gold.resolve())
    assert binding.deployment_config_sha256 == sha256_file(paths.candidate_config)


def test_build_routing_cannot_be_promoted_as_deployment(deployment):
    paths, settings, document = deployment
    document["pipeline"]["silver_table"] = "candidate_target"
    paths.candidate_config.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="only target_classification"):
        migration.bind_target_deployment(
            paths, settings=settings, configs_root=paths.workspace / "configs"
        )


def test_environment_cannot_resolve_a_different_physical_table(deployment):
    paths, settings, _ = deployment
    other = settings.model_copy(update={"data_dir": paths.workspace / "other-data"})
    with pytest.raises(ValueError, match="physical target destinations"):
        migration.bind_target_deployment(
            paths, settings=other, configs_root=paths.workspace / "configs"
        )


def test_deployment_rejects_an_inactive_assay_copy(deployment):
    paths, settings, _ = deployment
    with pytest.raises(ValueError, match="physical assay destination"):
        migration.bind_target_deployment(
            replace(paths, assay=paths.workspace / "assay-copy"),
            settings=settings,
            configs_root=paths.workspace / "configs",
        )
