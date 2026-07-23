"""Scan PROFILE field_rules for lambda normalizer identity failures."""
from __future__ import annotations

import importlib

from bioetl.domain.normalization.profiles._normalization_helpers import _normalizer_ref
from bioetl.domain.normalization.profiles._registry_declarations import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_COMPOUND_RECORD_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_PROTEIN_CLASS_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_PROFILE,
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE,
    CHEMBL_TISSUE_PROFILE,
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBCHEM_COMPOUND_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    UNIPROT_IDMAPPING_PROFILE,
    UNIPROT_PROTEIN_PROFILE,
)

PROFILES = [
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_COMPOUND_RECORD_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_PROTEIN_CLASS_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    CHEMBL_TARGET_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE,
    CHEMBL_TISSUE_PROFILE,
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBCHEM_COMPOUND_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    UNIPROT_IDMAPPING_PROFILE,
    UNIPROT_PROTEIN_PROFILE,
]


def main() -> int:
    failures: list[str] = []
    checked = 0
    for profile in PROFILES:
        for field_name, rule in profile.field_rules.items():
            checked += 1
            try:
                ref = _normalizer_ref(rule.normalizer)
            except TypeError as exc:
                failures.append(
                    f"{profile.profile_name}.{field_name}: {exc} "
                    f"(qualname={getattr(rule.normalizer, '__qualname__', None)!r})"
                )
                continue
            if "<lambda>" in ref:
                failures.append(
                    f"{profile.profile_name}.{field_name}: ref={ref}"
                )
            # also force identity property
            try:
                _ = rule.identity
            except TypeError as exc:
                failures.append(
                    f"{profile.profile_name}.{field_name}.identity: {exc}"
                )
        try:
            _ = profile.identity
        except TypeError as exc:
            failures.append(f"{profile.profile_name}.identity: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{profile.profile_name}.identity other: {exc}")

    print(f"checked_normalizers={checked}")
    print(f"failures={len(failures)}")
    for item in failures:
        print(item)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
