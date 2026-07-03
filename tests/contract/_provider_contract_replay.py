"""Replay registry for provider contract drift checks."""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests.contract._provider_contract_drift import compare_provider_probe_to_snapshot

ROOT = Path(__file__).resolve().parents[2]
_GIT_LFS_POINTER_PREFIX = "version https://git-lfs.github.com/spec/v1"


@dataclass(frozen=True)
class ProviderContractReplayProbe:
    """Single replayable provider probe backed by a VCR cassette interaction."""

    provider: str
    probe: str
    cassette_rel_path: str
    interaction_index: int = 0

    @property
    def cassette_path(self) -> Path:
        """Return the absolute cassette path."""
        return ROOT / self.cassette_rel_path


PROVIDER_CONTRACT_REPLAY_PROBES: tuple[ProviderContractReplayProbe, ...] = (
    ProviderContractReplayProbe(
        provider="chembl",
        probe="activity_endpoint_schema",
        cassette_rel_path="tests/fixtures/vcr/chembl/TestChemblAdapter.test_fetch_activities.yaml",
        interaction_index=1,
    ),
    ProviderContractReplayProbe(
        provider="chembl",
        probe="molecule_endpoint_schema",
        cassette_rel_path="tests/fixtures/vcr/chembl/TestMoleculeExtractionParams.test_molecule_filtered_api_request.yaml",
    ),
    ProviderContractReplayProbe(
        provider="chembl",
        probe="target_endpoint_schema",
        cassette_rel_path="tests/fixtures/vcr/chembl/TestTargetExtractionParams.test_target_filtered_api_request.yaml",
    ),
    ProviderContractReplayProbe(
        provider="crossref",
        probe="work_lookup_by_doi",
        cassette_rel_path="tests/fixtures/vcr/crossref/works_batch.yaml",
        interaction_index=1,
    ),
    ProviderContractReplayProbe(
        provider="crossref",
        probe="works_query_endpoint",
        cassette_rel_path="tests/fixtures/vcr/crossref/test_crossref_search_by_title.yaml",
    ),
    ProviderContractReplayProbe(
        provider="crossref",
        probe="agency_lookup_for_doi",
        cassette_rel_path="tests/fixtures/vcr/crossref/provider_contract_agency_lookup_for_doi.yaml",
    ),
    ProviderContractReplayProbe(
        provider="openalex",
        probe="works_filter_by_doi",
        cassette_rel_path="tests/fixtures/vcr/openalex/TestOpenAlexAdapterIntegration.test_fetch_filtered_by_doi.yaml",
    ),
    ProviderContractReplayProbe(
        provider="openalex",
        probe="works_search_endpoint",
        cassette_rel_path="tests/fixtures/vcr/openalex/TestOpenAlexAdapterIntegration.test_fetch_with_query.yaml",
    ),
    ProviderContractReplayProbe(
        provider="openalex",
        probe="health_probe_shape",
        cassette_rel_path="tests/fixtures/vcr/openalex/TestOpenAlexAdapterIntegration.test_health_check.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubchem",
        probe="compound_by_molecule_id",
        cassette_rel_path="tests/fixtures/vcr/pubchem/test_pubchem_compound_structural_fields.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubchem",
        probe="compound_property_endpoint",
        cassette_rel_path="tests/fixtures/vcr/pubchem/provider_contract_compound_property_endpoint.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubchem",
        probe="smiles_search",
        cassette_rel_path="tests/fixtures/vcr/pubchem/provider_contract_smiles_search.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubmed",
        probe="esearch_endpoint",
        cassette_rel_path="tests/fixtures/vcr/pubmed/test_health_check.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubmed",
        probe="esummary_endpoint",
        cassette_rel_path="tests/fixtures/vcr/pubmed/provider_contract_esummary_endpoint.yaml",
    ),
    ProviderContractReplayProbe(
        provider="pubmed",
        probe="einfo_database_list",
        cassette_rel_path="tests/fixtures/vcr/pubmed/provider_contract_einfo_database_list.yaml",
    ),
    ProviderContractReplayProbe(
        provider="semanticscholar",
        probe="paper_search_endpoint",
        cassette_rel_path="tests/fixtures/vcr/semanticscholar/TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml",
    ),
    ProviderContractReplayProbe(
        provider="semanticscholar",
        probe="paper_batch_lookup_by_doi",
        cassette_rel_path="tests/fixtures/vcr/semanticscholar/TestSemanticScholarAdapterIntegration.test_fetch_batch_dois.yaml",
    ),
    ProviderContractReplayProbe(
        provider="uniprot",
        probe="uniprotkb_search_endpoint",
        cassette_rel_path="tests/fixtures/vcr/uniprot/TestUniProtAdapterIntegration.test_fetch_proteins.yaml",
        interaction_index=0,
    ),
    ProviderContractReplayProbe(
        provider="uniprot",
        probe="specific_protein_lookup",
        cassette_rel_path="tests/fixtures/vcr/uniprot/provider_contract_specific_protein_lookup.yaml",
    ),
    ProviderContractReplayProbe(
        provider="uniprot",
        probe="taxonomy_endpoint",
        cassette_rel_path="tests/fixtures/vcr/uniprot/provider_contract_taxonomy_endpoint.yaml",
    ),
)


def load_provider_contract_replay_payload(case: ProviderContractReplayProbe) -> Any:
    """Load JSON payload from a replay cassette interaction."""
    cassette_text = case.cassette_path.read_text(encoding="utf-8")
    if cassette_text.startswith(_GIT_LFS_POINTER_PREFIX):
        pytest.skip(
            "Provider contract replay cassette is a Git LFS pointer; "
            f"run git lfs pull before replaying {case.cassette_rel_path}"
        )

    cassette_payload_raw = yaml.safe_load(cassette_text)
    if not isinstance(cassette_payload_raw, dict):
        raise AssertionError(
            f"{case.cassette_rel_path} must be a VCR cassette YAML mapping for "
            f"{case.provider}.{case.probe}, got "
            f"{type(cassette_payload_raw).__name__}"
        )

    cassette_payload = cast(dict[str, Any], cassette_payload_raw)
    interactions = cast(list[dict[str, Any]], cassette_payload.get("interactions", []))
    if case.interaction_index >= len(interactions):
        raise AssertionError(
            f"{case.cassette_rel_path} is missing interaction index "
            f"{case.interaction_index} for {case.provider}.{case.probe}"
        )

    interaction = interactions[case.interaction_index]
    response = cast(dict[str, Any], interaction["response"])
    status = cast(dict[str, Any], response["status"])
    status_code = cast(int, status["code"])
    if status_code < 200 or status_code >= 300:
        raise AssertionError(
            f"{case.cassette_rel_path} returned HTTP {status_code} "
            f"for {case.provider}.{case.probe}"
        )

    body = cast(dict[str, Any], response["body"])
    raw_body = body.get("string")
    if isinstance(raw_body, bytes):
        headers = cast(dict[str, Any], response.get("headers", {}))
        content_encodings = [
            str(value).lower()
            for values in headers.values()
            for value in (values if isinstance(values, list) else [values])
        ]
        if any("gzip" in value for value in content_encodings):
            raw_body = gzip.decompress(raw_body).decode("utf-8")
        else:
            raw_body = raw_body.decode("utf-8")
    if not isinstance(raw_body, str):
        raise AssertionError(
            f"{case.cassette_rel_path} has no JSON string body for "
            f"{case.provider}.{case.probe}"
        )
    return json.loads(raw_body)


def build_provider_contract_replay_report(
    case: ProviderContractReplayProbe,
) -> dict[str, Any]:
    """Build a drift report from the replay cassette backing a probe."""
    payload = load_provider_contract_replay_payload(case)
    report = compare_provider_probe_to_snapshot(
        case.provider,
        case.probe,
        payload,
    )
    report["cassette_rel_path"] = case.cassette_rel_path
    report["interaction_index"] = case.interaction_index
    return report
