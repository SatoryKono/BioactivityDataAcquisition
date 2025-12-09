"""Default field providers implementation."""

from bioetl.domain.ports.providers import DefaultFieldProviderABC

_ASSAY_DEFAULT_FIELDS = [
    "aidx",
    "assay_category",
    "assay_cell_type",
    "assay_chembl_id",
    "assay_classifications",
    "assay_group",
    "assay_organism",
    "assay_parameters",
    "assay_strain",
    "assay_subcellular_fraction",
    "assay_tax_id",
    "assay_test_type",
    "assay_tissue",
    "assay_type",
    "assay_type_description",
    "bao_format",
    "bao_label",
    "cell_chembl_id",
    "confidence_description",
    "confidence_score",
    "description",
    "document_chembl_id",
    "relationship_description",
    "relationship_type",
    "score",
    "src_assay_id",
    "src_id",
    "target_chembl_id",
    "tissue_chembl_id",
    "variant_sequence",
]


class ApplicationFieldProvider(DefaultFieldProviderABC):
    """Provider for default entity fields defined in application layer."""

    def get_default_fields(self, entity: str) -> list[str]:
        """Get default fields for a given entity."""
        if entity == "assay":
            return list(_ASSAY_DEFAULT_FIELDS)
        return []
