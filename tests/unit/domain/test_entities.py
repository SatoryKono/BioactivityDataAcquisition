"""Unit tests for domain entities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.entities import (
    Bioactivity,
    BioactivityState,
    CrossRefPublicationEntity,
    ChemblPublicationSimilarity,
    PubchemMolecule,
    UniprotTarget,
)
from bioetl.domain.types import ContentHash, EntityID, RunType
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit

_FIXED_RUN_ID = UUID("11111111-1111-4111-8111-111111111111")
_FIXED_SOURCE_BATCH_ID = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def base_entity_kwargs():
    """Common kwargs for creating entities."""
    return {
        "entity_id": EntityID("TEST123"),
        "content_hash": ContentHash("abc123hash"),
        "run_id": _FIXED_RUN_ID,
        "run_type": RunType.INCREMENTAL,
        "source_batch_id": _FIXED_SOURCE_BATCH_ID,
        "ingestion_ts": FIXED_TEST_TIME,
        "_index": 0,
    }


@pytest.mark.unit
class TestBaseEntity:
    """Tests for BaseEntity validation."""

    def test_base_entity_requires_entity_id(self, base_entity_kwargs):
        """Test that empty entity_id raises ValueError."""
        base_entity_kwargs["entity_id"] = EntityID("")
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            Bioactivity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_id="CHEMBL123",
                target_id="CHEMBL456",
                assay_id="CHEMBL789",
            )

    def test_base_entity_requires_content_hash(self, base_entity_kwargs):
        """Test that empty content_hash raises ValueError."""
        base_entity_kwargs["content_hash"] = ContentHash("")
        with pytest.raises(ValueError, match="Content hash cannot be empty"):
            Bioactivity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_id="CHEMBL123",
                target_id="CHEMBL456",
                assay_id="CHEMBL789",
            )

    def test_base_entity_requires_ingestion_ts(self, base_entity_kwargs):
        """Test that ingestion_ts is required (no default) per ADR-014."""
        # Remove ingestion_ts to verify it's required
        kwargs_without_ts = {
            k: v for k, v in base_entity_kwargs.items() if k != "ingestion_ts"
        }
        with pytest.raises(TypeError, match="ingestion_ts"):
            Bioactivity(
                **kwargs_without_ts,
                activity_id="ACT1",
                molecule_id="CHEMBL123",
                target_id="CHEMBL456",
                assay_id="CHEMBL789",
            )

    def test_base_entity_accepts_explicit_ingestion_ts(self, base_entity_kwargs):
        """Test that explicitly passed ingestion_ts is used."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL123",
            target_id="CHEMBL456",
            assay_id="CHEMBL789",
        )
        assert bioactivity.ingestion_ts is not None
        assert isinstance(bioactivity.ingestion_ts, datetime)
        assert bioactivity.ingestion_ts.tzinfo == UTC


@pytest.mark.unit
class TestBioactivity:
    """Tests for Bioactivity entity."""

    def test_bioactivity_creation_success(self, base_entity_kwargs):
        """Test successful Bioactivity creation with required fields."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT123",
            molecule_id="CHEMBL1",
            target_id="CHEMBL2",
            assay_id="CHEMBL3",
        )
        assert bioactivity.activity_id == "ACT123"
        assert bioactivity.molecule_id == "CHEMBL1"
        assert bioactivity.target_id == "CHEMBL2"
        assert bioactivity.assay_id == "CHEMBL3"

    def test_bioactivity_with_optional_fields(self, base_entity_kwargs):
        """Test Bioactivity with all optional fields."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT456",
            molecule_id="CHEMBL100",
            target_id="CHEMBL200",
            assay_id="CHEMBL300",
            activity_type="IC50",
            activity_value=10.5,
            activity_relation="=",
            standard_type="IC50",
            standard_value=10.5,
            standard_units="nM",
            standard_relation="=",
            pchembl_value=7.5,
            activity_comment="High quality",
            data_validity_comment="Valid",
        )
        assert bioactivity.activity_type == "IC50"
        assert bioactivity.activity_value == pytest.approx(10.5)
        assert bioactivity.activity_relation == "="
        assert bioactivity.standard_type == "IC50"
        assert bioactivity.standard_value == pytest.approx(10.5)
        assert bioactivity.standard_units == "nM"
        assert bioactivity.standard_relation == "="
        assert bioactivity.pchembl_value == pytest.approx(7.5)
        assert bioactivity.activity_comment == "High quality"
        assert bioactivity.data_validity_comment == "Valid"

    def test_bioactivity_requires_activity_id(self, base_entity_kwargs):
        """Test that empty activity_id raises ValueError."""
        with pytest.raises(ValueError, match="Activity ID is required"):
            Bioactivity(
                **base_entity_kwargs,
                activity_id="",
                molecule_id="CHEMBL1",
                target_id="CHEMBL2",
                assay_id="CHEMBL3",
            )

    def test_bioactivity_pchembl_must_be_nonnegative(self, base_entity_kwargs):
        """Test that negative pchembl_value raises ValueError."""
        with pytest.raises(ValueError, match="pChemBL value must be non-negative"):
            Bioactivity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_id="CHEMBL1",
                target_id="CHEMBL2",
                assay_id="CHEMBL3",
                pchembl_value=-1.0,
            )

    def test_bioactivity_pchembl_zero_is_valid(self, base_entity_kwargs):
        """Test that zero pchembl_value is valid."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL1",
            target_id="CHEMBL2",
            assay_id="CHEMBL3",
            pchembl_value=0.0,
        )
        assert bioactivity.pchembl_value == pytest.approx(0.0)

    def test_bioactivity_is_frozen(self, base_entity_kwargs):
        """Test that Bioactivity is immutable."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL1",
            target_id="CHEMBL2",
            assay_id="CHEMBL3",
        )
        with pytest.raises(AttributeError):
            bioactivity.activity_id = "NEW_ID"

    def test_bioactivity_default_state_is_validated(self, base_entity_kwargs):
        """Test that default state is VALIDATED."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL1",
        )
        assert bioactivity.state == BioactivityState.VALIDATED

    def test_bioactivity_with_state(self, base_entity_kwargs):
        """Test creating bioactivity with explicit state."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL1",
            _state=BioactivityState.RAW,
        )
        assert bioactivity.state == BioactivityState.RAW

    def test_bioactivity_with_state_transition(self, base_entity_kwargs):
        """Test with_state creates new instance with updated state."""
        bioactivity = Bioactivity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_id="CHEMBL1",
            _state=BioactivityState.RAW,
        )
        normalized = bioactivity.with_state(BioactivityState.NORMALIZED)
        assert normalized.state == BioactivityState.NORMALIZED
        assert bioactivity.state == BioactivityState.RAW  # Original unchanged

    def test_bioactivity_from_raw_factory(self, base_entity_kwargs):
        """Test from_raw factory method creates entity in RAW state."""
        raw_data = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL1",
            "target_id": "CHEMBL2",
            "standard_value": "10.5",
            "pchembl_value": 7.5,
        }
        bioactivity = Bioactivity.from_raw(
            raw_data=raw_data,
            run_id=base_entity_kwargs["run_id"],
            ingestion_ts=base_entity_kwargs["ingestion_ts"],
        )
        assert bioactivity.state == BioactivityState.RAW
        assert bioactivity.activity_id == "12345"
        assert bioactivity.molecule_id == "CHEMBL1"
        assert bioactivity.activity_type is None
        assert bioactivity.activity_relation is None
        assert bioactivity.standard_value == pytest.approx(10.5)
        assert bioactivity.pchembl_value == pytest.approx(7.5)

    def test_bioactivity_from_raw_maps_legacy_measurement_fields(
        self, base_entity_kwargs
    ):
        """Test from_raw maps legacy provider measurement keys to canonical entity fields."""
        raw_data = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL1",
            "type": "IC50",
            "relation": "=",
            "value": "2.5",
            "units": "uM",
        }
        bioactivity = Bioactivity.from_raw(
            raw_data=raw_data,
            run_id=base_entity_kwargs["run_id"],
            ingestion_ts=base_entity_kwargs["ingestion_ts"],
        )
        assert bioactivity.activity_type == "IC50"
        assert bioactivity.activity_relation == "="
        assert bioactivity.activity_value == pytest.approx(2.5)
        assert bioactivity.units == "uM"

    def test_bioactivity_from_raw_missing_activity_id(self):
        """Test from_raw raises ValueError if activity_id missing."""
        with pytest.raises(ValueError, match="activity_id"):
            Bioactivity.from_raw(
                raw_data={"molecule_id": "CHEMBL1"},
                run_id=uuid4(),
                ingestion_ts=FIXED_TEST_TIME,
            )

    def test_bioactivity_from_raw_missing_molecule_id(self):
        """Test from_raw raises ValueError if molecule_id missing."""
        with pytest.raises(ValueError, match="molecule_id"):
            Bioactivity.from_raw(
                raw_data={"activity_id": 123},
                run_id=uuid4(),
                ingestion_ts=FIXED_TEST_TIME,
            )


@pytest.mark.unit
class TestBioactivityState:
    """Tests for BioactivityState enum."""

    def test_state_values(self):
        """Test state enum values."""
        assert BioactivityState.RAW.value == "raw"
        assert BioactivityState.NORMALIZED.value == "normalized"
        assert BioactivityState.VALIDATED.value == "validated"

    def test_is_ready_for_silver(self):
        """Test is_ready_for_silver returns True for NORMALIZED and VALIDATED."""
        assert not BioactivityState.RAW.is_ready_for_silver()
        assert BioactivityState.NORMALIZED.is_ready_for_silver()
        assert BioactivityState.VALIDATED.is_ready_for_silver()

    def test_is_fully_validated(self):
        """Test is_fully_validated returns True only for VALIDATED."""
        assert not BioactivityState.RAW.is_fully_validated()
        assert not BioactivityState.NORMALIZED.is_fully_validated()
        assert BioactivityState.VALIDATED.is_fully_validated()


@pytest.mark.unit
class TestPubchemMolecule:
    """Tests for PubchemMolecule entity."""

    def test_compound_creation_with_smiles(self, base_entity_kwargs):
        """Test PubchemMolecule creation with canonical SMILES."""
        compound = PubchemMolecule(
            **base_entity_kwargs,
            molecule_id="12345",
            canonical_smiles="CCO",
        )
        assert compound.molecule_id == "12345"
        assert compound.canonical_smiles == "CCO"

    def test_compound_creation_with_isomeric_smiles(self, base_entity_kwargs):
        """Test PubchemMolecule creation with isomeric SMILES."""
        compound = PubchemMolecule(
            **base_entity_kwargs,
            molecule_id="12345",
            isomeric_smiles="C[C@H](O)CC",
        )
        assert compound.isomeric_smiles == "C[C@H](O)CC"

    def test_compound_creation_with_inchi(self, base_entity_kwargs):
        """Test PubchemMolecule creation with InChI."""
        compound = PubchemMolecule(
            **base_entity_kwargs,
            molecule_id="12345",
            inchi="InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        )
        assert compound.inchi == "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"

    def test_compound_with_all_optional_fields(self, base_entity_kwargs):
        """Test PubchemMolecule with all optional fields."""
        compound = PubchemMolecule(
            **base_entity_kwargs,
            molecule_id="2244",
            molecular_formula="C9H8O4",
            molecular_weight="180.16",
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            isomeric_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            inchi="InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            inchi_key="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            iupac_name="2-acetyloxybenzoic amolecule_id",
        )
        assert compound.molecular_formula == "C9H8O4"
        assert compound.molecular_weight == "180.16"
        assert compound.inchi_key == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert compound.iupac_name == "2-acetyloxybenzoic amolecule_id"

    def test_compound_requires_molecule_id(self, base_entity_kwargs):
        """Test that empty molecule_id raises ValueError."""
        with pytest.raises(ValueError, match="PubchemMolecule molecule_id is required"):
            PubchemMolecule(
                **base_entity_kwargs,
                molecule_id="",
                canonical_smiles="CCO",
            )

    def test_compound_requires_structural_identifier(self, base_entity_kwargs):
        """Test that at least one structural identifier is required."""
        with pytest.raises(
            ValueError,
            match="PubchemMolecule must have at least one structural identifier",
        ):
            PubchemMolecule(
                **base_entity_kwargs,
                molecule_id="12345",
                # No SMILES or InChI
            )

    def test_compound_inchi_key_alone_not_sufficient(self, base_entity_kwargs):
        """Test that InChIKey alone is not sufficient."""
        with pytest.raises(
            ValueError,
            match="PubchemMolecule must have at least one structural identifier",
        ):
            PubchemMolecule(
                **base_entity_kwargs,
                molecule_id="12345",
                inchi_key="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                # InChIKey is not counted as structural identifier
            )

    def test_compound_is_frozen(self, base_entity_kwargs):
        """Test that PubchemMolecule is immutable."""
        compound = PubchemMolecule(
            **base_entity_kwargs,
            molecule_id="12345",
            canonical_smiles="CCO",
        )
        with pytest.raises(AttributeError):
            compound.molecule_id = "99999"


@pytest.mark.unit
class TestUniprotTarget:
    """Tests for UniprotTarget entity."""

    def test_protein_creation_success(self, base_entity_kwargs):
        """Test successful UniprotTarget creation."""
        protein = UniprotTarget(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        assert protein.accession == "P12345"
        assert protein.entry_name == "TEST_HUMAN"
        assert protein.protein_name == "Test protein"

    def test_protein_with_all_optional_fields(self, base_entity_kwargs):
        """Test UniprotTarget with all optional fields."""
        protein = UniprotTarget(
            **base_entity_kwargs,
            accession="P00533",
            entry_name="EGFR_HUMAN",
            protein_name="Epidermal growth factor receptor",
            gene_primary="EGFR",
            gene_synonyms='["ERBB1"]',
            taxonomy_id=9606,
            sequence_length=1210,
        )
        assert protein.gene_primary == "EGFR"
        assert protein.gene_synonyms == '["ERBB1"]'
        assert protein.taxonomy_id == 9606
        assert protein.sequence_length == 1210

    def test_protein_default_gene_primary_is_none(self, base_entity_kwargs):
        """Test that canonical gene fields default to None."""
        protein = UniprotTarget(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        assert protein.gene_primary is None
        assert protein.gene_synonyms is None

    def test_protein_requires_accession(self, base_entity_kwargs):
        """Test that empty accession raises ValueError."""
        with pytest.raises(ValueError, match="UniprotTarget accession is required"):
            UniprotTarget(
                **base_entity_kwargs,
                accession="",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
            )

    def test_protein_sequence_length_must_be_positive(self, base_entity_kwargs):
        """Test that non-positive sequence_length raises ValueError."""
        with pytest.raises(ValueError, match="Sequence length must be positive"):
            UniprotTarget(
                **base_entity_kwargs,
                accession="P12345",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
                sequence_length=0,
            )

    def test_protein_sequence_length_negative_raises(self, base_entity_kwargs):
        """Test that negative sequence_length raises ValueError."""
        with pytest.raises(ValueError, match="Sequence length must be positive"):
            UniprotTarget(
                **base_entity_kwargs,
                accession="P12345",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
                sequence_length=-100,
            )

    def test_protein_sequence_length_none_is_valid(self, base_entity_kwargs):
        """Test that None sequence_length is valid."""
        protein = UniprotTarget(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
            sequence_length=None,
        )
        assert protein.sequence_length is None

    def test_protein_is_frozen(self, base_entity_kwargs):
        """Test that UniprotTarget is immutable."""
        protein = UniprotTarget(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        with pytest.raises(AttributeError):
            protein.accession = "P99999"


@pytest.mark.unit
class TestCrossRefPublicationEntity:
    """Tests for CrossRef CrossRefPublicationEntity (formerly Work).

    Tests the CrossRefPublicationEntity domain entity which represents scholarly
    publications from CrossRef or other bibliographic sources.
    """

    def test_publication_creation_success(self, base_entity_kwargs):
        """Test successful CrossRefPublicationEntity creation."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test.article",
        )
        assert publication.doi == "10.1234/test.article"
        assert publication._source == "crossref"
        assert publication.publication_type is None

    def test_publication_with_all_optional_fields(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with all optional fields."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1038/nature12373",
            title="The complete genome sequence",
            abstract="This is the abstract",
            authors=["Kay Prüfer", "Fernando Racimo"],
            journal="Nature",
            issn=["0028-0836", "1476-4687"],
            publisher="Springer Nature",
            volume="499",
            issue="7461",
            page_first="480",
            page_last="485",
            publication_year=2023,
            published_print="2023-07-25",
            published_online="2023-07-20",
            publication_type="journal-article",
            citations_received=2847,
            citations_made=50,
            language="en",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            subject_keywords=["Genetics", "Genomics"],
        )
        assert publication.title == "The complete genome sequence"
        assert publication.journal == "Nature"
        assert publication.publication_year == 2023
        assert publication.citations_received == 2847
        assert len(publication.authors) == 2
        assert len(publication.issn) == 2

    def test_publication_requires_doi(self, base_entity_kwargs):
        """Test that empty doi raises ValueError."""
        with pytest.raises(ValueError, match="Publication DOI is required"):
            CrossRefPublicationEntity(
                **base_entity_kwargs,
                doi="",
            )

    def test_publication_preprint_publication_type(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with PREPRINT publication_type."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1101/2023.01.01.123456",
            publication_type="PREPRINT",
        )
        assert publication.publication_type == "PREPRINT"

    def test_publication_default_authors_none(self, base_entity_kwargs):
        """Test that authors defaults to None (JSON string format)."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert publication.authors is None

    def test_publication_default_issn_empty_list(self, base_entity_kwargs):
        """Test that issn defaults to empty list."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert publication.issn == []

    def test_publication_default_subject_keywords_empty_list(self, base_entity_kwargs):
        """Test that subject_keywords defaults to empty list."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert publication.subject_keywords == []

    def test_publication_is_frozen(self, base_entity_kwargs):
        """Test that CrossRefPublicationEntity is immutable."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        with pytest.raises(AttributeError):
            publication.doi = "10.9999/changed"

    def test_publication_default_source_is_crossref(self, base_entity_kwargs):
        """Test that _source defaults to 'crossref'."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert publication._source == "crossref"

    def test_publication_custom_source(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with custom _source."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            _source="pubmed",
        )
        assert publication._source == "pubmed"

    def test_publication_with_citation_metrics(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with citation metrics."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            citations_received=150,
            citations_made=45,
        )
        assert publication.citations_received == 150
        assert publication.citations_made == 45

    def test_publication_citations_received_can_be_zero(self, base_entity_kwargs):
        """Test that citations_received can be zero."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            citations_received=0,
        )
        assert publication.citations_received == 0

    def test_publication_with_date_fields(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity date fields."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            publication_year=2023,
            published_print="2023-06-15",
            published_online="2023-05-01",
        )
        assert publication.publication_year == 2023
        assert publication.published_print == "2023-06-15"
        assert publication.published_online == "2023-05-01"

    def test_publication_year_can_be_none(self, base_entity_kwargs):
        """Test that publication_year can be None for publications with unknown date."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            publication_year=None,
        )
        assert publication.publication_year is None

    def test_publication_with_license_url(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with license URL."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            license_url="https://creativecommons.org/licenses/by/4.0/",
        )
        assert publication.license_url == "https://creativecommons.org/licenses/by/4.0/"

    def test_publication_with_language(self, base_entity_kwargs):
        """Test CrossRefPublicationEntity with language code."""
        publication = CrossRefPublicationEntity(
            **base_entity_kwargs,
            doi="10.1234/test",
            language="en",
        )
        assert publication.language == "en"


@pytest.mark.unit
class TestPublicationRecord:
    """Tests for CrossRef PublicationRecord DTO."""

    def test_publication_record_creation(self):
        """Test PublicationRecord DTO creation."""
        from bioetl.domain.entities.crossref import PublicationRecord

        record = PublicationRecord(
            doi="10.1234/test",
            title="Test Publication",
        )
        assert record.doi == "10.1234/test"
        assert record.title == "Test Publication"

    def test_publication_record_is_frozen(self):
        """Test PublicationRecord is immutable."""
        from bioetl.domain.entities.crossref import PublicationRecord

        record = PublicationRecord(doi="10.1234/test")
        with pytest.raises(Exception):  # Pydantic raises ValidationError on mutation
            record.doi = "changed"

    def test_publication_record_forbids_extra_fields(self):
        """Test PublicationRecord rejects extra fields."""
        from pydantic import ValidationError

        from bioetl.domain.entities.crossref import PublicationRecord

        with pytest.raises(ValidationError):
            PublicationRecord(
                doi="10.1234/test",
                unknown_field="value",
            )

    def test_publication_record_default_values(self):
        """Test PublicationRecord default values."""
        from bioetl.domain.entities.crossref import PublicationRecord

        record = PublicationRecord(doi="10.1234/test")
        assert record.title is None
        assert record.abstract is None
        assert record.authors is None  # JSON string format, defaults to None
        assert record.issn == []
        assert record.subjects == []
        # Note: _source is set by transformer, not in DTO
        assert record.doc_type == "PUBLICATION"

    def test_publication_record_with_all_fields(self):
        """Test PublicationRecord with all fields."""
        import json

        from bioetl.domain.entities.crossref import PublicationRecord

        authors_json = json.dumps(["John Doe", "Jane Smith"])
        record = PublicationRecord(
            doi="10.1038/nature12373",
            title="Test Title",
            abstract="Test abstract",
            authors=authors_json,  # JSON string format
            journal="Nature",
            issn=["0028-0836"],
            publisher="Springer",
            volume="523",
            issue="7562",
            first_page="561",
            last_page="567",
            year=2015,
            published_print="2015-07-30",
            published_online="2015-07-25",
            doc_type="PUBLICATION",
            citation_count=892,
            reference_count=50,
            language="en",
            license_url="https://license.com",
            subjects=["Science"],
            # Note: _source is set by transformer, not in DTO
        )
        assert record.citation_count == 892
        assert record.authors == authors_json
        assert len(json.loads(record.authors)) == 2


@pytest.mark.unit
class TestDocumentSimilarity:
    """Tests for ChemblPublicationSimilarity entity."""

    def test_valid_entity(self, base_entity_kwargs):
        """Test creation of valid entity."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
            tid_tani=0.8,
            mol_tani=0.6,
            avg_tani=0.7,
            max_tani=0.8,
        )

        assert entity.sim_id == 1
        assert entity.doc_1 == 100
        assert entity.doc_2 == 200
        assert entity.tid_tani == pytest.approx(0.8)
        assert entity.mol_tani == pytest.approx(0.6)
        assert entity.avg_tani == pytest.approx(0.7)
        assert entity.max_tani == pytest.approx(0.8)

    def test_minimal_entity(self, base_entity_kwargs):
        """Test creation with only required fields."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
        )

        assert entity.sim_id == 1
        assert entity.tid_tani is None
        assert entity.mol_tani is None
        assert entity.avg_tani is None
        assert entity.max_tani is None
        assert entity.pubmed_id1 is None
        assert entity.pubmed_id2 is None

    def test_with_pubmed_ids(self, base_entity_kwargs):
        """Test creation with PubMed identifiers."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
            pubmed_id1=12345678,
            pubmed_id2=87654321,
        )

        assert entity.pubmed_id1 == 12345678
        assert entity.pubmed_id2 == 87654321

    def test_invalid_sim_id_zero(self, base_entity_kwargs):
        """Test that sim_id=0 raises error."""
        with pytest.raises(ValueError, match="sim_id must be positive"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=0,
                doc_1=100,
                doc_2=200,
            )

    def test_invalid_sim_id_negative(self, base_entity_kwargs):
        """Test that negative sim_id raises error."""
        with pytest.raises(ValueError, match="sim_id must be positive"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=-1,
                doc_1=100,
                doc_2=200,
            )

    def test_invalid_doc_1_zero(self, base_entity_kwargs):
        """Test that doc_1=0 raises error."""
        with pytest.raises(ValueError, match="doc_1 and doc_2 must be positive"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=1,
                doc_1=0,
                doc_2=200,
            )

    def test_invalid_doc_2_zero(self, base_entity_kwargs):
        """Test that doc_2=0 raises error."""
        with pytest.raises(ValueError, match="doc_1 and doc_2 must be positive"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=1,
                doc_1=100,
                doc_2=0,
            )

    def test_invalid_same_document(self, base_entity_kwargs):
        """Test that doc_1==doc_2 raises error."""
        with pytest.raises(ValueError, match="cannot be similar to itself"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=1,
                doc_1=100,
                doc_2=100,
            )

    def test_invalid_tanimoto_above_one(self, base_entity_kwargs):
        """Test that Tanimoto > 1.0 raises error."""
        with pytest.raises(ValueError, match="tid_tani must be in"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=1,
                doc_1=100,
                doc_2=200,
                tid_tani=1.5,
            )

    def test_invalid_tanimoto_negative(self, base_entity_kwargs):
        """Test that negative Tanimoto raises error."""
        with pytest.raises(ValueError, match="mol_tani must be in"):
            ChemblPublicationSimilarity(
                **base_entity_kwargs,
                sim_id=1,
                doc_1=100,
                doc_2=200,
                mol_tani=-0.1,
            )

    def test_valid_tanimoto_boundary_zero(self, base_entity_kwargs):
        """Test that Tanimoto=0.0 is valid."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
            tid_tani=0.0,
        )
        assert entity.tid_tani == pytest.approx(0.0)

    def test_valid_tanimoto_boundary_one(self, base_entity_kwargs):
        """Test that Tanimoto=1.0 is valid."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
            mol_tani=1.0,
        )
        assert entity.mol_tani == pytest.approx(1.0)

    def test_entity_is_frozen(self, base_entity_kwargs):
        """Test that ChemblPublicationSimilarity is immutable."""
        entity = ChemblPublicationSimilarity(
            **base_entity_kwargs,
            sim_id=1,
            doc_1=100,
            doc_2=200,
        )
        with pytest.raises(AttributeError):
            entity.sim_id = 2


@pytest.mark.unit
class TestProteinClassification:
    """Tests for ProteinClassification entity."""

    def test_create_root_node(self, base_entity_kwargs):
        """Test creating a root classification node."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=1,
            parent_id=None,
            pref_name="Enzyme",
            class_level=1,
        )

        assert entity.protein_class_id == 1
        assert entity.is_root() is True
        assert entity.is_deprecated() is False

    def test_create_child_node(self, base_entity_kwargs):
        """Test creating a child classification node."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=100,
            parent_id=1,
            pref_name="Kinase",
            class_level=2,
        )

        assert entity.protein_class_id == 100
        assert entity.parent_id == 1
        assert entity.is_root() is False

    def test_deprecated_by_replaced_by(self, base_entity_kwargs):
        """Test deprecation via replaced_by field."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=50,
            replaced_by=100,
        )

        assert entity.is_deprecated() is True

    def test_deprecated_by_downgraded_flag(self, base_entity_kwargs):
        """Test deprecation via downgraded flag."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=60,
            downgraded=1,
        )

        assert entity.is_deprecated() is True

    def test_not_deprecated_when_downgraded_zero(self, base_entity_kwargs):
        """Test not deprecated when downgraded is 0."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=60,
            downgraded=0,
        )

        assert entity.is_deprecated() is False

    def test_invalid_protein_class_id_zero(self, base_entity_kwargs):
        """Test validation of protein_class_id with zero."""
        from bioetl.domain.entities import ProteinClassification

        with pytest.raises(ValueError, match="protein_class_id must be >= 1"):
            ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=0,
            )

    def test_invalid_protein_class_id_negative(self, base_entity_kwargs):
        """Test validation of protein_class_id with negative value."""
        from bioetl.domain.entities import ProteinClassification

        with pytest.raises(ValueError, match="protein_class_id must be >= 1"):
            ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=-1,
            )

    def test_invalid_class_level_zero(self, base_entity_kwargs):
        """Test validation of class_level with zero."""
        from bioetl.domain.entities import ProteinClassification

        with pytest.raises(ValueError, match="class_level must be 1-8"):
            ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=1,
                class_level=0,
            )

    def test_invalid_class_level_too_high(self, base_entity_kwargs):
        """Test validation of class_level with value > 8."""
        from bioetl.domain.entities import ProteinClassification

        with pytest.raises(ValueError, match="class_level must be 1-8"):
            ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=1,
                class_level=9,
            )

    def test_valid_class_levels(self, base_entity_kwargs):
        """Test that all valid class levels (1-8) are accepted."""
        from bioetl.domain.entities import ProteinClassification

        for level in range(1, 9):
            entity = ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=level,
                class_level=level,
            )
            assert entity.class_level == level

    def test_invalid_downgraded_value(self, base_entity_kwargs):
        """Test validation of downgraded flag with invalid value."""
        from bioetl.domain.entities import ProteinClassification

        with pytest.raises(ValueError, match="downgraded must be 0 or 1"):
            ProteinClassification(
                **base_entity_kwargs,
                protein_class_id=1,
                downgraded=2,
            )

    def test_entity_is_frozen(self, base_entity_kwargs):
        """Test that ProteinClassification is immutable."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=1,
            pref_name="Enzyme",
        )
        with pytest.raises(AttributeError):
            entity.protein_class_id = 2

    def test_full_entity_creation(self, base_entity_kwargs):
        """Test creating entity with all fields."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=100,
            parent_id=1,
            class_level=2,
            pref_name="Kinase",
            short_name="KIN",
            protein_class_desc="Enzymes that transfer phosphate groups",
            definition="Full definition of kinase class",
            sort_order=10,
            replaced_by=None,
            downgraded=0,
        )

        assert entity.protein_class_id == 100
        assert entity.parent_id == 1
        assert entity.class_level == 2
        assert entity.pref_name == "Kinase"
        assert entity.short_name == "KIN"
        assert entity.protein_class_desc == "Enzymes that transfer phosphate groups"
        assert entity.definition == "Full definition of kinase class"
        assert entity.sort_order == 10
        assert entity.replaced_by is None
        assert entity.downgraded == 0

    def test_class_level_none_is_valid(self, base_entity_kwargs):
        """Test that class_level can be None."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=1,
            class_level=None,
        )
        assert entity.class_level is None

    def test_downgraded_none_is_valid(self, base_entity_kwargs):
        """Test that downgraded can be None."""
        from bioetl.domain.entities import ProteinClassification

        entity = ProteinClassification(
            **base_entity_kwargs,
            protein_class_id=1,
            downgraded=None,
        )
        assert entity.downgraded is None
        assert entity.is_deprecated() is False
