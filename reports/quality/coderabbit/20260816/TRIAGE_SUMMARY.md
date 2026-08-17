# TRIAGE SUMMARY — CR-FULL-20260816 (five completed leaves)

Ground truth: code/tests/contracts outrank CodeRabbit.
BASE_SHA of the leaf reviews: `6a2c8abe8ac5501bae3fef69667c3ff09280e46c`.
Disposition date: 2026-08-16. Checkout used for verification was a later
working tree; domain files cited below were read directly.

## Scope

| Leaf | Raw | confirm | reject |
| --- | ---: | ---: | ---: |
| `S01-domain-aggregates` | 17 | 1 | 16 |
| `S01-domain-behavior` | 51 | 16 | 35 |
| `S01-domain-composite` | 27 | 9 | 18 |
| `S01-domain-config` | 13 | 1 | 12 |
| `S01-domain-contracts` | 6 | 3 | 3 |
| **total** | **114** | **32** | **82** |

Later leaves in this campaign directory (for example `S01-domain-exceptions`)
remain `pending` until separately reviewed.

## Confirmed residuals

Do not reopen #8643/#8644/#8645/#8652 unless a finding below is a proven
regression. Several confirms are **residuals after those fixes**, not the
original claims.

### Critical

- `CR-20260816-A-S01-domain-behavior-051` — `validate_composite` always runs
  deep preflight after structural fail-closed; non-mapping `composite_config`
  and untyped `output_schema`/`sources` still reach `.get`/set.

### Aggregates

- `…-aggregates-014` — `seal_with_counts` accepts external transform counts,
  but `mark_committed` emits `self.valid_count`.

### Behavior

- `…-008` pM/fM molar window not applied
- `…-010` CSS `.status-warning` vs rendered `status-warn`
- `…-011` affiliation dict items stringified
- `…-017` `required` string split into characters
- `…-018` `classify_potency` hardcodes 4.0/6.0
- `…-019` non-mapping `properties` raise
- `…-023` `enrichment_rate` can exceed 0–1
- `…-024` frozen explanation VOs expose mutable lists
- `…-028` self-comparison pair counts as coverage
- `…-032` disposed-issue rewrite is not idempotent
- `…-033` explicit null `cross_validation` is a blocker
- `…-037` group keys still use `repr()`
- `…-038` empty existing schema treated as missing table
- `…-039` identifier `None` becomes `"None"`
- `…-040` fallback hash still uses `repr()`
- `…-044` `_optional_unit_interval` accepts `bool`/`NaN`
- `…-049` fallback field-name `str()` coercion

### Composite / config / contracts

- `…-composite-006` non-string `field_priorities` silently coerced
- `…-composite-007` / `…-017` `bool()` fail-opens `'false'`
- `…-composite-010` quoted-literal bypass for nested operators
- `…-composite-011` malformed optional sections dropped
- `…-composite-012` trailing text after `IS [NOT] NULL`
- `…-composite-014` whitespace-only `output_field`
- `…-composite-016` duplicate `effective_output_field`
- `…-composite-019` `records_enriched > records_merged` when merged==0
- `…-config-001` `PARTITION_APPEND_*` without `partition_cols`
- `…-contracts-002` undocumented-format `entity_id` / `example_assay_id`
- `…-contracts-005` fractional `pub_month`/`pub_day`
- `…-contracts-006` fractional `top_level_count`

## Rejected classes

- Synthetic “new public API needs ADR/version bump”
- Coverage-inventory refresh because CR treated existing modules as new
- Test-only requests already covered
- Style / DRY / import hoisting / slots cleanup
- False `in`/`not_in` substring claim (`_condition_options` wraps a string)
- `requires-python >=3.12` already shipped
- Already-fixed #8643–#8645 paths (percent-with-unit, structural non-dict
  fail-closed, RUNNING→FAILED replacement, etc.)

## Issues

All 32 confirms are linked to stream issue
[#8863](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8863).
Implementation is separately authorized; this ledger does not mix product
fixes. Exact-cover of remaining leaves stays on #8859.

## Ledgers

- `TRIAGE_OVERRIDES.json`
- `FINDINGS.jsonl` / `FINDINGS.md`
- `TRIAGE.md`
- `DE_DUPE_MAP.json`

## Later-leaf start (2026-08-17)

Independent ground-truth of S01-domain-types criticals against current main:

- confirm 	ypes-018 / 	ypes-022 -> stream #8893
- remaining 34 S01-domain-types findings and ~720 other ok-leaf raw items stay on #8890
- product streams already opened: #8891 / #8888 / #8889 (PR #8892)

## S01-domain-types remainder (2026-08-17)

Independent ground-truth of the remaining 34 S01-domain-types findings:

- confirm 13 -> stream #8895 (004/010/011/012/013/014/015/016/017/019/023/026/028)
- reject 21 (style / DRY / API expansion / Protocol / shipped heuristic)
- leaf S01-domain-types is now fully disposed (36/36 including 018/022 on #8893)

## S01-domain-value_objects + S01-domain-schemas (2026-08-17)

- value_objects 41: confirm 18 -> #8905; reject 23
- schemas 42: confirm 6 -> #8905; reject 36
- rejected after reproduction: vo-008 (UTC offset is contract expansion), sch-016 (UTC-required ingestion_ts breaks shipped fixtures)
