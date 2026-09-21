______________________________________________________________________

Version: 4.1.0
Status: proposed-no-go
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-21'

Lifecycle: supporting_context
Retirement criterion: archive after migration closeout or an explicit decision to cancel the migration

______________________________________________________________________

# Финальный план переноса BioactivityDataAcquisition: GitHub → GitLab

Версия: v4.1 от 2026-09-21, после evidence-аудита выбранного профиля
`B1 + M1` (`R4-01…R4-09`).

Источник: `github.com/SatoryKono/BioactivityDataAcquisition` (public).

Предлагаемый target: top-level group `gitlab.com/bioetl1`, project path
`bioetl1/bioactivity-data-acquisition`, display name `BioactivityDataAcquisition`,
visibility `Public`, tier `Premium`. Namespace и subscription ещё не подтверждены
authenticated evidence.

Целевая модель: GitLab — source of truth; существующий GitHub repository —
публичный live push mirror по выбранному режиму M1.

> Этот документ — проверяемый план и набор gates, а не утверждённая инструкция
> production-переключения. Текущий итог аудита: **NO-GO** до закрытия всех P0 и
> относящихся к выбранным ветвям P1. Операторский runbook с конкретными ID,
> аккаунтами, окнами и командами выпускается только после успешной репетиции.

## 1. Итог аудита и рекомендуемая стратегия

### 1.1. Выбранная стратегия

Зафиксирована комбинация **B1 + M1**:

- **B1 — GitLab GitHub Importer** переносит полный согласованный Git/LFS и
  metadata scope в новый production project после freeze;
- **M1 — existing GitHub repository как live push mirror** сохраняет старые URLs,
  issues/PR history и публичную доступность кода;
- `attachments_import=true`, `collaborators_import=false`,
  `timeout_strategy=pessimistic`;
- GitLab становится единственным writer/source of truth; любые записи в GitHub
  после cutover считаются incidents.

B2 и B3 не являются автоматическими fallback. Если B1 не проходит rehearsal или
secret scan требует rewrite истории, выполнение возвращается в `NO-GO` и D-01
принимается заново. Переход на B2/B3 без нового решения и закрытого D-09 запрещён.

### 1.2. Критические выводы аудита

| ID | Приоритет | Вывод | Требуемое изменение |
| --- | --- | --- | --- |
| R3-01 | P0 | Исходные числа v3 устарели | Снимок §2 заменяет их; финальные числа снимаются под freeze |
| R3-02 | P0 | Текущий checkout — partial clone `blob:none` | Не использовать его как migration source; создать свежий полный mirror clone |
| R3-03 | P0 | GitHub Importer не выполняет delta/re-import | Production import начинается после freeze в новый проект; rehearsal-проект одноразовый |
| R3-04 | P0 | Live mirror несовместим с archived GitHub | Выбрать M1, M2 или M3 в §3.2; термин «archived live mirror» запрещён |
| R3-05 | P0 | После первой GitLab-only записи обычного rollback больше нет | Ввести point of no return и post-write recovery как отдельную миграцию |
| R3-06 | P0 | `.gitlab-ci.yml` — пилот, не эквивалент текущего merge gate | Перенести или осознанно заменить 50 workflow-файлов и 12 gate-групп |
| R3-07 | P0 | Mirror push может запустить GitHub Actions и публикацию в GHCR | До первого mirrored push отключить GitHub Actions на уровне репозитория и проверить нулевые side effects |
| R3-08 | P0 для B3 | Переписанная история не зеркалится безопасно в старый GitHub без destructive update | Для B3 выбрать новый mirror, immutable legacy snapshot либо согласованный rewrite с SHA map |
| R3-09 | P1 | Projects, Actions artifacts, GHCR и settings не покрыты Git-импортом | Добавить disposition для каждой внешней поверхности |
| R3-10 | P0 | Live GitHub rulesets сейчас disabled | Freeze и защита источника не могут опираться на документированное, но неактивное состояние |
| R3-11 | P0 | Required approvals и regex mirror filters зависят от тарифа | Тариф утверждается до CI design freeze |
| R3-12 | P1 | Git и LFS требуют разных доказательств | All-ref LFS manifest, чистый clone и отдельный mirror smoke обязательны |
| R3-13 | P0 | Единый RPO/RTO неоперационен | Задать числовые цели по data planes до репетиции |
| R3-14 | P0 | Не решены GHCR, PyPI/TestPyPI OIDC, SBOM и provenance | Зафиксировать publish/registry strategy до cutover |
| R3-15 | P1 | Counts не доказывают эквивалентность | Использовать object mapping, checksums, настройки и negative tests |

Evidence-аудит выбранного профиля добавил:

| ID | Приоритет | Вывод | Решение в v4.1 |
| --- | --- | --- | --- |
| R4-01 | P0 | Пользователь выбрал B1 + M1 | D-01 и D-03 зафиксированы; B2/B3 не являются fallback |
| R4-02 | P0 | `bioetl1` не разрешается публичным GitLab API, authenticated access отсутствует | Создать/подтвердить top-level group и Premium subscription до Gate A |
| R4-03 | P0 | Покрытый identity union = 41, conservative planning bound = 89; точное число placeholders заранее неизвестно | Premium `<100 seats`, limit 500, фактические usage/limit и `Import User` abort обязательны |
| R4-04 | P0 | 30 382 GitHub workflow runs за 30 дней делают hosted-only runner model рискованной | Основной self-hosted group runner + отдельный protected observability runner |
| R4-05 | P0 | Pilot GitLab CI покрывает только lock/test-fast/lint/SAST, а required catalog содержит 12 gate-групп | Реализовать fail-closed parity до rehearsal |
| R4-06 | P0 | GHCR package существует и имеет 188 downloads; Releases/PyPI/TestPyPI отсутствуют | GitLab Registry — canonical; GHCR — immutable legacy; PyPI activation вне migration scope |
| R4-07 | P1 | 206 файлов и 2 765 вхождений с legacy GitHub URL | M1 сохраняет исторические ссылки; новые canonical links переводятся на GitLab контролируемо |
| R4-08 | P0 | 2 193 commits, 645 issues и 565 PR созданы за 30 дней | Target freeze ≤4h, hard abort 8h, observation 30 дней |
| R4-09 | P1 | Projects и полный GHCR inventory не прочитаны из-за отсутствующих `read:project`/`read:packages` scopes | Закрыть scoped inventories до Gate A без расширения production credentials |

## 2. Проверенный снимок источника

Снимок получен read-only командами Git/GitHub API 2026-09-21. Он нужен для
планирования, но не заменяет финальный freeze manifest.

| Поверхность | Проверенный факт | Доказательство / примечание |
| --- | --- | --- |
| Repository | ID `1107864078`, public, default branch `main` | GitHub REST API |
| Default branch | `main`, SHA `03d9092ba456961fd8193a881741fff2fbdebea9` | GitHub API и `origin/main` |
| Ветки | 11 | `git ls-remote --heads origin`; все canonical branches входят в M1 |
| Теги | 55: 23 annotated, 32 lightweight | `git ls-remote --tags --refs`; локальная object-type проверка; все tags входят в M1 |
| Коммиты | 16 686 в `main`; 16 699 уникальных, достижимых из текущих `origin/*` refs | Не считать окончательным all-ref inventory до нового полного mirror clone |
| Активность Git | 2 193 commits за последние 30 дней; активность в 29 из 30 дней | Снимок GitHub API на 2026-09-21 |
| Issues | 30 open + 6 420 closed = 6 450; 645 созданы за 30 дней | GitHub GraphQL; REST `open_issues_count` смешивает issues и PR |
| Pull requests | 6 open + 1 078 closed + 3 042 merged = 4 126; 565 созданы за 30 дней | GitHub GraphQL |
| Workflows | 50 tracked YAML; 79 API objects; 30 382 runs за 30 дней | Канонический inventory: [GitHub Actions Workflow Inventory](../04-reference/github-actions-workflows.md) |
| Runners | Repository-level GitHub runners: 0; `dashboard-render-host.yml` требует `self-hosted, bioetl-observability` | Для GitLab нужен основной group runner и отдельный protected observability runner |
| GitLab CI | Пилот: lockfile, `make test-fast`, `make lint`, SAST include | Не является production parity с 12 gate-группами |
| LFS | 167 LFS OID на `main`, около 110,7 MiB; bounded smoke-набор остаётся plain Git | All-ref полнота ещё не доказана |
| GitHub repository size | 1 418 591 KiB по REST API | Оценка Git repository; LFS и attachments считать отдельно |
| Identities | 14 contributors + 4 anonymous; covered-surface union 41; conservative planning bound 89 | Issue-event inventory ограничен первыми 30 000 events; фактические placeholders проверяются импортом |
| Releases / packages | Releases: 0; PyPI/TestPyPI `bioetl`: отсутствует; public GHCR package существует, 188 downloads | Полный GHCR tag/digest/bytes inventory требует отдельного `read:packages` credential |
| Environments / secrets | Environments: `copilot`, `ghcr-publish`, `observability-render-host`, `pypi`, `testpypi`; repository secret: `MUSE_API_KEY`; Actions variables: 0 | Реестр фиксирует только имена/назначение, без secret values |
| Wiki / Pages / Discussions | отключены / отсутствуют | GitHub REST API |
| Projects | feature включён; количество не подтверждено | Текущий token не имеет `read:project` |
| Legacy GitHub URLs | 206 файлов, 2 765 вхождений | M1 сохраняет историческую адресацию; новые canonical links меняются отдельно |
| Target lookup | Public GitLab API возвращает 404 для group/user/project `bioetl1`; authenticated evidence отсутствует | 404 не доказывает доступность namespace: он может быть private; `glab` и GitLab token отсутствуют |
| Submodules | отсутствуют | `.gitmodules` отсутствует |
| Source protection | оба repository ruleset имеют `enforcement: disabled`; `main` не protected | Противоречит опубликованному snapshot в [GitHub Interaction Policy](../00-project/governance/05-github-policy.md) |
| Checkout | `remote.origin.promisor=true`, filter `blob:none` | Непригоден как migration source |

Контрольные числа динамичны. В production manifest включаются source repository
ID, `T_freeze`, API query/version, immutable raw response и checksum ответа.

## 3. Этап A — решения и входные условия

### 3.1. Выбранная ветвь переноса

Решение D-01 принято: **B1 — GitLab GitHub Importer**. Production destination —
новый пустой project; импорт запускается после freeze с
`attachments_import=true`, `collaborators_import=false` и
`timeout_strategy=pessimistic`.

B2 и B3 исключены из текущего execution scope и не являются fallback. Если B1 не
проходит rehearsal либо secret scan требует rewrite истории, статус возвращается
в `NO-GO`; смена ветви требует новой версии плана. Поэтому D-09 для выбранного
профиля имеет статус `Not applicable`.

### 3.2. Выбранный режим GitHub после cutover

Решение D-03 принято: **M1 — existing public GitHub repository как live push
mirror**.

- repository остаётся unarchived, чтобы GitLab мог выполнять push mirror;
- направление только GitLab → GitHub по HTTPS с отдельным fine-grained PAT;
- `Keep divergent refs=true`; downstream divergence вызывает alert и incident;
- зеркалируются все 11 canonical branches и все 55 tags; provider refs не входят;
- branch regex не используется, поэтому поведение не зависит от regex-функции
  платного тарифа;
- GitHub Actions, Dependabot, schedules, publishing, bots и изменяющие integrations
  отключаются до первого mirror push;
- новые GitHub issues, PR, comments и direct pushes считаются incidents;
- full `ls-remote` reconciliation для heads/tags является обязательной проверкой.

M1 сохраняет существующие public URLs и metadata history, что снижает риск для
2 765 legacy URL occurrences. GitHub не предоставляет идеального режима
«история видна, создание запрещено» для всех metadata surfaces, поэтому
остаточный риск контролируется мониторингом и incident procedure.

### 3.3. Decision package

| ID | Статус | Решение / предложение |
| --- | --- | --- |
| D-01 | **selected** | B1 GitLab GitHub Importer; B2/B3 не fallback |
| D-02 | **proposed** | `bioetl1/bioactivity-data-acquisition`, display name `BioactivityDataAcquisition`, `Public`, Premium, 2 seats, self-hosted runners |
| D-03 | **selected** | M1, все 11 branches и 55 tags, без regex, `Keep divergent refs=true` |
| D-04 | **proposed** | group namespace, planning bound 89 identities, Premium placeholder capacity, abort при любом `Import User` |
| D-05 | **proposed** | все 12 gate-групп и security stack сохраняются fail-closed; reductions запрещены |
| D-06 | **proposed** | числовые RPO/RTO, frequency и retention из §12.3 |
| D-07 | **proposed** | GitLab Registry canonical; GHCR immutable legacy; PyPI activation вне migration scope |
| D-08 | **proposed** | PONR — первая GitLab-only test issue с dual approval; 30-day observation |
| D-09 | **Not applicable** | B2/B3 metadata migrator не нужен выбранному B1 |

### 3.4. Рекомендуемый target и identity package

Рекомендуемый target после authenticated reservation:

- production top-level group `bioetl1`;
- project path `bioetl1/bioactivity-data-acquisition`;
- display name `BioactivityDataAcquisition`, visibility `Public`;
- GitLab Premium, два seats: Owner и независимый Maintainer/approver;
- основной self-hosted group runner;
- отдельный protected runner с tag `bioetl-observability`;
- GitLab.com runners — только fallback и rehearsal capacity.

Public API 404 не доказывает, что `bioetl1` свободен или принадлежит команде:
private namespace может выглядеть так же. D-02 нельзя утвердить без authenticated
проверки ownership, subscription, quota и возможности создать project.

Identity evidence: 14 contributors + 4 anonymous, 4 issue identities, 10 PR
identities, 15 issue-comment identities, 8 review-comment identities, 9 pull
review identities, 24 identities в доступных issue events и 1 direct
collaborator. Case-sensitive union покрытых поверхностей равен 41; conservative
planning bound — **89**. Issue Events API ограничил выборку первыми 30 000 events,
поэтому bound не считается точным числом placeholders.

Рекомендуется Premium top-level group с `<100 seats`: документированный limit —
500 placeholders против 200 на Free/trial. Перед каждым import вычисляется:

```text
headroom = displayed limit - current usage - 89
```

Минимум для Gate A — неотрицательный `headroom`; рекомендуемый operational запас
после bound — не менее 300. Любое назначение `Import User` означает abort и
повторный импорт в новый project. Rehearsal выполняется в отдельной top-level
group, чтобы contribution mappings не затрагивали production.

Ограничения тарифа учитываются как design input:

- GitLab.com не поддерживает `Internal` visibility;
- Free: 10 GiB на project repository + LFS; Premium/Ultimate: 500 GiB;
- maximum push size GitLab.com — 5 GiB на запрос; LFS upload регулируется
  отдельно;
- push mirroring доступен на Free, но regex branch filter — Premium/Ultimate;
- optional approvals доступны на Free, обязательные approval rules и Code Owner
  enforcement — Premium/Ultimate.

### 3.5. Контракт gates и Gate A

Каждая gate-запись имеет stable ID и обязательные поля: applicability, severity,
owner role, approver, immutable evidence, expected result, failure action и
waiverability. `Non-waivable` означает только `abort/fix/retry`; устное принятие
риска не закрывает запись. P0 по secrets, Git/LFS completeness, identity loss,
publishing и fail-closed CI всегда non-waivable.

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GA-01 | B1 + M1 / P0 | Migration Owner → Executive Sponsor | D-01/D-03 selected; D-02/D-04…D-08 утверждены; D-09 отмечен N/A; rejected alternatives сохранены | abort; non-waivable |
| GA-02 | B1 / P0 identity | Identity Owner → top-level Group Owner | authenticated ownership production group, Premium subscription, 2 seats, placeholder usage/limit с датой, bound 89 и headroom ≥0; personal namespace запрещён | abort or change target; non-waivable |
| GA-03 | B1 / P1 | Rehearsal Lead → Migration Owner | отдельная rehearsal top-level group; mappings и permissions не затрагивают production | recreate rehearsal; waiver только письменный до первого import |
| GA-04 | B1 + M1 / P0 | Backup Owner → Recovery Approver | backup/restore set §4 восстановлен в изоляции с checksums и source IDs | abort and repair backup; non-waivable |
| GA-05 | B1 + M1 / P0 secrets/source | Security Owner → Security Approver | новый полный non-promisor mirror clone; secret scan завершён; активные findings отсутствуют | abort; secret rewrite требует нового execution decision; non-waivable |
| GA-06 | B1 + M1 / P1 | Credential Owner → Security Approver | раздельные least-privilege credentials импортёра, GitLab API и зеркала; expiry/rotation записаны без values | reprovision; waiver запрещён для shared credential |
| GA-07 | B1 + M1 / P0 recovery | Plane Owners → Migration Owner | назначены owners Git/LFS, metadata, CI/security, publishing, cutover/recovery; предложенные §12.3 objectives письменно утверждены | abort; non-waivable |
| GA-08 | B1 / P0 identity | Identity Owner → Migration Owner | подготовлены import monitoring и post-import queries для `Import User`, approvals, reviewers и assignees; abort criterion включён в runbook | abort or increase capacity; non-waivable |

## 4. Инвентаризация и резервирование

### 4.1. Инвентарь

Для каждой поверхности фиксируются `source`, `scope decision`, `count`,
`size_bytes`, `checksum/digest`, permissions, dependencies, target,
validation, rollback/recovery action, owner и evidence URL.

Обязательные поверхности:

- Git refs, default branch, annotated tag objects и signatures;
- LFS OID по всем сохраняемым refs, path, size и content checksum;
- issues, PR, comments, reviews, review threads, events, reactions, labels,
  milestones, assignees, attachments и cross-references;
- repository settings, rulesets/protection, merge policy, deploy keys, webhooks,
  collaborators, apps и bots;
- 50 tracked workflows, 79 API workflow objects, schedules, environments,
  runners, artifact retention и Actions artifacts disposition;
- secret registry **без значений**: name, owner, purpose, scope, recovery source,
  rotation and expiry;
- Projects, issue/PR templates, labels automation и private vulnerability route;
- releases/assets, GitHub Packages/GHCR tags and digests, PyPI/TestPyPI trusted
  publishers, SBOM/provenance;
- Wiki, Pages, Discussions, forks, stars/watchers и repository redirects;
- hardcoded GitHub URLs в docs/configs/scripts и API-dependent tooling.

Actions artifacts не переносятся по умолчанию. Для их большого текущего набора
сначала утверждается retention policy: `discard expired`, `retain evidence`,
`export named artifact families` или `legal hold`. Counts без байтов и срока
хранения недостаточны.

### 4.2. Backup set

Backup хранится вне обоих изменяемых projects и включает:

1. свежий `git clone --mirror` без shallow/promisor filter;
2. `git lfs fetch --all` и immutable LFS manifest;
3. Git bundle или эквивалентную независимую копию всех согласованных refs;
4. постраничные raw API exports metadata со source IDs, URLs, relations и
   response checksums;
5. attachment/release-asset bytes с checksum и source relation;
6. settings/API inventory, workflow state, schedules, environments,
   integrations, registry/package inventory;
7. secrets metadata и процедуру повторного provision без сохранения secret
   values в plan/evidence.

`git push --mirror`, GitHub mirror и GitLab project export сами по себе не
являются backup. GitLab project export официально не включает CI/CD variables,
job traces/artifacts, package/container images, webhooks, encrypted tokens и
часть approval/security settings.

### 4.3. Приёмка backup

В изолированной среде должны быть восстановлены:

- Git refs и annotated tag objects;
- LFS bytes из независимой копии;
- цепочка `issue → discussion → attachment → PR/MR`;
- settings snapshot и secret re-provisioning checklist.

Hash доказывает целостность файла, но не восстанавливаемость. Read-only export,
который не прошёл restore rehearsal, не называется backup.

## 5. Профили исполнения

### 5.1. B1 — GitLab GitHub Importer

Профиль API фиксируется без token value:

```json
{
  "repo_id": "1107864078",
  "target_namespace": "bioetl1",
  "new_name": "bioactivity-data-acquisition",
  "optional_stages": {
    "attachments_import": true,
    "collaborators_import": false
  },
  "timeout_strategy": "pessimistic"
}
```

`collaborators_import=false` является частью выбранного профиля и не меняется в
production runbook: UI default может импортировать роли вплоть до Owner, что не
соответствует least-privilege target. Memberships создаются отдельно по
утверждённой role map. `attachments_import=true` задаётся явно, поскольку по
умолчанию вложения не импортируются; дополнительная длительность входит во
freeze measurement.

GitHub credential: только classic PAT; официальный профиль требует `repo`, а
`read:org` добавляется для collaborators или Git LFS. Отдельного «LFS scope» у
PAT нет. GitLab API credential имеет только необходимый scope и отдельный срок.

Importer переносит LFS и широкий набор metadata, но **не импортирует required
status checks**. Состояние `Complete` необходимо, но недостаточно;
`Partially completed` блокирует cutover до устранения. Waiver допустим только для
заранее исключённого non-mandatory объекта и не отменяет non-waivable P0.
Re-import создаёт новый project copy и не является delta import.

### 5.2. B2 — вне выбранного scope

B2 не реализуется, не репетируется и не используется как fallback в этой версии
плана. Переход на B2 требует нового execution decision, pinned metadata migrator,
обновлённого D-09 и отдельного evidence-аудита.

### 5.3. B3 — вне выбранного scope

B3 не реализуется, не репетируется и не используется как fallback. Находка
секрета, требующего rewrite истории, останавливает B1 и возвращает программу в
`NO-GO`; cleanup, SHA mapping и GitHub posture проектируются в новой версии
плана, а не во время cutover.

## 6. Финальный пакет GitLab и CI/security parity

Финальный набор `.gitlab-ci.yml`, root `CODEOWNERS`, scripts, templates и docs
попадает коммитом в GitHub до freeze. Project IDs, URLs, environment names,
runner tags и schedule owners параметризуются; rehearsal IDs не копируются.

Текущий `.gitlab-ci.yml` остаётся пилотом: он покрывает только lockfile,
`make test-fast`, `make lint` и SAST. При 30 382 GitHub workflow runs за 30 дней
GitLab.com hosted-only model не принимается как основной. Target runner model:
основной self-hosted group runner, отдельный protected runner с tag
`bioetl-observability`, GitLab.com runners только как rehearsal/fallback.

Gate C запрещено закрывать, пока:

1. для каждого из 50 GitHub workflow-файлов не записан disposition:
   `migrate`, `replace`, `retire-with-approved-risk` или
   `GitHub-mirror-only-disabled`;
2. все 12 gate-групп из
   [`configs/quality/github_required_checks.yaml`](../../configs/quality/github_required_checks.yaml)
   имеют fail-closed GitLab equivalent либо signed exception;
3. реализованы classifier, SHA binding, `not_applicable` с причиной,
   aggregation и artifact contracts;
4. global Git history fetch задан как полный (`GIT_DEPTH: "0"`) там, где
   проверки используют history/tags;
5. отдельно приняты MR, default-branch, schedule и tag pipelines;
6. отсутствие pipeline/job/report не может дать merge; `allow_failure`, manual,
   delayed и optional semantics проверены отрицательными тестами;
7. protected `main`, запрет direct/force push и deletion, successful pipeline,
   squash/merge policy и approvals проверены тестовым MR;
8. root `CODEOWNERS` использует GitLab users/groups и проверен на изменении
   critical path; required approvals и Code Owner approval включены на Premium;
9. fail-closed aggregator блокирует merge при missing pipeline/job/report,
   scanner error, cancelled/skipped/manual/optional обходе или SHA mismatch;
10. отдельный protected `bioetl-observability` runner прошёл positive и
    unavailable-runner negative scenarios.

GitLab SAST считается заменой, а не доказанной эквивалентностью CodeQL.
Security stack обязан сохранить SAST, Bandit, detect-secrets, Gitleaks,
pip-audit, OSV, Trivy, SPDX SBOM и zizmor; GitHub Actions YAML analysis,
dependency-review semantics, OpenSSF Scorecard и vulnerability triage получают
явный GitLab equivalent либо signed exception. MR, `main`, tag и schedule
pipelines принимаются отдельно.

BioETL baseline нельзя ослаблять ради миграции. Проверяются направления
зависимостей, агрегатные инварианты, strict Gold contracts, DQ, deterministic
replay, idempotent write и immutable quarantine payload. В рамках миграции test
count и coverage не уменьшаются; изменение baseline возможно только отдельной,
завершённой до миграции governance-задачей. Skip/xfail и debt budgets не
увеличиваются. Debt budgets могут только уменьшаться или оставаться неизменными;
их повышение в рамках миграции запрещено.

Publish disposition для выбранного профиля:

- GitLab Container Registry становится canonical registry;
- существующий public package
  `ghcr.io/satorykono/bioactivitydataacquisition` и его уже опубликованные
  digests остаются immutable legacy; после cutover новые GHCR writes запрещены;
- migration notice направляет consumers на GitLab Registry;
- broad long-lived GitHub `write:packages` token не создаётся;
- PyPI/TestPyPI `bioetl` сейчас отсутствуют, поэтому их activation вне migration
  scope; будущая публикация проектируется отдельно через GitLab.com OIDC trusted
  publisher;
- для immutable image digest сохраняются SPDX SBOM и keyless Cosign/Sigstore
  provenance;
- mirrored push не запускает package publish, release или attestation.

Полный GHCR inventory tags/digests/bytes остаётся Gate A evidence gap до
read-only запроса credential с `read:packages`; secret value в evidence не
сохраняется.

## 7. Этап B — репетиция

Репетиция выполняется в отдельной top-level GitLab group, без production
secrets, registry credentials и production publish permissions. Target project
одноразовый; он не переименовывается в production.

### 7.1. Обязательные сценарии

| ID | Severity | Сценарий |
| --- | --- | --- |
| RB-01 | P0 | полный happy-path выбранного B1 importer profile |
| RB-02 | P1 | partial importer failure и повтор запуска с нуля в новом project |
| RB-03 | P1 | token expiry/rate limit и безопасный restart |
| RB-04 | P0 | отсутствующий LFS object и checksum mismatch блокируют gate |
| RB-05 | P1 | attachment download failure и restart/idempotency |
| RB-06 | P0 | unavailable runner и отсутствующий required report блокируют merge |
| RB-07 | P0 | skipped/cancelled/manual/optional CI bypass attempts не обходят gate |
| RB-08 | P1 | divergent, stale и deleted GitHub refs при `Keep divergent refs` |
| RB-09 | P0 | pre-write rollback |
| RB-10 | P0 | post-write recovery sample для commit, LFS, issue, comment и attachment |
| RB-11 | P1 | временная архивация GitHub как freeze barrier |
| RB-12 | P0 | GitLab→GitHub mirror push без GitHub Actions/Dependabot/publish side effects |
| RB-13 | P0 | placeholder capacity, отсутствие `Import User`, затем проверка author, approvals, reviewers и assignees |
| RB-14 | N/A | зарезервирован для B2/B3 metadata migrator; выбранный B1 не применяет |
| RB-15 | P1 для M1 | full `ls-remote` reconciliation всех 11 branches и 55 tags, включая legitimate upstream deletion и unauthorized downstream ref |

### 7.2. Измерения и доказательства

Репетиция фиксирует:

- total duration и длительность каждого stage;
- required freeze window с запасом и abort threshold;
- importer status и failed entities;
- all-ref Git/LFS completeness;
- identity mapping и seat/role effect;
- mirror lag/error state;
- RTO каждого recovery сценария;
- CI runtime, report contracts и negative-test outcomes.

Fresh clone выполняется без общего Git/LFS cache. VCR-проверки включают как
LFS cassettes, так и bounded plain-text smoke set.

Историческая документация GitLab указывает LFS support для push mirror по HTTPS,
но текущая production capability всё равно доказывается репетицией. SSH mirror
не принимается как LFS path без отдельного vendor-proof и теста.

### 7.3. Gate B

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GB-01 | B1 / P0 | Rehearsal Lead → Migration Owner | RB-01 завершён; нет необъяснённых missing objects; importer status приемлем | abort/fix/re-run in new project; non-waivable |
| GB-02 | B1 + M1 / P0 | Scenario Owners → Migration Owner | все применимые P0 `RB-*` имеют immutable evidence и expected outcome | abort and repeat; non-waivable |
| GB-03 | B1 + M1 / P1 | Cutover Owner → Migration Owner | измеренное freeze window с запасом не превышает 8h и удовлетворяет формуле §9.1 | resize window or reject cutover; waiver запрещён при превышении hard limit |
| GB-04 | post-write / P0 recovery | Recovery Owner → Recovery Approver | RB-10 успешен с losses ledger и fail-forward path D-08 испытан | abort; non-waivable |
| GB-05 | B1 / P1 | Rehearsal Lead → Identity Owner | rehearsal project/top-level group, mappings и permissions отделены от production | recreate rehearsal; non-waivable after import starts |
| GB-06 | B1 / P0 identity | Identity Owner → top-level Group Owner | RB-13: нет `Import User`; authors, approvals, reviewers, assignees и role/seat effect сверены выборочно и агрегатно | abort/increase capacity/re-import; non-waivable |
| GB-07 | B1 + M1 / P0 Git/LFS | Git/LFS Owner → Migration Owner | all-ref manifest, annotated tags, LFS OID/bytes и fresh clone совпадают в обязательном scope | abort and repair/re-import; non-waivable |
| GB-08 | CI/publishing / P0 | CI/Security + Publishing Owners → Migration Approver | RB-06, RB-07 и RB-12 подтверждают fail-closed CI и нулевые publish side effects | abort; non-waivable |

## 8. Этап C — production readiness

### 8.1. Readiness checklist

До freeze должны быть готовы:

- финальный commit с GitLab CI/config/docs и указателями на новый source of truth;
- reproducible settings manifest/API scripts;
- production namespace/project name reservation;
- для B1 — отдельный classic GitHub importer PAT (`repo`, `read:org` где
  требуется, включая LFS) и отдельный least-privilege GitLab API token;
- для M1 — отдельный fine-grained GitHub mirror PAT с `Contents: read/write` и,
  поскольку repository содержит `.github/workflows`, `Workflows: read/write`,
  scoped только к `SatoryKono/BioactivityDataAcquisition`; importer и mirror
  никогда не используют один credential;
- credential expiry, owner и rotation procedure;
- мониторинг importer, pipeline, runners, mirror и backup;
- cutover ledger template и communication plan;
- проверенный способ отключить GitHub Actions на уровне repository;
- plan для Dependabot, GitHub Apps, schedules, webhooks и bots;
- formal go/no-go roster.

### 8.2. Gate C→D

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GC-01 | B1 + M1 / P0 readiness | Configuration Owner → Migration Approver | финальный commit и воспроизводимый settings manifest зафиксированы; production reservation, Premium subscription, runners и go/no-go roster готовы | abort/fix; non-waivable |
| GC-02 | B1 + M1 / P0 | Rehearsal Lead → Migration Approver | freeze, LFS, CI negative tests, RB-09/RB-10 и M1 mirror scenarios успешны в двух репетициях | abort/repeat; non-waivable |
| GC-03 | CI/security/publishing / P0 | CI/Security + Publishing Owners → Migration Approver | fail-closed controls, protected runners, GitLab Registry path и publish isolation доказаны; открытых P0 findings нет | abort; non-waivable |
| GC-04 | B1 + M1 / P1 | Credential Owner → Security Approver | importer, GitLab API и mirror используют разные least-privilege credentials; scopes, expiry, rotation и revocation evidence записаны без values | reprovision; shared/over-scoped credential non-waivable |
| GC-05 | B1 + M1 / P0 decisions | Migration Owner → Executive Sponsor | D-02/D-04…D-08 и предложенные §12.3 objectives утверждены; D-09 N/A; все применимые rehearsal scenarios закрыты | NO-GO; non-waivable |

## 9. Этап D — freeze и production import

### 9.1. Freeze mechanism

Freeze — это технический барьер, а не уведомление:

1. объявить окно и запретить merge/push/new issue/PR/comments;
2. остановить Dependabot, auto-merge, schedules, bots, webhooks и изменяющие
   integrations;
3. завершить либо отменить queued/in-progress GitHub Actions и через API
   подтвердить terminal state;
4. отключить GitHub Actions repository-wide;
5. зафиксировать открытые issues/PR и судьбу каждой открытой PR;
6. применить испытанную временную архивацию GitHub либо другой утверждённый
   механизм; live rulesets как freeze barrier не использовать, пока API
   показывает `enforcement: disabled`;
7. записать `T_freeze`, repository ID, `main` SHA, refs, object counts, settings,
   LFS и metadata manifests;
8. повторить backup delta и checksums.

Если importer несовместим с archived source, это должно быть обнаружено на
репетиции. В production нельзя импровизировать unarchive без эквивалентного
write barrier.

Целевое freeze-окно — не более 4 часов, hard limit — 8 часов. На `T+6h`
Cutover Owner обязан пересчитать forecast: если завершение и приёмка не
укладываются в `T+8h`, выполняется pre-write abort. Production разрешён только
после двух репетиций, для которых выполняется:

```text
max(rehearsal_duration) × 1.5 + 60m ≤ 8h
```

### 9.2. Production import

- Production destination — новый пустой GitLab project
  `bioetl1/bioactivity-data-acquisition` после authenticated reservation.
- B1 запускается один раз после `T_freeze`; rehearsal import не обновляется.
- B2/B3 не запускаются и не используются как recovery path.
- До окончания §10 запись в GitLab закрыта для всех, кроме migration service
  identities.
- Settings, protected branches, approvals, variables, runners, schedules,
  integrations и publish environments восстанавливаются из manifest; imported
  settings не считаются автоматически правильными.
- Для импортированных open MR запускается новый pipeline; imported status не
  используется как основание merge.
- После production import до открытия записи сверяются placeholder usage/limit,
  отсутствие объектов `Import User`, author mapping, approvals, reviewers,
  assignees и memberships; результаты входят в evidence bundle.

Abort выполняется при importer `Failed`, необъяснённом `Partially completed`,
missing LFS, любом назначении `Import User`, новом secret finding, превышении
freeze budget или невозможности включить fail-closed controls.

## 10. Этап E — контракт эквивалентности и приёмка

Counts используются только как diagnostic signal. Контракт принимает объекты и
семантику.

### 10.1. Git

- все 11 canonical `refs/heads/*` и 55 `refs/tags/*` совпадают по SHA для B1;
- default branch совпадает;
- 23 annotated tag objects и 32 lightweight tags классифицированы; для annotated
  tags сравнены object, target, message, tagger и signature state;
- provider-owned refs (`refs/pull/*`, `refs/merge-requests/*`) перечислены как
  исключения и не публикуются через M1;
- `git fsck --full` и fresh clone проходят.

### 10.2. LFS

Для каждого сохраняемого OID проверяются path, size и bytes checksum на source,
GitLab и выбранном GitHub mirror. Обязательны fresh clone, checkout
representative refs, `git lfs fetch --all` и `git lfs fsck` без старого cache.

Успешный Git push без LFS validation не считается успешным переносом.

### 10.3. Metadata

Machine-readable mapping имеет ключ:

```text
source_repository_id + source_type + source_id
    -> target_project_id + target_type + target_id
```

Для каждого обязательного объекта сравниваются state, author mapping,
assignees, labels, milestones, timestamps, comments/reviews, attachments bytes
и relations. Ограничения ссылок GitHub `#number` → GitLab issue/MR фиксируются
как expected transformations.

Обязательный результат — ноль missing objects и ноль необъяснённых differences
в согласованном B1 scope. Любое исключение должно быть записано в утверждённом
pre-import transformation manifest; post-factum сокращение scope запрещено.

### 10.4. Settings, CI и security

Проверяются:

- protected branches/tags, merge policy, approvals/CODEOWNERS;
- MR pipeline fail-closed behavior и SHA binding;
- schedules, runners, variables metadata, environments and integrations;
- отсутствие job/report и scanner error;
- positive security finding как отдельный outcome, не scanner failure;
- security coverage delta относительно GitHub;
- release/registry/OIDC path;
- GitHub Actions effectively disabled before mirror.

### 10.5. Gate E→F

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GE-01 | B1 / P0 scope | Validation Lead → Migration Approver | mandatory scope сохранён; differences объяснены и одобрены на уровне объектов, не только counts | abort/fix/re-import; non-waivable для missing mandatory object |
| GE-02 | B1 + M1 / P0 Git/LFS | Git/LFS Owner → Migration Approver | §10.1–10.2: 11 branches, 55 tags и каждый required LFS OID/bytes доказаны manifest/checksum/fresh clone | abort; non-waivable |
| GE-03 | B1 / P0 identity | Identity Owner → top-level Group Owner | нет `Import User`; production authors, approvals, reviewers, assignees и memberships соответствуют mapping/expected transformations | abort/re-import or approved target-capacity change; non-waivable |
| GE-04 | CI/security / P0 | CI/Security Owner → Security Approver | 12 gate-групп и required controls fail closed; missing pipeline/job/report и bypass attempts блокируют merge | abort; non-waivable |
| GE-05 | publishing / P0 | Publishing Owner → Publishing Approver | GitLab Registry/SBOM/provenance работают; GHCR остаётся immutable legacy; GitHub mirror даёт ноль publish side effects | abort; non-waivable |
| GE-06 | B1 + M1 / P0 recovery | Backup Owner → Recovery Approver | independent backup доступен и восстановлен; RB-09/RB-10 выполнены; post-write posture утверждён | abort; non-waivable |
| GE-07 | M1 / P1 | Mirror Owner → Migration Approver | all-branch/all-tag policy, LFS fresh-read и full `ls-remote` reconciliation прошли | fix/retest; non-waivable для выбранного M1 |
| GE-08 | B1 + M1 / P0 objectives | Recovery Owner → Migration Approver | §12.3: утверждённые RPO/recoverable points и RTO clocks измерены и находятся в целях | abort or revise approved objectives then repeat rehearsal; non-waivable |

Gate закрывает только именованный Migration Approver после подписи полного
evidence bundle; агрегатные counts без object-level доказательств недостаточны.

## 11. Этап F — cutover, зеркало и наблюдение

### 11.1. Point of no return

До первой GitLab-only mutation возможен обычный pre-write rollback. Точный
**point of no return (PONR)** — создание первой GitLab-only test issue с label
`migration-verification` от имени migration service identity после совместного
одобрения Migration Approver и Recovery Approver.

Cutover ledger до создания issue фиксирует UTC timestamp, actor, approvals,
issue intent, source `main` SHA, последнюю recoverable point и checksums Git/LFS/
metadata manifests. После PONR default strategy — fail-forward на GitLab;
возврат на GitHub является отдельной reverse migration, а не rollback.

### 11.2. Активация GitLab

1. включить protected branch и merge controls;
2. получить dual approval PONR в cutover ledger;
3. открыть запись migration service identity и создать test issue с label
   `migration-verification` в заранее разрешённой области;
4. после успешной проверки PONR открыть обычную запись только в GitLab;
5. обновить repository descriptions, README, contribution/security links;
6. включить только утверждённые schedules, bots и publishing paths;
7. начать observation period, не удаляя production source/backup.

### 11.3. Push mirror

Для выбранного M1:

- направление только GitLab → существующий GitHub repository;
- authentication — HTTPS fine-grained PAT;
- `Keep divergent refs=true`, чтобы divergent update дал failure/alert, а не
  молчаливую потерю; downstream-only refs остаются до классификации;
- branch regex не используется: зеркалируются все 11 canonical branches и все
  55 tags, а provider-owned refs исключаются;
- source и target используют один object format;
- monitor проверяет last successful update, lag, error и ref divergence;
- direct GitHub push, новый GitHub issue/PR/comment считаются incidents;
- GitHub Actions, Dependabot, schedules, bots и publish остаются отключёнными.

После каждого rehearsal/cutover change и периодически в observation window
выполняется full `git ls-remote` reconciliation для `refs/heads/*` и
`refs/tags/*`. Каждому target-only или mismatched ref присваивается один класс:

1. **unauthorized downstream divergence** — остановить mirror, сохранить SHA и
   actor evidence, обработать incident; удалять/перезаписывать ref только после
   одобрения Mirror Owner и Security Owner;
2. **legitimate upstream deletion** — наличие ref в deletion manifest проверено;
   если `Keep divergent refs` оставил его downstream, удалить явно утверждённой
   GitHub ref-deletion процедурой и повторить reconciliation;
3. **approved target-only ref** — редкое исключение, явно включённое в D-03 с
   owner, сроком и причиной.

Автоматическое удаление target-only refs без классификации запрещено.

Vendor baseline для обычного push mirror — до пяти минут. Принятый с запасом
10-minute mirror RPO из D-06 подтверждается rehearsal; режим
`Only mirror protected branches` не используется.

Mirror acceptance:

1. новый Git ref достигает GitHub в пределах mirror RPO;
2. все 11 canonical branches и 55 tags присутствуют, provider-owned refs не
   публикуются;
3. full heads/tags `ls-remote` reconciliation не содержит необъяснённых refs;
4. divergence создаёт alert и не перезаписывается;
5. legitimate upstream deletion удаляется по утверждённой процедуре, а
   unauthorized divergence сохраняет evidence;
6. новый LFS object, которого не было на GitHub, читается fresh clone без общего
   cache;
7. mirrored push не запускает workflow, package publish, release или bot action.

Для M1 временный archive снимается только после repository-wide отключения
GitHub Actions, Dependabot/schedules/publishing и проверки mirror credential.
До открытия обычной записи обязателен новый LFS object, ранее отсутствовавший на
GitHub, и его чтение через fresh clone без общего cache.

### 11.4. Observation period

Observation period длится не менее 30 дней и завершается не ранее чем после семи
полных clean days с момента последнего P0/P1 migration incident. В этот период:

- independent backups продолжаются;
- mirror lag и failed updates алертятся;
- GitHub repository не удаляется и остаётся public/unarchived;
- GitLab metadata mutations журналируются для recovery;
- любые GitHub issues/PR/comments/direct pushes triage как migration incident.

## 12. Recovery, RPO и RTO

### 12.1. Pre-write rollback

До point of no return:

1. оставить GitHub frozen;
2. остановить GitLab jobs/integrations;
3. сохранить evidence и failed target;
4. удалить или заморозить GitLab project по решению owner;
5. снять GitHub archive/freeze и восстановить workflows/integrations из
   manifest;
6. подтвердить GitHub CI и writer set.

### 12.2. Post-write recovery

После point of no return:

1. при P0 остановить writers и automations на обеих сторонах в течение 15 минут;
2. сохранить GitLab project, refs, LFS, metadata и audit evidence;
3. определить последнюю согласованную точку;
4. не позднее 60 минут после объявления incident выбрать fail-forward на GitLab
   либо отдельную reverse migration;
5. reverse migration выполнять только после испытанного mapping и с
   зарегистрированными потерями authorship, IDs, timestamps, reactions,
   discussions и attachments;
6. GitLab project не удалять до двусторонней сверки.

Нативного 1:1 rollback GitLab issues/MR/comments в GitHub план не обещает.
Если бизнес требует сохранения исходных IDs/authors/timestamps, post-write
возврат считается unsupported до доказанной sandbox automation.

### 12.3. Data-plane recovery objectives

RPO и RTO не объединяются в один показатель. Ниже приведены **предлагаемые
числовые цели, ожидающие письменного утверждения owners**; изменение целей после
неудачной репетиции требует повторной репетиции, а не waiver.

Общая retention policy: rolling checkpoints — 14 дней, daily full snapshots —
35 дней, weekly snapshots — 13 недель, cutover evidence — 180 дней. SPDX SBOM и
provenance сохраняются 365 дней.

| Plane | RPO target | Доказательство последней recoverable point | Backup/sync frequency | Retention | RTO target | RTO clock start → stop |
| --- | --- | --- | --- | --- | --- | --- |
| Canonical Git refs | 15 min | signed refs manifest + independent bundle checksum at `T_recoverable` | after every push + forced checkpoint every 10 min; daily full | 14d / 35d / 13w / cutover 180d | 4 h | incident declared → fresh clone доступен и `git fsck --full` успешен |
| Canonical LFS | 30 min | required all-ref OID manifest + bytes checksums at `T_recoverable` | every 15 min; daily full | 14d / 35d / 13w / cutover 180d | 4 h | incident declared → required OID fetched, checked out and `git lfs fsck` successful |
| M1 mirror delivery | 10 min | last successful mirror timestamp + heads/tags/OID fresh-read evidence | every upstream push + forced reconciliation every 10 min | logs 35d; cutover evidence 180d | 30 min | upstream push accepted → fresh GitHub read and reconciliation successful |
| Issues/MR/comments | 30 min | append/export checkpoint with source IDs, page checksums and last event timestamp | every 15 min; daily full | 14d / 35d / 13w / cutover 180d | 8 h | incident declared → target query and source→target mapping verified |
| Attachments/uploads | 1 h | object manifest with relation, size and checksum at `T_recoverable` | every 30 min; daily full | 14d / 35d / 13w / cutover 180d | 12 h | incident declared → all required bytes restored and checksums verified |
| CI settings/variables/schedules | 4 h | settings manifest + secrets metadata/re-provision checkpoint | before every settings change + every 2 h; daily full | 14d / 35d / 13w / cutover 180d | 4 h | incident declared → required pipeline passes with schedules/integrations in approved state |
| Registry/packages | 1 h | tag/digest/SPDX SBOM/provenance manifest at `T_recoverable` | every publish + daily full | snapshots 35d; cutover 180d; SBOM/provenance 365d | 8 h | incident declared → approved artifact pull and digest/signature checks succeed |
| Public read access | N/A: availability, не data-loss objective | latest successful endpoint probe and deployment/ref identity | probe every 5 min | probe logs 35d; cutover evidence 180d | 2 h | outage detected/declared → approved public endpoint serves verified content |

`RPO=0` допустим только в управляемом freeze scope с доказанной последней
recoverable point. Асинхронное зеркало имеет lag и не является backup; ошибочный
force-push/delete может реплицироваться. Аварийный сценарий недоступности GitLab
использует независимую backup copy и собственный допустимый data loss, а не
предполагаемую доступность GitLab export.

## 13. Статусы аудитов и управление исполнением

Статусы имеют только три значения:

- `учтено в плане` — требование присутствует в v4.1;
- `реализовано` — создан артефакт/настройка и приложено evidence;
- `проверено на репетиции` — сценарий фактически выполнен в изоляции.

Статус не повышается по тексту плана.

| Набор | Статус на 2026-09-21 | Примечание |
| --- | --- | --- |
| MIG-01…MIG-14 | учтено в плане | Унаследовано из v2/v3; реализация требует evidence |
| R2-01…R2-11 | учтено в плане | Унаследовано из v3 и уточнено текущим аудитом |
| R3-01…R3-15 | учтено в плане | Выводы первого evidence-аудита; ни один не заявлен реализованным |
| R4-01…R4-09 | учтено в плане | Выводы аудита выбранного B1 + M1; реализация требует evidence |

Минимальный execution ledger для каждого пункта:

| Field | Значение |
| --- | --- |
| Requirement ID | `MIG-*`, `R2-*`, `R3-*` или `R4-*` |
| Selected branch | `B1 + M1` |
| Status | одно из трёх допустимых значений |
| Owner | именованная роль/аккаунт |
| Evidence | immutable URL/path + checksum |
| Verified at | UTC timestamp |
| Failure action | abort, fix/retry или signed waiver только если запись waiverable |
| Waiverability | `non-waivable` либо approver и допустимый scope waiver |

## 14. Условия продвижения плана

Этот документ остаётся `supporting_context` и не ведёт параллельную execution
queue. Единственная очередь исполнения — задача `MIG-GHGL-01` в
[Consolidated Open Tasks Plan](consolidated-open-tasks-plan-2026-03-21.md).

План может быть повышен из `proposed-no-go` только когда:

1. `MIG-GHGL-01` назначена owner и approver;
2. выбранные D-01 `B1` и D-03 `M1` сохранены без подмены fallback;
3. D-02 и D-04…D-08 письменно утверждены, D-09 остаётся N/A;
4. Gate A закрыт по stable evidence records `GA-01…GA-08`;
5. read-only inventory, all-ref LFS и backup restore завершены;
6. namespace/tier/runners подтверждены authenticated evidence;
7. отдельный операторский runbook подготовлен для rehearsal без production
   secrets.

До выполнения этих условий rehearsal и production cutover остаются **NO-GO**.

## 15. Нормативные и vendor-источники

Репозиторные источники:

- [BioETL Normative Sources Index](../00-project/NORMATIVE_SOURCES.md)
- [BioETL Rules](../00-project/RULES.md)
- [GitHub Actions Workflow Inventory](../04-reference/github-actions-workflows.md)
- [GitHub Interaction Policy](../00-project/governance/05-github-policy.md)
- [`github_required_checks.yaml`](../../configs/quality/github_required_checks.yaml)
- [Post-change validation](../00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md)

Vendor facts, повторно проверяемые не позднее чем за семь дней до rehearsal и
cutover:

- [GitLab: Migrate from GitHub](https://docs.gitlab.com/user/project/import/github/)
- [GitLab: Import API](https://docs.gitlab.com/api/import/)
- [GitLab: Post-migration contribution mapping](https://docs.gitlab.com/user/import/mapping/post_migration_mapping/)
- [GitLab: Push mirroring](https://docs.gitlab.com/user/project/repository/mirror/push/)
- [GitLab: Repository mirroring](https://docs.gitlab.com/user/project/repository/mirror/)
- [GitLab: Storage](https://docs.gitlab.com/user/storage_usage_quotas/)
- [GitLab.com settings and limits](https://docs.gitlab.com/user/gitlab_com/)
- [GitLab: Project visibility](https://docs.gitlab.com/user/public_access/)
- [GitLab: Project export limitations](https://docs.gitlab.com/user/project/settings/import_export/)
- [GitLab: Merge request approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [GitHub: Archiving repositories](https://docs.github.com/en/repositories/archiving-a-github-repository/archiving-repositories)
- [GitHub: Duplicating a repository with LFS](https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository)
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GitHub: Disable and enable workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
