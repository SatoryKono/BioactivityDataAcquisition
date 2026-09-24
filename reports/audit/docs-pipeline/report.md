# docs-pipeline

- prompt: `prompt.audit.docs-pipeline`
- surface_score: **2**
- proven: 4; P0/P1: 0
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

Команда `python -m scripts.docs verify` включает check-links, drift, docstrings, cleanup-inventory, normalization-matrix `--check` и `mkdocs build --strict` во временный каталог. CI: `.github/workflows/docs.yml` job `validate-mkdocs` (pr-gate `docs-governance`); pin uv.lock mkdocs 1.6.1 и `uv run --frozen`. GitHub Pages не деплоится. surface_score 2: сборка и проверки ссылок/API в CI есть, но `build-site` не strict, `.png`/`.svg` пропускают check-links и strict MkDocs, mkdocstrings не рендерит страницы, а tracked INDEX.md штампуется локальным datetime.now().

## Findings

- **DOCS-PIPE-001** P2 PROVEN `docs/02-architecture/diagrams/descriptions/INDEX.md:3` — Tracked generated description index stores a local wall-clock stamp, and its generator is not a docs CI drift check.
- **DOCS-PIPE-002** P2 PROVEN `scripts/docs/checks/check_links.py:669` — The canonical link gate and strict MkDocs build both ignore missing PNG/SVG targets.
- **DOCS-PIPE-003** P2 PROVEN `scripts/docs/build/mkdocs_build.py:29` — Packaged site build does not pass `--strict`, while the CI verification chain does.
- **DOCS-PIPE-004** P2 PROVEN `mkdocs.yml:125` — mkdocstrings is enabled, but no docs page has a directive, so the strict build does not render the public API.

## Remediations

- Default `python -m scripts.docs build-site` to `mkdocs build --strict` so it matches `verify`.
- Fail `check-links` on missing local `.png`/`.svg`, or stop treating MkDocs `not_found: info` as the image gate while `render-diagrams` is `if: false`.
- Remove local `datetime.now()` from `generate_description_indexes.py` and `generate_all_bundles.py`; normalize stamps in `--check` and write with temp+os.replace.
- Wire mkdocstrings to the published API or extend `test_api_reference_public_facades.py` past the three curated tables.
- Keep Pages unpublished until `site_url`, a deploy workflow, and `06-doc-publication-policy.md` change together.
