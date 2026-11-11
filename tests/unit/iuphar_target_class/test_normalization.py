"""TC-03 normalization, EC depth, and invalid_input isolation."""

from __future__ import annotations

import pytest
from dataclasses import replace

from iuphar_target_class.models import GlueFixture, RawTargetRow, RunProvenance
from iuphar_target_class.normalization import (
    isolated_invalid_result,
    normalize_missing,
    parse_ec_numbers,
    require_approved_normalization,
    validate_batch,
    validate_input,
)

pytestmark = pytest.mark.unit

PROVENANCE = RunProvenance(
    snapshot_id="snapshot-unset",
    normalization_version=None,
    rules_version="plan-v1-r8",
    schema_version="plan-v1-r8",
    retrieved_at="2026-11-11T00:00:00Z",
    run_started_at="2026-11-11T00:00:01Z",
)


def _row(**fields: str | None) -> RawTargetRow:
    payload = {
        "target_id": None,
        "uniprot": None,
        "gene_symbol": None,
        "gene_id": None,
        "organism": None,
        "isoform_suffix": None,
        "isoform_id": None,
        "name": None,
        "synonyms": None,
        "ec": None,
        "keywords": None,
        "predicted_l1": None,
        "predicted_l2": None,
    }
    payload.update(fields)
    return RawTargetRow("row-1", payload, target_kind="protein")


@pytest.mark.parametrize(
    "marker",
    [None, "", " ", "   ", "N/A", "n/a", "#n/a", "  N/A  "],
)
def test_missing_markers_become_none(marker: str | None) -> None:
    assert normalize_missing(marker) is None


def test_valid_text_is_unchanged() -> None:
    assert normalize_missing(" Enzyme ") == " Enzyme "
    assert normalize_missing("P04637") == "P04637"


def test_glued_identifier_is_invalid_and_not_repaired() -> None:
    row = _row(target_id="920840")
    glue = GlueFixture("target_id", "920840", ("concatenated identifiers",))
    validated = validate_input(
        row,
        provenance=PROVENANCE,
        glue_fixtures=(glue,),
        catalog=frozenset({"840"}),
    )
    assert validated.input_validation_status == "invalid_input"
    assert validated.target_id is None
    assert validated.raw_fields["target_id"] == "920840"
    assert validated.catalog_status is None
    assert validated.ec_numbers == ()
    isolated = isolated_invalid_result(validated)
    assert isolated.match_status is None
    assert isolated.effective_class is None
    assert isolated.provenance.snapshot_id == "snapshot-unset"
    assert isolated.row_sha256


def test_glued_uniprot_token_in_a_list_is_invalid() -> None:
    glue = GlueFixture("uniprot", "P04637P00533", ("concatenated identifiers",))
    glued = validate_input(
        _row(uniprot="P04637P00533;P04637"),
        provenance=PROVENANCE,
        glue_fixtures=(glue,),
    )
    assert glued.input_validation_status == "invalid_input"
    assert glued.uniprot_accessions == ()
    assert glued.raw_fields["uniprot"] == "P04637P00533;P04637"
    assert "glued identifier in uniprot" in glued.input_errors
    clean = validate_input(
        _row(uniprot="P04637;P00533"),
        provenance=PROVENANCE,
        glue_fixtures=(glue,),
    )
    assert clean.input_validation_status == "valid"
    assert clean.uniprot_accessions == ("P04637", "P00533")


def test_absent_well_formed_id_is_not_found() -> None:
    validated = validate_input(
        _row(target_id="840"),
        provenance=PROVENANCE,
        catalog=frozenset(),
    )
    assert validated.input_validation_status == "valid"
    assert validated.catalog_status == "not_found"
    assert validated.target_id == "840"


def test_invalid_row_does_not_block_the_batch() -> None:
    glue = GlueFixture("target_id", "920840", ("concatenated identifiers",))
    rows = (
        _row(target_id="920840"),
        RawTargetRow(
            "row-2",
            {"target_id": "100", "uniprot": "P04637-1", "isoform_id": "P04637-1"},
            target_kind="protein",
        ),
    )
    results = validate_batch(rows, provenance=PROVENANCE, glue_fixtures=(glue,))
    assert results[0].input_validation_status == "invalid_input"
    assert results[1].input_validation_status == "valid"
    assert results[1].uniprot_accessions == ("P04637-1",)
    assert results[1].isoform_id == "P04637-1"


def test_partial_ec_keeps_depth_and_is_not_expanded() -> None:
    shallow = parse_ec_numbers("3.-.-.-")
    assert shallow[0].valid is True
    assert shallow[0].depth == 1
    assert shallow[0].confirmed_levels == ("3",)
    assert shallow[0].category_name == "Hydrolases"
    assert "3.1.1.1" not in shallow[0].confirmed_levels
    deeper = parse_ec_numbers("3.1.-.-")
    assert deeper[0].depth == 2
    assert deeper[0].confirmed_levels == ("3", "3.1")
    assert deeper[0].raw == "3.1.-.-"


def test_invalid_ec_is_kept_as_a_diagnostic() -> None:
    validated = validate_input(
        _row(target_id="100", ec="not-an-ec"),
        provenance=PROVENANCE,
        catalog=frozenset({"100"}),
    )
    assert validated.input_validation_status == "valid"
    assert validated.ec_numbers[0].valid is False
    assert validated.diagnostics[0].code == "invalid_ec"
    assert validated.ec_raw == "not-an-ec"


def test_unapproved_marker_version_blocks_an_accepted_run() -> None:
    with pytest.raises(ValueError, match="missing_markers version"):
        require_approved_normalization(PROVENANCE)


@pytest.mark.parametrize("version", ["", " ", "\t\n"])
def test_blank_marker_version_blocks_an_accepted_run(version: str) -> None:
    with pytest.raises(ValueError, match="missing_markers version"):
        require_approved_normalization(
            replace(PROVENANCE, normalization_version=version)
        )


def test_approved_marker_version_allows_the_run() -> None:
    approved = replace(PROVENANCE, normalization_version="markers-v1")
    assert require_approved_normalization(approved) is None


@pytest.mark.parametrize("token", ["².1.1.1", "٣.1.1.1", "3.².1.1", "9" * 5000])
def test_malformed_ec_does_not_interrupt_following_rows(token: str) -> None:
    rows = (_row(ec=token), _row(ec="3.1.1.1"))
    invalid, valid = validate_batch(rows, provenance=PROVENANCE)
    assert invalid.ec_numbers[0].valid is False
    assert invalid.ec_numbers[0].raw == token
    assert invalid.diagnostics[0].code == "invalid_ec"
    assert valid.ec_numbers[0].valid is True


def test_missing_tokens_are_filtered_after_splitting() -> None:
    result = validate_input(
        _row(
            uniprot="P04637;N/A|#n/a",
            ec="3.1.1.1;N/A",
            synonyms="name|n/a",
            keywords="N/A;enzyme",
        ),
        provenance=PROVENANCE,
        catalog=frozenset({"N/A"}),
    )
    assert result.uniprot_accessions == ("P04637",)
    assert result.synonyms == ("name",)
    assert result.keywords == ("enzyme",)
    assert result.catalog_status == "not_found"
    assert len(result.ec_numbers) == 1
    assert result.ec_numbers[0].valid is True
    assert result.diagnostics == ()
    assert result.raw_fields["uniprot"] == "P04637;N/A|#n/a"
