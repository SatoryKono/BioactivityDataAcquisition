from dataclasses import dataclass, field

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
            {"name": "tags", "data_type": "array"},
            {"name": "metadata", "data_type": "object"},
            {"name": "label", "data_type": "string"},
        ]
    )


def test_chembl_normalization_service_normalizes_scalars_and_ids() -> None:
    service = ChemblNormalizationService(_ConfigStub())
    raw = {"name": "  Alpha  ", "activity_id": "act1", "extra": "keep"}

    normalized = service.normalize(raw)

    assert normalized["name"] == "alpha"
    assert normalized["activity_id"] == "ACT1"
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
