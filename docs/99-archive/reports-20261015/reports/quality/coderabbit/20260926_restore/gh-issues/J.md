## Summary
Ошибки транспорта и health/circuit классифицируются как успех или не доходят до breaker/retry: ChEMBL paging, circuit breaker 5xx/429, health window, redaction, Crossref, OpenAlex, request metrics.

## Findings
- `chembl/_fetch_paging_filtered.py:82-93` (major): `CHEMBL_ADAPTER_ERRORS` глотаются на continuation page.
- `http/circuit_breaker.py:166-191` (major): HTTP 5xx/429 не считаются failure.
- `decorators/circuit_breaker.py:172-190` (major): `BioETLError` в `_iterate_with_error_recording` не пишется в breaker.
- `http/_health_monitor_transitions.py:41-58` (major): clear window не от последнего error.
- `health_check_provider_mixin.py:146-155` (major): `last_error` без `_redact_transport_error_message`.
- `crossref/_doi_batch_processor.py:76-99` (major): `HTTPStatusError` не разобран (404 vs прочие).
- `openalex/health_probe.py:53-68` (major): `HTTPStatusError` не мапится в DEGRADED для 429/503.
- `base_metrics.py:87-91` (minor): `HTTPStatusError` не классифицируется как error-метрика до re-raise.
- `chembl/health.py:176-185` (minor): DEGRADED page size может превысить `_page_size`.

## Acceptance
- [ ] Continuation-page ошибки уходят в retry/split, не в «успех».
- [ ] 5xx/429 двигают circuit breaker; secrets не попадают в health `last_error`.
- [ ] OpenAlex/Crossref/ChEMBL health статусы согласованы с тестами.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S03-infra-adapters.jsonl`.
