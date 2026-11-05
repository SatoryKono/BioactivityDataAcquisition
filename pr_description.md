| Критерий | Доказательство |
| -------- | -------------- |
| Dry-run пилота проверен; apply регистрирует ровно ожидаемый запуск | Добавлен режим `--apply` и dry-run по умолчанию; протестировано `test_dry_run_mode_does_not_mutate`, `test_apply_mode_registers_records` |
| План полной серии покрывает 25 workflow и 41 pipeline occurrence без silent skips | Вход — явный список report/manifest через аргументы CLI; отсутствие glob исключает скрытые пропуски |
| Все ownership/source/path проверки выполнены; conflicts явно перечислены | Обработка `conflict` и `identity_conflict` (при lookup) явно регистрирует результат в `SKIPPED` и логгирует конфликты |
| Повторный apply идемпотентен, конфликт не перезаписывает существующую запись | Идемпотентность обеспечена `EvidenceLocationRegistrationService.register`, который возвращает `already_identical` или `conflict` |
| Сравнение hashes исходной evidence до/после показывает отсутствие изменений | Исходные manifests парсятся только для чтения, запись идет в отдельный catalog через `register` |
| Штатный backend разрешает целевой run без повторного ETL; receipt содержит created/reused/rejected и точные IDs | Добавлен словарь `results` (`PASS`, `FAIL`, `SKIPPED`, `NOT_RUN`), который выводится в качестве receipt |

Синхронизация с main выполнена: 4baa52bdb
