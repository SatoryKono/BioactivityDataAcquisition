# Паспорт закрытия: P17-003-external-callers

- **Владелец работы:** проверка внешних callers для PR #12548
- **Срок:** 2026-10-26
- **Точная ревизия (SHA):** `173b6ff3eab1b99c7a84583518fee21fff89cfcd` (содержимое workflow совпадает с `origin/main`; локальный HEAD измерения записан в evidence)
- **Область:** внешние callers `.github/workflows/reusable-setup.yml` и `.github/workflows/reusable-mermaid-setup.yml`
- **Версии инструментов и backend:** `rg`, GitHub CLI `gh`, GitHub REST API version `2022-11-28`
- **Команды и exit codes:** см. evidence; краткая сводка ниже
- **Ожидаемый результат:** найти внешних callers deprecated reusable workflow
- **Допустимые пропуски:** N/A
- **Ссылка на доказательства:** `reports/audit-runs/20261026-p17-003-external-callers/evidence.json`
- **Независимый проверяющий:** N/A

Канонического генератора этого отчёта в репозитории нет. Evidence собрано прямыми вызовами `rg` и `GET /search/code`. Секреты в артефакт не записываются: в curl стоит `$GH_TOKEN`.

## Учётные данные

Измерение сделано токеном GitHub App installation. Активный аккаунт GitHub CLI: `cursor`. Заголовок `X-OAuth-Scopes` отсутствует.

`GET https://api.github.com/user` (HTTP 403, process exit 1, 0.272s): `Resource not accessible by integration`.

Персональные токены из черновика (`GITHUB_TOKEN_02`, `SARIF_GITHUB_TOKEN`) в этом checkout отсутствуют. Их прежний результат не переизмерялся и не используется как evidence.

## Команды

Локально, из корня репозитория:

```bash
rg -n --glob '!reusable-setup.yml' 'reusable-setup\.yml' .github/workflows
rg -n --glob '!reusable-mermaid-setup.yml' 'reusable-mermaid-setup\.yml' .github/workflows
rg -n 'uses:[[:space:]]*.*reusable-(setup|mermaid-setup)\.yml'
```

Все три команды: process exit 1, 0 совпадений.

Внешний поиск, без подстановки секрета:

```bash
curl -sS -D - -o /tmp/search-body.json \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -G "https://api.github.com/search/code" \
  --data-urlencode "q=SatoryKono/BioactivityDataAcquisition/.github/workflows/reusable-setup.yml -repo:SatoryKono/BioactivityDataAcquisition"
```

Тот же endpoint для `reusable-mermaid-setup.yml`.

## Результаты проверки

1. **Локальные `uses:` callers:** 0 (MEASURED, exit 1).
2. **Внешний code search по пути workflow, исключая этот репозиторий:**
   - `reusable-setup.yml`: HTTP 200, process exit 0, 0.473s, `total_count=0`, `incomplete_results=false`, items пустые.
   - `reusable-mermaid-setup.yml`: первый вызов HTTP 429; повтор HTTP 200, process exit 0, 0.503s, `total_count=0`, `incomplete_results=false`.
3. **Внешний code search с квалификатором `uses:` и `-repo:`:**
   - `reusable-setup.yml`: HTTP 429, secondary rate limit (`code_search` limit 10). Нуль callers этим запросом не подтверждён.
   - `reusable-mermaid-setup.yml`: повтор HTTP 200, process exit 0, `total_count=0`, `incomplete_results=false`.
4. Квота code search в сохранённых ответах: limit 10, resource `code_search`. `X-OAuth-Scopes` пустой.

## Вывод

Статус BLOCKED. Нулевые ответы относятся только к коду, который видит этот installation token. `GET /user` не даёт организации, приватные репозитории вне установки не проверены, а `uses:`-запрос для `reusable-setup.yml` завершился HTTP 429. Issue #12482 остаётся открытым. `reusable-setup.yml` и `reusable-mermaid-setup.yml` не удаляются.
