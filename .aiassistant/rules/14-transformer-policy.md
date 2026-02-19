---
trigger: model_decision
description: USE WHEN creating or modifying transformers; ensuring consistent mapping and serialization.
---

transformer-policy

> Scope:
>
> - USE WHEN designing or editing transformers (`src/bioetl/application/pipelines/**/transformer.py`)
> - USE WHEN writing unit tests for transformers

# MAPPING CONVENTIONS

- **Declarative DSL**: Use `FieldGroup` and `FieldSpec` for core attribute mapping.
- **Nested Data**: Use `flatten_nested_dict` for API sub-objects (e.g., `action_type`, `ligand_efficiency`).
- **Identifier Support**: Support both unified (`molecule_id`) and legacy (`molecule_chembl_id`) keys in raw records.
- **Primary Keys**: Always include `entity_id` and `content_hash` in the transformed record.

# DATA NORMALIZATION

- **Empty Collections**: Normalize empty lists `[]` or dicts `{}` to `None` (NULL).
- **JSON Serialization**: Use canonical serialization for list/dict fields:
  - `sort_keys=True`
  - `separators=(',', ':')` (compact)
  - `ensure_ascii=True`
- **Taxonomy IDs**: Convert to string and validate using `validate_taxonomy_id`.
- **Numbers**: Use `safe_float` or `safe_int` converters to handle API strings/nulls gracefully.

# TESTING

- **Core Fields**: Verify all business identifiers and values are correctly mapped.
- **Null Safety**: Explicitly test behavior with `None` values for nested objects.
- **JSON Format**: Assert that JSON strings are compact (no extra spaces) to match canonical serialization.
- **Data Types**: Verify ID fields are strings and numeric fields match expected Silver types.
