# Durability Crash/Restart Sweep (Wave E - Lineage)

| Строка | Сценарий | Вердикт | Ограничение / Дефект |
|---|---|---|---|
| 15a | Crash after fragment write (Lineage) | NOT_VERIFIABLE | fragment remains but without indexes. Currently `FileLineageStore` does not have recovery sync mechanisms for partial index crash inside the barrier. |
| 15b | Crash mid-index append (Lineage) | NOT_VERIFIABLE | partial indexes are left without rollback in next worker process, because no recovery routine checks for index integrity across crashes. |
