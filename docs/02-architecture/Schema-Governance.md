# Schema Governance

*Status: Target state baseline (2026).*

## Schema Lifecycle

Schema lifecycle for Bronze/Silver/Gold is standardized as a gated flow:

1. **Draft**
   - Schema is authored in provider/entity contract files.
   - Validation examples and backward-compatibility notes are mandatory.
1. **Review**
   - Architecture + data governance review confirms medallion compliance and naming rules.
   - Changes are classified as `backward-compatible` or `breaking`.
1. **Pre-release verification (governance gate)**
   - Contract checks, fixture replay, and drift simulation are executed.
   - Gate emits `blocking` or `warning` findings.
1. **Release**
   - Schema version and changelog are published together.
   - Rollout strategy is selected (dual-write, shadow-read, or direct cutover).
1. **Deprecation / Removal**
   - Deprecated fields keep a migration window.
   - Removal requires version bump and explicit ADR reference.

## Drift Handling

Drift management separates detection from enforcement:

- **Bronze**: drift is tolerated (append-only raw capture).
- **Silver**: soft enforcement — unknown/changed fields trigger drift events, not immediate stop.
- **Gold**: strict enforcement — unresolved drift is treated as a release-blocking contract mismatch.

Drift workflow:

1. Detect drift (`new_field`, `type_change`, `nullability_change`, `enum_expansion`).
1. Classify severity:
   - `blocking`: destructive or ambiguous change (e.g., type narrowing).
   - `warning`: additive or safely coercible change.
1. Route action:
   - warning → ticket + SLA.
   - blocking → stop Gold publish until schema contract is updated.

## Contract Versioning

Versioning policy for schema contracts:

- **MAJOR**: incompatible contract (rename, type incompatibility, semantic change).
- **MINOR**: backward-compatible additive changes.
- **PATCH**: metadata, docs, constraints tightening without consumer break.

Additional rules:

- Contract version is declared per entity.
- Breaking changes require ADR and migration plan.
- Gold contract version MUST be traceable to Silver source contract version.

## PK & Partition Strategy

Primary key and partition rules for target-state schema design:

- PK MUST represent stable business identity (`provider_id` + optional natural discriminator).
- Content hash MUST represent version identity (record state), not business identity.
- Silver partitioning SHOULD use bounded cardinality keys (`year`, `month`, `entity_type`).
- Gold partitioning SHOULD align with primary query access patterns, avoiding high-cardinality UUID/hash partition keys.

Recommended constraints:

- Avoid partition keys with expected cardinality >50k.
- Use Z-ORDER / clustering for high-cardinality filters instead of deep partition fan-out.

## JSON Typing Standard

Canonical JSON typing baseline for cross-provider normalization:

- Integer-like optional fields in analytical schemas: nullable numeric representation compatible with dataframe engines.
- Floating point values normalized with bounded precision.
- Date values serialized as `YYYY-MM-DD`.
- Timestamp values serialized as ISO-8601 UTC.
- Booleans are strict (`true` / `false`), no string booleans.
- Missing or unknown values represented as `null` (sentinel values are forbidden).

Normalization before content-hash or contract checks:

- trim strings,
- round floats to agreed precision,
- map NaN/Inf to `null`,
- exclude runtime metadata fields from hash comparison.

## SCD2 Decision Matrix

| Change type                        | Business meaning            | SCD2 action                                                | Gate class |
| ---------------------------------- | --------------------------- | ---------------------------------------------------------- | ---------- |
| Descriptive attribute update       | Normal historical evolution | New version row (`valid_from` / `valid_to`)                | warning    |
| Identity key change                | Potential entity remap      | Manual review + migration                                  | blocking   |
| Type narrowing / incompatible cast | Contract break risk         | Block publish until migration approved                     | blocking   |
| Additive nullable attribute        | Non-breaking extension      | Keep current row; write new value on next version boundary | warning    |
| Enum expansion                     | Usually additive            | Accept with monitoring                                     | warning    |
| Enum contraction                   | Potential data loss         | Require impact analysis and migration                      | blocking   |

Decision rule:

- If change can cause historical reinterpretation or data loss, classify as `blocking`.
- If change is additive and preserves historical semantics, classify as `warning`.
