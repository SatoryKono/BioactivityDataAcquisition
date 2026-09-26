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
"""Unit tests for extraction-input preflight (#10578 / #10610)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from bioetl.composition.runtime_builders.inputs_extraction_preflight import (
    ExtractionInputError,
    validate_resolved_extraction_input,
)
from bioetl.domain.filtering import FilterColumn, InputFilterConfig

pytestmark = pytest.mark.unit

_REQUIRED_PIPELINE = "pubchem_compound"
_OPEN_SCAN_PIPELINE = "chembl_activity"


def test_open_scan_pipeline_skips_preflight() -> None:
    provenance = validate_resolved_extraction_input(
        pipeline_name=_OPEN_SCAN_PIPELINE,
        provider="chembl",
        query=None,
        filter_config=None,
    )
    assert provenance is None


def test_nonempty_query_is_accepted_without_filter() -> None:
    provenance = validate_resolved_extraction_input(
        pipeline_name=_REQUIRED_PIPELINE,
        provider="pubchem",
        query="  aspirin  ",
        filter_config=None,
    )
    assert provenance is not None
    assert provenance.input_kind == "query"
    assert provenance.id_count is None
    assert provenance.source_path is None


def test_blank_query_without_filter_raises() -> None:
    with pytest.raises(ExtractionInputError, match="has neither"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query="   ",
            filter_config=None,
        )


def test_disabled_filter_without_query_raises() -> None:
    with pytest.raises(ExtractionInputError, match="has neither"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=InputFilterConfig(enabled=False),
        )


def test_direct_multi_filter_ids_are_counted() -> None:
    filter_config = InputFilterConfig(
        enabled=True,
        direct_multi_filter_ids={"cid": ("1", "2"), "sid": ("9",)},
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name=_REQUIRED_PIPELINE,
        provider="pubchem",
        query=None,
        filter_config=filter_config,
    )
    assert provenance is not None
    assert provenance.input_kind == "direct_multi_filter_ids"
    assert provenance.filter_field == "cid,sid"
    assert provenance.id_count == 3


def test_empty_direct_multi_filter_ids_raise() -> None:
    filter_config = SimpleNamespace(
        enabled=True,
        is_direct_multi_filter=True,
        direct_multi_filter_ids={"cid": ()},
        is_direct_filter=False,
        direct_filter_ids=None,
        source_path=None,
        column_name=None,
        columns=(),
        filter_field=None,
    )
    with pytest.raises(ExtractionInputError, match="direct_multi_filter_ids"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,  # type: ignore[arg-type]
        )


def test_direct_filter_ids_are_counted() -> None:
    filter_config = InputFilterConfig(
        enabled=True,
        filter_field="molecule_chembl_id",
        direct_filter_ids=("CHEMBL1", "CHEMBL2"),
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name=_REQUIRED_PIPELINE,
        provider="pubchem",
        query=None,
        filter_config=filter_config,
    )
    assert provenance is not None
    assert provenance.input_kind == "direct_filter_ids"
    assert provenance.filter_field == "molecule_chembl_id"
    assert provenance.id_count == 2


def test_empty_direct_filter_ids_raise() -> None:
    filter_config = SimpleNamespace(
        enabled=True,
        is_direct_multi_filter=False,
        direct_multi_filter_ids=None,
        is_direct_filter=True,
        direct_filter_ids=(),
        source_path=None,
        column_name=None,
        columns=(),
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="direct_filter_ids"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,  # type: ignore[arg-type]
        )


def test_csv_filter_without_source_path_raises() -> None:
    filter_config = SimpleNamespace(
        enabled=True,
        is_direct_multi_filter=False,
        is_direct_filter=False,
        source_path=None,
        column_name="cid",
        columns=(),
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="source_path is"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,  # type: ignore[arg-type]
        )


def test_csv_filter_without_column_name_raises() -> None:
    filter_config = SimpleNamespace(
        enabled=True,
        is_direct_multi_filter=False,
        is_direct_filter=False,
        source_path="ids.csv",
        column_name=None,
        columns=(),
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="without a"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,  # type: ignore[arg-type]
        )


def test_csv_column_name_falls_back_to_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "ids.csv"
    csv_path.write_text("cid\n1\n2\n", encoding="utf-8")
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        columns=(FilterColumn(column_name="cid", filter_field="cid"),),
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name=_REQUIRED_PIPELINE,
        provider="pubchem",
        query=None,
        filter_config=filter_config,
    )
    assert provenance is not None
    assert provenance.input_kind == "csv_filter_ids"
    assert provenance.column_name == "cid"
    assert provenance.id_count == 2
    assert provenance.source_path == str(csv_path)


def test_csv_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(missing),
        column_name="cid",
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="absent"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,
        )


def test_csv_empty_header_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="cid",
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="no header"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,
        )


def test_csv_missing_column_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "ids.csv"
    csv_path.write_text("other\n1\n", encoding="utf-8")
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="cid",
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="missing required column"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,
        )


def test_csv_blank_ids_raise(tmp_path: Path) -> None:
    csv_path = tmp_path / "ids.csv"
    csv_path.write_text("cid\n\n  \n", encoding="utf-8")
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="cid",
        filter_field="cid",
    )
    with pytest.raises(ExtractionInputError, match="no non-empty"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,
        )


def test_csv_oserror_is_wrapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = tmp_path / "ids.csv"
    csv_path.write_text("cid\n1\n", encoding="utf-8")
    filter_config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="cid",
        filter_field="cid",
    )

    def _raise_oserror(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", _raise_oserror)
    with pytest.raises(ExtractionInputError, match="could not be read"):
        validate_resolved_extraction_input(
            pipeline_name=_REQUIRED_PIPELINE,
            provider="pubchem",
            query=None,
            filter_config=filter_config,
        )
