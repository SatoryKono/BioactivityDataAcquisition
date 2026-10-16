## Summary
Кластер корректности UniProt-адаптера: частичные ID-mapping результаты, жёсткий `limit=1`, неполный FASTA-контракт, разъехавшийся extract accession.

## Findings
- `src/bioetl/infrastructure/adapters/uniprot/_idmapping_transport.py:153-164` (major): `_fetch_results` на non-200 и reject payload возвращает частичный результат вместо `IDMappingJobError`; нет потолка страниц `next`.
- `src/bioetl/infrastructure/adapters/uniprot/filtering_adapter_mixin.py:44` (major): `_fetch_non_protein_filtered` передаёт `limit=1` вместо оставшегося global limit.
- `src/bioetl/infrastructure/adapters/uniprot/feature_sequence_adapter_mixin.py:140-151` (major): `_get_parsed_sequences` не парсит FASTA header через `FastaParser.parse_header` и не заполняет `UniProtSequenceRecord`.
- `src/bioetl/infrastructure/adapters/uniprot/filtering_adapter_mixin.py:231-236` (major): accession читается разными функциями; нужен один helper для `primaryAccession` и `accession`.

## Acceptance
- [ ] Non-200 / rejected payload → ошибка, не silent partial.
- [ ] Global limit распределяется по accession; unlimited сохраняется.
- [ ] Sequence records соответствуют контракту.
- [ ] Один extract-accession путь покрыт тестом.

## Evidence
`reports/quality/coderabbit/20260925_085141/review_S03-infra-adapters.jsonl` (restore 2026-09-26, 16 findings).
