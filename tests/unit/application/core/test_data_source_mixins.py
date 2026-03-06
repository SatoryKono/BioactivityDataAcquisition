"""Unit tests for source-metadata delegation mixin."""

from __future__ import annotations

from bioetl.application.core._data_source_mixins import _SourceMetadataDelegationMixin


class _WrappedAdapter:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def get_source_metadata(self, api_version: str | None = None) -> dict[str, str]:
        self.calls.append(api_version)
        return {"api_version": api_version or "none"}


class _DelegatingWrapper(_SourceMetadataDelegationMixin):
    def __init__(self, data_source: object) -> None:
        self._data_source = data_source


def test_get_source_metadata_delegates_to_wrapped_data_source() -> None:
    wrapped = _WrappedAdapter()
    wrapper = _DelegatingWrapper(wrapped)

    result = wrapper.get_source_metadata("v2")

    assert result == {"api_version": "v2"}
    assert wrapped.calls == ["v2"]


def test_get_source_metadata_returns_none_when_method_missing() -> None:
    wrapper = _DelegatingWrapper(data_source=object())

    result = wrapper.get_source_metadata("v2")

    assert result is None


def test_get_source_metadata_returns_none_when_attribute_not_callable() -> None:
    class _NonCallableMetadataSource:
        get_source_metadata = "not-callable"

    wrapper = _DelegatingWrapper(data_source=_NonCallableMetadataSource())

    result = wrapper.get_source_metadata("v2")

    assert result is None
