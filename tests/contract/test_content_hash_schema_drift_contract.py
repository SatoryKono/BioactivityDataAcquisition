"""Contract tests for content hash behavior under schema drift.

These tests codify the forward-compatibility contract for identity:
adding technical underscore-prefixed fields must not change content hash.
"""

from __future__ import annotations

import pytest

from bioetl.domain.constants import META_FIELDS
from bioetl.domain.transformations import detect_schema_drift, generate_content_hash
from bioetl.domain.types import DriftLevel


@pytest.mark.contracts
@pytest.mark.no_api
class TestContentHashSchemaDriftContract:
    """Contracts for hash stability when schema evolves."""

    def test_hash_stable_when_new_underscore_field_added(self) -> None:
        """Adding a new technical '_' field MUST NOT alter content hash."""
        base_record = {
            "entity_id": "CHEMBL25",
            "title": "Aspirin",
            "value": 42,
        }
        drifted_record = {
            **base_record,
            "_new_technical_field": "schema-drift-v2",
        }

        base_hash = generate_content_hash(base_record, "chembl")
        drifted_hash = generate_content_hash(drifted_record, "chembl")

        assert base_hash == drifted_hash

    def test_hash_stable_when_only_canonical_meta_fields_change(self) -> None:
        """Canonical META_FIELDS MUST stay outside the content-identity surface."""
        base_record = {
            "entity_id": "CHEMBL25",
            "title": "Aspirin",
            "value": 42,
        }
        drifted_record = dict(base_record)
        for field_name in META_FIELDS:
            drifted_record[field_name] = f"meta::{field_name}"

        base_hash = generate_content_hash(base_record, "chembl")
        drifted_hash = generate_content_hash(drifted_record, "chembl")

        assert base_hash == drifted_hash

    def test_schema_drift_remains_informational_for_added_underscore_fields(
        self,
    ) -> None:
        """Adding optional technical fields should remain informational drift."""
        old_schema = {"entity_id", "title", "value"}
        new_schema = {
            *old_schema,
            "_new_technical_field",
            "_yet_another_meta",
        }

        level, details = detect_schema_drift(
            old_schema=old_schema,
            new_schema=set(new_schema),
            required_fields={"entity_id"},
        )

        assert level == DriftLevel.INFO
        assert "_new_technical_field" in details["added_fields"]
        assert "_yet_another_meta" in details["added_fields"]
