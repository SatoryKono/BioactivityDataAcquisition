______________________________________________________________________

Version: 4.0.0
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

Версия: v4 от 2026-09-21, после третьего аудита (`R3-01…R3-15`).

Источник: `github.com/SatoryKono/BioactivityDataAcquisition` (public).

Целевой namespace: `gitlab.com/bioetl1`; точный project path, видимость и тариф
ещё не утверждены.

Целевая модель: GitLab — source of truth. Режим GitHub после переключения
выбирается отдельным решением в §3.2.

> Этот документ — проверяемый план и набор gates, а не утверждённая инструкция
> production-переключения. Текущий итог аудита: **NO-GO** до закрытия всех P0 и
> относящихся к выбранным ветвям P1. Операторский runbook с конкретными ID,
> аккаунтами, окнами и командами выпускается только после успешной репетиции.

## 1. Итог аудита и рекомендуемая стратегия

### 1.1. Рекомендация

Базовой ветвью исполнения рекомендуется **B1 — полный GitHub Importer**:

- объём истории work items велик, поэтому выборочный перенос B2 создаёт
  непропорциональный риск разрыва ссылок и контекста;
- официальный GitLab GitHub Importer переносит Git, LFS, issues, pull requests,
  reviews, comments, labels, milestones, wiki и часть branch protection;
- B3 оправдан только подтверждённой необходимостью переписать историю после
  revoke/rotate и security-аудита.

Решение остаётся условным до Gate A. Если security-аудит обнаружит секрет,
который требуется удалять из истории, B1 и B2 запрещены и выбирается B3. Если
полный импортёр не проходит репетицию, B2 допускается только как явно lossy
`scoped work-item migration` с подписанным перечнем потерь.

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

## 2. Проверенный снимок источника

Снимок получен read-only командами Git/GitHub API 2026-09-21. Он нужен для
планирования, но не заменяет финальный freeze manifest.

| Поверхность | Проверенный факт | Доказательство / примечание |
| --- | --- | --- |
| Default branch | `main`, SHA `03d9092ba456961fd8193a881741fff2fbdebea9` | GitHub API и `origin/main` |
| Ветки | 11 | `git ls-remote --heads origin` |
| Теги | 55: 23 annotated, 32 lightweight | `git ls-remote --tags --refs`; локальная object-type проверка |
| Коммиты | 16 686 в `main`; 16 699 уникальных, достижимых из текущих `origin/*` refs | Не считать окончательным all-ref inventory до нового полного mirror clone |
| Issues | 25 open + 6 420 closed = 6 445 | GitHub GraphQL; REST `open_issues_count` смешивает issues и PR |
| Pull requests | 6 open + 1 078 closed + 3 042 merged = 4 126 | GitHub GraphQL |
| Workflows | 50 tracked YAML; 79 API objects: 35 active, 44 disabled manually | Канонический inventory: [GitHub Actions Workflow Inventory](../04-reference/github-actions-workflows.md) |
| GitLab CI | Пилот: lockfile, `make test-fast`, `make lint`, SAST include | Не является production parity |
| LFS | 167 LFS OID на `main`, около 110,7 MiB; bounded smoke-набор остаётся plain Git | All-ref полнота ещё не доказана |
| GitHub repository size | 1 418 591 KiB по REST API | Оценка Git repository; LFS и attachments считать отдельно |
| Releases | 0 | GitHub GraphQL; утверждение v3 о двух релизах опровергнуто текущим состоянием |
| Wiki / Pages / Discussions | отключены / отсутствуют | GitHub REST API |
| Projects | feature включён; количество не подтверждено | Для API-инвентаря нужен соответствующий scope |
| Submodules | отсутствуют | `.gitmodules` отсутствует |
| Source protection | оба repository ruleset имеют `enforcement: disabled`; `main` не protected | Противоречит опубликованному snapshot в [GitHub Interaction Policy](../00-project/governance/05-github-policy.md) |
| Checkout | `remote.origin.promisor=true`, filter `blob:none` | Непригоден как единственный migration source |

Контрольные числа динамичны. В production manifest включаются source repository
ID, `T_freeze`, API query/version, immutable raw response и checksum ответа.

## 3. Этап A — решения и входные условия

### 3.1. Выбор ветви переноса

Владелец миграции утверждает ровно одну ветвь:

- **B1 — full GitHub Importer (рекомендуется).** Новый пустой production-проект,
  API import с явно заданными `optional_stages.attachments_import` и
  `optional_stages.collaborators_import`, `timeout_strategy=pessimistic`.
- **B2 — Git/LFS + scoped work items.** Полная Git-история сохраняется, но
  metadata scope задаётся immutable allowlist. В документах запрещено называть
  B2 полной или эквивалентной миграцией.
- **B3 — очищенная Git/LFS-история + metadata migration.** Выполняется только
  после revoke/rotate и утверждённого cleanup scope. SHA меняются; нужен
  `old_sha → new_sha` map, повторный secret scan и отдельное решение по GitHub.

Пока D-09 не закрыт испытанным и pinned metadata migrator profile, B2 и B3 —
только кандидаты, а не готовые fallback-ветви. Запрещено импортировать metadata
B1, а затем молча заменять Git repository результатом B3: commit links и MR diff
context станут несогласованными.

### 3.2. Режим GitHub после cutover

Выбирается ровно один режим:

- **M1 — existing repository как live push mirror.** Репозиторий должен быть
  unarchived. GitHub Actions, Dependabot и изменяющие интеграции отключены.
  История issues/PR остаётся доступна, но GitHub не предоставляет идеального
  режима «история видна, создание запрещено» для всех metadata surfaces;
  остаточный риск новых объектов принимается явно.
- **M2 — existing repository как archived historical snapshot + новый GitHub
  repository как live code mirror (рекомендуется, если обязательны и
  неизменяемая история, и актуальное зеркало).** Старые URLs и metadata остаются
  read-only, новый mirror содержит только согласованный набор Git/LFS refs.
- **M3 — existing repository как archived snapshot без live mirror.** Выбирается,
  если неизменяемость важнее актуальной GitHub-копии.

GitHub archive делает code, branches, tags, issues, PR, releases и permissions
read-only, поэтому live push mirror в archived repository невозможен.

Для B3 режим M1 допускается только после явного согласования destructive
force-update текущего GitHub. Без такого решения выбирается M2 или M3.

### 3.3. Остальные обязательные решения

До Gate A утверждаются decision records:

| ID | Решение | Минимальное содержание |
| --- | --- | --- |
| D-01 | Execution profile | B1/B2/B3, причины, rejected alternatives, SHA semantics |
| D-02 | Target | точный project path и production top-level group; public/private; plan и seat count; quota headroom; текущие placeholder usage/limit с датой проверки; runner model |
| D-03 | GitHub posture | M1/M2/M3, branch policy, отдельная tag policy, судьба issues/PR, public/private conflict |
| D-04 | Identity | group namespace; верхняя оценка уникальных source identities; placeholder usage/актуальный vendor limit и запас; reassignment owner/recipients; bots/deleted accounts; проверки approvals/reviewers/assignees; abort при `Import User` |
| D-05 | CI/security parity | принятые замены и запрещённые reductions по каждому control |
| D-06 | Recovery objectives | RPO, recoverable-point evidence, backup frequency/retention, RTO и clock по каждому plane из §12.3 |
| D-07 | Publishing | GHCR/GitLab Registry, PyPI/TestPyPI OIDC, releases, SBOM, provenance |
| D-08 | Point of no return | первая разрешённая GitLab-only mutation, approver, observation period |
| D-09 | B2/B3 metadata migrator | конкретный API/tool; pinned version/commit/image digest; restart и idempotency; rate limits; fidelity author/timestamp/attachment; ID mapping; known losses; B3 policy для old-SHA links |

Если важно сохранить и впоследствии переназначить contribution mapping,
`bioetl1` должен быть **group namespace**, а не personal namespace: импорт в
personal namespace назначает contributions владельцу без возможности последующего
переназначения. Placeholder users создаются и лимитируются на уровне top-level
group. Текущая vendor-документация для post-migration mapping на GitLab.com
требует подготовленного paid namespace. До production import фиксируются
plan/seat count, текущий usage, актуальный vendor limit и оценка требуемых
identities; точное число placeholders заранее не гарантируется, поэтому любой
объект, назначенный `Import User`, означает abort.

Ограничения тарифа учитываются как design input:

- GitLab.com не поддерживает `Internal` visibility;
- Free: 10 GiB на project repository + LFS; Premium/Ultimate: 500 GiB;
- maximum push size GitLab.com — 5 GiB на запрос; LFS upload регулируется
  отдельно;
- push mirroring доступен на Free, но regex branch filter — Premium/Ultimate;
- optional approvals доступны на Free, обязательные approval rules и Code Owner
  enforcement — Premium/Ultimate.

### 3.4. Контракт gates и Gate A

Каждая gate-запись имеет stable ID и обязательные поля: applicability, severity,
owner role, approver, immutable evidence, expected result, failure action и
waiverability. `Non-waivable` означает только `abort/fix/retry`; устное принятие
риска не закрывает запись. P0 по secrets, Git/LFS completeness, identity loss,
publishing и fail-closed CI всегда non-waivable.

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GA-01 | все ветви / P0 | Migration Owner → Executive Sponsor | D-01…D-09 подписаны; нет `TBD` в применимых решениях; B2/B3 не выбираются при незакрытом D-09 | abort; non-waivable |
| GA-02 | metadata import / P0 identity | Identity Owner → top-level Group Owner | production group namespace, plan/seat count, текущие placeholder usage/limit с датой, upper bound identities и headroom; personal namespace запрещён при требуемом mapping | abort or change target; non-waivable |
| GA-03 | все ветви / P1 | Rehearsal Lead → Migration Owner | отдельная rehearsal top-level group; mappings и permissions не затрагивают production | recreate rehearsal; waiver только письменный до первого import |
| GA-04 | все ветви / P0 | Backup Owner → Recovery Approver | backup/restore set §4 восстановлен в изоляции с checksums и source IDs | abort and repair backup; non-waivable |
| GA-05 | все ветви / P0 secrets/source | Security Owner → Security Approver | новый полный non-promisor mirror clone; secret scan завершён; активные findings отсутствуют либо выбран B3 после revoke/rotate | abort; non-waivable |
| GA-06 | B1/M1/M2 / P1 | Credential Owner → Security Approver | раздельные least-privilege credentials импортёра, GitLab API и зеркала; expiry/rotation записаны без values | reprovision; waiver запрещён для shared credential |
| GA-07 | все ветви / P0 recovery | Plane Owners → Migration Owner | назначены owners Git/LFS, metadata, CI/security, publishing, cutover/recovery; §12.3 заполнен числовыми целями и clocks | abort; non-waivable |
| GA-08 | metadata import / P0 identity | Identity Owner → Migration Owner | подготовлены import monitoring и post-import queries для `Import User`, approvals, reviewers и assignees; abort criterion включён в runbook | abort or increase capacity; non-waivable |

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
  "repo_id": "<github-repository-id>",
  "target_namespace": "bioetl1/<approved-subgroup>",
  "new_name": "<approved-project-name>",
  "optional_stages": {
    "attachments_import": true,
    "collaborators_import": false
  },
  "timeout_strategy": "pessimistic"
}
```

`collaborators_import` включается только после D-04 и role-map review. В UI он
выбран по умолчанию и может дать роли вплоть до Owner; outside collaborators не
импортируются. `attachments_import` по умолчанию не выполняется и увеличивает
длительность.

GitHub credential: только classic PAT; официальный профиль требует `repo`, а
`read:org` добавляется для collaborators или Git LFS. Отдельного «LFS scope» у
PAT нет. GitLab API credential имеет только необходимый scope и отдельный срок.

Importer переносит LFS и широкий набор metadata, но **не импортирует required
status checks**. Состояние `Complete` необходимо, но недостаточно;
`Partially completed` блокирует cutover до устранения. Waiver допустим только для
заранее исключённого non-mandatory объекта и не отменяет non-waivable P0.
Re-import создаёт новый project copy и не является delta import.

### 5.2. B2 — Git/LFS + scoped work items

B2 не допускается к rehearsal, пока D-09 не утвердит конкретный migrator. Базовый
технический профиль для оценки — repository-owned API runner поверх GitHub
GraphQL/REST и GitLab REST API v4; production artifact должен быть pinned по
commit/version и image digest, а запросы/ответы — версионированы и сохранены как
evidence. Замена этого профиля сторонним tool требует обновления D-09.

До rehearsal создаётся immutable таблица:

| Entity | Included | Selection rule | Expected count | Preserved fields | Known losses | Verification query |
| --- | --- | --- | --- | --- | --- | --- |

Для каждого включённого issue обязательны comments и attachments либо signed
loss. Неперенесённые ссылки остаются абсолютными GitHub URLs или получают
явный tombstone; GitLab `#NNN` не должен вести к другому объекту из-за
совпадения номера.

Git переносится из полного mirror clone. LFS выполняется отдельными
`fetch --all` и `push --all`, затем проверяется из свежего clone.

D-09 и rehearsal обязаны доказать resumable checkpoints, idempotent retry без
дубликатов, соблюдение rate limits, сохранность допустимых authors/timestamps и
attachment bytes, детерминированный source→target ID map и полный реестр known
losses. Наличие только ad-hoc script без pinned artifact и restart evidence
означает, что B2 остаётся кандидатом.

### 5.3. B3 — очищенная история

До rewrite:

1. revoke/rotate скомпрометированные credentials;
2. закрыть или заморозить open PR;
3. сохранить независимую forensic copy с ограниченным доступом;
4. утвердить paths/patterns, refs, tags и expected removals.

После rewrite обязательны:

- machine-readable `old_sha → new_sha` map;
- D-09 policy для каждой metadata-ссылки на старый SHA: переписать по map,
  сохранить абсолютную ссылку на immutable legacy snapshot либо зарегистрировать
  как approved unresolved link; silent retarget запрещён;
- отчёт `git-filter-repo` по changed refs и orphaned LFS;
- secret и large-blob scans;
- проверка tree/content equivalence за вычетом approved removals;
- документирование потерянных signatures и нарушенного PR diff context;
- согласованный режим M1/M2/M3.

Находка нового секрета после rehearsal останавливает перенос и требует нового
cleanup + полной повторной проверки.

## 6. Финальный пакет GitLab и CI/security parity

Финальный набор `.gitlab-ci.yml`, root `CODEOWNERS`, scripts, templates и docs
попадает коммитом в GitHub до freeze. Project IDs, URLs, environment names,
runner tags и schedule owners параметризуются; rehearsal IDs не копируются.

Текущий `.gitlab-ci.yml` остаётся пилотом. Gate C запрещено закрывать, пока:

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
   critical path; если обязательна Code Owner approval, выбран Premium/Ultimate.

GitLab SAST считается заменой, а не доказанной эквивалентностью CodeQL.
Отдельно сравниваются Python SAST, GitHub Actions YAML analysis, secret scanning
and push protection, dependency review, OSV/pip-audit, Gitleaks/detect-secrets,
Trivy/SBOM, OpenSSF Scorecard, zizmor и vulnerability triage.

BioETL baseline нельзя ослаблять ради миграции. Проверяются направления
зависимостей, агрегатные инварианты, strict Gold contracts, DQ, deterministic
replay, idempotent write и immutable quarantine payload. В рамках миграции test
count и coverage не уменьшаются; изменение baseline возможно только отдельной,
завершённой до миграции governance-задачей. Skip/xfail и debt budgets не
увеличиваются. Debt budgets могут только уменьшаться или оставаться неизменными;
их повышение в рамках миграции запрещено.

Publish parity закрывается отдельно:

- выбрать будущий registry и судьбу существующих GHCR images/tags/digests;
- перевязать PyPI/TestPyPI trusted publisher на GitLab OIDC до отключения GitHub
  publish path;
- воспроизвести release assets, SBOM и provenance для того же commit SHA;
- защитить publish environments, credentials и manual approvals;
- доказать, что mirrored push не публикует GHCR image и не создаёт attestations.

## 7. Этап B — репетиция

Репетиция выполняется в отдельной top-level GitLab group, без production
secrets, registry credentials и production publish permissions. Target project
одноразовый; он не переименовывается в production.

### 7.1. Обязательные сценарии

| ID | Severity | Сценарий |
| --- | --- | --- |
| RB-01 | P0 | полный happy-path выбранной B-ветви |
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
| RB-14 | P0 для B2/B3 | metadata migrator restart/idempotency, rate-limit handling, mapping и known-loss report |
| RB-15 | P1 для M1/M2 | full `ls-remote` reconciliation веток и тегов, включая legitimate upstream deletion и unauthorized downstream ref |

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
| GB-01 | выбранная B-ветвь / P0 | Rehearsal Lead → Migration Owner | RB-01 завершён; нет необъяснённых missing objects; importer status приемлем | abort/fix/re-run in new project; non-waivable |
| GB-02 | по applicability / P0 | Scenario Owners → Migration Owner | все применимые P0 `RB-*` имеют immutable evidence и expected outcome | abort and repeat; non-waivable |
| GB-03 | все ветви / P1 | Cutover Owner → Migration Owner | измеренное freeze window с запасом не превышает письменный abort threshold | resize window or reject cutover; waiver только Sponsor |
| GB-04 | post-write / P0 recovery | Recovery Owner → Recovery Approver | RB-10 успешен с losses ledger либо D-08 явно устанавливает испытанный fail-forward-only path | abort; non-waivable |
| GB-05 | все ветви / P1 | Rehearsal Lead → Identity Owner | rehearsal project/top-level group, mappings и permissions отделены от production | recreate rehearsal; non-waivable after import starts |
| GB-06 | metadata import / P0 identity | Identity Owner → top-level Group Owner | RB-13: нет `Import User`; authors, approvals, reviewers, assignees и role/seat effect сверены выборочно и агрегатно | abort/increase capacity/re-import; non-waivable |
| GB-07 | все ветви / P0 Git/LFS | Git/LFS Owner → Migration Owner | all-ref manifest, annotated tags, LFS OID/bytes и fresh clone совпадают в обязательном scope | abort and repair/re-import; non-waivable |
| GB-08 | CI/publishing / P0 | CI/Security + Publishing Owners → Migration Approver | RB-06, RB-07 и RB-12 подтверждают fail-closed CI и нулевые publish side effects | abort; non-waivable |
| GB-09 | B2/B3 / P0 metadata | Metadata Owner → Migration Owner | RB-14 подтверждает pinned D-09 profile, restart/idempotency, rate limits, fidelity, ID map и known losses | B2/B3 остаются кандидатами; non-waivable |

## 8. Этап C — production readiness

### 8.1. Readiness checklist

До freeze должны быть готовы:

- финальный commit с GitLab CI/config/docs и указателями на новый source of truth;
- reproducible settings manifest/API scripts;
- production namespace/project name reservation;
- для B1 — classic importer PAT и отдельный GitLab API token;
- для B2/B3 — только credentials утверждённого D-09 profile с раздельными
  source/target scopes;
- для M1/M2 — один отдельный fine-grained GitHub mirror PAT с
  `Contents: read/write` и, поскольку repository содержит `.github/workflows`,
  `Workflows: read/write`, scoped к одному repository; для M3 mirror credential
  не создаётся;
- credential expiry, owner и rotation procedure;
- мониторинг применимых importer/metadata runner, pipeline, mirror и backup;
- cutover ledger template и communication plan;
- проверенный способ отключить GitHub Actions на уровне repository;
- plan для Dependabot, GitHub Apps, schedules, webhooks и bots;
- formal go/no-go roster.

### 8.2. Gate C→D

| ID | Applicability / severity | Owner role → approver | Evidence / expected result | Failure action / waiver |
| --- | --- | --- | --- | --- |
| GC-01 | все ветви / P0 readiness | Configuration Owner → Migration Approver | финальный commit и воспроизводимый settings manifest зафиксированы; production reservation и go/no-go roster готовы | abort/fix; non-waivable |
| GC-02 | по выбранным B/M ветвям / P0 | Rehearsal Lead → Migration Approver | freeze, LFS, CI negative tests, RB-09 и выбранный post-write recovery успешны; mirror scenarios требуются только для M1/M2, D-09 scenarios — только для B2/B3 | abort/repeat; non-waivable |
| GC-03 | CI/security/publishing / P0 | CI/Security + Publishing Owners → Migration Approver | fail-closed controls и publish isolation доказаны; открытых P0 findings нет | abort; non-waivable |
| GC-04 | по выбранным B/M ветвям / P1 | Credential Owner → Security Approver | существуют только применимые раздельные least-privilege credentials; scopes, expiry, rotation и revocation evidence записаны без values | reprovision; shared/over-scoped credential non-waivable |
| GC-05 | все ветви / P0 decisions | Migration Owner → Executive Sponsor | нет `TBD` в применимых D-01…D-09 и §12.3; все применимые rehearsal scenarios закрыты | NO-GO; non-waivable |

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

### 9.2. Production import

- Production destination — новый пустой GitLab project.
- B1 запускается один раз после `T_freeze`; rehearsal import не обновляется.
- B2/B3 используют immutable source prepared under freeze.
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

- согласованный набор `refs/heads/*` и `refs/tags/*` совпадает по SHA для B1/B2;
- default branch совпадает;
- annotated tag object, target, message, tagger и signature state сравнены;
- provider-owned refs (`refs/pull/*`, `refs/merge-requests/*`) перечислены как
  исключения;
- B3 использует `old_sha → new_sha`, tree equivalence и approved-removal list;
- `git fsck --full` и fresh clone проходят.

### 10.2. LFS

Для каждого сохраняемого OID проверяются path, size и bytes checksum на source,
GitLab и, если применимо, GitHub mirror. Обязательны fresh clone, checkout
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
в согласованном scope. Для B2 пропущенный объект должен находиться в signed
exclusion manifest.

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
| GE-01 | все ветви / P0 scope | Validation Lead → Migration Approver | mandatory scope сохранён; differences объяснены и одобрены на уровне объектов, не только counts | abort/fix/re-import; non-waivable для missing mandatory object |
| GE-02 | все ветви / P0 Git/LFS | Git/LFS Owner → Migration Approver | §10.1–10.2: refs/tags и каждый required LFS OID/bytes доказаны manifest/checksum/fresh clone | abort; non-waivable |
| GE-03 | metadata import / P0 identity | Identity Owner → top-level Group Owner | нет `Import User`; production authors, approvals, reviewers, assignees и memberships соответствуют mapping/expected transformations | abort/re-import or approved target-capacity change; non-waivable |
| GE-04 | CI/security / P0 | CI/Security Owner → Security Approver | required controls fail closed; missing pipeline/job/report и bypass attempts блокируют merge | abort; non-waivable |
| GE-05 | publishing / P0 | Publishing Owner → Publishing Approver | target registry/OIDC/SBOM/provenance работают; GitHub mirror даёт ноль publish side effects | abort; non-waivable |
| GE-06 | все ветви / P0 recovery | Backup Owner → Recovery Approver | independent backup доступен и восстановлен; RB-09 выполнен; post-write posture утверждён | abort; non-waivable |
| GE-07 | M1/M2 / P1 | Mirror Owner → Migration Approver | mirror mode готов; branch/tag policy и full `ls-remote` reconciliation прошли | fix/retest; waiver только выбором M3 до cutover |
| GE-08 | все ветви / P0 objectives | Recovery Owner → Migration Approver | §12.3: RPO/recoverable points и RTO clocks измерены и находятся в целях | abort or revise approved objectives then repeat rehearsal; non-waivable |

Gate закрывает только именованный Migration Approver после подписи полного
evidence bundle; агрегатные counts без object-level доказательств недостаточны.

## 11. Этап F — cutover, зеркало и наблюдение

### 11.1. Point of no return

До первой GitLab-only mutation возможен обычный pre-write rollback. Первая
разрешённая запись, которой нет на GitHub source, — **point of no return**.
Время, actor, approver и объект записываются в cutover ledger.

После этой точки возврат на GitHub — не rollback, а reverse migration с
потерями либо fail-forward recovery.

### 11.2. Активация GitLab

1. включить protected branch и merge controls;
2. открыть запись только в GitLab;
3. создать разрешённый test object в заранее выделенной области;
4. обновить repository descriptions, README, contribution/security links;
5. включить только утверждённые schedules, bots и publishing paths;
6. начать observation period, не удаляя production source/backup.

### 11.3. Push mirror

Для M1/M2:

- направление только GitLab → GitHub;
- authentication — HTTPS fine-grained PAT;
- `Keep divergent refs=true`, чтобы divergent update дал failure/alert, а не
  молчаливую потерю; при этом downstream-only refs остаются и могут стать stale,
  поэтому эта настройка не заменяет reconciliation;
- regex mirror filter управляет только branches и доступен на соответствующем
  платном tier; tags им не фильтруются;
- D-03 задаёт отдельную tag policy: mirror all approved tags либо publish/remove
  tags через испытанную контролируемую процедуру; selective tag scope нельзя
  считать обеспеченным branch regex;
- source и target используют один object format;
- monitor проверяет last successful update, lag, error и ref divergence;
- direct GitHub push считается incident;
- GitHub Actions/Dependabot/publish остаются отключёнными.

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

Vendor baseline для push mirror — до пяти минут, либо до одной минуты при
`Only mirror protected branches`. Числовой mirror RPO задаётся в D-06 с запасом
и подтверждается rehearsal.

Mirror acceptance:

1. новый Git ref достигает GitHub в пределах mirror RPO;
2. запрещённые branches и tags не публикуются согласно разным policy;
3. full heads/tags `ls-remote` reconciliation не содержит необъяснённых refs;
4. divergence создаёт alert и не перезаписывается;
5. legitimate upstream deletion удаляется по утверждённой процедуре, а
   unauthorized divergence сохраняет evidence;
6. новый LFS object, которого не было на GitHub, читается fresh clone без общего
   cache;
7. mirrored push не запускает workflow, package publish, release или bot action.

Для M1 временный archive снимается только после repository-wide отключения
GitHub Actions и проверки mirror credentials. Для M2 исторический repository
остаётся archived, зеркало направляется в новый repository. Для M3 mirror не
создаётся.

### 11.4. Observation period

Длительность задаётся D-08. В период наблюдения:

- independent backups продолжаются;
- mirror lag и failed updates алертятся;
- GitHub source/legacy repository не удаляется;
- GitLab metadata mutations журналируются для recovery;
- любые GitHub issues/PR/direct pushes triage как migration incident.

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

1. остановить writers и automations на обеих сторонах;
2. сохранить GitLab project, refs, LFS, metadata и audit evidence;
3. определить последнюю согласованную точку;
4. выбрать fail-forward на GitLab либо отдельную reverse migration;
5. reverse migration выполнять только после испытанного mapping и с
   зарегистрированными потерями authorship, IDs, timestamps, reactions,
   discussions и attachments;
6. GitLab project не удалять до двусторонней сверки.

Нативного 1:1 rollback GitLab issues/MR/comments в GitHub план не обещает.
Если бизнес требует сохранения исходных IDs/authors/timestamps, post-write
возврат считается unsupported до доказанной sandbox automation.

### 12.3. Data-plane recovery objectives

RPO и RTO не объединяются в один показатель. До репетиции Owner заполняет
числовые значения, частоты, retention и UTC timestamps; любой `TBD` блокирует
Gate A.

| Plane | RPO target | Доказательство последней recoverable point | Backup/sync frequency | Retention | RTO target | RTO clock start → stop |
| --- | --- | --- | --- | --- | --- | --- |
| Canonical Git refs | TBD | signed refs manifest + independent bundle/mirror checksum at `T_recoverable` | TBD | TBD | TBD | incident declared → fresh clone доступен и `git fsck --full` успешен |
| Canonical LFS | TBD | required OID manifest + bytes checksums at `T_recoverable` | TBD | TBD | TBD | incident declared → required OID fetched, checked out and `git lfs fsck` successful |
| GitHub mirror refs/LFS | TBD mirror-delivery lag, не backup RPO | last successful mirror timestamp + heads/tags/OID fresh-read evidence | on upstream push plus forced check TBD | operational logs TBD; backup retention задаётся canonical planes | TBD | upstream push accepted → fresh GitHub read and reconciliation successful |
| Issues/MR/comments | TBD | append/export checkpoint with source IDs, page checksums and last event timestamp | TBD | TBD | TBD | incident declared → target query and source→target mapping verified |
| Attachments/uploads | TBD | object manifest with relation, size and checksum at `T_recoverable` | TBD | TBD | TBD | incident declared → all required bytes restored and checksums verified |
| CI settings/variables/schedules | TBD | settings manifest + secrets metadata/re-provision checkpoint | TBD | TBD | TBD | incident declared → required pipeline passes with schedules/integrations in approved state |
| Releases/packages/registries | TBD | tag/digest/SBOM/provenance manifest at `T_recoverable` | TBD | TBD | TBD | incident declared → approved artifact pulls/downloads and digest checks succeed |
| Public read access | N/A: availability, не data-loss objective | latest successful endpoint probe and deployment/ref identity | N/A | probe/evidence logs TBD | TBD | outage detected/declared → approved public endpoint serves verified content |

`RPO=0` допустим только в управляемом freeze scope с доказанной последней
recoverable point. Асинхронное зеркало имеет lag и не является backup; ошибочный
force-push/delete может реплицироваться. Аварийный сценарий недоступности GitLab
использует независимую backup copy и собственный допустимый data loss, а не
предполагаемую доступность GitLab export.

## 13. Статусы аудитов и управление исполнением

Статусы имеют только три значения:

- `учтено в плане` — требование присутствует в v4;
- `реализовано` — создан артефакт/настройка и приложено evidence;
- `проверено на репетиции` — сценарий фактически выполнен в изоляции.

Статус не повышается по тексту плана.

| Набор | Статус на 2026-09-21 | Примечание |
| --- | --- | --- |
| MIG-01…MIG-14 | учтено в плане | Унаследовано из v2/v3; реализация требует evidence |
| R2-01…R2-11 | учтено в плане | Унаследовано из v3 и уточнено текущим аудитом |
| R3-01…R3-15 | учтено в плане | Новые выводы §1.2; ни один не заявлен реализованным |

Минимальный execution ledger для каждого пункта:

| Field | Значение |
| --- | --- |
| Requirement ID | `MIG-*`, `R2-*` или `R3-*` |
| Selected branch | B1/B2/B3 и M1/M2/M3 |
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
2. Gate A закрыт по stable evidence records `GA-01…GA-08`;
3. B1/B2/B3 и M1/M2/M3 выбраны; для B2/B3 закрыт D-09;
4. read-only inventory и backup restore завершены;
5. отдельный операторский runbook подготовлен для rehearsal без production
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
