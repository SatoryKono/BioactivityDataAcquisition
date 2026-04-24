"""Published immutable ChEMBL semantic-policy payloads for normalization."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
]


@dataclass(frozen=True, slots=True)
class ChemblControlledVocabularyFamily:
    """Immutable controlled-vocabulary policy for one ChEMBL family."""

    family_name: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblOntologyPolicyFamily:
    """Immutable ontology/reference policy for one ChEMBL family."""

    family_name: str
    fields: tuple[str, ...]
    code_label_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChemblPolicyRegistryData:
    """Immutable semantic-policy payload consumed by domain normalization."""

    controlled_vocabularies: tuple[ChemblControlledVocabularyFamily, ...]
    ontology_families: tuple[ChemblOntologyPolicyFamily, ...]
    publication_classification_fields: tuple[str, ...]


DEFAULT_CHEMBL_POLICY_REGISTRY_DATA = ChemblPolicyRegistryData(
    controlled_vocabularies=(
        ChemblControlledVocabularyFamily(
            family_name="units",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.units",
                "chembl_activity.qudt_units",
                "chembl_assay_parameters.units",
                "chembl_assay_parameters.standard_units",
            ),
        ),
        ChemblControlledVocabularyFamily(
            family_name="operators",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.relation",
                "chembl_assay_parameters.relation",
            ),
        ),
        ChemblControlledVocabularyFamily(
            family_name="assay_parameter_types",
            invalid_value_mode="preserve_unknown_uppercase_lexeme",
            fields=("chembl_assay_parameters.type",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="target_component_types",
            invalid_value_mode="reject_unknown_json_array_element",
            fields=("chembl_target.component_types",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="target_component_relationships",
            invalid_value_mode="reject_unknown_json_array_element",
            fields=("chembl_target.component_relationships",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="subcellular_fractions",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_assay.assay_subcellular_fraction",
                "chembl_subcellular_fraction.subcellular_fraction",
            ),
        ),
    ),
    ontology_families=(
        ChemblOntologyPolicyFamily(
            family_name="bao",
            fields=(
                "chembl_activity.bao_endpoint",
                "chembl_activity.bao_format",
                "chembl_assay.bao_format",
            ),
            code_label_fields=("chembl_assay.bao_label",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="uo",
            fields=("chembl_activity.uo_units",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="bto",
            fields=("chembl_tissue.bto_id",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="caloha",
            fields=("chembl_tissue.caloha_id",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="efo",
            fields=(
                "chembl_cell_line.efo_id",
                "chembl_tissue.efo_id",
            ),
        ),
        ChemblOntologyPolicyFamily(
            family_name="clo",
            fields=("chembl_cell_line.clo_id",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="uberon",
            fields=("chembl_tissue.uberon_id",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="cellosaurus",
            fields=("chembl_cell_line.cellosaurus_id",),
        ),
    ),
    publication_classification_fields=(
        "publication_type_unified",
        "publication_subclass",
        "publication_class",
    ),
)
