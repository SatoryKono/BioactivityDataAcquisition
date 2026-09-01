______________________________________________________________________

Version: 1.1.0
Status: deprecated
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-09-01'

______________________________________________________________________

# Cyclic audit pack (10 domains) — redirects

These files are **bookmarks**. SSOT is ADR-060 kernel + overlay + generated render.
Do not paste the old megacards; they duplicated the cyclic controller (D1) and
defaulted `ALLOW_*` unsafely (D2).

```bash
python -m scripts.ai.prompts compile --domain <domain> --profile audit-readonly
python -m scripts.ai.prompts compile --domain <domain> --profile full-write
```

| # | Legacy id | Overlay | Generated default |
| --- | --- | --- | --- |
| 1 | `prompt.audit.cycle.docs` | `overlays/docs.yaml` | `generated/docs/audit-readonly.md` |
| 2 | `prompt.audit.cycle.diagrams` | `overlays/diagrams.yaml` | `generated/diagrams/audit-readonly.md` |
| 3 | `prompt.audit.cycle.agents-memory` | `overlays/agents-memory.yaml` | `generated/agents-memory/audit-readonly.md` |
| 4 | `prompt.audit.cycle.configs` | `overlays/configs.yaml` | `generated/configs/audit-readonly.md` |
| 5 | `prompt.audit.cycle.tests` | `overlays/tests.yaml` | `generated/tests/audit-readonly.md` |
| 6 | `prompt.audit.cycle.tech-debt` | `overlays/tech-debt.yaml` | `generated/tech-debt/audit-readonly.md` |
| 7 | `prompt.audit.cycle.architecture` | `overlays/architecture.yaml` | `generated/architecture/audit-readonly.md` |
| 8 | `prompt.audit.cycle.telemetry` | `overlays/telemetry.yaml` | `generated/telemetry/audit-readonly.md` |
| 9 | `prompt.audit.cycle.dashboards` | `overlays/dashboards.yaml` | `generated/dashboards/audit-readonly.md` |
| 10 | `prompt.audit.cycle.coderabbit` | `overlays/coderabbit.yaml` | `generated/coderabbit/audit-readonly.md` |

Compatibility wrappers: `compatibility/<legacy-id>.md`.
Migration: [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
Frozen snapshot: [materialized-v3](../project/materialized-v3/README.md).
