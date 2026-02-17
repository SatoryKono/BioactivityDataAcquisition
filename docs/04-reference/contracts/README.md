# Contract Versioning Rules

## Change classification

- **MAJOR**: rename/remove field, type narrowing, changing field from nullable to non-nullable.
- **MINOR**: additive nullable fields, non-breaking enum extensions.
- **PATCH**: description/example/editorial updates with no schema compatibility impact.

## Mandatory metadata in JSON contracts

Every contract JSON file **MUST** include:

- `$version` — semantic version of the contract.
- `$changelog` — link to contract changelog entry.

## Filename/version sync

Contract filenames use `*_vX.Y.json` and **MUST** be synchronized with `$version`:

- `*_v1.0.json` → `$version: "1.0.0"`
- `*_v1.1.json` → `$version: "1.1.0"`
- `*_v2.3.json` → `$version: "2.3.0"`
