# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit coverage for pipeline payload normalization helpers (#8595)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config import pipeline_payload_normalization as mod

pytestmark = pytest.mark.unit


def test_present_override_paths_only_includes_existing_keys() -> None:
    paths = mod._present_override_paths(
        {"batch_size": 10, "other": 1},
        ("batch_size", "page_size"),
        prefix="source",
    )
    assert paths == ["source.batch_size"]


def test_has_mapping_content_rejects_empty_and_non_mapping() -> None:
    assert mod._has_mapping_content({"a": 1}) is True
    assert mod._has_mapping_content({}) is False
    assert mod._has_mapping_content(None) is False
    assert mod._has_mapping_content("x") is False


def test_collect_forbidden_provider_config_overrides_empty_when_absent() -> None:
    assert mod._collect_forbidden_provider_config_overrides(None) == []
    assert mod._collect_forbidden_provider_config_overrides("not-a-map") == []


def test_collect_forbidden_provider_config_overrides_lists_transport_keys() -> None:
    forbidden = mod._collect_forbidden_provider_config_overrides(
        {
            "batch_size": 50,
            "pagination": {"page_size": 25},
            "page_size": 25,
        }
    )
    assert "source.provider_config" in forbidden
    assert "source.provider_config.pagination" in forbidden
    assert "source.provider_config.batch_size" in forbidden
    assert "source.provider_config.page_size" in forbidden


def test_collect_forbidden_pipeline_source_overrides_composes_helpers() -> None:
    forbidden = sorted(
        mod._collect_forbidden_pipeline_source_overrides(
            {
                "batch_size": 10,
                "rate_limit": {"rps": 1},
                "circuit_breaker": {"enabled": True},
                "batch": {"size": 5},
                "provider_config": {"max_url_length": 2000},
            }
        )
    )
    assert "source.batch" in forbidden
    assert "source.batch_size" in forbidden
    assert "source.rate_limit" in forbidden
    assert "source.circuit_breaker" in forbidden
    assert "source.provider_config" in forbidden
    assert "source.provider_config.max_url_length" in forbidden


def test_collect_forbidden_pipeline_source_overrides_allows_clean_entity_source() -> None:
    assert (
        mod._collect_forbidden_pipeline_source_overrides(
            {"parameters": {"limit": 10}}
        )
        == []
    )


def test_load_source_section_rejects_forbidden_transport_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail-closed: entity source must not redefine provider transport."""

    class _FakeSource:
        def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]:
            return {"source": {"base_url": "https://example.test"}}

    monkeypatch.setattr(
        mod,
        "load_source_config_from_root",
        lambda provider, configs_root=None: _FakeSource(),
    )

    # parents[2] of configs/entities/chembl/activity.yaml → configs/
    config_path = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    config: dict[str, object] = {
        "provider": "chembl",
        "source": {"batch_size": 99},
    }
    with pytest.raises(ValueError, match="batch_size"):
        mod.load_source_section(config, config_path)


def test_load_source_section_merges_when_entity_source_is_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeSource:
        def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]:
            return {"source": {"base_url": "https://example.test", "timeout": 30}}

    monkeypatch.setattr(
        mod,
        "load_source_config_from_root",
        lambda provider, configs_root=None: _FakeSource(),
    )

    config_path = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    config: dict[str, object] = {
        "provider": "chembl",
        "source": {"parameters": {"limit": 5}},
    }
    mod.load_source_section(config, config_path)
    source = config["source"]
    assert isinstance(source, dict)
    assert source["base_url"] == "https://example.test"
    assert source["parameters"] == {"limit": 5}
