# Durability Crash/Restart Sweep (Wave D - Gold)

| Строка | Сценарий | Вердикт | Ограничение / Дефект |
|---|---|---|---|
| 8 | Crash during normal commit (Gold) | NOT_VERIFIABLE | проверка только Python-границы helper; сбой внутри `write_deltalake` не инжектится |
| 9 | Crash during dual-write single commit | NOT_VERIFIABLE | каждый target коммитится тем же native helper |
| 10 | Crash during postwrite (pre-entry gate) | NOT_VERIFIABLE | в `_write_single_target_impl` нет pre-entry gate перед `_post_write_gold` |
| 10b | Crash during postwrite (collaborator gate) | VERIFIED | SIGKILL во втором `create_gold_metadata_bundle` после обоих коммитов |
| 11a | Dual-write: сохранность (crash before commit) | VERIFIED | SIGKILL на входе `_dispatch_write`; Delta-таблиц нет |
| 11b | Dual-write: обнаружение (crash during commit) | NOT_VERIFIABLE | нет Python-границы для барьера; SIGKILL внутри native commit не доказан |
| 11c | Dual-write: replay (crash after commit) | NOT_VERIFIABLE | native helper возвращается только после `write_deltalake` |
