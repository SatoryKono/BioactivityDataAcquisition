# Паспорт закрытия: P17-003-external-callers

- **Владелец работы:** проверка внешних callers для PR #12548
- **Срок:** 2026-10-26
- **Точная ревизия (SHA):** `173b6ff3eab1b99c7a84583518fee21fff89cfcd` (содержимое workflow совпадает с `origin/main`; локальный HEAD измерения записан в evidence)
- **Область:** внешние callers `.github/workflows/reusable-setup.yml` и `.github/workflows/reusable-mermaid-setup.yml`
- **Интерфейсы в evidence:** локальный `rg`, GitHub REST API version `2022-11-28`; в raw stderr встречается префикс `gh:`, но фактический executable/argv не записан
- **Команды и exit codes:** см. evidence; краткая сводка ниже
- **Ожидаемый результат:** найти внешних callers deprecated reusable workflow
- **Допустимые пропуски:** N/A
- **Ссылка на доказательства:** `reports/audit-runs/20261026-p17-003-external-callers/evidence.json`
- **Независимый проверяющий:** N/A

Канонического генератора этого отчёта в репозитории нет. Секреты в артефакт не записываются: в сохранённых строках curl указан плейсхолдер `$GH_TOKEN`.

**Уточнение provenance команд:** поле `curl` в `evidence.json` — запрошенная/иллюстративная строка, а не подтверждённый argv запущенного процесса. Фактическая команда и её аргументы для внешних запросов не записаны, поэтому invocation остаётся `UNKNOWN`. Raw HTTP-статусы, exit codes и stderr сохранены. В нескольких записях stderr начинается с `gh:`; это наблюдаемый текст ошибки, но он не восстанавливает точную команду. Для записей без stderr поле также не выводит фактическую команду. Первоначальный JSON сохранён в истории Git: исходный blob `5a0711a25dbac8e20e26bd8b56d4310ec0411631`, SHA-256 `e0ebc9b82f06c4c088199af8e0c22350d9135028fcb3a395fd8f2c3d483ddcf3`.

## Учётные данные

Измерение сделано токеном GitHub App installation. Активный аккаунт GitHub CLI: `cursor`. Заголовок `X-OAuth-Scopes` отсутствует.

Endpoint `GET https://api.github.com/user` записан в evidence с HTTP 403, process exit 1 и длительностью 0.272s: `Resource not accessible by integration`. Точная фактически выполненная команда неизвестна; сохранённая строка curl является иллюстративной.

Персональные токены из черновика (`GITHUB_TOKEN_02`, `SARIF_GITHUB_TOKEN`) в этом checkout отсутствуют. Их прежний результат не переизмерялся и не используется как evidence.

## Локальные команды и иллюстративный HTTP-пример

Локально, из корня репозитория:

```bash
rg -n --glob '!reusable-setup.yml' 'reusable-setup\.yml' .github/workflows
rg -n --glob '!reusable-mermaid-setup.yml' 'reusable-mermaid-setup\.yml' .github/workflows
rg -n 'uses:[[:space:]]*.*reusable-(setup|mermaid-setup)\.yml'
```

Все три команды: process exit 1, 0 совпадений.

В evidence сохранены строки curl для внешних search-запросов. Это примеры запрошенных запросов, не подтверждённые команды исполнения:

```bash
curl -sS -D - -o /tmp/search-body.json \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -G "https://api.github.com/search/code" \
  --data-urlencode "q=SatoryKono/BioactivityDataAcquisition/.github/workflows/reusable-setup.yml -repo:SatoryKono/BioactivityDataAcquisition"
```

Для `reusable-mermaid-setup.yml` в evidence записана аналогичная строка запроса. Точные фактически выполненные команды и argv для этих запросов неизвестны.

## Происхождение результатов

- Поля `curl` во всех девяти записях `code_search` и в записи `user_endpoint` классифицированы как запрошенные/иллюстративные; они не подтверждают запуск `curl`.
- В трёх записях `code_search` с `process_exit_code: 1` raw stderr начинается с `gh:`; у `user_endpoint` сохранён такой же префикс. Эти строки сохранены без изменений. Ни stderr, ни HTTP-поля не раскрывают точный фактический argv; он остаётся `UNKNOWN`.
- Если в исходной записи stderr отсутствовал или был пуст, это состояние сохранено; недостающий текст не восстановлен.
- Новых сетевых запросов для этой корректировки не выполнялось.

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

Статус BLOCKED. Нулевые ответы относятся только к коду, который видит этот installation token. `GET /user` не даёт организации, приватные репозитории вне установки не проверены, а `uses:`-запрос для `reusable-setup.yml` завершился HTTP 429. `reusable-setup.yml` и `reusable-mermaid-setup.yml` не удаляются.

**Исторический статус в этом снимке (26.10.2026):** на момент фиксации результатов Issue #12482 оставалась открытой. Это отражает состояние issue для данного снимка, а не её последующий статус.

**Актуальное уточнение (26.10.2026, 18:26:03 UTC):** Issue #12482 закрыта со статусом `completed` по принятому retain-решению ([запись о приёмке](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12482#issuecomment-6424075387)). Оба reusable workflow — `reusable-setup.yml` и `reusable-mermaid-setup.yml` — сохранены. Наличие внешних callers остаётся неизвестным из-за ограничений доступа и неполного покрытия поиска, описанных выше. Закрытие issue не означает слияние PR #12548 и не доказывает отсутствие внешних callers.
