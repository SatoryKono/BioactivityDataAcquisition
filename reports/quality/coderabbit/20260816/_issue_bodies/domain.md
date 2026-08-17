## Parent

#8859 (`CR-FULL-20260816`). Product stream split out of closed #8890 bulk confirms. Do **not** open one GitHub issue per raw finding. Do not reopen #8643 / #8644 / #8645 / #8652 without a fresh reproduction.

Campaign pin: `BASE_SHA=6a2c8abe8ac5501bae3fef69667c3ff09280e46c`.

## Outcome

Fix leftover domain confirms from #8890 (hashing/DQ score, workflow config freeze, step-transition validation). Validation-003 is test-only — skip if no product change remains.

## Confirmed majors (re-verify on current `origin/main` before implement)

- [ ] `CR-20260816-A-S01-domain-transformations-005` (major) `src/bioetl/domain/transformations/hashing.py` — Update the business-key branch in the entity ID generation logic to use the business-key value only when it is present and non-null; otherwise call generate_content_hash(record, provider) and retur...
- [ ] `CR-20260816-A-S01-domain-transformations-006` (major) `src/bioetl/domain/transformations/quality.py` — Update calculate_dq_score to validate count invariants before handling the zero-total case or calculating the ratio: reject negative counts and any valid_count greater than total_count. Preserve th...
- [ ] `CR-20260816-A-S01-domain-validation-003` (major) `src/bioetl/domain/validation/primitives.py` — Add unit tests covering nominal valid inputs and expected outputs for validate_positive_int, validate_non_negative, and validate_non_empty_string. Also add validate_non_negative cases for non-finit...
- [ ] `CR-20260816-A-S01-domain-workflow-002` (major) `src/bioetl/domain/workflow/config.py` — Defensively copy and freeze the mutable mappings in the configuration models, including multi_filter_ids, fallback_mapping, and TransformStepConfig.config, during construction so later caller mutat...
- [ ] `CR-20260816-A-S01-domain-workflow-005` (major) `src/bioetl/domain/workflow/step_transition.py` — Update WorkflowStepTransitionPolicy with a __post_init__ validation that accepts only the defined run and skip dispositions and requires stores_output to exactly match whether disposition equals _D...

## Also in this stream (2 minor/trivial)

`CR-20260816-A-S01-domain-transformations-004`, `CR-20260816-A-S01-domain-validation-007`

Re-verify before implementing; skip any item already resolved on current main.

## Constraints

- Code/tests/contracts outrank CodeRabbit wording.
- One independent behavior change per task unless items share a helper.
- No `.env*` mutation.
- No tech-debt budget / exemption / threshold increase.
- Exact-cover retries stay on #8859.
