from dataclasses import dataclass, field

import pandas as pd

from bioetl.domain.normalization_service import ChemblNormalizationService
from bioetl.domain.transform.contracts import NormalizationConfig


@dataclass
class _ConfigStub:
    normalization: NormalizationConfig = field(
        default_factory=lambda: NormalizationConfig(
            case_sensitive_fields=["label"],
            id_fields=["activity_id"],
        )
    )
    fields: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"name": "name", "data_type": "string"},
            {"name": "activity_id", "data_type": "string"},
            {"name": "assay_id", "data_type": "string"},
            {"name": "tags", "data_type": "array"},
            {"name": "metadata", "data_type": "object"},
            {"name": "label", "data_type": "string"},
        ]
    )


def test_chembl_normalization_service_normalizes_scalars_and_ids() -> None:
    service = ChemblNormalizationService(_ConfigStub())
    raw = {
        "name": "  Alpha  ",
        "activity_id": "act1",
        "assay_id": "ass1",
        "extra": "keep",
    }

    normalized = service.normalize(raw)

    assert normalized["name"] == "alpha"
    assert normalized["activity_id"] == "ACT1"
    assert normalized["assay_id"] == "ASS1"
    assert normalized["extra"] == "keep"


def test_chembl_normalization_service_serializes_nested_values() -> None:
    service = ChemblNormalizationService(_ConfigStub())
    raw = {
        "tags": ["A", "b", ""],
        "metadata": {"key": "Value", "other": None},
        "label": "MiXeD",
    }

    normalized = service.normalize(raw)

    assert normalized["tags"] == "a|b"
    assert normalized["metadata"] == "key:value"
    assert normalized["label"] == "MiXeD"


def test_chembl_normalization_service_handles_empty_collections() -> None:
    service = ChemblNormalizationService(_ConfigStub())
    raw = {"tags": [], "metadata": {}, "label": "  NoChange "}

    normalized = service.normalize(raw)

    assert normalized["tags"] is None
    assert normalized["metadata"] is None
    assert normalized["label"] == "NoChange"


def test_chembl_normalization_service_normalizes_dataframe_batch() -> None:
    service = ChemblNormalizationService(_ConfigStub())
    df = pd.DataFrame(
        {
            "name": ["  Alpha  ", "Beta"],
            "activity_id": ["act1", "act2"],
            "tags": [["A", "b"], ["c"]],
            "metadata": [
                {"key": "Value", "other": None},
                {"another": "Item"},
            ],
            "label": ["MiXeD", "lower"],
        }
    )

    normalized_df = service.normalize_dataframe(df)

    assert normalized_df["name"].tolist() == ["alpha", "beta"]
    assert normalized_df["activity_id"].tolist() == ["ACT1", "ACT2"]
    assert normalized_df["tags"].tolist() == ["a|b", "c"]
    assert normalized_df["metadata"].tolist() == ["key:value", "another:item"]
    assert normalized_df["label"].tolist() == ["MiXeD", "lower"]
