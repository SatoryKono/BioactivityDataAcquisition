"""Architecture test: Gold Schema Contracts validation.

REQ-ARCH-045: Gold layer must have versioned JSON Schema contracts.
See docs/02-architecture/decisions/ADR-018-gold-strict-validation.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Path relative to project root
CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")

# Required Gold schema contracts with version 1.0
# Note: Using sorted tuple for deterministic pytest-xdist test collection order
# Generated from Pandera schemas by python -m scripts.schema generate-contracts
REQUIRED_SCHEMAS = (
    "chembl_activity_v1.0.json",
    "chembl_assay_v1.0.json",
    "chembl_assay_parameters_v1.0.json",
    "chembl_cell_line_v1.0.json",
    "chembl_compound_record_v1.0.json",
    "chembl_publication_v1.0.json",
    "chembl_publication_similarity_v1.0.json",
    "chembl_publication_term_v1.0.json",
    "chembl_molecule_v1.0.json",
    "chembl_protein_class_v1.0.json",
    "chembl_subcellular_fraction_v1.0.json",
    "chembl_target_v3.0.json",
    "chembl_target_protein_classification_v2.2.json",
    "chembl_target_component_v1.0.json",
    "chembl_tissue_v1.0.json",
    "composite_activity_v1.0.json",
    "composite_assay_v1.0.json",
    "composite_molecule_v1.0.json",
    "composite_publication_v1.0.json",
    "composite_target_v1.0.json",
    "crossref_publication_v1.0.json",
    "openalex_publication_v1.0.json",
    "pubchem_compound_v1.0.json",
    "pubmed_publication_v1.0.json",
    "semanticscholar_publication_v1.0.json",
    "uniprot_idmapping_v1.0.json",
    "uniprot_protein_v1.0.json",
)
LEGACY_SCHEMAS = (
    "chembl_document_v1.0.json",
    "chembl_document_similarity_v1.0.json",
    "chembl_document_term_v1.0.json",
)

# Required JSON Schema properties
REQUIRED_SCHEMA_PROPERTIES = {
    "$schema",
    "$version",
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

    def test_required_schema_list_matches_exported_gold_contracts(
        self, schema_files: dict[str, Path]
    ) -> None:
        """The static required-contract guard must cover every published export."""
        unguarded_exports = sorted(set(schema_files) - set(REQUIRED_SCHEMAS))

        assert not unguarded_exports, (
            "Gold schema exports missing from REQUIRED_SCHEMAS:\n"
            + "\n".join(f"  - {name}" for name in unguarded_exports)
            + "\n\nEvery published Gold contract must be covered by architecture guards."
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
    def test_schema_version_matches_filename(
        self, contracts_path: Path, schema_name: str
    ) -> None:
        """Gold schema payload version must align with the versioned filename."""
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        version = schema.get("$version")
        filename_version = schema_name.split("_v", maxsplit=1)[1].removesuffix(".json")
        expected_version = f"{filename_version}.0"

        assert version == expected_version, (
            f"{schema_name} has incorrect version: {version}. "
            f"Expected: {expected_version} for {schema_name}."
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
        """Gold schemas MUST include stable identity/lineage fields.

        Published Gold contracts expose entity identity universally and content hashes
        for provider-owned datasets. Composite contracts currently omit content_hash in
        their public contract surface, so the assertion follows the generated contracts
        rather than internal transient runtime columns.
        """
        schema_path = contracts_path / schema_name

        if not schema_path.exists():
            pytest.skip(f"Schema {schema_name} not found (covered by existence test)")

        with schema_path.open() as f:
            schema = json.load(f)

        properties = set(schema.get("properties", {}).keys())

        required_lineage = {"entity_id"}
        if not schema_name.startswith("composite_"):
            required_lineage.add("content_hash")

        missing_lineage = required_lineage - properties

        assert not missing_lineage, (
            f"{schema_name} missing lineage fields:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing_lineage))
            + "\n\nPublished Gold contracts must preserve canonical identity fields."
        )

    def test_no_extra_schemas_without_version(
        self, schema_files: dict[str, Path]
    ) -> None:
        """All Gold schema files MUST include version in filename."""
        unversioned = [
            name
            for name in schema_files.keys()
            if not any(
                f"_v{v}" in name for v in ["1.0", "1.1", "2.0", "2.1", "2.2", "3.0"]
            )
        ]

        assert not unversioned, (
            "Unversioned schema files found:\n"
            + "\n".join(f"  - {s}" for s in sorted(unversioned))
            + "\n\nAll Gold contracts must include version (e.g., entity_v1.0.json)."
        )

    def test_legacy_chembl_document_contracts_removed(
        self, schema_files: dict[str, Path]
    ) -> None:
        """Legacy document-named ChEMBL contracts MUST NOT exist."""
        present_legacy = sorted(set(LEGACY_SCHEMAS) & set(schema_files.keys()))
        assert not present_legacy, (
            "Legacy ChEMBL document contracts must be removed:\n"
            + "\n".join(f"  - {name}" for name in present_legacy)
            + "\n\nUse canonical chembl_publication* contract names."
        )
