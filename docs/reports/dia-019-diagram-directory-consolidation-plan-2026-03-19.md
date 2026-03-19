# DIA-019: Diagram Directory Consolidation Plan

Date: 2026-03-19
Status: Proposed migration runbook
Type: Non-normative refactoring plan

## Goal

Свести все diagram-related assets под один корень:

- `docs/02-architecture/diagrams/`

При этом:

- не менять production code;
- не смешивать diagrams с `docs/02-architecture/generated/**` и `docs/02-architecture/decisions/**`;
- не ломать render, lint, bundle generation, visual-smoke и docs navigation;
- не объявлять новые canonical paths, пока toolchain и ссылки не переведены.

## Scope

В scope входят:

- `docs/02-architecture/mmd-diagrams/**`
- `docs/02-architecture/diagram-descriptions/**`
- diagram-only docs в `docs/02-architecture/`
- `scripts/diagrams/**`
- diagram wrappers/canonical agent scripts в `docs/00-project/ai/agents/scripts/diagrams/**`
- diagram refs в `mkdocs.yml`, `Makefile`, `docs/**`, `docs/00-project/**`

Вне scope:

- `docs/02-architecture/generated/**`
- `docs/02-architecture/decisions/**`
- rename individual `.mmd` / `.mermaid` basenames
- пересмотр содержания самих диаграмм

## Baseline

Текущая структура размазана между:

- `docs/02-architecture/mmd-diagrams/**`
- `docs/02-architecture/diagram-descriptions/**`
- root docs: `06-diagram-policy.md`, `diagrams.md`, `architecture-diagrams.md`, `container-diagram.md`, `data-flow.md`

Подтверждённые текущие объёмы:

- `architecture`: 52
- `class-diagrams`: 19
- `foundation`: 55
- `views`: 162
- `diagram-descriptions files`: 292
- bundle exports: 8 tracked outputs (`4 docx + 4 pdf`)

## Key Constraint

Это не просто move файлов. Diagram toolchain жёстко зашит на старые пути и старые имена bundle/manifests. Значит миграция должна идти так:

1. Сначала path abstraction и toolchain sync.
2. Потом move корня `mmd-diagrams -> diagrams`.
3. Только после стабилизации можно трогать внутренние family-имена и bundle naming.

## Target Structure

```text
docs/02-architecture/
  decisions/
  generated/
  diagrams/
    README.md
    governance/
      policy.md
      workflow.md
      inventory.md
      views-inventory.md
      history/
        00-diagramming-policy.md
        catalog.md
        modernization-program.md
        regression-test-plan.md
        views-plan.md
        prompt-diagram-expansion.md
    guide/
      index.md
      architecture-reference.md
      container-reference.md
      data-flow-reference.md
    sources/
      architecture/
      class/
      foundation/
      views/
      _template.mmd
    rendered/
      architecture/svg/
      architecture/png/
      class/svg/
      class/png/
      foundation/svg/
      foundation/png/
      views/svg/
      views/png/
    bundles/
      architecture.bundle.md
      architecture.bundle.docx
      architecture.bundle.pdf
      class.bundle.md
      class.bundle.docx
      class.bundle.pdf
      foundation.bundle.md
      foundation.bundle.docx
      foundation.bundle.pdf
      views.bundle.md
      views.bundle.docx
      views.bundle.pdf
    descriptions/
      index.md
      architecture/
      class/
      foundation/
      views/
      legacy/
        mermaid/
    manifests/
      quality-gates.txt
      visual-smoke.txt
    tooling/
      render.sh
      svgo.config.js
    theme/
```

## Critical Toolchain Scope

### Render entrypoints and validators

- `docs/02-architecture/mmd-diagrams/render.sh`
- `scripts/diagrams/validate_mermaid_syntax.sh`
- `scripts/diagrams/run_diagram_checks.sh`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-1.sh`

### Bundle and export generators

- `scripts/diagrams/generate_all_bundles.py`
- `scripts/diagrams/generate_architecture_bundle.py`
- `scripts/diagrams/generate_views_bundle.py`
- `scripts/diagrams/generate_with_descriptions_docx.py`
- `scripts/diagrams/generate_with_descriptions_pdf.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-2.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-3.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh`

### Quality/smoke/manifests

- `scripts/diagrams/check_diagram_artifacts.py`
- `scripts/diagrams/check_diagram_quality_gates.py`
- `scripts/diagrams/check_diagram_visual_smoke.py`
- `scripts/diagrams/check_svg_text_visibility.py`
- `scripts/diagrams/check_class_method_render_integrity.py`
- `scripts/diagrams/run_diagram_nightly_suite.py`
- `scripts/diagrams/fix_pagebreaks_in_bundles.py`

### Path-sensitive helpers

- `scripts/diagrams/lint_diagrams.py`
- `scripts/diagrams/uniform_diagram_sizes.py`
- `scripts/diagrams/inject_svg_styles.py`
- `scripts/diagrams/strip_svg_foreign_object.py`
- `scripts/diagrams/add_svg_text_fallback.py`
- `scripts/diagrams/prune_orphan_nodes.py`
- `scripts/diagrams/fix_mermaid_operators.py`
- `scripts/diagrams/report_diagram_padding.py`

### Docs and navigation

- `mkdocs.yml`
- `Makefile`
- `docs/02-architecture/*.md` diagram-only docs
- `docs/02-architecture/00-overview.md`
- `docs/02-architecture/01-domain-layer.md`
- `docs/02-architecture/02-application-layer.md`
- `docs/02-architecture/03-infrastructure-layer.md`
- `docs/02-architecture/04-interfaces-layer.md`
- `docs/02-architecture/05-composition-layer.md`
- `docs/00-project/**`

## Migration Principle

Не делать в одной волне два типа churn:

- move корня;
- rename внутренних family-каталогов и bundle names.

Отдельный риск: логика ряда скриптов проверяет literal path parts вроде `class-diagrams`, а не абстрактный diagram family. Поэтому rename `class-diagrams -> class` допустим только после toolchain abstraction.

## DIA-019.0 Baseline Freeze

### Objectives

- Зафиксировать current consumers и hardcoded paths.
- Подтвердить counts.
- Удалить временные мусорные артефакты.

### Actions

1. Снять baseline по:
   - `mkdocs.yml`
   - `Makefile`
   - `scripts/diagrams/**`
   - `docs/00-project/ai/agents/scripts/diagrams/**`
   - root diagram docs в `docs/02-architecture/`
2. Зафиксировать counts.
3. Удалить временный lock/temp file:
   - `docs/02-architecture/mmd-diagrams/~$ews-diagrams-with-descriptions.docx`

### Verify

```bash
rg -n "mmd-diagrams|diagram-descriptions|06-diagram-policy|render.sh|with-descriptions|visual-smoke-manifest|quality-gate-manifest" docs mkdocs.yml Makefile scripts configs/quality docs/00-project -g '*.md' -g '*.py' -g '*.sh' -g '*.yml' -g '*.yaml' -g 'Makefile'
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --links
```

### DoD

- Baseline recorded.
- Scope frozen.
- Known temp artifacts removed.

## DIA-019.1 Toolchain and Render Scripts Sync

### Objectives

- Ввести единый diagram root constant/helper.
- Отвязать scripts от literal `docs/02-architecture/mmd-diagrams`.
- Подготовить migration without filesystem move.

### Actions

1. Ввести shared root resolver / constants для:
   - diagram root
   - source root
   - bundle root
   - manifest paths
   - theme/tooling paths
2. Обновить:
   - `scripts/diagrams/*.py`
   - `scripts/diagrams/*.sh`
   - `docs/00-project/ai/agents/scripts/diagrams/*.py`
   - `docs/00-project/ai/agents/scripts/diagrams/*.sh`
3. Не переносить файлы физически на этом шаге.
4. Убедиться, что `render.sh`, bundle generators и smoke scripts берут paths из одного места.

### Explicit files to touch

- `scripts/diagrams/validate_mermaid_syntax.sh`
- `scripts/diagrams/check_diagram_artifacts.py`
- `scripts/diagrams/check_diagram_quality_gates.py`
- `scripts/diagrams/check_diagram_visual_smoke.py`
- `scripts/diagrams/run_diagram_nightly_suite.py`
- `scripts/diagrams/generate_all_bundles.py`
- `scripts/diagrams/generate_architecture_bundle.py`
- `scripts/diagrams/generate_views_bundle.py`
- `scripts/diagrams/generate_with_descriptions_docx.py`
- `scripts/diagrams/generate_with_descriptions_pdf.py`
- `scripts/diagrams/fix_pagebreaks_in_bundles.py`
- `scripts/diagrams/lint_diagrams.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-1.sh`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-2.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-3.py`
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh`

### Verify

```bash
./.venv/Scripts/python.exe scripts/diagrams/generate_all_bundles.py
bash docs/02-architecture/mmd-diagrams/render.sh --filter '12*'
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_visual_smoke.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt
bash scripts/diagrams/validate_mermaid_syntax.sh
```

### DoD

- Toolchain no longer depends on hardcoded root in multiple places.
- Render/check/generate scripts still work before move.

## DIA-019.2 Root Move Only

### Objectives

- Перенести только верхний root:
  - `docs/02-architecture/mmd-diagrams -> docs/02-architecture/diagrams`
- Сохранить внутренние names unchanged:
  - `architecture`
  - `class-diagrams`
  - `foundation`
  - `views`
  - `docs`

### Actions

1. Выполнить `git mv` только для корня.
2. Обновить references с `mmd-diagrams/` на `diagrams/` в:
   - `mkdocs.yml`
   - `Makefile`
   - `docs/**`
   - `docs/00-project/**`
   - `scripts/**`
3. Regenerate generated manifests/inventory where needed, а не править вручную.

### Verify

```bash
rg -n "mmd-diagrams/" docs mkdocs.yml Makefile scripts docs/00-project -g '*.md' -g '*.py' -g '*.sh' -g '*.yml' -g '*.yaml' -g 'Makefile'
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --links
bash docs/02-architecture/diagrams/render.sh --filter '14*'
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/visual-smoke-manifest.txt
```

### DoD

- Old root path no longer used.
- Toolchain works on new root.

## DIA-019.3 Consolidate External Diagram Docs

### Objectives

- Свести diagram-only prose under one subtree.
- Перенести description tree under same root.

### Actions

1. Move root docs:
   - `06-diagram-policy.md -> diagrams/governance/policy.md`
   - `diagrams.md -> diagrams/guide/index.md`
   - `architecture-diagrams.md -> diagrams/guide/architecture-reference.md`
   - `container-diagram.md -> diagrams/guide/container-reference.md`
   - `data-flow.md -> diagrams/guide/data-flow-reference.md`
2. Move:
   - `docs/02-architecture/diagram-descriptions/** -> docs/02-architecture/diagrams/descriptions/**`
3. Keep temporary thin stubs only if nav transition requires them.

### Verify

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --links
rg -n "diagram-descriptions|06-diagram-policy\\.md|architecture-diagrams\\.md|container-diagram\\.md|data-flow\\.md" docs mkdocs.yml -g '*.md' -g '*.yml'
```

### DoD

- Diagram prose/docs live under one root.
- Description tree moved under diagrams root.

## DIA-019.4 Internal Directory Normalization

### Objectives

- Нормализовать внутреннюю структуру под `sources/rendered/governance/tooling`.

### Actions

1. Rename families:
   - `diagrams/architecture -> diagrams/sources/architecture`
   - `diagrams/class-diagrams -> diagrams/sources/class`
   - `diagrams/foundation -> diagrams/sources/foundation`
   - `diagrams/views -> diagrams/sources/views`
2. Move sibling render folders into:
   - `diagrams/rendered/<family>/svg`
   - `diagrams/rendered/<family>/png`
3. Rename:
   - `diagrams/docs -> diagrams/governance`
4. Move tooling files:
   - `diagrams/render.sh -> diagrams/tooling/render.sh`
   - `diagrams/svgo.config.js -> diagrams/tooling/svgo.config.js`

### Special caution

Этот шаг допустим только после DIA-019.1 и DIA-019.2, потому что:

- `lint_diagrams.py`
- `check_class_method_render_integrity.py`
- `uniform_diagram_sizes.py`

используют literal family names вроде `class-diagrams`.

### Verify

```bash
./.venv/Scripts/python.exe scripts/diagrams/generate_all_bundles.py
bash docs/02-architecture/diagrams/tooling/render.sh --filter '16*'
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/visual-smoke-manifest.txt
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --links
```

### DoD

- Internal tree normalized.
- Rendered outputs separated from sources.

## DIA-019.5 Bundle and Manifest Naming Normalization

### Objectives

- Упростить bundle/manifests naming.

### Actions

1. Rename bundles:
   - `architecture-diagrams-with-descriptions.* -> bundles/architecture.bundle.*`
   - `class-diagrams-with-descriptions.* -> bundles/class.bundle.*`
   - `foundation-diagrams-with-descriptions.* -> bundles/foundation.bundle.*`
   - `views-diagrams-with-descriptions.* -> bundles/views.bundle.*`
2. Rename manifests:
   - `quality-gate-manifest.txt -> manifests/quality-gates.txt`
   - `visual-smoke-manifest.txt -> manifests/visual-smoke.txt`
3. Update generators, PDF/DOCX scripts, smoke and nightly scripts.

### Verify

```bash
./.venv/Scripts/python.exe scripts/diagrams/generate_all_bundles.py
./.venv/Scripts/python.exe scripts/diagrams/generate_with_descriptions_docx.py --input-md docs/02-architecture/diagrams/bundles/architecture.bundle.md --input-md docs/02-architecture/diagrams/bundles/class.bundle.md --input-md docs/02-architecture/diagrams/bundles/foundation.bundle.md --input-md docs/02-architecture/diagrams/bundles/views.bundle.md
./.venv/Scripts/python.exe scripts/diagrams/generate_with_descriptions_pdf.py --skip-bounds-check --input-md docs/02-architecture/diagrams/bundles/architecture.bundle.md --input-md docs/02-architecture/diagrams/bundles/class.bundle.md --input-md docs/02-architecture/diagrams/bundles/foundation.bundle.md --input-md docs/02-architecture/diagrams/bundles/views.bundle.md
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
```

### DoD

- New bundle names and manifest names are canonical.
- DOCX/PDF generation works on new names.

## DIA-019.6 Navigation, Registry, and Cleanup

### Objectives

- Добить nav and references.
- Убрать legacy paths.

### Actions

1. Fully update:
   - `mkdocs.yml`
   - `Makefile`
   - `docs/02-architecture/00-overview.md`
   - layer docs `[01..05]-*.md`
   - `docs/00-project/**`
   - `skills/**` if they point to old docs paths
2. Regenerate:
   - script inventory / config manifests if generated
3. Remove temporary stubs and legacy compatibility paths.

### Verify

```bash
rg -n "mmd-diagrams|diagram-descriptions|06-diagram-policy\\.md|with-descriptions|visual-smoke-manifest|quality-gate-manifest" docs mkdocs.yml Makefile scripts docs/00-project configs/quality -g '*.md' -g '*.py' -g '*.sh' -g '*.yml' -g '*.yaml' -g 'Makefile'
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --links
./.venv/Scripts/python.exe scripts/diagrams/generate_all_bundles.py
bash docs/02-architecture/diagrams/tooling/render.sh
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
./.venv/Scripts/python.exe scripts/diagrams/check_diagram_visual_smoke.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
```

### DoD

- No live references to old diagram roots remain.
- All diagram assets are under one subdirectory.

## Stop Conditions

- Если после DIA-019.1 нельзя стабилизировать toolchain without hardcoded root assumptions, move step откладывается.
- Если rename `class-diagrams -> class` вызывает cascading breaks in lint/render/check scripts, freeze internal family names and close only root consolidation.
- Если `mkdocs.yml` churn становится слишком широким для одной волны, allow temporary stubs and close nav in a final dedicated batch.

## Success Criteria

- `find docs/02-architecture -maxdepth 2 -type d | rg 'mmd-diagrams|diagram-descriptions'` returns `0`
- all diagram assets live under `docs/02-architecture/diagrams/`
- render/lint/check scripts work on new paths
- `mkdocs.yml` and `Makefile` no longer point to old roots
- markdown bundles, DOCX, PDF, manifests regenerated on new paths
- link checks and diagram quality checks stay green

## Final Note

Главная корректировка относительно раннего варианта плана:

- обновление render/toolchain scripts теперь считается не сопутствующей задачей, а критическим первым батчем;
- move корня отделён от rename внутренних family names;
- wrappers и agent-canonical scripts в `docs/00-project/ai/agents/scripts/diagrams/**` явно включены в scope.
