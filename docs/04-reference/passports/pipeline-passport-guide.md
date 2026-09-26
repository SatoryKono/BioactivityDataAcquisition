# Pipeline passport projections

Pipeline passports are deterministic documentation projections. The canonical
flow is:

```text
runtime registration + validated config + contracts + CLI
    -> structured passport facts
    -> generated JSON
    -> compact generated Markdown
```

Do not edit files under `generated/pipelines/` or `pipelines/` manually. Change
the canonical runtime/config owner, the projector in
`scripts/docs/passports/`, or an allowed owner-approved sidecar under
`manual/pipelines/`.

## Shared semantics

Individual passports show pipeline-specific values and link to their evidence.
The shared meanings of Bronze append-only snapshots, strict Gold validation,
quarantine, RunManifest, RunLedger, checkpoints, and correlation fields are
owned by the architecture/contracts documentation:

- [ADR-018: strict Gold validation](../../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [Run manifest and ledger contract](../contracts/run-manifest-ledger.md)
- [Domain aggregate invariants](../domain/invariants.md)
- [Observability contract](../observability/metrics-catalog.md)

## Generated and manual ownership

Generated facts own identity, source/config references, extraction filters,
field groups, DQ thresholds, write mode, contracts, commands, and diagrams.
Sidecars may add only purpose, business context, curated field-group labels,
operator notes, known limitations, rationale, approved exceptions, or a
supported additional-diagram choice. A sidecar cannot override a generated
endpoint, threshold, key, contract, command, or source path.

## Commands

```bash
python -m scripts.docs passports generate
python -m scripts.docs passports check
pytest -q tests/unit/scripts/docs/passports
pytest -q tests/architecture/test_passport_documentation_projections.py
```

`generate` writes all JSON/Markdown projections atomically. `check` validates
schemas, completeness, source references, publication structure, and byte
drift. `duplication-report.json` records normalized before/after Markdown
metrics.

## Adding a pipeline

1. Register the pipeline through the canonical composition registry and add its
   validated entity/provider/DQ/Gold configuration.
2. Ensure extraction filters and field groups are declared by their runtime
   owners.
3. Regenerate passports; do not add a generated page by hand.
4. Add a sidecar only for information that cannot be projected reliably.
5. Run the commands above and the strict documentation link/Mermaid gates.

Mermaid diagrams are rendered from the same facts as JSON and Markdown. They
must remain bounded, deterministic, free of occurrence IDs, and add
pipeline-specific topology rather than decorative prose.
