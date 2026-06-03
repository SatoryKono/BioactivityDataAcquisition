---
id: adr-049-loc-policy
title: Created ADR-049 for context-aware LOC target policy
task_id: adr-049-loc-policy
created_at: '2026-06-03T07:37:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "Created ADR-049 documenting context-aware LOC target policy to exclude legitimate\
  \ file patterns from 250 LOC target.\n\nCreated Documentation:\n\nADR-049: Context-Aware\
  \ LOC Target Policy\n- Status: Accepted\n- Location: docs/02-architecture/decisions/ADR-049-context-aware-loc-target-policy.md\n\
  \nPolicy Summary:\n\nFiles EXCLUDED from 250 LOC target:\n\n1. Import Facade Files\n\
  - Pattern: Files that primarily import and re-export from sub-modules\n- Example:\
  \ metrics_definitions.py (335 LOC)\n- Rationale: Legitimate architectural pattern,\
  \ functional decomposition achieved\n- Acceptance: File primarily consists of imports\
  \ and re-exports via __all__\n\n2. Schema/Field Definition Files  \n- Pattern: Files\
  \ containing Pydantic/PyArrow schema or field definitions\n- Examples: silver_chembl_core.py\
  \ (395 LOC), pipeline_config_common_schemas.py (392 LOC)\n- Rationale: Field definitions\
  \ inherently large, decomposition fragments schemas\n- Acceptance: File primarily\
  \ contains schema/field definitions without business logic\n\nFiles KEPT in 250\
  \ LOC target:\n\nBusiness Logic Files\n- Pattern: Files containing actual business\
  \ logic, algorithms, or complex operations\n- Examples: fs_adr_service.py, config/_base.py,\
  \ high-risk persistence files\n- Rationale: Contains business logic suitable for\
  \ functional decomposition\n\nGitHub Issues Updated:\n- #5056: Added policy recommendation\
  \ comment\n- #5057: Added policy recommendation comment with updated status\n\n\
  Benefits:\n1. Focused refactoring on files that benefit from decomposition\n2. Preserves\
  \ legitimate architectural patterns\n3. Reduces wasted effort on inappropriate refactoring\
  \ targets\n4. Context-aware quality metrics"
---

# Episodic summary

## Task

- Title: Created ADR-049 for context-aware LOC target policy

## Outcome

- Created ADR-049 documenting context-aware LOC target policy to exclude legitimate file patterns from 250 LOC target.

Created Documentation:

ADR-049: Context-Aware LOC Target Policy
- Status: Accepted
- Location: docs/02-architecture/decisions/ADR-049-context-aware-loc-target-policy.md

Policy Summary:

Files EXCLUDED from 250 LOC target:

1. Import Facade Files
- Pattern: Files that primarily import and re-export from sub-modules
- Example: metrics_definitions.py (335 LOC)
- Rationale: Legitimate architectural pattern, functional decomposition achieved
- Acceptance: File primarily consists of imports and re-exports via __all__

2. Schema/Field Definition Files  
- Pattern: Files containing Pydantic/PyArrow schema or field definitions
- Examples: silver_chembl_core.py (395 LOC), pipeline_config_common_schemas.py (392 LOC)
- Rationale: Field definitions inherently large, decomposition fragments schemas
- Acceptance: File primarily contains schema/field definitions without business logic

Files KEPT in 250 LOC target:

Business Logic Files
- Pattern: Files containing actual business logic, algorithms, or complex operations
- Examples: fs_adr_service.py, config/_base.py, high-risk persistence files
- Rationale: Contains business logic suitable for functional decomposition

GitHub Issues Updated:
- #5056: Added policy recommendation comment
- #5057: Added policy recommendation comment with updated status

Benefits:
1. Focused refactoring on files that benefit from decomposition
2. Preserves legitimate architectural patterns
3. Reduces wasted effort on inappropriate refactoring targets
4. Context-aware quality metrics

## Lessons learned

- Replace with durable follow-up if needed
