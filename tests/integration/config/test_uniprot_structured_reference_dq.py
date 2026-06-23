from __future__ import annotations

import re
from pathlib import Path

import pytest

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader


@pytest.fixture(scope="module")
def dq_loader() -> DQConfigLoader:
    return DQConfigLoader(Path("configs"))


@pytest.mark.integration
def test_uniprot_protein_structured_reference_patterns_match_runtime_payloads(
    dq_loader: DQConfigLoader,
) -> None:
    config = dq_loader.load("uniprot", "protein")
    patterns = {
        rule.field: rule.pattern
        for rule in config.field_validations
        if rule.validation_type == "pattern"
        and rule.field
        in {"go_terms", "pdb_xrefs", "interpro_xrefs", "pfam_xrefs", "reactome_xrefs"}
    }

    assert re.match(
        patterns["go_terms"] or "",
        '[{"aspect":"F","evidence":"IEA","id":"GO:0005524","term":"ATP binding"}]',
    )
    assert re.match(
        patterns["pdb_xrefs"] or "",
        '[{"chains":"A/B=1-480","id":"1ABC","method":"X-ray","resolution":"2.10 A"}]',
    )
    assert re.match(
        patterns["interpro_xrefs"] or "",
        '[{"id":"IPR000719","name":"Protein kinase domain"}]',
    )
    assert re.match(
        patterns["pfam_xrefs"] or "",
        '[{"id":"PF00069","match_status":"1","name":"Pkinase"}]',
    )
    assert re.match(
        patterns["reactome_xrefs"] or "",
        '[{"id":"R-HSA-177929","pathway_name":"Signaling by EGFR"}]',
    )


@pytest.mark.integration
def test_uniprot_protein_reference_patterns_preserve_legacy_string_arrays(
    dq_loader: DQConfigLoader,
) -> None:
    config = dq_loader.load("uniprot", "protein")
    patterns = {
        rule.field: rule.pattern
        for rule in config.field_validations
        if rule.validation_type == "pattern"
        and rule.field
        in {"go_terms", "pdb_xrefs", "interpro_xrefs", "pfam_xrefs", "reactome_xrefs"}
    }

    assert re.match(patterns["go_terms"] or "", '["GO:0005524","GO:0005886"]')
    assert re.match(patterns["pdb_xrefs"] or "", '["1ABC","2XYZ"]')
    assert re.match(patterns["interpro_xrefs"] or "", '["IPR000001","IPR000719"]')
    assert re.match(patterns["pfam_xrefs"] or "", '["PF00001","PF00069"]')
    assert re.match(
        patterns["reactome_xrefs"] or "",
        '["R-HSA-164843","R-HSA-177929"]',
    )
