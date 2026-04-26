# Сбор evidence завершён: documentation-publication-remediation

Дата: 2026-03-23
Статус: актуализировано

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Главные выводы

- Repo-level docs guards уже зелёные: `check_doc_links.py` проходит, `report_docs_kpi.py` находится в состоянии `on_track`.
- Оставшийся publication noise в `mkdocs build --strict` сосредоточен не в code-doc contradictions, а в markdown-ссылках из active docs на `configs/`, `tests/`, `src/` и `scripts`, которые не публикуются как site docs.
- Repo-only evidence/backlog docs и internal-published mirrors формируют
  отдельные non-normative surfaces и не должны диктовать wording для active
  published guides.
- Runtime-specific orchestration copies для Codex и Claude являются intentional split, но это должно быть явно сказано в onboarding memory.

## Рекомендуемая политика

- В active published docs ссылки на repo targets вне `docs/` следует оформлять как inline repo paths, а не как markdown links.
- Runtime-specific orchestration docs следует явно маркировать как split by runtime, а не как несанкционированный drift.
