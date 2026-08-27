______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-27'

______________________________________________________________________

# Product / engineering cyclic pack (`prompt.audit.project.new2.*`)

Домены, которых **нет** в `prompt.audit.cycle.*` / `prompt.audit.project.new.*`:
Medallion, DQ, control-plane, провайдеры, HTTP-клиенты, нормализация, CLI,
секреты, VCR, QA-gates, GHA, REQ-trace, ops, scripts inventory.

Не runtime SSOT. Не заменяют `cycle/` и `new/`. Loop:
`prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

Файлы пронумерованы `NN-*` по **важности для BioETL** (write-path и DQ выше
CLI/CI; `scripts-inventory` в конце). Критерий: `RULES.md` §2 Medallion /
DQ / control-plane, затем каталог провайдеров и HTTP-acquisition, identity
нормализации, публичный CLI, секреты, тестовый VCR, QA-гейты, CI, REQ-trace,
ops (ADR-010 optional), гигиена `scripts/**`.

После 01–14 — CodeRabbit (`prompt.audit.project.new.coderabbit` или
`prompt.audit.cycle.coderabbit`).

Render (id не менялся):

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.project.new2.medallion `
  --param N=10 --param MODE=full --param LANGUAGE=ru
```

| NN | Id | File | Объект | Зачем здесь |
| --- | --- | --- | --- | --- |
| 01 | `prompt.audit.project.new2.medallion` | [01-medallion.md](01-medallion.md) | Bronze/Silver/Gold, quarantine, replay | `RULES` §2, write-path |
| 02 | `prompt.audit.project.new2.dq-contracts` | [02-dq-contracts.md](02-dq-contracts.md) | Pandera, column_order, QC, meta.yaml | `RULES` §2.8, Gold |
| 03 | `prompt.audit.project.new2.control-plane` | [03-control-plane.md](03-control-plane.md) | Manifest, ledger, resume/repair | ADR-044/046/047 |
| 04 | `prompt.audit.project.new2.providers` | [04-providers.md](04-providers.md) | Provider YAML ↔ adapters | каталог пайплайнов |
| 05 | `prompt.audit.project.new2.http-clients` | [05-http-clients.md](05-http-clients.md) | HTTP retry, QPS, UA, pagination | `RULES` §4.1.1 |
| 06 | `prompt.audit.project.new2.normalization` | [06-normalization.md](06-normalization.md) | Identifier families | identity строк |
| 07 | `prompt.audit.project.new2.cli-compat` | [07-cli-compat.md](07-cli-compat.md) | Public CLI/HTTP entrypoints | freeze публичного API |
| 08 | `prompt.audit.project.new2.security-secrets` | [08-security-secrets.md](08-security-secrets.md) | Secrets, SBOM-adjacent, .env | `RULES` §5, .env |
| 09 | `prompt.audit.project.new2.vcr-http` | [09-vcr-http.md](09-vcr-http.md) | VCR cassettes, secret-safety | детерминизм HTTP-тестов |
| 10 | `prompt.audit.project.new2.qa-gates` | [10-qa-gates.md](10-qa-gates.md) | Quality scripts / scorecard | enforcement гейтов |
| 11 | `prompt.audit.project.new2.github-actions` | [11-github-actions.md](11-github-actions.md) | CI supply chain (cyclic) | как гейты исполняются |
| 12 | `prompt.audit.project.new2.requirements-trace` | [12-requirements-trace.md](12-requirements-trace.md) | REQ-* ↔ code/tests | трассировка REQ |
| 13 | `prompt.audit.project.new2.ops-runbooks` | [13-ops-runbooks.md](13-ops-runbooks.md) | DR, rollback, Game Day | ADR-010 optional |
| 14 | `prompt.audit.project.new2.scripts-inventory` | [14-scripts-inventory.md](14-scripts-inventory.md) | scripts/** lifecycle | гигиена tooling |

Порядок прогона: **01→14**. Id карточек (`prompt.audit.project.new2.<domain>`)
не менялись.
