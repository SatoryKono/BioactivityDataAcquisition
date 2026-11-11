# Финальный отчёт окна M2: Main Integrity

Окно M2 не принято. Cancel устаревших SHA допустим. Cancelled не равен green.

В окне нет ни одного `success`. Этот документ не называет Main Integrity зелёным. Политика M2 не отменяется, `.github/workflows/main-integrity.yml` этим отчётом не меняется.

Наблюдение и числа окна остаются в [#12583](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12583). Дефект tip без terminal перенесён в [#13023](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13023). Код там не предлагается.

## Что является финалом

Финальный отчёт закрытого окна — этот файл.

Частичный снимок до закрытия окна не переписан и не подменён: [main-integrity-m1-m2-report.md](main-integrity-m1-m2-report.md). На `origin/main` это снимок до 2026-11-07: 123 запуска, SHA `60e6098cb150aa61bc73c24db08eb8e1c7b93bf8`. Это не финальный отчёт.

## Окно и фильтр

- Часовой пояс окна: Asia/Baghdad (UTC+3).
- Границы: 2026-11-02 00:00 включительно — 2026-11-10 00:00 исключительно.
- `created_at` входит в полуинтервал от `2026-11-01T21:00:00Z` включительно до `2026-11-09T21:00:00Z` исключительно.
- Источник: Actions API, workflow `main-integrity.yml`, branch `main`, event `push`.
- `workflow_dispatch` за календарный диапазон `created=2026-11-01..2026-11-10`: `total_count=0`.
- Порог «≥20 push» выполнен в первый день (29 запусков 2 ноября). Длительность окна задали 7 календарных дней. Срок отчёта: 2026-11-11.

Terminal: `success`, `failure`, `timed_out`, `startup_failure`. `cancelled`, `skipped`, `waiting`, `in_progress` учитываются и не являются green.

Cancelled-without-successor-terminal: `cancelled`-запуск, после которого ни один более поздний запуск, созданный внутри окна, не дошёл до terminal.

Tip окна: запуск с самым поздним `created_at` внутри окна.

## Сверка двух рядов одного окна

Оба ряда ниже — одна и та же выборка. Первый ряд записан комментарием [#12583](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12583#issuecomment-6760763471) от 2026-11-10T06:31:53Z. Второй ряд — повторный запрос Actions API 2026-11-11 в этой сдаче.

| Ряд | Запуски | cancelled | failure | success | tip | cancelled-without-successor-terminal |
|---|---:|---:|---:|---:|---|---:|
| Комментарий 2026-11-10T06:31:53Z | 195 | 188 | 7 | 0 | [42693585720](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42693585720) / `6e5b15f00229cb79848192b0f848a88ae3c36161`, `cancelled` | 18 |
| Actions API 2026-11-11 | 195 | 188 | 7 | 0 | тот же run, `conclusion=cancelled`, `updated_at=2026-11-09T21:06:54Z` | 18 |

Расхождения нет.

Причина: фильтр повторной съёмки совпадает с фильтром комментария, и conclusion запусков окна между комментарием и повторной съёмкой не менялись. Широкая выгрузка `created=2026-11-01..2026-11-10`, event `push`, вернула `total_count=229` и 229 различных id. В полуинтервал окна вошли 195. У всех 195 `run_attempt=1`, 195 различных SHA. Единственный запуск окна с `updated_at` не раньше `2026-11-09T21:00:00Z` — tip; его `cancelled` уже стоял в комментарии от 2026-11-10. Сосед до окна: `created_at=2026-11-01T20:52:17Z`. Сосед после окна: run [42699379823](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42699379823), `created_at=2026-11-09T21:06:51Z`.

Последний terminal внутри окна в обоих рядах один: run [42582617175](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42582617175), SHA `1f5e2143db72fee6e63bb32af3faa6633d5179ac`, `failure`, `updated_at=2026-11-09T08:01:06Z`. После него внутри окна 18 запусков, все `cancelled`, включая tip.

## Почему частичный файл показывает другие числа

| Ряд | Интервал | Запуски | cancelled | failure | success | открытый на съёмке | SHA съёмки |
|---|---|---:|---:|---:|---:|---:|---|
| Файл `main-integrity-m1-m2-report.md` | `2026-11-02T00:00:00Z` … `2026-11-07T22:44:42Z` | 123 | 122 | 0 | 0 | 1 | `60e6098cb150aa61bc73c24db08eb8e1c7b93bf8` |
| Финал окна, оба ряда выше | Baghdad 2026-11-02 … 2026-11-09 включительно | 195 | 188 | 7 | 0 | 0 на момент комментария 2026-11-10 | tip `6e5b15f00229cb79848192b0f848a88ae3c36161` |

Это не конфликт двух финалов. Частичный файл обрывается 2026-11-07, до семи `failure` 8 и 9 ноября, и оставляет тогдашний tip в `in progress`. Семь terminal `failure` финального окна созданы 2026-11-08 и 2026-11-09. Частичный файл сохранён как был.

## Исходы финального окна

| Исход | Запуски | Доля |
|---|---:|---:|
| cancelled | 188 | 96.41% |
| failure | 7 | 3.59% |
| success | 0 | 0% |
| skipped | 0 | 0% |
| timed_out | 0 | 0% |
| startup_failure | 0 | 0% |
| Всего | 195 | 100% |

Доля SHA с terminal: 7/195, и все семь — `failure`. Доля SHA с `success`: 0/195.

По датам Baghdad: 02.11 — 29, 03.11 — 36, 04.11 — 1, 05.11 — 19, 06.11 — 16, 07.11 — 20, 08.11 — 39, 09.11 — 35.

В момент `2026-11-09T21:00:00Z` открыт был tip. Его `updated_at` позже конца окна. Остальные 194 запуска окна имеют `updated_at` раньше конца окна: 187 `cancelled` и 7 `failure`.

## Tip окна

| Поле | Значение |
|---|---|
| Run | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42693585720 |
| SHA | `6e5b15f00229cb79848192b0f848a88ae3c36161` |
| Создан | `2026-11-09T20:30:21Z` (23:30 +03) |
| Conclusion | `cancelled` в `2026-11-09T21:06:54Z`, уже после окна |
| Jobs со `success` | `integrity`; docker build, lint, compose, runtime contracts; `docker-complete` |
| `docker-push` | `cancelled`, шагов нет, `started_at` `2026-11-09T20:33:51Z`, `completed_at` `2026-11-09T21:06:53Z` |

Tip не получил terminal `success` или `failure`. Пустой список шагов `docker-push` значит, что job не дошёл до runner-шагов: он ждал environment `ghcr-publish`. Success соседних jobs не делает workflow green.

Следующий push снят tip: run [42699379823](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42699379823), SHA `719af0267ac2c8115a4d43b0b44ec765fdac86b5`, `created_at` `2026-11-09T21:06:51Z`, на две секунды раньше `completed_at` у `docker-push`.

На SHA tip файл `.github/workflows/main-integrity.yml` содержал группу `main-${{ github.ref }}` и `cancel-in-progress: true`. Это текст файла на SHA окна, не diff этого отчёта. Тот же механизм записан комментарием #12583 от 2026-11-11T09:07:08Z.

## Семь terminal failure

Повторная съёмка подтвердила id, SHA, `conclusion=failure` и время. Текст шага (Syft или Trivy) здесь цитируется по комментарию 2026-11-10T06:31:53Z; байты логов в этой сдаче заново не скачивались.

| Run | SHA | created_at | updated_at |
|---|---|---|---|
| [42464984375](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42464984375) | `0a6450ae61c0c5f4d349bfcf7a943f6a606d7c18` | `2026-11-08T08:55:43Z` | `2026-11-08T08:57:51Z` |
| [42472983176](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42472983176) | `3d62240e17f2aec4da6b960f68b23d2f79f57e74` | `2026-11-08T10:48:34Z` | `2026-11-08T10:53:11Z` |
| [42474307303](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42474307303) | `889da41aa3800a2a055f8e93202ff66650d56418` | `2026-11-08T11:07:00Z` | `2026-11-08T11:10:09Z` |
| [42567212178](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42567212178) | `e3491a271c9051eba3024e7bcca2fe21a47b3e20` | `2026-11-09T05:25:17Z` | `2026-11-09T05:27:42Z` |
| [42569184917](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42569184917) | `ee6555aeac278a3d69094bab917055968c742b47` | `2026-11-09T05:46:13Z` | `2026-11-09T05:48:42Z` |
| [42571973282](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42571973282) | `cc2163a39398e34534771667b96170f1976a3512` | `2026-11-09T06:15:54Z` | `2026-11-09T06:19:03Z` |
| [42582617175](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/42582617175) | `1f5e2143db72fee6e63bb32af3faa6633d5179ac` | `2026-11-09T07:57:52Z` | `2026-11-09T08:01:06Z` |

По комментарию 2026-11-10 шесть последних строк — сбой установки Syft v1.54.0 (HTTP 504), первая строка — установщик Trivy v0.70.0 (HTTP 504). Root allowlist tip окна не ломал: job `integrity` завершился `success`.

## После окна

[#13005](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/13005) влит 2026-11-11T09:58:31Z, после конца окна и после финального комментария. Он меняет concurrency на текущем `main`. Это не приёмка окна: tip `42693585720` остаётся `cancelled`, success окна остаётся 0, cancelled не становится green. Этот отчёт не откатывает #13005 и не предлагает новую правку workflow.

## Вердикт сдачи

#12583 сдаётся только как наблюдение и отчёт. Приёмка окна не выполнена. Follow-up дефекта: #13023.
