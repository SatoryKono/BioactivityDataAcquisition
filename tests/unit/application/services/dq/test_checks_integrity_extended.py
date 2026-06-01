"""Extended unit tests for _checks_integrity module.

Tests covering gaps identified in coverage analysis:
- check_referential_integrity: invalid ref_key format, missing columns, pyarrow table
- check_scd_integrity: with entity_key, overlapping validity periods, large entity sets
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.services.dq._checks_integrity import (
    check_referential_integrity,
    check_scd_integrity,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus


pytestmark = pytest.mark.unit

class TestCheckReferentialIntegrityExtended:
    """Extended tests for check_referential_integrity."""

    def test_invalid_ref_key_format_skipped(self) -> None:
        """ref_key without '->' separator is silently skipped."""
        df = pl.DataFrame({"cat_id": [1, 2, 3]})
        ref = pl.DataFrame({"id": [1, 2, 3]})
        result = check_referential_integrity(df, {"invalid_format": ref})
        # No valid FK results → PASS
        assert result.status == DQCheckStatus.PASS
        assert result.foreign_keys == {}

    def test_ref_key_missing_two_parts_in_ref_column(self) -> None:
        """ref_key like 'col -> table_only' (no '.col') is skipped."""
        df = pl.DataFrame({"cat_id": [1, 2, 3]})
        ref = pl.DataFrame({"id": [1, 2, 3]})
        # parts[1] = "table_only" → ref_parts has only 1 element → skip
        result = check_referential_integrity(df, {"cat_id -> table_only": ref})
        assert result.status == DQCheckStatus.PASS

    def test_local_column_missing_in_df_skipped(self) -> None:
        """If local column not in df, FK check is skipped."""
        df = pl.DataFrame({"other_col": [1, 2, 3]})
        ref = pl.DataFrame({"id": [1, 2, 3]})
        result = check_referential_integrity(df, {"missing_col -> ref_table.id": ref})
        assert result.status == DQCheckStatus.PASS

    def test_ref_column_missing_in_ref_table_skipped(self) -> None:
        """If referenced column not in ref_table, FK check is skipped."""
        df = pl.DataFrame({"cat_id": [1, 2, 3]})
        ref = pl.DataFrame({"other_field": [1, 2, 3]})
        result = check_referential_integrity(
            df, {"cat_id -> categories.nonexistent": ref}
        )
        assert result.status == DQCheckStatus.PASS

    def test_pyarrow_reference_table_converted(self) -> None:
        """PyArrow Table as reference should be converted to Polars and checked."""
        df = pl.DataFrame({"cat_id": [1, 2, 3]})
        ref_arrow = pa.table({"id": [1, 2, 3, 4]})
        result = check_referential_integrity(df, {"cat_id -> categories.id": ref_arrow})
        assert result.status == DQCheckStatus.PASS

    def test_small_orphan_rate_warns_not_fails(self) -> None:
        """<=1% orphans → WARN, not FAIL."""
        # 200 records with 1 orphan → 0.5% orphan rate
        cat_ids = [*list(range(1, 200)), 9999]  # 200 records, 1 orphan
        df = pl.DataFrame({"cat_id": cat_ids})
        ref = pl.DataFrame({"id": list(range(1, 200))})
        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        fk_result = result.foreign_keys.get("cat_id -> categories.id")
        assert fk_result is not None
        assert fk_result.status == DQCheckStatus.WARN

    def test_overall_fail_when_any_fk_fails(self) -> None:
        """If any FK has >1% orphans → overall FAIL."""
        df = pl.DataFrame({"cat_id": [1, 999, 998, 997]})  # 75% orphans
        ref = pl.DataFrame({"id": [1, 2, 3]})
        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        assert result.status == DQCheckStatus.FAIL

    def test_overall_warn_when_small_orphan_no_fail(self) -> None:
        """If some FK has tiny orphan rate → WARN overall."""
        cat_ids = [*list(range(1, 200)), 9999]
        df = pl.DataFrame({"cat_id": cat_ids})
        ref = pl.DataFrame({"id": list(range(1, 200))})
        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        assert result.status == DQCheckStatus.WARN

    def test_all_valid_references_pass(self) -> None:
        df = pl.DataFrame({"cat_id": [1, 2, 3]})
        ref = pl.DataFrame({"id": [1, 2, 3, 4, 5]})
        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        assert result.status == DQCheckStatus.PASS
        fk = result.foreign_keys.get("cat_id -> categories.id")
        assert fk is not None
        assert fk.orphan_records == 0


class TestCheckSCDIntegrityExtended:
    """Extended tests for check_scd_integrity."""

    def test_with_entity_key_not_in_df(self) -> None:
        """entity_key configured but not in DataFrame → PASS with basic counts."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        scd_config = {"type": 2, "entity_key": "missing_key"}
        result = check_scd_integrity(df, scd_config)
        assert result.status == DQCheckStatus.PASS
        assert result.total_entities == 3

    def test_overlapping_validity_periods_warn(self) -> None:
        """Records with overlapping _valid_from/_valid_to → WARN."""
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 3, 1),  # starts before previous ends
                ],
                "_valid_to": [
                    datetime(2024, 6, 1),  # ends after next starts
                    datetime(2024, 12, 1),
                ],
            }
        )
        scd_config = {
            "type": 2,
            "entity_key": "entity_id",
            "valid_from_col": "_valid_from",
            "valid_to_col": "_valid_to",
        }
        result = check_scd_integrity(df, scd_config)
        assert result.overlapping_validity_periods > 0
        assert result.status == DQCheckStatus.WARN

    def test_no_overlapping_periods_pass(self) -> None:
        """Non-overlapping validity periods → PASS."""
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A", "B"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 7, 1),
                    datetime(2024, 1, 1),
                ],
                "_valid_to": [
                    datetime(2024, 6, 30),
                    None,
                    None,
                ],
            }
        )
        scd_config = {
            "type": 2,
            "entity_key": "entity_id",
            "valid_from_col": "_valid_from",
            "valid_to_col": "_valid_to",
        }
        result = check_scd_integrity(df, scd_config)
        assert result.overlapping_validity_periods == 0
        assert result.status == DQCheckStatus.PASS

    def test_avg_versions_per_entity_calculated(self) -> None:
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A", "B"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 6, 1),
                    datetime(2024, 1, 1),
                ],
                "_valid_to": [datetime(2024, 6, 1), None, None],
            }
        )
        scd_config = {"type": 2, "entity_key": "entity_id"}
        result = check_scd_integrity(df, scd_config)
        # 3 records / 2 unique entities = 1.5
        assert result.avg_versions_per_entity == pytest.approx(1.5)

    def test_entities_with_history_counted(self) -> None:
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A", "B"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 6, 1),
                    datetime(2024, 1, 1),
                ],
                "_valid_to": [datetime(2024, 6, 1), None, None],
            }
        )
        scd_config = {"type": 2, "entity_key": "entity_id"}
        result = check_scd_integrity(df, scd_config)
        assert result.entities_with_history == 1  # only "A" has >1 version

    def test_scd_type_preserved(self) -> None:
        df = pl.DataFrame({"entity_id": ["A", "B"]})
        scd_config = {"type": 1, "entity_key": "entity_id"}
        result = check_scd_integrity(df, scd_config)
        assert result.scd_type == 1
