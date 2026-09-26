"""Shipped normalization profile declarations for the canonical registry."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_assay import (
    CHEMBL_ASSAY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_assay_parameters import (
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_cell_line import (
    CHEMBL_CELL_LINE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_compound_record import (
    CHEMBL_COMPOUND_RECORD_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_molecule import (
    CHEMBL_MOLECULE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_protein_class import (
    CHEMBL_PROTEIN_CLASS_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication import (
    CHEMBL_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication_similarity import (
    CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication_term import (
    CHEMBL_PUBLICATION_TERM_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_subcellular_fraction import (
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target import (
    CHEMBL_TARGET_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target_component import (
    CHEMBL_TARGET_COMPONENT_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target_protein_classification import (
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_tissue import (
    CHEMBL_TISSUE_PROFILE,
)
from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.openalex_publication import (
    OPENALEX_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from bioetl.domain.normalization.profiles.pubmed_publication import (
    PUBMED_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.uniprot_idmapping import (
    UNIPROT_IDMAPPING_PROFILE,
)
from bioetl.domain.normalization.profiles.uniprot_protein import (
    UNIPROT_PROTEIN_PROFILE,
)


@dataclass(frozen=True, slots=True)
class NormalizationProfileDeclaration:
    """One shipped normalization-profile registry declaration."""

    provider: str
    entity_type: str
    profile: NormalizationProfile
    module_path: str


NORMALIZATION_PROFILE_DECLARATIONS: tuple[NormalizationProfileDeclaration, ...] = (
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="activity",
        profile=CHEMBL_ACTIVITY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_activity.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="assay",
        profile=CHEMBL_ASSAY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_assay.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="assay_parameters",
        profile=CHEMBL_ASSAY_PARAMETERS_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="cell_line",
        profile=CHEMBL_CELL_LINE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_cell_line.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="compound_record",
        profile=CHEMBL_COMPOUND_RECORD_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_compound_record.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="molecule",
        profile=CHEMBL_MOLECULE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_molecule.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="protein_class",
        profile=CHEMBL_PROTEIN_CLASS_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_protein_class.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication",
        profile=CHEMBL_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication_similarity",
        profile=CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication_similarity.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication_term",
        profile=CHEMBL_PUBLICATION_TERM_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication_term.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="subcellular_fraction",
        profile=CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_subcellular_fraction.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="target",
        profile=CHEMBL_TARGET_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_target.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="target_component",
        profile=CHEMBL_TARGET_COMPONENT_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_target_component.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="target_protein_classification",
        profile=CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_target_protein_classification.py",
    ),
    NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="tissue",
        profile=CHEMBL_TISSUE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_tissue.py",
    ),
    NormalizationProfileDeclaration(
        provider="crossref",
        entity_type="publication",
        profile=CROSSREF_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/crossref_publication.py",
    ),
    NormalizationProfileDeclaration(
        provider="openalex",
        entity_type="publication",
        profile=OPENALEX_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/openalex_publication.py",
    ),
    NormalizationProfileDeclaration(
        provider="pubchem",
        entity_type="compound",
        profile=PUBCHEM_COMPOUND_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/pubchem_compound.py",
    ),
    NormalizationProfileDeclaration(
        provider="pubmed",
        entity_type="publication",
        profile=PUBMED_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/pubmed_publication.py",
    ),
    NormalizationProfileDeclaration(
        provider="semanticscholar",
        entity_type="publication",
        profile=SEMANTICSCHOLAR_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/semanticscholar_publication.py",
    ),
    NormalizationProfileDeclaration(
        provider="uniprot",
        entity_type="idmapping",
        profile=UNIPROT_IDMAPPING_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/uniprot_idmapping.py",
    ),
    NormalizationProfileDeclaration(
        provider="uniprot",
        entity_type="protein",
        profile=UNIPROT_PROTEIN_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/uniprot_protein.py",
    ),
)
