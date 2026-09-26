"""Provider attribution helpers for export sidecar manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ProviderAttributionRecord:
    """Provider-level data attribution and redistribution metadata."""

    provider: str
    source_url: str
    license_name: str
    license_url: str
    attribution_text: str
    redistribution_notes: str
    caveats: tuple[str, ...] = ()


ProviderAttribution = ProviderAttributionRecord


_PROVIDER_ATTRIBUTIONS: dict[str, ProviderAttributionRecord] = {
    "chembl": ProviderAttributionRecord(
        provider="chembl",
        source_url="https://www.ebi.ac.uk/chembl/",
        license_name="CC BY-SA 3.0",
        license_url="https://www.ebi.ac.uk/chembl/terms",
        attribution_text="ChEMBL data is provided by EMBL-EBI.",
        redistribution_notes=(
            "Preserve ChEMBL attribution and review share-alike obligations for "
            "redistributed derived datasets."
        ),
    ),
    "crossref": ProviderAttributionRecord(
        provider="crossref",
        source_url="https://api.crossref.org",
        license_name="Crossref metadata terms",
        license_url="https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
        attribution_text="Crossref metadata is provided by Crossref members.",
        redistribution_notes=(
            "Metadata is generally open, but linked full text and abstracts may "
            "carry separate rights."
        ),
    ),
    "openalex": ProviderAttributionRecord(
        provider="openalex",
        source_url="https://openalex.org/",
        license_name="CC0",
        license_url="https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing",
        attribution_text="OpenAlex data is provided by OurResearch.",
        redistribution_notes="OpenAlex states that its data is licensed as CC0.",
    ),
    "pubchem": ProviderAttributionRecord(
        provider="pubchem",
        source_url="https://pubchem.ncbi.nlm.nih.gov/",
        license_name="Source-specific / mixed",
        license_url="https://pubchem.ncbi.nlm.nih.gov/docs/downloads",
        attribution_text="PubChem data is provided by NCBI and PubChem contributors.",
        redistribution_notes=(
            "PubChem aggregates contributor data; check row/source provenance for "
            "source-specific licensing before redistribution."
        ),
    ),
    "pubmed": ProviderAttributionRecord(
        provider="pubmed",
        source_url="https://pubmed.ncbi.nlm.nih.gov/",
        license_name="NLM/NCBI terms and source-specific rights",
        license_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
        attribution_text="PubMed metadata is provided by NLM/NCBI.",
        redistribution_notes=(
            "Citation metadata and abstracts can have different rights; preserve "
            "source attribution and review NLM policies."
        ),
    ),
    "semanticscholar": ProviderAttributionRecord(
        provider="semanticscholar",
        source_url="https://www.semanticscholar.org/",
        license_name="Semantic Scholar API License Agreement",
        license_url="https://www.semanticscholar.org/product/api/license",
        attribution_text="Semantic Scholar data is provided by AI2.",
        redistribution_notes=(
            "Semantic Scholar API/data terms require attribution and may include "
            "use restrictions for API-derived data."
        ),
    ),
    "uniprot": ProviderAttributionRecord(
        provider="uniprot",
        source_url="https://www.uniprot.org/",
        license_name="CC BY 4.0",
        license_url="https://www.uniprot.org/help/license",
        attribution_text="UniProt data is provided by the UniProt Consortium.",
        redistribution_notes="Preserve UniProt attribution for redistributed outputs.",
    ),
}

_COMPOSITE_SOURCES: dict[str, tuple[str, ...]] = {
    "composite.activity": ("chembl",),
    "composite.assay": ("chembl",),
    "composite.molecule": ("chembl", "pubchem"),
    "composite.publication": (
        "chembl",
        "openalex",
        "pubmed",
        "semanticscholar",
    ),
    "composite.target": ("chembl", "uniprot"),
}


def providers_for_table(table_name: str) -> tuple[str, ...]:
    """Resolve provider attribution keys for one exported table."""
    if table_name in _COMPOSITE_SOURCES:
        return _COMPOSITE_SOURCES[table_name]
    provider = table_name.split(".", maxsplit=1)[0].strip()
    return (provider or "unknown",)


def provider_attribution_payload(
    provider: str,
    *,
    strict: bool,
) -> dict[str, object]:
    """Build provider attribution payload or an explicit missing-attribution row."""
    attribution = _PROVIDER_ATTRIBUTIONS.get(provider)
    if attribution is None:
        if strict:
            raise ValueError(
                f"Missing provider attribution for export provider: {provider}"
            )
        return {
            "provider": provider,
            "source_url": None,
            "license_name": "unknown",
            "license_url": None,
            "attribution_text": None,
            "redistribution_notes": (
                "Provider attribution is not registered; review source terms before "
                "redistribution."
            ),
            "caveats": ["missing_provider_attribution"],
        }
    payload = asdict(attribution)
    payload["caveats"] = list(attribution.caveats)
    return payload


def mixed_license_notice(providers: tuple[str, ...]) -> str:
    """Describe license obligations for single- and multi-provider exports."""
    if len(providers) <= 1:
        return (
            "Single-provider export; data/output license obligations remain separate "
            "from the MIT code license."
        )
    return (
        "Composite or multi-provider export; downstream redistribution must satisfy "
        "all contributing provider terms and must not be treated as MIT-licensed data."
    )


__all__ = [
    "ProviderAttribution",
    "ProviderAttributionRecord",
    "mixed_license_notice",
    "provider_attribution_payload",
    "providers_for_table",
]
