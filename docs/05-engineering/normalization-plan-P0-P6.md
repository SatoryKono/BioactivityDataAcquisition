---
Version: 1.0.0
Status: active
Class: published
Owner: Architecture / Domain
Reviewers:
- BioETL Team
Last verified: '2026-04-08'
---

# Normalization Plan P0–P6

## Purpose

Этот документ является canonical engineering reference для программы
нормализации вокруг `RunManifest`, `RunLedger`, runtime anchors и
`ChemBL Activity`.

Его задача не заменить узкие policy-docs или код, а зафиксировать:

- единый словарь терминов;
- инварианты детерминизма;
- канонический порядок `normalize -> canonical serialize -> hash -> persist`;
- фазовый план `P0`–`P6` для дальнейшей серии изменений;
- фактические code seams, через которые эти правила должны внедряться.

## Scope

Документ покрывает:

- control-plane path для `RunManifest` и `RunLedger`;
- runtime anchors, влияющие на checkpoint / resume compatibility;
- record-level normalization и `content_hash` semantics для `ChemBL Activity`;
- генерацию field matrix artifacts из кода;
- тестовые и governance expectations для детерминизма.

Документ не покрывает:

- миграцию historical artifacts;
- ретроактивную перезапись старых manifest / ledger / checkpoint файлов;
- детальную реализацию конкретных normalizer-функций.

## Canonical Terms

| Term | Meaning | Canonical owner |
| --- | --- | --- |
| `content_hash` | Hash бизнес-содержимого одной нормализованной записи; используется для dedup/version semantics | [content-hash-identity-policy.md](../02-architecture/policies/content-hash-identity-policy.md), [hashing.py](../../src/bioetl/domain/transformations/hashing.py) |
| `execution_fingerprint` | Hash семантической идентичности запуска; используется для replay/equivalence и checkpoint compatibility | [run_manifest_service.py](../../src/bioetl/application/services/run_manifest_service.py), [checkpoint_metadata_helpers.py](../../src/bioetl/composition/factories/pipeline/checkpoint_metadata_helpers.py) |
| `META_FIELDS` | Технические поля, которые не должны участвовать в identity/content hashing | [constants.py](../../src/bioetl/domain/constants.py) |
| business fields | Поля, описывающие сущность или событие по смыслу, а не по operational trace | this document + entity/profile contracts |
| runtime anchors | Control-plane поля вроде `contract_ref`, `contract_version`, `effective_config_hash`, влияющие на runtime compatibility | this document + checkpoint/control-plane seams |
| canonical JSON | JSON with stable key order and compact separators, used as the only byte representation before hashing | [hashing.py](../../src/bioetl/domain/transformations/hashing.py) |
| `NormalizationProfile` | Явный field-by-field contract для record normalization и hash inclusion policy | target state for `P4`–`P5` |
| set-like collection | Список, для которого порядок не несёт бизнес-смысла и может быть канонизирован явно по contract/profile rule | target state for `P4`–`P5` |

## Determinism Invariants

Следующие правила MUST считаться базовыми для всей серии работ:

1. Нормализация выполняется до hashing и до persist.
2. Каноническое байтовое представление перед hashing строится только через
   canonical JSON.
3. `content_hash` и `execution_fingerprint` не взаимозаменяемы и не должны
   смешиваться в одном термине.
4. `content_hash` считается только от business payload после исключения
   technical meta fields.
5. `execution_fingerprint` считается только от control-plane payload и не
   должен зависеть от persist-only полей вроде `manifest_id`, `entry_id`,
   `created_at`, `occurred_at`.
6. Domain задаёт pure normalization rules и не выполняет I/O, логирование,
   чтение настроек или скрытую генерацию времени.
7. Порядок в списках сохраняется по умолчанию; permutation-invariant behavior
   разрешён только для явно помеченных set-like полей.
8. Все SHA-256 style anchors должны иметь канонический вид: lowercase, 64 hex
   chars, без префиксов и без произвольного formatting.

## Current Code Seams

| Concern | Current seam | Current role |
| --- | --- | --- |
| Manifest fingerprint path | [run_manifest_service.py](../../src/bioetl/application/services/run_manifest_service.py) | Строит `execution_fingerprint` напрямую через `json.dumps(..., sort_keys=True)` |
| Manifest snapshot assembly | [run_manifest_builder.py](../../src/bioetl/composition/runtime_builders/run_manifest_builder.py) | Собирает launch/runtime/resolved config snapshots и runtime anchors |
| Ledger append path | [run_ledger_service.py](../../src/bioetl/application/services/run_ledger_service.py) | Собирает lifecycle events и `_diagnostic` envelope перед append |
| Ledger serialization model | [run_ledger.py](../../src/bioetl/domain/control_plane/run_ledger.py) | Нормализует JSON-safe payload формы и replay-oriented helpers |
| Checkpoint identity path | [checkpoint_metadata_helpers.py](../../src/bioetl/composition/factories/pipeline/checkpoint_metadata_helpers.py) | Собирает checkpoint `execution_fingerprint` из runtime metadata |
| Meta field exclusion | [constants.py](../../src/bioetl/domain/constants.py) | Держит `META_FIELDS` |
| Content hash normalization | [hashing.py](../../src/bioetl/domain/transformations/hashing.py) | Нормализует значения и считает `content_hash` |
| Record-level heuristics | [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py) | Текущий fallback path для DOI/PMID/date/JSON normalization |
| ChemBL Activity hash baseline | [activity.yaml](../../configs/entities/chembl/activity.yaml) | Держит baseline `hash_policy` и current normalization knobs |
| Control-plane operator reference | [run-manifest-inspection.md](../05-operations/runbooks/run-manifest-inspection.md) | Published inspection and traceability runbook |

Этот документ не отменяет ownership этих seams. Он фиксирует, как они должны
быть согласованы между собой.

## Canonical Type Policies

### JSON / object policy

- `dict` и `list` payload должны нормализоваться рекурсивно в JSON-safe object
  graph до сериализации.
- Ключи mapping-ов приводятся к строкам.
- Canonical serialization использует sorted keys и compact separators.
- Stringly-typed JSON в record-level полях не должен парситься “везде по
  умолчанию”; parse/canonicalize допустим только когда это разрешено явным
  field rule, profile rule или существующим dedicated normalizer path.

Example:

```json
{"b":2,"a":{"y":2,"x":1}}
```

Canonical form:

```json
{"a":{"x":1,"y":2},"b":2}
```

### Datetime policy

- Control-plane timestamps canonicalize to UTC ISO-8601 with trailing `Z`.
- Business date fields may preserve date-only precision when that is the field
  contract, for example `YYYY-MM-DD`.
- Naive datetimes MUST NOT silently leak into hashing/persist paths; they must
  be rejected or normalized through an explicit sanctioned seam.

Example:

- input: `2026-04-08T12:15:30+03:00`
- canonical control-plane output: `2026-04-08T09:15:30Z`

### UUID policy

- UUIDs canonicalize through `UUID(...) -> str(...)`.
- Canonical UUID form is lowercase hyphenated text.
- Blank optional UUID-like values collapse to `None`.
- Invalid UUID values on write path should fail validation rather than survive
  as ambiguous free text.

### SHA-256 / hash anchor policy

- Canonical lexical form: lowercase 64-char hex.
- No `sha256:` prefix.
- No uppercase letters.
- `content_hash`, `execution_fingerprint`, and `effective_config_hash` may all
  use SHA-256 as encoding, but they remain different artifacts with different
  input payloads and different business meaning.

### Float and numeric policy

- `NaN` and `Inf` normalize to `null`.
- Deterministic rounding is allowed only through explicit policy.
- Current record-level baseline for `content_hash` uses float rounding with
  precision `10` in [hashing.py](../../src/bioetl/domain/transformations/hashing.py)
  and [activity.yaml](../../configs/entities/chembl/activity.yaml).
- Numeric strings are not globally auto-cast; coercion must be field-specific.

### List and set-like collection policy

- Default behavior: preserve order.
- Set-like semantics require an explicit rule.
- For set-like primitive lists, canonical order is lexical or numeric order.
- For set-like object lists, canonical order is stable canonical JSON string
  order after recursive normalization.
- Sorting set-like collections does not automatically imply deduplication;
  duplicate collapse requires a separate explicit rule.

### Blank / null policy

- Optional runtime anchor text fields should use `blank -> None`.
- Business string fields may preserve `""` only when the field contract says
  that empty string is semantically different from missing value.
- Canonical policy must never allow a blank string to masquerade as a valid
  `contract_ref`, `contract_version`, or hash anchor.

### META_FIELDS vs business fields

- Any field starting with `_` is technical by default and MUST NOT contribute to
  `content_hash`.
- `META_FIELDS` in [constants.py](../../src/bioetl/domain/constants.py) remain
  the active baseline for explicit exclusions.
- Runtime anchors are control-plane business fields for execution identity, but
  they are not entity business fields and therefore do not belong in
  `content_hash` unless a field-level contract explicitly states otherwise.

## Manual Reproduction Rules

### Manual reproduction of `execution_fingerprint`

1. Build the semantic manifest payload only from normalized control-plane input:
   `run_type`, `pipeline_name`, `provider`, `entity`, normalized
   `launch_context`, `runtime_config`, `resolved_config`, normalized
   `code_provenance`, `source_refs`, and `planned_artifacts`.
2. Exclude persist-only identifiers and timestamps:
   `manifest_id`, `created_at`, `entry_id`, `occurred_at`.
3. Serialize through canonical JSON.
4. Compute lowercase SHA-256 hex of that canonical payload.

Important current-state note:

- The repository currently has one fingerprint path in
  [run_manifest_service.py](../../src/bioetl/application/services/run_manifest_service.py)
  and another narrower execution identity path in
  [checkpoint_metadata_helpers.py](../../src/bioetl/composition/factories/pipeline/checkpoint_metadata_helpers.py).
- `P2` must make any intentional distinction explicit. Silent divergence is not
  acceptable.

### Manual reproduction of `content_hash`

1. Start with normalized business record payload.
2. Remove all technical fields excluded by `META_FIELDS`, underscore-prefix
   policy, and entity/profile-specific exclude rules.
3. Apply field-level normalization rules.
4. Serialize to canonical JSON.
5. Compute `sha256(provider + canonical_json(normalized_record))`.

Current ChemBL Activity baseline is declared in
[activity.yaml](../../configs/entities/chembl/activity.yaml).

## P0 — Baseline, Vocabulary, and Seam Inventory

### Objective

Собрать в одном published document текущие правила, термины и code seams без
изменения runtime behavior.

### Scope of the phase

- glossary sync for `content_hash`, `execution_fingerprint`, `META_FIELDS`,
  `business fields`, `runtime anchors`;
- inventory of current implementation seams;
- canonical ordering rule `normalize -> canonical serialize -> hash -> persist`;
- cross-links to current policies and runbooks.

### Exit criteria

- published document exists;
- sections `P0`–`P6` exist;
- current seams are linked directly to code;
- vocabulary no longer requires reading five separate files to understand the
  plan.

## P1 — Domain Control-Plane Normalizers

### Objective

Ввести один pure domain normalizer для control-plane payloads.

### Target state

- dedicated `src/bioetl/domain/normalization/control_plane.py`;
- canonical functions for RunManifest spec and RunLedger payloads;
- normalization of UUID, datetime, stable objects, and explicitly set-like
  collections without I/O.

### Primary seams

- [run_manifest.py](../../src/bioetl/domain/control_plane/run_manifest.py)
- [run_ledger.py](../../src/bioetl/domain/control_plane/run_ledger.py)
- [run_manifest_builder.py](../../src/bioetl/composition/runtime_builders/run_manifest_builder.py)

### Exit criteria

- one reusable domain module owns control-plane normalization;
- snapshot builders stop inventing their own incompatible normalization rules.

## P2 — RunManifest Fingerprint Path

### Objective

Сделать `execution_fingerprint` функцией от нормализованного control-plane
payload, а не от случайной упаковки manifest input.

### Target state

- [run_manifest_service.py](../../src/bioetl/application/services/run_manifest_service.py)
  normalizes input before hashing;
- canonical JSON is the only byte representation before fingerprinting;
- permutation of semantically set-like inputs does not change the fingerprint;
- checkpoint execution identity either reuses the same canonical helper or
  declares a versioned, explicitly narrower contract.

### Exit criteria

- no hidden duplicate hash path with different payload rules;
- backward-compatibility posture is explicit.

## P3 — RunLedger Canonical Persist Path

### Objective

Сделать append-only ledger детерминированным по сериализации.

### Target state

- [run_ledger_service.py](../../src/bioetl/application/services/run_ledger_service.py)
  calls a shared normalizer before append;
- `details` and `_diagnostic` envelopes persist in canonical form;
- infrastructure stores already-normalized ledger payloads and does not perform
  its own business normalization.

### Exit criteria

- equivalent events serialize identically;
- JSONL output is stable across key-order permutations;
- read path remains compatible with historical non-canonical entries.

## P4 — Runtime Anchors and Profile Framework

### Objective

Нормализовать runtime anchors и одновременно подготовить field-rule framework
для entity-level normalization.

### Target state

- canonical rules for `contract_ref`, `contract_version`,
  `effective_config_hash`, and related checkpoint anchors;
- blank strings collapse to `None` for optional anchors;
- invalid semver/hash forms fail fast on write path;
- domain-level `FieldRule` / `NormalizationProfile` contracts exist and can
  declare field normalization and hash participation.

### Primary seams

- [run_manifest_builder.py](../../src/bioetl/composition/runtime_builders/run_manifest_builder.py)
- [checkpoint_metadata_helpers.py](../../src/bioetl/composition/factories/pipeline/checkpoint_metadata_helpers.py)
- contract registry seams under
  [src/bioetl/domain/control_plane/](../../src/bioetl/domain/control_plane/)

### Exit criteria

- runtime anchors compare stably across runs;
- profile framework can describe include/exclude and set-like semantics
  explicitly.

## P5 — ChemBL Activity Profile and Generated Field Matrix

### Objective

Перевести `ChemBL Activity` с implicit heuristics на explicit field-level
contract и сделать field matrix artifact производным от кода.

### Target state

- complete profile for
  [CHEMBL activity schema](../../src/bioetl/domain/schemas/chembl/activity.py);
- [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py)
  becomes profile-aware;
- set-like list invariance is field-driven, not global;
- field matrix artifacts are generated from schema + profile in deterministic
  order.

### Current baseline inputs

- [activity.yaml](../../configs/entities/chembl/activity.yaml)
- [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py)

### Exit criteria

- every schema field is either covered by a profile rule or excluded explicitly;
- `content_hash` semantics are explainable field-by-field;
- matrix artifacts no longer depend on manual spreadsheets.

## P6 — Tests, Rollout, and Governance

### Objective

Закрепить детерминизм тестами и governance checks so that normalization policy
can evolve only through explicit changesets.

### Required test classes

- golden tests for `execution_fingerprint`;
- golden tests for `ChemBL Activity content_hash`;
- property-based tests for permutation invariance and null/blank semantics;
- snapshot or byte-for-byte determinism tests for field matrix artifacts.

### Required governance checks

- docs verification for published cross-links;
- architecture checks that domain normalizers remain dependency-free;
- explicit rollout notes whenever a hash/fingerprint policy changes.

### Exit criteria

- determinism is enforced by CI-visible tests rather than tribal knowledge;
- field matrix generation is reproducible;
- policy changes become deliberate and reviewable.

## Recommended Execution Order

1. `P0`
2. `P1`
3. `P2` and `P3`
4. `P4`
5. `P5`
6. `P6`

Control-plane work and record-level work may partially overlap, but `P0` must
land first because it defines the shared vocabulary and invariants.

## Validation Commands

```bash
rg -n '^## P[0-6]\\b' docs/05-engineering/normalization-plan-P0-P6.md
python3 -m scripts.docs verify --skip-build
```

## Related Documents

- [RULES.md](../00-project/RULES.md)
- [Content Hash Identity Policy](../02-architecture/policies/content-hash-identity-policy.md)
- [ADR-014 Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-044 Run Manifest and Run Ledger](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest Inspection](../05-operations/runbooks/run-manifest-inspection.md)
- [Checkpoint Debugging](../05-operations/runbooks/checkpoint-debugging.md)
