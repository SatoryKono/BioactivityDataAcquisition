---
id: docs-audit-dq-contracts-deep-fix
title: 'Deep dq-contracts.md fix: removed Jinja2 and aligned with runtime'
task_id: docs-audit-dq-contracts-deep-fix
created_at: '2026-06-03T06:58:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "Completed deep fix of dq-contracts.md to remove outdated Jinja2 surfaces\
  \ and align with runtime DQ contract model.\n\nAdditional P0 fixes discovered and\
  \ completed:\n1. Removed all Jinja2 expression references:\n   - Cross-field validations:\
  \ replaced Jinja2 condition expressions with Literal condition types (all_present,\
  \ any_present, mutually_exclusive, conditional_required, custom)\n   - Conditional\
  \ validations: replaced Jinja2 condition expressions with structured condition_field/condition_value/condition_operator\
  \ model\n   - Removed else branch from conditional validations (not supported in\
  \ runtime)\n\n2. Aligned field validation contract with runtime FieldValidation:\n\
  \   - Changed 'type' to 'validation_type' in all examples\n   - Changed 'min'/'max'\
  \ to 'min_value'/'max_value' for range validation\n   - Changed 'validation' to\
  \ 'validator' for custom validation\n   - Removed 'min_items' parameter (not supported\
  \ in runtime not_empty_list)\n   - Added 'severity' and 'severity_enricher' fields\n\
  \   - Added missing validation types: not_null, not_empty_list\n\n3. Fixed all YAML\
  \ examples in document:\n   - Entity field validations examples\n   - Cross-field\
  \ validations examples\n   - Conditional validations examples\n   - Full config\
  \ example with all validation types\n   - Validation rule reference table\n\n4.\
  \ Cross-field validation structure updated:\n   - Added 'name' field (required in\
  \ runtime)\n   - Changed from field/related_field to fields tuple\n   - Changed\
  \ from Jinja2 condition to Literal condition type\n   - Added trigger_field/required_field\
  \ for conditional_required\n   - Added validator for custom conditions\n\n5. Conditional\
  \ validation structure updated:\n   - Added 'name' field (required in runtime)\n\
  \   - Changed from Jinja2 condition to condition_field/condition_value/condition_operator\n\
  \   - Changed then/else branches to then_validations tuple\n   - Removed else branch\
  \ (not supported in runtime)\n\nAll changes based on runtime verification:\n- src/bioetl/domain/config/validation.py\
  \ (FieldValidation, CrossFieldValidation, ConditionalValidation)\n- src/bioetl/domain/config/dq.py\
  \ (DQConfig)\n- configs/entities/chembl/activity.yaml (actual YAML config structure)\n\
  \nThis completes the P0 dq-contracts.md fixes beyond the initial disposition model\
  \ changes, addressing the 'remove outdated Jinja2/transform/allow/escalate surfaces'\
  \ requirement from the audit plan."
---

# Episodic summary

## Task

- Title: Deep dq-contracts.md fix: removed Jinja2 and aligned with runtime

## Outcome

- Completed deep fix of dq-contracts.md to remove outdated Jinja2 surfaces and align with runtime DQ contract model.

Additional P0 fixes discovered and completed:
1. Removed all Jinja2 expression references:
   - Cross-field validations: replaced Jinja2 condition expressions with Literal condition types (all_present, any_present, mutually_exclusive, conditional_required, custom)
   - Conditional validations: replaced Jinja2 condition expressions with structured condition_field/condition_value/condition_operator model
   - Removed else branch from conditional validations (not supported in runtime)

2. Aligned field validation contract with runtime FieldValidation:
   - Changed 'type' to 'validation_type' in all examples
   - Changed 'min'/'max' to 'min_value'/'max_value' for range validation
   - Changed 'validation' to 'validator' for custom validation
   - Removed 'min_items' parameter (not supported in runtime not_empty_list)
   - Added 'severity' and 'severity_enricher' fields
   - Added missing validation types: not_null, not_empty_list

3. Fixed all YAML examples in document:
   - Entity field validations examples
   - Cross-field validations examples
   - Conditional validations examples
   - Full config example with all validation types
   - Validation rule reference table

4. Cross-field validation structure updated:
   - Added 'name' field (required in runtime)
   - Changed from field/related_field to fields tuple
   - Changed from Jinja2 condition to Literal condition type
   - Added trigger_field/required_field for conditional_required
   - Added validator for custom conditions

5. Conditional validation structure updated:
   - Added 'name' field (required in runtime)
   - Changed from Jinja2 condition to condition_field/condition_value/condition_operator
   - Changed then/else branches to then_validations tuple
   - Removed else branch (not supported in runtime)

All changes based on runtime verification:
- src/bioetl/domain/config/validation.py (FieldValidation, CrossFieldValidation, ConditionalValidation)
- src/bioetl/domain/config/dq.py (DQConfig)
- configs/entities/chembl/activity.yaml (actual YAML config structure)

This completes the P0 dq-contracts.md fixes beyond the initial disposition model changes, addressing the 'remove outdated Jinja2/transform/allow/escalate surfaces' requirement from the audit plan.

## Lessons learned

- Replace with durable follow-up if needed
