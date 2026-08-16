______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-12'

______________________________________________________________________

# Pipeline Dataflow Documentation

How to read and maintain pipeline **dataflow** documentation for BioETL:
passports, generated field/dataflow packs, and the relationship to entity
configs.

## Audience

- Contributors adding or changing a pipeline
- Reviewers checking that docs match configs and generated passports

## Sources of truth

| Surface | Path | Role |
| --- | --- | --- |
| Entity / provider configs | `configs/entities/{provider}/{entity}.yaml` | Runtime pipeline config SSOT |
| Pipeline catalog | [pipeline-catalog.md](../04-reference/pipeline-catalog.md) | Published inventory |
| Generated passports | `docs/02-architecture/generated/pipeline-dataflows/` | Code/config-derived passport packs |
| Passport CLI | `python -m scripts.docs passports` | Generate / check passports |
| Dataflow guide (config) | [pipeline-configuration.md](pipeline-configuration.md) | How configs compose |

Active narrative and contracts live under `docs/00-05`. Generated passports are
**derived**; do not hand-edit them to “fix” CI — regenerate instead.

## Reading a passport pack

Example (ChEMBL activity):

- Passport:
  `docs/02-architecture/generated/pipeline-dataflows/chembl_activity/pipeline-passport.md`
- Related entity config: `configs/entities/chembl/activity.yaml`
- Catalog row: [pipeline-catalog.md](../04-reference/pipeline-catalog.md)

Typical passport sections: source criteria, filters, processing stages, DQ
hooks, and layer field notes. Treat them as the published projection of the
entity config + code, not as a second config language.

## Maintainer workflow

1. Change entity/provider config and/or pipeline code under `src/bioetl/`.
2. Regenerate or check passports:

   ```bash
   uv run python -m scripts.docs passports check
   # when generators require an update:
   uv run python -m scripts.docs passports generate
   ```

3. Run the docs verification chain before merge:

   ```bash
   uv run python -m scripts.docs verify
   ```

4. CI (`Docs & Diagrams` / `.github/workflows/docs.yml`) re-runs passport check,
   link checks, and `python -m scripts.docs verify` on relevant path filters.

## Related guides

- [pipeline-configuration.md](pipeline-configuration.md) — config layout and ownership
- [pipeline-lifecycle.md](pipeline-lifecycle.md) — run lifecycle
- [docs-verification.md](docs-verification.md) — full docs gate checklist
- [Project Map](../00-project/00-map.md) — navigator entry points
