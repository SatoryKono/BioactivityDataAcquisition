# Аудит Schema/config

Run: `20260819T082349Z-configs-cycle-592bf60`

Base: `origin/main@592bf60b74adf0a643a744ce3b7fc1b0c5a36c23`

Branch: `fix/audit-project-51eaed1f-configs`

## Итог

`surface_score: 3` — контроль зрелый: schema/config gates воспроизводимы,
единственный материальный drift найден автоматизированным тестом, исправлен
каноническим generator и повторно проверен. Открытых P0–P3 findings нет.

Проверено 10 содержательных направлений. Найден один P2 finding (`CFG-001`):
устаревший `docs/04-reference/config_comparison_matrix.csv`. Исправление обновило
только канонические generated artifacts; runtime config semantics не менялись.

## Scope

- `configs/**`: hierarchy, JSON schemas, provider/entity/composite YAML,
  compatibility and quality registries.
- `scripts/schema/**`, связанные tests/docs/ADRs: read-only evidence и validation.
- Canonical generated config artifacts: write только через
  `python -m scripts.schema generate-config-matrix --update`.
- Audit artifacts under this run and `reports/audit/configs/`.

Вне scope: `.env*`, runtime code changes, Docker/monitoring startup, merge в
`main`. Ни один `.env` файл не изменялся; secret values не выводились в
команды, логи или audit artifacts. При публикации root `.env` допускается
только как credential source согласно `AGENTS.md`.

## Результаты итераций

| Итерация | Поверхность | Результат |
| ---: | --- | --- |
| 1 | Hierarchy/inventory | PASS: 5 base, 7 provider, 27 entity and 5 composite entity contracts; legacy hierarchy отсутствует. |
| 2 | JSON Schema/generation | PASS: четыре JSON schemas parse; `generate-pipeline --check` и `validate-configs` зелёные. |
| 3 | Compatibility/retired aliases | PASS: registry и architecture tests подтверждают rejected retired forms. |
| 4 | Secrets/env | PASS: в tracked provider YAML нет `${ENV_VAR}`, secret literals или private-key markers; `.env` untouched. |
| 5 | Quality/debt budgets | PASS: aggregate и selected SHA-256 flat; `check-exemptions` сообщает 0 violations. |
| 6 | Composite identifiers | PASS по canonical contract: `doi/pmid` primary, `title` только fallback; title не primary key. |
| 7 | Provider/settings authority | PASS: ADR-057 precedence и strict provider source подтверждены validators/tests. |
| 8 | Unified entity completeness | PASS: 27/27 configs имеют требуемую структуру; gap analyzer сообщает 0 issues. |
| 9 | DQ/filter/schema parity | PASS: required fields/optionality и blocking schema parity зелёные; warnings non-blocking. |
| 10 | Generated artifacts/automation | FAIL → FIXED: matrix drift воспроизведён и устранён canonical generator. |

## Findings

### CFG-001 — resolved — P2 / Medium

`tests/architecture/test_config_discrepancy_report_drift.py:32` воспроизвёл
расхождение deterministic generator с
`docs/04-reference/config_comparison_matrix.csv`. Выполнен только canonical
generator; `--check` и focused regression после исправления выходят с кодом 0.

Новый GitHub issue не создан: finding закрыт в этом run, а исторический
дубликат #6240 уже закрыт. Issue write permission не использовалось для создания
шума без открытого остаточного дефекта.

## Control-wording observation (вне findings)

Внешний checklist говорит `never title`, но active
`.codex/agents/py-config-bot.md:46-48` запрещает `title` только как primary join
key. `configs/composites/publication.yaml:101-109` задаёт `doi/pmid` как primary
и `title` как fallback; integration tests закрепляют этот контракт. Закрытый
issue #3907 также описывает title fallback как намеренный residual enrichment
path. Поэтому config не изменялся, а wording prompt source не редактировался как
вне `Schema/config` scope.

## Validation evidence

- `python -m scripts.schema validate-configs` — PASS, 66 configs.
- `python -m scripts.schema check-invariants` — PASS, 27 pipeline configs.
- `python -m scripts.schema validate-unified-configs` — PASS, 27 configs.
- `python -m scripts.schema check-required-fields` — PASS.
- `python -m scripts.schema audit-optionality --check` — PASS.
- `python -m scripts.schema check-config-paths configs` — PASS.
- `python -m scripts.schema verify-schema-parity --mode blocking` — PASS;
  Silver-only warning inventory остаётся non-blocking.
- `python -m scripts.schema generate-pipeline --check` — PASS, 4 schemas.
- `python -m scripts.schema analyze-gaps` — PASS, 27 clean, 0 issues.
- `python -m scripts.engineering.qa check-exemptions` — PASS, 0 violations.
- Full `tests/integration/config` — PASS.
- Architecture `-k "config or schema or dq"` — один pre-fix drift failure;
  focused post-fix test и финальный broad rerun — PASS; три теста ожидаемо
  skipped на WSL по filesystem-performance marker.
- `python -m scripts.docs check-drift --runtime-mirrors --freshness` — PASS.
- `python -m scripts.docs check-links --links --specs --configs` — config,
  specs и nav subchecks PASS, общий exit 1 из-за 12 существующих broken links
  в prompt-library вне `Schema/config` и вне текущего diff.
- `bash scripts/engineering/dev/pretest_guardrails.sh --mode check --scope governance --skip-cleanup` — FAIL на существующем
  `configs/quality/scripts_inventory_manifest.json` drift вне текущего diff.
- `python -m scripts.docs verify --skip-links` — FAIL на существующем
  documentation cleanup inventory drift вне текущего diff.
- `python -m scripts.engineering.qa report-debt-governance-gates --check` —
  PASS на audited base, но после синхронизации с текущим `origin/main` FAIL на
  upstream module-coverage/scorecard generated-artifact drift; audited product diff не
  изменяет эти artifacts или их budgets.

Canonical WSL venv `/home/fedor/.venvs/bioetl` не содержит `pytest`; test
commands выполнены эквивалентным repository venv согласно wrapper fallback.

## Budgets, generated artifacts, mirrors

- `configs/quality/**` aggregate SHA-256: baseline = final =
  `be7dcdb5fec98cb304865c53bd78ff5c989b5a0fae98ce035fe3c1dd0a3c84a0`.
- После rebase upstream quality aggregate =
  `1f96c5ebbf77681d7f95593c576f3f1947dd7bba8c81d55a66877192cc2d911b`;
  `git diff origin/main -- configs/quality` пуст, поэтому product budget delta = 0.
- Budget delta: flat; debt outcome: `unchanged`.
- Generated artifacts refreshed only by the canonical generator.
- Runtime/docs mirror sync: not applicable; `.codex/**` and `.junie/**` were not changed.
- ADR-010: no mandatory Docker/Redis references introduced; monitoring not started.

## Proof-or-Stop и внешние blockers

Worktree-bound bundle:
`reports/quality/proof-or-stop/20260819T082349Z-configs-cycle-592bf60/bundle.json`.
После синхронизации со свежим `origin/main@7857c349dcdf9ec091d2ce6b1bee587ab7f71225`
финальная offline verification возвращает `STOP`:
`failed_receipt:governance`, `failed_receipt:docs_runtime` и
`failed_receipt:debt`; tests receipt имеет `pass`. Дополнительно trust tier
`local_single_host` помечен degradation. По текущему rollout это soft-fail
evidence, но claim `done` не qualified и не должен называться готовым к merge.
Исправление внешних generated inventories не применялось, поскольку это
расширило бы явно заданный `Schema/config` scope.

## Evidence-only close

Перед публикацией `origin/main` продвинулся до
`21dcaa936808fba3e3368136b8865db180ee36e1` и уже содержит product fix в
commit `3ade5d6e2a74b024737cfc6dd91402eb41cf793c`.
`git diff --quiet origin/main -- docs/04-reference/config_comparison_matrix.csv reports/quality/config-discrepancy-baseline.json`
вернул 0. В отдельном detached worktree текущего `origin/main` повторно прошли
`validate-configs` (66), `check-invariants` (27), canonical matrix `--check`,
focused drift test и `check-exemptions`. Поэтому feature branch не push-илась
и новый PR не создавался: это был бы дубликат уже принятого исправления.

## Open gaps

В audited config surface открытых findings нет: `CFG-001` resolved upstream;
P0/P1 отсутствуют. На repository closeout остаются три внешних validation
blockers, описанных выше.
