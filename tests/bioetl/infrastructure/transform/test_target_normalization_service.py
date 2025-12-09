from types import SimpleNamespace

import pandas as pd

from bioetl.infrastructure.transform.impl.normalize import (
    DefaultNormalizationTransformerImpl,
)


class _DummyConfig:
    def __init__(self) -> None:
        self.fields = [
            {"name": "target_components", "data_type": "array"},
            {"name": "cross_references", "data_type": "array"},
        ]
        self.normalization = SimpleNamespace(
            case_sensitive_fields=["target_components", "cross_references"],
            id_fields=["target_chembl_id", "accession", "xref_id"],
        )

    def get_fields(self):
        return self.fields

    def get_normalization(self):
        return self.normalization


def test_normalization_service_handles_target_arrays():
    service = DefaultNormalizationTransformerImpl(_DummyConfig())
    df = pd.DataFrame(
        {
            "target_components": [
                """[
                    {
                        "component_id": 1,
                        "accession": "p12345",
                        "target_component_synonyms": ["alpha","beta"],
                        "target_component_xrefs": [
                            {"xref_src": "UniProt", "xref_id": "p12345"},
                            {"xref_src": "PubChem", "xref_id": "CID42"}
                        ]
                    }
                ]""",
            ],
            "cross_references": [
                '[{"xref_src": "UniProt", "xref_id": "p12345"}]',
            ],
        }
    )

    normalized = service.apply_normalize_dataframe(df)

    component_value = normalized.loc[0, "target_components"]
    assert component_value == (
        "accession:P12345|component_id:1|"
        "target_component_synonyms:alpha|beta|"
        "target_component_xrefs:xref_id:P12345|xref_src:UniProt|xref_id:42|xref_src:PubChem"
    )

    xref_value = normalized.loc[0, "cross_references"]
    assert xref_value == "xref_id:P12345|xref_src:UniProt"
