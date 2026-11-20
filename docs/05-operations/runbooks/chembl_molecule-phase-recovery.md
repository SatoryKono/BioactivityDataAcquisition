______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-20'

______________________________________________________________________

# Восстановление фаз ChEMBL Molecule из Bronze

## Trigger

В ранее обработанном `chembl_molecule` исходный `max_phase` заполнен, но
Silver содержит NULL или усечённое значение; Gold исключён по
`column_filter_mismatch:potential_duplicate`.

## Impact

Исправления #13197 и #13198 сохраняют reviewed `max_phase`, включая `0.5`,
и удаляют ошибочное условие `potential_duplicate` из Gold eligibility.
Уже записанные NULL-фазы требуют повторной обработки. Контракт Gold остаётся
строгим, source-profile extraction params, hash algorithm и список hash-полей
не меняются. Исправленные значения меняют `content_hash`; изменившийся фильтр
меняет effective-config digest и допустимый Gold cohort.

## Preconditions

Использовать проверенный commit с исправлениями и прошедшими локальными
transformer, Gold/SCD2 и config tests. Для исходного batch должны быть доступны
Bronze, прежние отчёты и право создать отдельные выходные каталоги.

1. Зафиксировать точный commit, merged config, SHA-256 и список исходных
   `*.jsonl.zst`, число записей и уникальных `molecule_id`, распределение фаз.
   Сохранить прежние Silver, Gold, checkpoints, manifests и отчёты.
2. Задать в окружении дочернего процесса новые абсолютные `BIOETL_DATA_DIR`,
   `BIOETL_REPORT_ROOT`, `BIOETL_ARCHIVE_ROOT`. Проверить resolved paths и
   вычисленные Settings: назначения не должны совпадать с исходными или
   общими таблицами. `.env` не изменять. Для локального отдельного report root
   допустимо явно задать `BIOETL_ENFORCE_REPORT_ROOT_MARKER=false` в том же
   процессе; DQ policy и Gold validation остаются строгими.
3. Проверить preview через `--dry-run` в отдельном preview root. Основной
   backfill запускать в другом новом root: backfill очищает назначения.

## Procedure

Пример для сохранённого batch от 18 ноября 2026 года; заменить пути на
проверенные абсолютные каталоги. На Windows использовать
`.venv-win/Scripts/python.exe` вместо `python`.

```text
python -m bioetl run --pipeline chembl_molecule --run-type backfill --limit 1000 --use-cached-bronze --cached-bronze-path <absolute-original-molecule-bronze-dir> --cached-bronze-date 2026-11-18 --no-exact-replay --required-persistence-profile degraded_observable --no-ensure-observability-backend
```

Cached source читает сжатый Bronze без обращения к provider API. Это ordinary
cached processing исправленным кодом: новые run ID, manifest и effective-config
anchors со ссылкой на исходный batch. Явный persistence profile фиксируется
в отчёте; он не отключает DQ или строгую Gold validation. Strict exact replay
предназначен для воспроизведения закреплённого результата и не описывает
восстановление новым кодом. Resume продолжает прежний запуск/checkpoint;
для этого восстановления его не использовать.

## Verification

- Сверить SHA-256 исходника до и после обработки; сопоставить Bronze, actual
  Silver Delta и current Gold Delta по `molecule_id`, проверить `entity_id`.
  При чтении Delta учитывать partition columns, включая `molecule_type`.
- Проверить точные фазы, nullable policy и полный strict Gold contract без
  служебных колонок SCD2. Сопоставить каждый reject с reason code, проверить
  баланс всех стадий и отсутствие необъяснённых потерь.
- Для исторического снимка из 1000 записей требуется: Silver=1000,
  заполненные фазы=1000, Gold current=1000, `0.5`=3; дробные IDs:
  `CHEMBL14830`, `CHEMBL23194`, `CHEMBL31184`.
- Повторить тот же cached input в режиме `incremental` в принятом новом root.
  Сопоставить entity IDs, normalized content hashes, число current rows,
  SCD2 versions и даты начала версий. Повторный backfill с очисткой не
  доказывает идемпотентность SCD2 merge.
- Проверить перечень downstream outputs, включая `composite_molecule`.
  Восстановленные и ещё открытые области перечислить явно; результат одного
  снимка не означает восстановление всей базы.
- Отдельно запустить
  `python -m bioetl workflow run chembl_molecule --limit 1000 --required-persistence-profile degraded_observable`
  с ещё одним новым data/report/archive root. Профиль обязателен: штатный
  `replay_ready` отклоняет live-запуск без immutable snapshot-backed Bronze.
  Оценивать фактический новый cohort; не предполагать равенство исторической
  API-выборке. Сохранить HTTP/retry ошибки, exit status, отчёты и monitoring
  evidence.

## Rollback/Recovery

До приёмки не переключать consumers на новые outputs. При ошибке сохранить
диагностические outputs и исходные данные, устранить причину с regression
proof и повторить в новом root. Для отката потребитель использует прежнее
назначение; не заменять и не удалять оригиналы. Локальные проверки привязать
к точному SHA отдельно от remote CI.

## Источники контракта

- [Provider reference](../../04-reference/providers/chembl/molecule.md)
- [Molecule schema](../../04-reference/schemas/domain/chembl/molecule-schema.md)
- [Gold contract](../../04-reference/contracts/gold/chembl_molecule_v1.0.json)

## Post-incident

Сохранить команды, exit codes, новый run/manifest ID, effective-config digest,
контрольные суммы, сравнение фаз и Gold, перечень downstream datasets.
Закрывать назначенные задачи только по проверенным критериям; результаты
локального запуска и CI на текущем SHA указывать раздельно.

## Compliance

Оригиналы и `.env` сохраняются. DQ и strict Gold validation обязательны;
исходная выборка ChEMBL и hash policy не расширяются. Перезапуск сервисов
и переключение consumers не являются частью этой процедуры восстановления.

## Выполненное восстановление (2026-11-19/20, #13196 / #13201)

Восстановление выполнено на checkout `735969e92ad082541cf4af6b431113bc3e7db119`
(main после #13214 и #13225) в отдельных offline/live roots для
`chembl_molecule`. Исходный Bronze
(`data/workflows-limit1000-20261118T042057Z/.../bronze/chembl/molecule`,
batch `64dfb0f8-ee12-557b-a3cf-ec181f7ccbbe`) до и после обработки неизменён:
1000 записей, 1000 уникальных `molecule_chembl_id`, max_phase заполнен 1000/1000,
дробные фазы `0.5` у `CHEMBL14830`, `CHEMBL23194`, `CHEMBL31184` (по 3 записи).

| Прогон | Run ID | Результат |
|---|---|---|
| Offline backfill (cached Bronze) | `774f4a22-b2b2-5358-a6ae-9e202157ec4e` | Silver 1000/1000 unique, Gold current 1000, rejects 0, funnel OK |
| Повторный backfill (очистка+перезапись) | `7c23c3cd-e3f3-543f-a460-2ab9f2f40eb3` | 1000/1000/1000; `content_hash` совпал со первым прогоном по 1000/1000 |
| Incremental повтор (SCD2 merge) | `c869cf53-f97b-5ac7-84cb-7ce83782d772` | total=current=1000, версий >1 нет; `content_hash` идентичен |
| Live workflow (новый API cohort) | workflow `0b68c9b0-17a2-5f2b-ad4c-f5056820fdce`, pipeline `3f634546-3144-5462-9b0b-62c2ce411ccc` | 1000/1000/1000, фазы сохранены; профиль `degraded_observable`, metrics push warning (нет backend) |

Заметки по протоколу:

- Live workflow штатно требует `replay_ready`; для новой API-выборки
  использован явный `--required-persistence-profile degraded_observable` —
  это зафиксировано в effective-config, DQ и strict Gold validation не
  ослаблялись.
- Производные datasets: `composite_molecule` нигде не материализован
  (конфиг `configs/composites/molecule.yaml` существует, output root
  отсутствует); повреждённый исходный Silver/Gold в default roots сохранён
  без изменений и остаётся историческим evidence.
- Публикация metrics в live прогоне вернула `URLError` (observability backend
  не запущен, ADR-010); на восстановление данных не влияет, зафиксировано как
  warning.
