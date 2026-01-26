"""Architecture test: force_full_scan enforcement for publication pipelines.

Tests that all publication pipeline configs have force_full_scan=true
to ensure reproducible extraction (ADR-030).

REQ-ARCH-050: Publication pipelines MUST use force_full_scan=true.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Publication-related entity types that require force_full_scan
PUBLICATION_ENTITY_TYPES = {
    "publication",
    "publication_term",
    "publication_similarity",
    "work",  # CrossRef uses "work" for publications
}

# All publication pipeline configs that MUST have force_full_scan=true
PUBLICATION_PIPELINE_CONFIGS = [
    "configs/pipelines/chembl/publication.yaml",
    "configs/pipelines/chembl/publication_term.yaml",
    "configs/pipelines/chembl/publication_similarity.yaml",
    "configs/pipelines/pubmed/publication.yaml",
    "configs/pipelines/crossref/publication.yaml",
    "configs/pipelines/openalex/publication.yaml",
    "configs/pipelines/semanticscholar/publication.yaml",
]


class TestForceFullScanPublicationConfigs:
    """Tests for force_full_scan enforcement in publication configs."""

    @pytest.mark.parametrize("config_path", PUBLICATION_PIPELINE_CONFIGS)
    def test_publication_config_has_force_full_scan_enabled(
        self, config_path: str
    ) -> None:
        """Publication pipeline configs MUST have force_full_scan: true.

        ADR-030 requires all publication-related pipelines to perform full scans
        on each run due to API offset instability. Checkpoint-based resume is
        disabled for these pipelines; deduplication happens on Silver via content_hash.
        """
        path = Path(config_path)

        if not path.exists():
            pytest.skip(f"{config_path} does not exist")

        with path.open() as f:
            config = yaml.safe_load(f)

        # Skip composite configs (they use sub-pipelines)
        if "composite" in config:
            pytest.skip(f"{config_path} is a composite pipeline")

        # Verify force_full_scan is explicitly set to true
        force_full_scan = config.get("force_full_scan", False)
        assert force_full_scan is True, (
            f"{config_path} MUST have 'force_full_scan: true' per ADR-030. "
            f"Found: force_full_scan={force_full_scan}"
        )

    def test_all_publication_configs_are_tested(self) -> None:
        """All publication pipeline configs MUST be in the test list.

        This ensures new publication configs are added to PUBLICATION_PIPELINE_CONFIGS.
        """
        configs_dir = Path("configs/pipelines")

        if not configs_dir.exists():
            pytest.skip("configs/pipelines directory does not exist")

        # Find all YAML files with "publication" in the name
        found_publication_configs = []
        for yaml_file in configs_dir.glob("**/publication*.yaml"):
            relative_path = str(yaml_file)
            found_publication_configs.append(relative_path)

        # Check that we test all found configs (except composite)
        missing_from_tests = []
        for config_path in found_publication_configs:
            # Skip composite publication config
            if "composite" in config_path:
                continue
            if config_path not in PUBLICATION_PIPELINE_CONFIGS:
                missing_from_tests.append(config_path)

        if missing_from_tests:
            msg = (
                "Found publication configs not in test list:\n"
                + "\n".join(f"  - {p}" for p in missing_from_tests)
                + "\n\nAdd these to PUBLICATION_PIPELINE_CONFIGS in "
                "tests/architecture/test_force_full_scan_publication.py"
            )
            pytest.fail(msg)


class TestForceFullScanNonPublicationConfigs:
    """Tests that non-publication configs don't have force_full_scan enabled."""

    def test_non_publication_configs_default_to_false(self) -> None:
        """Non-publication configs SHOULD NOT have force_full_scan: true.

        Only publication-related entities should use force_full_scan.
        Other entities (activity, compound, target) can use checkpoint resume.
        """
        configs_dir = Path("configs/pipelines")

        if not configs_dir.exists():
            pytest.skip("configs/pipelines directory does not exist")

        incorrectly_enabled = []

        for yaml_file in configs_dir.glob("**/*.yaml"):
            # Skip publication configs and base configs
            if "publication" in yaml_file.name or yaml_file.name.startswith("_"):
                continue

            with yaml_file.open() as f:
                config = yaml.safe_load(f)

            if config is None:
                continue

            # Skip composite configs
            if "composite" in config:
                continue

            entity_type = config.get("entity_type", "")
            force_full_scan = config.get("force_full_scan", False)

            # Non-publication entities shouldn't have force_full_scan=true
            if (
                entity_type not in PUBLICATION_ENTITY_TYPES
                and force_full_scan is True
            ):
                incorrectly_enabled.append(f"{yaml_file} (entity_type={entity_type})")

        if incorrectly_enabled:
            msg = (
                "Non-publication configs with force_full_scan=true:\n"
                + "\n".join(f"  - {p}" for p in incorrectly_enabled)
                + "\n\nforce_full_scan should only be enabled for publication entities."
            )
            pytest.fail(msg)
