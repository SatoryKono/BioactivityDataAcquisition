"""Unit tests for domain entities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.domain.entities import Activity, Compound, Protein, Work
from bioetl.domain.types import ContentHash, EntityID, RunType


@pytest.fixture
def base_entity_kwargs():
    """Common kwargs for creating entities."""
    return {
        "entity_id": EntityID("TEST123"),
        "content_hash": ContentHash("abc123hash"),
        "run_id": uuid4(),
        "run_type": RunType.INCREMENTAL,
        "source_batch_id": uuid4(),
        "ingestion_ts": datetime.now(UTC),
        "_index": 0,
    }


@pytest.mark.unit
class TestBaseEntity:
    """Tests for BaseEntity validation."""

    def test_base_entity_requires_entity_id(self, base_entity_kwargs):
        """Test that empty entity_id raises ValueError."""
        base_entity_kwargs["entity_id"] = EntityID("")
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            Activity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_chembl_id="CHEMBL123",
                target_chembl_id="CHEMBL456",
                assay_chembl_id="CHEMBL789",
            )

    def test_base_entity_requires_content_hash(self, base_entity_kwargs):
        """Test that empty content_hash raises ValueError."""
        base_entity_kwargs["content_hash"] = ContentHash("")
        with pytest.raises(ValueError, match="Content hash cannot be empty"):
            Activity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_chembl_id="CHEMBL123",
                target_chembl_id="CHEMBL456",
                assay_chembl_id="CHEMBL789",
            )

    def test_base_entity_requires_ingestion_ts(self, base_entity_kwargs):
        """Test that ingestion_ts is required (no default) per ADR-014."""
        # Remove ingestion_ts to verify it's required
        kwargs_without_ts = {
            k: v for k, v in base_entity_kwargs.items() if k != "ingestion_ts"
        }
        with pytest.raises(TypeError, match="ingestion_ts"):
            Activity(
                **kwargs_without_ts,
                activity_id="ACT1",
                molecule_chembl_id="CHEMBL123",
                target_chembl_id="CHEMBL456",
                assay_chembl_id="CHEMBL789",
            )

    def test_base_entity_accepts_explicit_ingestion_ts(self, base_entity_kwargs):
        """Test that explicitly passed ingestion_ts is used."""
        activity = Activity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_chembl_id="CHEMBL123",
            target_chembl_id="CHEMBL456",
            assay_chembl_id="CHEMBL789",
        )
        assert activity.ingestion_ts is not None
        assert isinstance(activity.ingestion_ts, datetime)
        assert activity.ingestion_ts.tzinfo == UTC


@pytest.mark.unit
class TestActivity:
    """Tests for Activity entity."""

    def test_activity_creation_success(self, base_entity_kwargs):
        """Test successful Activity creation with required fields."""
        activity = Activity(
            **base_entity_kwargs,
            activity_id="ACT123",
            molecule_chembl_id="CHEMBL1",
            target_chembl_id="CHEMBL2",
            assay_chembl_id="CHEMBL3",
        )
        assert activity.activity_id == "ACT123"
        assert activity.molecule_chembl_id == "CHEMBL1"
        assert activity.target_chembl_id == "CHEMBL2"
        assert activity.assay_chembl_id == "CHEMBL3"

    def test_activity_with_optional_fields(self, base_entity_kwargs):
        """Test Activity with all optional fields."""
        activity = Activity(
            **base_entity_kwargs,
            activity_id="ACT456",
            molecule_chembl_id="CHEMBL100",
            target_chembl_id="CHEMBL200",
            assay_chembl_id="CHEMBL300",
            standard_type="IC50",
            standard_value=10.5,
            standard_units="nM",
            standard_relation="=",
            pchembl_value=7.5,
            activity_comment="High quality",
            data_validity_comment="Valid",
        )
        assert activity.standard_type == "IC50"
        assert activity.standard_value == 10.5
        assert activity.standard_units == "nM"
        assert activity.standard_relation == "="
        assert activity.pchembl_value == 7.5
        assert activity.activity_comment == "High quality"
        assert activity.data_validity_comment == "Valid"

    def test_activity_requires_activity_id(self, base_entity_kwargs):
        """Test that empty activity_id raises ValueError."""
        with pytest.raises(ValueError, match="Activity ID is required"):
            Activity(
                **base_entity_kwargs,
                activity_id="",
                molecule_chembl_id="CHEMBL1",
                target_chembl_id="CHEMBL2",
                assay_chembl_id="CHEMBL3",
            )

    def test_activity_pchembl_must_be_nonnegative(self, base_entity_kwargs):
        """Test that negative pchembl_value raises ValueError."""
        with pytest.raises(ValueError, match="pChemBL value must be non-negative"):
            Activity(
                **base_entity_kwargs,
                activity_id="ACT1",
                molecule_chembl_id="CHEMBL1",
                target_chembl_id="CHEMBL2",
                assay_chembl_id="CHEMBL3",
                pchembl_value=-1.0,
            )

    def test_activity_pchembl_zero_is_valid(self, base_entity_kwargs):
        """Test that zero pchembl_value is valid."""
        activity = Activity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_chembl_id="CHEMBL1",
            target_chembl_id="CHEMBL2",
            assay_chembl_id="CHEMBL3",
            pchembl_value=0.0,
        )
        assert activity.pchembl_value == 0.0

    def test_activity_is_frozen(self, base_entity_kwargs):
        """Test that Activity is immutable."""
        activity = Activity(
            **base_entity_kwargs,
            activity_id="ACT1",
            molecule_chembl_id="CHEMBL1",
            target_chembl_id="CHEMBL2",
            assay_chembl_id="CHEMBL3",
        )
        with pytest.raises(AttributeError):
            activity.activity_id = "NEW_ID"


@pytest.mark.unit
class TestCompound:
    """Tests for Compound entity."""

    def test_compound_creation_with_smiles(self, base_entity_kwargs):
        """Test Compound creation with canonical SMILES."""
        compound = Compound(
            **base_entity_kwargs,
            cid="12345",
            canonical_smiles="CCO",
        )
        assert compound.cid == "12345"
        assert compound.canonical_smiles == "CCO"

    def test_compound_creation_with_isomeric_smiles(self, base_entity_kwargs):
        """Test Compound creation with isomeric SMILES."""
        compound = Compound(
            **base_entity_kwargs,
            cid="12345",
            isomeric_smiles="C[C@H](O)CC",
        )
        assert compound.isomeric_smiles == "C[C@H](O)CC"

    def test_compound_creation_with_inchi(self, base_entity_kwargs):
        """Test Compound creation with InChI."""
        compound = Compound(
            **base_entity_kwargs,
            cid="12345",
            inchi="InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        )
        assert compound.inchi == "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"

    def test_compound_with_all_optional_fields(self, base_entity_kwargs):
        """Test Compound with all optional fields."""
        compound = Compound(
            **base_entity_kwargs,
            cid="2244",
            molecular_formula="C9H8O4",
            molecular_weight="180.16",
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            isomeric_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            inchi="InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            inchikey="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            iupac_name="2-acetyloxybenzoic acid",
        )
        assert compound.molecular_formula == "C9H8O4"
        assert compound.molecular_weight == "180.16"
        assert compound.inchikey == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert compound.iupac_name == "2-acetyloxybenzoic acid"

    def test_compound_requires_cid(self, base_entity_kwargs):
        """Test that empty cid raises ValueError."""
        with pytest.raises(ValueError, match="Compound CID is required"):
            Compound(
                **base_entity_kwargs,
                cid="",
                canonical_smiles="CCO",
            )

    def test_compound_requires_structural_identifier(self, base_entity_kwargs):
        """Test that at least one structural identifier is required."""
        with pytest.raises(
            ValueError, match="Compound must have at least one structural identifier"
        ):
            Compound(
                **base_entity_kwargs,
                cid="12345",
                # No SMILES or InChI
            )

    def test_compound_inchikey_alone_not_sufficient(self, base_entity_kwargs):
        """Test that InChIKey alone is not sufficient."""
        with pytest.raises(
            ValueError, match="Compound must have at least one structural identifier"
        ):
            Compound(
                **base_entity_kwargs,
                cid="12345",
                inchikey="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                # InChIKey is not counted as structural identifier
            )

    def test_compound_is_frozen(self, base_entity_kwargs):
        """Test that Compound is immutable."""
        compound = Compound(
            **base_entity_kwargs,
            cid="12345",
            canonical_smiles="CCO",
        )
        with pytest.raises(AttributeError):
            compound.cid = "99999"


@pytest.mark.unit
class TestProtein:
    """Tests for Protein entity."""

    def test_protein_creation_success(self, base_entity_kwargs):
        """Test successful Protein creation."""
        protein = Protein(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        assert protein.accession == "P12345"
        assert protein.entry_name == "TEST_HUMAN"
        assert protein.protein_name == "Test protein"

    def test_protein_with_all_optional_fields(self, base_entity_kwargs):
        """Test Protein with all optional fields."""
        protein = Protein(
            **base_entity_kwargs,
            accession="P00533",
            entry_name="EGFR_HUMAN",
            protein_name="Epidermal growth factor receptor",
            gene_names=["EGFR", "ERBB1"],
            organism_id=9606,
            sequence_length=1210,
        )
        assert protein.gene_names == ["EGFR", "ERBB1"]
        assert protein.organism_id == 9606
        assert protein.sequence_length == 1210

    def test_protein_default_gene_names_empty_list(self, base_entity_kwargs):
        """Test that gene_names defaults to empty list."""
        protein = Protein(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        assert protein.gene_names == []

    def test_protein_requires_accession(self, base_entity_kwargs):
        """Test that empty accession raises ValueError."""
        with pytest.raises(ValueError, match="Protein accession is required"):
            Protein(
                **base_entity_kwargs,
                accession="",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
            )

    def test_protein_sequence_length_must_be_positive(self, base_entity_kwargs):
        """Test that non-positive sequence_length raises ValueError."""
        with pytest.raises(ValueError, match="Sequence length must be positive"):
            Protein(
                **base_entity_kwargs,
                accession="P12345",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
                sequence_length=0,
            )

    def test_protein_sequence_length_negative_raises(self, base_entity_kwargs):
        """Test that negative sequence_length raises ValueError."""
        with pytest.raises(ValueError, match="Sequence length must be positive"):
            Protein(
                **base_entity_kwargs,
                accession="P12345",
                entry_name="TEST_HUMAN",
                protein_name="Test protein",
                sequence_length=-100,
            )

    def test_protein_sequence_length_none_is_valid(self, base_entity_kwargs):
        """Test that None sequence_length is valid."""
        protein = Protein(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
            sequence_length=None,
        )
        assert protein.sequence_length is None

    def test_protein_is_frozen(self, base_entity_kwargs):
        """Test that Protein is immutable."""
        protein = Protein(
            **base_entity_kwargs,
            accession="P12345",
            entry_name="TEST_HUMAN",
            protein_name="Test protein",
        )
        with pytest.raises(AttributeError):
            protein.accession = "P99999"


@pytest.mark.unit
class TestWork:
    """Tests for CrossRef Work entity."""

    def test_work_creation_success(self, base_entity_kwargs):
        """Test successful Work creation."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1234/test.article",
        )
        assert work.doi == "10.1234/test.article"
        assert work.source == "crossref"
        assert work.doc_type == "PUBLICATION"

    def test_work_with_all_optional_fields(self, base_entity_kwargs):
        """Test Work with all optional fields."""
        work = Work(
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
            first_page="480",
            last_page="485",
            year=2023,
            published_print="2023-07-25",
            published_online="2023-07-20",
            doc_type="PUBLICATION",
            citation_count=2847,
            reference_count=50,
            language="en",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            subjects=["Genetics", "Genomics"],
        )
        assert work.title == "The complete genome sequence"
        assert work.journal == "Nature"
        assert work.year == 2023
        assert work.citation_count == 2847
        assert len(work.authors) == 2
        assert len(work.issn) == 2

    def test_work_requires_doi(self, base_entity_kwargs):
        """Test that empty doi raises ValueError."""
        with pytest.raises(ValueError, match="CrossRef Work DOI is required"):
            Work(
                **base_entity_kwargs,
                doi="",
            )

    def test_work_preprint_doc_type(self, base_entity_kwargs):
        """Test Work with PREPRINT doc_type."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1101/2023.01.01.123456",
            doc_type="PREPRINT",
        )
        assert work.doc_type == "PREPRINT"

    def test_work_default_authors_empty_list(self, base_entity_kwargs):
        """Test that authors defaults to empty list."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert work.authors == []

    def test_work_default_issn_empty_list(self, base_entity_kwargs):
        """Test that issn defaults to empty list."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert work.issn == []

    def test_work_default_subjects_empty_list(self, base_entity_kwargs):
        """Test that subjects defaults to empty list."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        assert work.subjects == []

    def test_work_is_frozen(self, base_entity_kwargs):
        """Test that Work is immutable."""
        work = Work(
            **base_entity_kwargs,
            doi="10.1234/test",
        )
        with pytest.raises(AttributeError):
            work.doi = "10.9999/changed"
