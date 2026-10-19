# Итоговая запись для #12107

Проверенный commit дельты `5a600bcb7422a405c5285343a07e8a245029f50d` → `0fd0768ff931724e61c1482cf981df896abe8e81`: `0fd0768ff931724e61c1482cf981df896abe8e81`.
Проверенный tree: `36668affe9a8976a8e110f1c50a39348f0d89172`.

Постоянный реестр 11 follow-up, который остаётся после закрытия #12107:

https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0fd0768ff931724e61c1482cf981df896abe8e81/reports/audit-runs/12107-r07/behavior-followups.json

SHA256 реестра `a31f45ef37b22f59a3394e24628f31f740b59d73010801a3111a747aac017cb3`, 19365 bytes. Поля `survives_12107_closure` и `closes_with_12107` сами по себе передачу не подтверждают. Подтверждение — эта ссылка на commit `0fd0768ff931724e61c1482cf981df896abe8e81`.

Tracking responsibility для всех 11 id: роль BioETL Team, тип tracking, не semantic owner. Основание: заголовок Owner в `docs/02-architecture/diagrams/descriptions/architecture/05b-adapter-hierarchy-providers.md`. Отдельные remediation issues при необходимости создаёт GitHub-владелец. Реализации в R07 не начинались.

| Follow-up | Критерий закрытия |
| --- | --- |
| `R07-FU-HEALTH-STATUS-ChemblAdapter` | In-process fixture без live-сети: `ChemblAdapter.health_check` возвращает HEALTHY на успешном probe и non-HEALTHY на документированной ошибке probe. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-PubMedAdapter` | In-process fixture без live-сети: `PubMedAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-SemanticScholarAdapter` | In-process fixture без live-сети: `SemanticScholarAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-OpenAlexAdapter` | In-process fixture без live-сети: `OpenAlexAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-HEALTH-STATUS-OpenAlexAdapter` | In-process fixture без live-сети: `OpenAlexAdapter.health_check` возвращает HEALTHY на успешном probe и non-HEALTHY на документированной ошибке probe. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-CrossRefAdapter` | In-process fixture без live-сети: `CrossRefAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-HEALTH-STATUS-CrossRefAdapter` | In-process fixture без live-сети: `CrossRefAdapter.health_check` возвращает HEALTHY на успешном probe и non-HEALTHY на документированной ошибке probe. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-UniProtAdapter` | In-process fixture без live-сети: `UniProtAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-HEALTH-STATUS-UniProtAdapter` | In-process fixture без live-сети: `UniProtAdapter.health_check` возвращает HEALTHY на успешном probe и non-HEALTHY на документированной ошибке probe. Timeout и cancellation остаются у #12108. |
| `R07-FU-FETCH-PAYLOAD-PubChemAdapter` | In-process fixture без live-сети: `PubChemAdapter.fetch` отдаёт одну scripted-запись. Timeout и cancellation остаются у #12108. |
| `R07-FU-HEALTH-STATUS-PubChemAdapter` | In-process fixture без live-сети: `PubChemAdapter.health_check` возвращает HEALTHY на успешном probe и non-HEALTHY на документированной ошибке probe. Timeout и cancellation остаются у #12108. |
