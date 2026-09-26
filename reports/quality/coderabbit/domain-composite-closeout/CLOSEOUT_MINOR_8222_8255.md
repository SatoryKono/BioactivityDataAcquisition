

# domain/composite residual closeout (minor pack #8222–#8255)

- Branch: `main`
- Fixed: **14**
- Rejected: **0**
- Total: **14**

## Dispositions

- **#8222** `fixed` — EnrichmentResult.timeout rejects negative/non-finite timeout_seconds.
- **#8223** `fixed` — EnrichmentResult rejects negative counts and enriched/not_found > input.
- **#8224** `fixed` — Cross-validation thresholds/tolerances reject non-finite numbers.
- **#8233** `fixed` — Duplicate pipeline names sorted in ValueError messages.
- **#8236** `fixed` — Serialization preserves explicit timeout 0 for domain validation (no `or 600`).
- **#8243** `fixed` — to_metric_value docstring documents 0-11 range including terminals.
- **#8244** `fixed` — Lineage enrichment_status nested payload + legacy string parse.
- **#8245** `fixed` — DependencyResult.timeout Returns docstring matches duration fallback.
- **#8246** `fixed` — Malformed ISO timestamps skipped / return None.
- **#8247** `fixed` — FieldMapping.providers case-insensitive dedupe; has_provider reuses it.
- **#8250** `fixed` — Sort policies stripped at conversion; validate stored values.
- **#8252** `fixed` — FieldComparisonSpec defaults FUZZY=0.8 / NUMERIC=0.10 when threshold=0.
- **#8254** `fixed` — is_gold_field uses FieldGroupDefinition.include_in_gold overrides.
- **#8255** `fixed` — AggregationFieldSpec validates filter_condition grammar fail-closed.

## Validation
- `pytest tests/unit/domain/composite` green
- Residual: tests/unit/domain/composite/test_domain_composite_cr_residuals_8222_8255.py
- No tech-debt budget growth
