"""Tests for shared publication ISSN field assembly."""

from __future__ import annotations

from bioetl.application.pipelines.common.publication_issn import build_issn_fields


def _serialize(values: object) -> str | None:
    if values is None:
        return None
    return "[" + ",".join(f'"{value}"' for value in values) + "]"


def test_build_issn_fields_from_scalar() -> None:
    fields = build_issn_fields(
        "0028-0836",
        serialize_json_list=_serialize,
    )

    assert fields == {"issn": "0028-0836", "issn_list": '["0028-0836"]'}


def test_build_issn_fields_from_comma_delimited_string() -> None:
    fields = build_issn_fields(
        "0028-0836, 1476-4687",
        serialize_json_list=_serialize,
    )

    assert fields == {
        "issn": "0028-0836",
        "issn_list": '["0028-0836","1476-4687"]',
    }


def test_build_issn_fields_from_missing_value() -> None:
    fields = build_issn_fields(None, serialize_json_list=_serialize)

    assert fields == {"issn": None, "issn_list": None}
