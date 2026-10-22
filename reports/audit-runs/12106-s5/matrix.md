# Durability Crash/Restart Sweep (Wave D - Gold)

| Строка | Сценарий | Вердикт | Ограничение / Дефект |
|---|---|---|---|
| 8 | Crash during normal commit (Gold) | NOT_VERIFIABLE | Gold writer pre-entry gate is missing |
| 9 | Crash during dual-write single commit | NOT_VERIFIABLE | Gold writer pre-entry gate is missing |
| 10 | Crash during postwrite (pre-entry gate) | NOT_VERIFIABLE | pre-entry gate отсутствует |
| 10b | Crash during postwrite (collaborator gate) | VERIFIED | |
| 11a | Dual-write: сохранность (crash before commit) | NOT_VERIFIABLE | Gold writer pre-entry gate is missing |
| 11b | Dual-write: обнаружение (crash during commit) | NOT_VERIFIABLE | Gold writer pre-entry gate is missing |
| 11c | Dual-write: replay (crash after commit) | NOT_VERIFIABLE | Gold writer pre-entry gate is missing |
