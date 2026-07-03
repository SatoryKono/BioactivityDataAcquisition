# mypy: disable-error-code="misc"
"""UniProt cross-references and taxonomy/GO components.

Part of UniprotTargetSchema split to comply with LOC limits.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "UniprotXrefSchema",
]


class UniprotXrefSchema(pa.DataFrameModel):  # Pandera typing limitation
    """Database cross-references, taxonomy and GO components."""

    # === Cross-References (Extracted) ===
    go_terms: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of GO terms with evidence codes"
    )
    drugbank_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of DrugBank identifiers"
    )
    chembl_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of ChEMBL target identifiers"
    )
    guidetopharmacology_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of Guide to Pharmacology identifiers"
    )
    pdb_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of PDB cross-references with structure details",
    )
    interpro_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of InterPro domain entries with id and name",
    )
    pfam_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of Pfam family entries with id, name, and match_status",
    )
    reactome_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of Reactome pathway entries with id and pathway_name",
    )

    # === Taxonomy Components ===
    superkingdom: Series[str] | None = pa.Field(
        nullable=True,
        description="Superkingdom/Domain (Bacteria, Archaea, Eukaryota, Viruses)",
    )
    phylum: Series[str] | None = pa.Field(
        nullable=True,
        description="Phylum from taxonomic lineage",
    )
    genus: Series[str] | None = pa.Field(
        nullable=True,
        description="Genus from taxonomic lineage",
    )

    # === GO Components ===
    molecular_function: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of GO molecular function terms (aspect F)",
    )
    cellular_component: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of GO cellular component terms (aspect C)",
    )
