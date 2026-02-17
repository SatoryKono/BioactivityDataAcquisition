"""Architecture test: Gold Schema Contracts validation.

REQ-ARCH-045: Gold layer must have versioned JSON Schema contracts.
See docs/02-architecture/decisions/ADR-018-gold-strict-validation.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Path relative to project root
CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")

# Required Gold schema contracts with version 1.0
# Note: Using sorted tuple for deterministic pytest-xdist test collection order
# Generated from Pandera schemas by src/tools/scripts/generate_contracts.py
REQUIRED_SCHEMAS = (
    "chembl_activity_v1.0.json",
    "chembl_assay_v1.0.json",
    "chembl_assay_parameters_v1.0.json",
    "chembl_cell_line_v1.0.json",
    "chembl_compound_record_v1.0.json",
    "chembl_document_v1.0.json",
    "chembl_document_similarity_v1.0.json",
    "chembl_document_term_v1.0.json",
    "chembl_molecule_v1.0.json",
    "chembl_protein_class_v1.0.json",
    "chembl_target_v1.0.json",
    "chembl_target_component_v1.0.json",
    "crossref_publication_v1.0.json",
    "openalex_publication_v1.0.json",
    "pubchem_compound_v1.0.json",
    "pubmed_publication_v1.0.json",
    "semanticscholar_publication_v1.0.json",
    "uniprot_idmapping_v1.0.json",
    "uniprot_protein_v1.0.json",
)

# Required JSON Schema properties
REQUIRED_SCHEMA_PROPERTIES = {
    "$schema",
    "$version",
    "$changelog",
    "title",
    "description",
    "type",
    "properties",
    "required",
}


class TestGoldSchemaContracts:
    """Tests ensuring Gold schema contracts are valid and complete."""

    @pytest.fixture
    def contracts_path(self) -> Path:
        """Get contracts directory path."""
        if CONTRACTS_DIR.exists():
            return CONTRACTS_DIR
        return Path(__file__).parent.parent.parent / CONTRACTS_DIR

    @pytest.fixture
    def schema_files(self, contracts_path: Path) -> dict[str, Path]:
        """Get all JSON schema files in contracts directory."""
        return {f.name: f for f in contracts_path.glob("*.json")}

    def test_all_required_schemas_exist(self, schema_files: dict[str, Path]) -> None:
        """All required Gold schema contracts MUST exist.

        These contracts define the data interface for downstream consumers.
        """
        missing = set(REQUIRED_SCHEMAS) - set(schema_files.keys())

        assert not missing, (
            "Missing Gold schema contracts:\n"
            + "\n".join(f"  - {s}" for s in sorted(missing))
            + "\n\nGold contracts are required for data consumer documentation. "
            "See ADR-018 for Gold strict validation requirements."
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_is_valid_json(self, contracts_path: Path, schema_name: str) -> None:
        """Each Gold schema contract MUST be valid JSON."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        try:
            with schema_path.open() as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {schema_name}: {e}")

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_has_required_properties(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Each Gold schema MUST have required JSON Schema properties."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        missing = REQUIRED_SCHEMA_PROPERTIES - set(schema.keys())

        assert not missing, f"Missing properties in {schema_name}:\n" + "\n".join(
            f"  - {p}" for p in sorted(missing)
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_version_is_1_0_0(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Gold v1.0 schemas MUST have version 1.0.0."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        version = schema.get("$version")

        assert version == "1.0.0", (
            f"{schema_name} has incorrect version: {version}. "
            f"Expected: 1.0.0 for v1.0 schema files."
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_uses_draft_07(self, contracts_path: Path, schema_name: str) -> None:
        """Gold schemas MUST use JSON Schema draft-07."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        json_schema_version = schema.get("$schema")

        assert json_schema_version == "http://json-schema.org/draft-07/schema#", (
            f"{schema_name} uses unsupported JSON Schema version: {json_schema_version}. "
            f"All Gold contracts must use draft-07 for consistency."
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_has_lineage_fields(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Gold schemas MUST include standard lineage fields.

        Required lineage fields per RULES.md §2.4:
        - _content_hash: For versioning and deduplication
        - _ingestion_ts: For temporal tracking
        """
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        properties = set(schema.get("properties", {}).keys())

        # Core lineage fields required for all Gold schemas (from Pandera schemas)
        # All schemas now use the same lineage pattern: _run_id, _run_type, _ingestion_ts
        required_lineage = {"_ingestion_ts", "_run_id", "_run_type"}

        missing_lineage = required_lineage - properties

        assert not missing_lineage, (
            f"{schema_name} missing lineage fields:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing_lineage))
            + "\n\nLineage fields are required per RULES.md §2.4."
        )

    def test_no_extra_schemas_without_version(
        self, schema_files: dict[str, Path]
    ) -> None:
        """All Gold schema files MUST include version in filename."""
        unversioned = [
            name
            for name in schema_files.keys()
            if not any(f"_v{v}" in name for v in ["1.0", "1.1", "2.0"])
        ]

        assert not unversioned, (
            "Unversioned schema files found:\n"
            + "\n".join(f"  - {s}" for s in sorted(unversioned))
            + "\n\nAll Gold contracts must include version (e.g., entity_v1.0.json)."
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_filename_version_matches_schema_version(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Filename version MUST match $version in schema."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        match = re.search(r"_v(\d+)\.(\d+)\.json$", schema_name)
        assert match, (
            f"Schema filename does not follow *_vX.Y.json pattern: {schema_name}"
        )

        with schema_path.open() as f:
            schema = json.load(f)

        expected_version = f"{match.group(1)}.{match.group(2)}.0"
        assert schema.get("$version") == expected_version, (
            f"{schema_name} has $version={schema.get('$version')}, "
            f"expected {expected_version} from filename"
        )

    @pytest.mark.parametrize("schema_name", sorted(REQUIRED_SCHEMAS))
    def test_schema_has_changelog_link(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Each schema MUST contain changelog link metadata."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        changelog = schema.get("$changelog")
        assert isinstance(changelog, str) and changelog.strip(), (
            f"{schema_name} missing non-empty $changelog link"
        )
