______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-27'

______________________________________________________________________

# Product / engineering cyclic pack (`prompt.audit.project.new2.*`)

Домены, которых **нет** в `prompt.audit.cycle.*` / `prompt.audit.project.new.*`:
Medallion, HTTP-клиенты, DQ, control-plane, провайдеры, CLI, VCR, scripts
inventory, GHA-цикл, секреты, нормализация, REQ-trace, ops, QA-gates.

Не runtime SSOT. Не заменяют `cycle/` и `new/`. Loop:
`prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=false`**.

Порядок: **A (1–5) → B (6–10) → C (11–14)**. После A–C — CodeRabbit
(`prompt.audit.project.new.coderabbit` или `prompt.audit.cycle.coderabbit`).

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.project.new2.medallion `
  --param N=10 --param MODE=full --param LANGUAGE=ru
```

| # | Волна | Id | File | Объект |
| --- | --- | --- | --- | --- |
| 1 | A | `prompt.audit.project.new2.medallion` | [medallion.md](medallion.md) | Bronze/Silver/Gold, quarantine, replay |
| 2 | A | `prompt.audit.project.new2.http-clients` | [http-clients.md](http-clients.md) | HTTP retry, QPS, UA, pagination |
| 3 | A | `prompt.audit.project.new2.dq-contracts` | [dq-contracts.md](dq-contracts.md) | Pandera, column_order, QC, meta.yaml |
| 4 | A | `prompt.audit.project.new2.control-plane` | [control-plane.md](control-plane.md) | Manifest, ledger, resume/repair |
| 5 | A | `prompt.audit.project.new2.providers` | [providers.md](providers.md) | Provider YAML ↔ adapters |
| 6 | B | `prompt.audit.project.new2.cli-compat` | [cli-compat.md](cli-compat.md) | Public CLI/HTTP entrypoints |
| 7 | B | `prompt.audit.project.new2.vcr-http` | [vcr-http.md](vcr-http.md) | VCR cassettes, secret-safety |
| 8 | B | `prompt.audit.project.new2.scripts-inventory` | [scripts-inventory.md](scripts-inventory.md) | scripts/** lifecycle |
| 9 | B | `prompt.audit.project.new2.github-actions` | [github-actions.md](github-actions.md) | CI supply chain (cyclic) |
| 10 | B | `prompt.audit.project.new2.security-secrets` | [security-secrets.md](security-secrets.md) | Secrets, SBOM-adjacent, .env |
| 11 | C | `prompt.audit.project.new2.normalization` | [normalization.md](normalization.md) | Identifier families |
| 12 | C | `prompt.audit.project.new2.requirements-trace` | [requirements-trace.md](requirements-trace.md) | REQ-* ↔ code/tests |
| 13 | C | `prompt.audit.project.new2.ops-runbooks` | [ops-runbooks.md](ops-runbooks.md) | DR, rollback, Game Day |
| 14 | C | `prompt.audit.project.new2.qa-gates` | [qa-gates.md](qa-gates.md) | Quality scripts / scorecard freshness |
