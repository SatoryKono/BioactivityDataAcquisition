# P17. CI/CD, GitHub Actions, release и dependency/build gates

## A. Audit Manifest
- **Repo:** `https://github.com/SatoryKono/BioactivityDataAcquisition`
- **Branch:** `main`
- **Revision (pin commit):** `ddbb7a0ee687365258bc407110e38601c4c3b765`
- **Scope:** `.github/workflows/**`, `.github/actions/**`, build/package/tool configs, release automation
- **Date/Time:** 2026-11-02
- **Environment:** OS Ubuntu, Python 3.12/3.13, uv 0.11.26
- **Unverified items:** Live hosting settings (branch protection / ruleset enforcement, required checks, environments) — текущий live GET не выполнялся; см. Finding 2 и исторический снимок в `docs/04-reference/github-actions-workflows.md`.

## B. Scope/ownership и exclusions
- **In Scope:** CI gate correctness, transitive workflow behavior, release automation (`release.yml`), dependency governance.
- **Out of Scope (Excluded):** Live mutation of GitHub settings; runtime CI history (нет доступа к полному журналу запусков).

## C. Evidence Ledger
- `E1 NORMATIVE`: `docs/00-project/RULES.md`, ADR stack; `docs/04-reference/github-actions-workflows.md` (inventory + keep-disabled policy for `release.yml`); header comments in `.github/workflows/release.yml` (`KEEP-DISABLED (#11182)`).
- `E2 STATIC`: `.github/workflows/release.yml`, `.github/workflows/tests.yml`, `pyproject.toml`, tracked `.github/workflows/*.yml` inventory.
- `E3 EXECUTABLE`: Read-only verification commands below (no workflow mutations).
- `E4 RUNTIME`: Не выполнялось — история запусков CI не читалась; live hosting API (rulesets/environments) не вызывался.

## D. Findings Register

### Finding 1
- **finding_id**: `pack-v2.1/P17-CICD-001`
- **root_cause_id**: `release-publish-keep-disabled-residual`
- **owner_prompt**: `P17`
- **concern**: В `.github/workflows/release.yml` триггер `release` удалён (#11182); `on:` содержит только `workflow_dispatch`. Job `publish-pypi` сохраняет `if: github.event_name == 'release'` и поэтому недостижим. Это согласуется с явной политикой keep-disabled: header workflow (`Do not re-enable` / `Publish stays outside GitHub Actions. workflow_dispatch is not a substitute`) и inventory (`docs/04-reference/github-actions-workflows.md`: `release.yml` → `keep-disabled`, «Do not restore the `release` trigger»).
- **severity**: `P3`
- **confidence**: `high`
- **status**: `CONFIRMED`
- **expected**: Keep-disabled release path либо без недостижимых publish-job'ов, либо с явной пометкой, что residual `if: release` оставлен намеренно и не является каналом публикации.
- **actual**: `publish-pypi` (и зависящий `create-github-release-assets`) остаются в YAML с условием `github.event_name == 'release'`, которое при текущем `on:` недостижимо; публикация через Actions намеренно отключена политикой, а не «сломана» как рабочий канал.
- **evidence_ids**: `E1`, `E2`, `E3`
- **attempted_disproof**: Проверено, запускает ли `workflow_dispatch` `publish-pypi`. `publish-testpypi` допускает `workflow_dispatch && dry_run == false` (строка 206). `publish-pypi` требует строго `github.event_name == 'release'` (строка 232) и при текущем `on:` не стартует. Восстановление публикации через расширение условия на `workflow_dispatch` **противоречит** политике #11182 / keep-disabled и **не** рекомендуется.
- **exceptions_checked**: Keep-disabled / publish-outside-Actions (#11182) — принимается как действующее исключение; residual unreachable jobs = optional hygiene, не regression рабочего publish-канала.
- **impact**: Канал публикации через Actions остаётся отключённым по политике. Residual dead jobs повышают риск ошибочной «починки» через `workflow_dispatch`, если рекомендация будет понята неверно.
- **root_cause**: После #11182 release-trigger удалён и publish оставлен вне Actions; YAML-фрагменты `publish-pypi` / `create-github-release-assets` не вычищены как optional cleanup в keep-disabled workflow.
- **recommendation**: Optional hygiene only — удалить недостижимые `publish-pypi` / `create-github-release-assets` **без** включения публикации и **без** расширения условий на `workflow_dispatch`. Любое восстановление publish-канала — только после явного изменения политики (`docs/04-reference/github-actions-workflows.md` + header `release.yml`).
- **scope / non-goals**: Только документация/optional cleanup keep-disabled YAML. Non-goal: re-enable Actions publish.
- **acceptance criteria**: Либо residual jobs удалены без включения publish, либо явно задокументированы как keep-disabled leftovers; рекомендаций вида «сделать publish через `workflow_dispatch`» нет.
- **verification command**: `git show ddbb7a0ee687365258bc407110e38601c4c3b765:.github/workflows/release.yml | nl -ba | sed -n '1,20p;200,260p'`; `git diff --no-ext-diff --unified=0 ddbb7a0ee687365258bc407110e38601c4c3b765 HEAD -- .github/workflows/release.yml`; `rg -n 'KEEP-DISABLED|Publish stays outside|release.yml' docs/04-reference/github-actions-workflows.md .github/workflows/release.yml`
- **verification result**: На audited SHA header L2–L3 = keep-disabled; `on:` = только `workflow_dispatch`; `publish-pypi` L226–L232 с `if: github.event_name == 'release'`. Diff `release.yml` audited SHA → `HEAD` пустой. Inventory: `release.yml` → `keep-disabled` / «Do not restore the `release` trigger (#11182)».
- **dependencies**: Нет (политика #11182 уже зафиксирована).

### Finding 2
- **finding_id**: `pack-v2.1/P17-CICD-002`
- **root_cause_id**: `live-hosting-settings-unverified`
- **owner_prompt**: `P17`
- **concern**: Текущие live branch protection / ruleset enforcement / environments нельзя подтвердить этим прогоном (live GitHub Settings API не вызывался).
- **severity**: `P3`
- **confidence**: `high`
- **status**: `NOT_VERIFIABLE`
- **expected**: Live hosting соответствует политике безопасности и актуальному inventory.
- **actual**: Live GET не выполнялся. Доступен **исторический** снимок в `docs/04-reference/github-actions-workflows.md` (Last verified / GET `2026-10-16`): rulesets `13643213` и `15730586` тогда были `enforcement: disabled`; это не доказательство текущего состояния.
- **evidence_ids**: `E1`, `E2`
- **attempted_disproof**: Прочитан published inventory; live API не вызывался → текущее состояние остаётся `NOT_VERIFIABLE`.
- **exceptions_checked**: Исторический снимок 2026-10-16 не подменяет live verification.
- **impact**: Неизвестен актуальный статус merge-protection / environments.
- **root_cause**: Отсутствие live API доступа в этом audit run.
- **recommendation**: Владелец репозитория — повторный read-only GET rulesets/environments; обновить inventory `Last verified`.
- **scope / non-goals**: N/A

## E. Quantitative Scorecard
- **Scale:** 1 (критичные незакрытые P0/P1 в scope) … 5 (нет открытых P0/P1; hosting verified; keep-disabled поверхности согласованы с политикой).
- **Formula (this run):** start 5; −1 за каждый открытый P0/P1 в register; −1 если hosting live settings `NOT_VERIFIABLE`; −0 за optional P3 hygiene в keep-disabled (не штраф сверх hosting). Итог: нет P0/P1, hosting `NOT_VERIFIABLE` → **Score 4**.
- **Score:** 4
- **Workflow file count:** 55 tracked `.github/workflows/*.yml` на audited SHA.
- **Count command/result:** `git ls-tree -r --name-only ddbb7a0ee687365258bc407110e38601c4c3b765 .github/workflows | rg '\.yml$' | wc -l` → `55` (совпадает с `docs/04-reference/github-actions-workflows.md`).
- **Justification:** Зафиксированы workflow count (55) и keep-disabled residual в `release.yml` (`E1`–`E3`); открытых P0/P1 нет. Штраф за live hosting `NOT_VERIFIABLE`. Полный обзор transitive graph / cache / secrets / lock-файлов / test matrices в этом прогоне **не** выполнялся с записанными командами (см. §H).

## F. Cross-cutting/root-cause clusters
- `release-publish-keep-disabled-residual`
- `live-hosting-settings-unverified`

## G. Prioritized roadmap P0->P3
1. [P3] Optional: удалить недостижимые `publish-pypi` / `create-github-release-assets` из keep-disabled `release.yml` **без** включения публикации.
2. [P3] Live GET branch protection / rulesets / environments и обновление inventory `Last verified`.

## H. Verification Matrix
- Transitive graph: `NOT_VERIFIABLE` — отдельная команда/результат обхода `workflow_call` графа в этом прогоне не записывались.
- Triggers/Permissions (кроме `release.yml`): `NOT_VERIFIABLE` — полный scan `on:`/`permissions:` по всем 55 workflow не выполнялся с записанным результатом. Для `release.yml` только: `git show ddbb7a0ee687365258bc407110e38601c4c3b765:.github/workflows/release.yml | nl -ba | sed -n '1,20p;200,260p'` → `on: workflow_dispatch`; jobs `publish-pypi`/`create-github-release-assets` с `if: github.event_name == 'release'`; header KEEP-DISABLED L2–L3.
- Cache keys: `NOT_VERIFIABLE` — поиск/проверка cache key patterns не выполнялись.
- Secrets/OIDC: `NOT_VERIFIABLE` — static/OIDC inventory по workflows не прогонялся; runtime publish не запускался.
- Lock files / test matrices: `NOT_VERIFIABLE` — `uv.lock` / matrix blocks не проверялись отдельными командами в этом прогоне.
- Workflow inventory count: выполнено — `git ls-tree -r --name-only ddbb7a0ee687365258bc407110e38601c4c3b765 .github/workflows | rg '\.yml$' | wc -l` → `55`.
- Hosting settings: `NOT_VERIFIABLE` (live GET не выполнялся); historical snapshot 2026-10-16 noted in docs inventory.

## I. `NOT_VERIFIABLE` и missing evidence
- Live конфигурация GitHub Environments и Secrets.
- Live ruleset enforcement / branch protection (исторический снимок 2026-10-16 ≠ current proof).
- Runtime история запусков CI (`E4`).

## J. Self-check
- Unsupported claims: Убраны «P1 / неполное удаление / чинить через `workflow_dispatch`» и вердикт «надежные» без runtime/hosting proof.
- Stale evidence: `release.yml` сравнён `git diff --no-ext-diff --unified=0 ddbb7a0ee687365258bc407110e38601c4c3b765 HEAD -- .github/workflows/release.yml` — diff пустой на tip honesty/inventory; pin audited SHA `ddbb7a0ee687365258bc407110e38601c4c3b765` сохранён.
- Exception handling: #11182 keep-disabled принят; residual jobs = optional cleanup.
- Score/severity consistency: нет открытых P0/P1; Score 4 из-за hosting `NOT_VERIFIABLE`.

## K. Verdict
В scope с записанными командами подтверждены: 55 tracked workflow YAML и keep-disabled residual в `release.yml` (#11182). Transitive graph, cache keys, secrets/OIDC, lock-файлы и test matrices — `NOT_VERIFIABLE` (команды не выполнялись). Runtime история CI и live hosting API **не** запускались. Главное замечание: residual недостижимые publish-job'ы в keep-disabled `release.yml` — optional P3 hygiene, не поломка рабочего канала публикации и не повод включать publish через `workflow_dispatch`.

## Issue drafts

> Pre-P20 draft only. Не создавать GitHub Issue из этой секции до сверки P20 (`docs/00-project/ai/prompts/library/audit/comprehensive.md`). Поля `final status` ниже — статус finding в P17, не разрешение на открытие Issue.

### Draft 1: release-publish-keep-disabled-residual
**Title:** CI: optional cleanup of unreachable publish jobs in keep-disabled release.yml

**Body:**
```markdown
**Provenance block:**
- audit_id: pack-v2.1/P17
- audited SHA: ddbb7a0ee687365258bc407110e38601c4c3b765
- root_cause_id: release-publish-keep-disabled-residual
- source finding IDs: pack-v2.1/P17-CICD-001
- draft severity: P3
- draft confidence: high
- finding status in P17: CONFIRMED
- issue open status: DRAFT_PENDING_P20 (do not open until P20)

**Problem:**
`.github/workflows/release.yml` is keep-disabled (#11182): `release` trigger removed; publish stays outside Actions; `workflow_dispatch` is not a substitute. Residual jobs `publish-pypi` / `create-github-release-assets` still use `if: github.event_name == 'release'` and are unreachable under the current `on:` block.

**Evidence:**
- `.github/workflows/release.yml:2-3` KEEP-DISABLED header
- `.github/workflows/release.yml:232` `publish-pypi` condition
- `docs/04-reference/github-actions-workflows.md` keep-disabled / do not restore `release` trigger
- `git diff --no-ext-diff --unified=0 ddbb7a0ee687365258bc407110e38601c4c3b765 HEAD -- .github/workflows/release.yml` → empty

**Expected vs actual:**
- **Expected:** Keep-disabled path either drops unreachable publish jobs or documents them as intentional leftovers without suggesting Actions publish restoration.
- **Actual:** Unreachable `if: release` jobs remain; policy already forbids re-enabling Actions publish.

**Impact:**
No working Actions publish channel by policy. Residual YAML risks misguided "fixes" that re-enable publish via `workflow_dispatch`.

**Scope / non-goals:**
- Scope: optional cleanup of `.github/workflows/release.yml` leftovers.
- Non-goal: restore Actions publish or expand job `if:` to `workflow_dispatch`.

**Architecture constraints:**
- Honor #11182 / keep-disabled; publish stays outside GitHub Actions until policy changes first.

**Implementation outline:**
- Optionally delete unreachable `publish-pypi` and `create-github-release-assets` jobs only.
- Do not re-add `release` trigger; do not make publish reachable via `workflow_dispatch`.

**Acceptance criteria:**
- Either residual unreachable publish jobs removed without enabling publish, or explicitly documented as keep-disabled leftovers.
- No recommendation remains to publish through Actions `workflow_dispatch`.

**Verification commands/tests:**
- `git show ddbb7a0ee687365258bc407110e38601c4c3b765:.github/workflows/release.yml | nl -ba | sed -n '1,20p;200,260p'`
- `git diff --no-ext-diff --unified=0 ddbb7a0ee687365258bc407110e38601c4c3b765 HEAD -- .github/workflows/release.yml`
- `rg -n 'KEEP-DISABLED|Publish stays outside|release.yml' docs/04-reference/github-actions-workflows.md .github/workflows/release.yml`

**Dependencies:**
- None for optional cleanup; policy change required before any publish re-enablement.

**Rollback/risk:**
- Low for deletion of unreachable jobs in already keep-disabled workflow.
```
