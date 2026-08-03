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
"""Architecture test: loading_strategy enforcement for publication pipelines.

Tests that all publication pipeline configs have:
- loading_strategy=full_scan_only (ADR-031)

This ensures reproducible extraction via full scans with deduplication on Silver.

REQ-ARCH-051: Publication pipelines MUST use loading_strategy=full_scan_only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

# Publication-related entity types that require full_scan_only
PUBLICATION_ENTITY_TYPES = {
    "publication",
    "publication_term",
    "publication_similarity",
    "work",  # CrossRef uses "work" for publications
}

# Derived entity types that require full_scan_only for deduplication
# These entities are extracted from parent records and need full scans
# to ensure comprehensive deduplication at Silver layer
DERIVED_ENTITY_TYPES = {
    "subcellular_fraction",  # Derived from assay records
}

# All entity types that legitimately require full_scan_only
FULL_SCAN_ENTITY_TYPES = PUBLICATION_ENTITY_TYPES | DERIVED_ENTITY_TYPES

# All publication pipeline configs that MUST have loading_strategy: full_scan_only
PUBLICATION_PIPELINE_CONFIGS = [
    "configs/entities/chembl/publication.yaml",
    "configs/entities/chembl/publication_term.yaml",
    "configs/entities/chembl/publication_similarity.yaml",
    "configs/entities/composite/publication.yaml",
    "configs/entities/pubmed/publication.yaml",
    "configs/entities/crossref/publication.yaml",
    "configs/entities/openalex/publication.yaml",
    "configs/entities/semanticscholar/publication.yaml",
]


class TestLoadingStrategyPublicationConfigs:
    """Tests for loading_strategy enforcement in publication configs."""

    @pytest.mark.parametrize("config_path", PUBLICATION_PIPELINE_CONFIGS)
    def test_publication_config_has_full_scan_only_strategy(
        self, config_path: str
    ) -> None:
        """Publication pipeline configs MUST have loading_strategy: full_scan_only.

        ADR-031 requires all publication-related pipelines to perform full scans
        on each run due to API offset instability. Checkpoint-based resume is
        disabled for these pipelines; deduplication happens on Silver via content_hash.
        """
        path = Path(config_path)

        if not path.exists():
            pytest.skip(f"{config_path} does not exist")

        with path.open() as f:
            config = yaml.safe_load(f)

        pipeline_cfg = config.get("pipeline") if isinstance(config, dict) else None
        if not isinstance(pipeline_cfg, dict):
            pytest.skip(f"{config_path} has no pipeline section")

        # Verify loading_strategy is explicitly set to full_scan_only (ADR-031)
        loading_strategy = pipeline_cfg.get("loading_strategy")
        assert loading_strategy == "full_scan_only", (
            f"{config_path} MUST have 'loading_strategy: full_scan_only' per ADR-031. "
            f"Found: loading_strategy={loading_strategy}"
        )

    def test_all_publication_configs_are_tested(self) -> None:
        """All publication pipeline configs MUST be in the test list.

        This ensures new publication configs are added to PUBLICATION_PIPELINE_CONFIGS.
        """
        configs_dir = Path("configs/entities")

        if not configs_dir.exists():
            pytest.skip("configs/entities directory does not exist")

        # Find all YAML files with "publication" in the name
        found_publication_configs = []
        for yaml_file in configs_dir.glob("**/publication*.yaml"):
            relative_path = str(yaml_file)
            found_publication_configs.append(relative_path)

        # Check that we test all found entity configs.
        # Normalize paths to use forward slashes for cross-platform comparison
        normalized_test_configs = {
            p.replace("\\", "/") for p in PUBLICATION_PIPELINE_CONFIGS
        }
        missing_from_tests = []
        for config_path in found_publication_configs:
            # Normalize path for comparison
            normalized_path = config_path.replace("\\", "/")
            if normalized_path not in normalized_test_configs:
                missing_from_tests.append(config_path)

        if missing_from_tests:
            msg = (
                "Found publication configs not in test list:\n"
                + "\n".join(f"  - {p}" for p in missing_from_tests)
                + "\n\nAdd these to PUBLICATION_PIPELINE_CONFIGS in "
                "tests/architecture/test_force_full_scan_publication.py"
            )
            pytest.fail(msg)


class TestLoadingStrategyNonPublicationConfigs:
    """Tests that non-publication configs don't have full_scan_only enabled."""

    def test_non_publication_configs_default_to_incremental(self) -> None:
        """Non-publication configs SHOULD NOT have loading_strategy: full_scan_only.

        Only publication-related entities should use full_scan_only.
        Other entities (activity, compound, target) can use checkpoint resume.
        """
        configs_dir = Path("configs/entities")

        if not configs_dir.exists():
            pytest.skip("configs/entities directory does not exist")

        incorrectly_enabled = []

        for yaml_file in configs_dir.glob("**/*.yaml"):
            # Skip publication configs
            if "publication" in yaml_file.name or yaml_file.name.startswith("_"):
                continue

            with yaml_file.open() as f:
                config = yaml.safe_load(f)

            if config is None:
                continue

            pipeline_cfg = config.get("pipeline") if isinstance(config, dict) else None
            if not isinstance(pipeline_cfg, dict):
                continue

            entity_type = pipeline_cfg.get("entity_type", "")
            loading_strategy = pipeline_cfg.get("loading_strategy")

            # Only publication and derived entities should have full_scan_only
            if (
                entity_type not in FULL_SCAN_ENTITY_TYPES
                and loading_strategy == "full_scan_only"
            ):
                incorrectly_enabled.append(f"{yaml_file} (entity_type={entity_type})")

        if incorrectly_enabled:
            msg = (
                "Non-publication configs with loading_strategy=full_scan_only:\n"
                + "\n".join(f"  - {p}" for p in incorrectly_enabled)
                + "\n\nfull_scan_only should only be used for publication entities."
            )
            pytest.fail(msg)
