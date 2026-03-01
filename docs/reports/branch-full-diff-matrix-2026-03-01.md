# Full Branch Diff Matrix (vs local HEAD) — 2026-03-01

Baseline: local branch `TMP01-01` (`HEAD`).\
Cell format: `STATUS +added/-deleted` from `git diff HEAD..origin/<branch>`.

Total union files: **478**.\
Full machine-readable matrix: `docs/reports/branch-full-diff-matrix-2026-03-01.csv`.

## Totals

| Branch | Changed files |
|---|---:|
| `bioetl-architecture-prompts-v3-lLJJu` | 240 |
| `audit-fix-diagrams-hZglG` | 263 |
| `audit-diagram-docs-scripts-fUJUM` | 349 |
| `improve-diagram-design-K2XMN` | 452 |

## Preview (first 200 files)

| File | `bioetl-architecture-prompts-v3-lLJJu` | `audit-fix-diagrams-hZglG` | `audit-diagram-docs-scripts-fUJUM` | `improve-diagram-design-K2XMN` |
|---|---|---|---|---|
| `"2_10_\321\203\320\273\321\203\321\207\321\210\320\265\320\275\320\270\320\271_\320\264\320\273\321\217_\320\276\320\277\321\202\320\270\320\274\320\270\320\267\320\260\321\206\320\270\320\270_\321\200\320\260.md"` | D +0/-57 | - | D +0/-57 | D +0/-57 |
| `"3_10_\321\203\320\273\321\203\321\207\321\210\320\265\320\275\320\270\320\271_\320\264\320\273\321\217_\320\276\320\277\321\202\320\270\320\274\320\270\320\267\320\260\321\206\320\270\320\270_\321\200\320\260.md"` | D +0/-52 | - | D +0/-52 | D +0/-52 |
| `.claude/agents/ORCHESTRATION.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/agents/py-audit-bot.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/agents/py-doc-bot.md` | M +2/-2 | - | M +2/-2 | M +2/-2 |
| `.claude/prompts/00-Audit/02-architecture-audit.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/00-Audit/02-file-structure-audit-standardization.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/00-Audit/03-code-inventory-audit.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/00-Documentation/00-documentation-audit-update-task.md` | M +2/-2 | - | M +2/-2 | M +2/-2 |
| `.claude/prompts/00-Documentation/01-docstrings-completion.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/00-Documentation/04-naming-compliance-audit-prompt.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/01-documentation-update-prompt.md` | M +8/-8 | - | M +8/-8 | M +8/-8 |
| `.claude/prompts/02-Sync/01-xwalk.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/02-docs-PR.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/03-pk-issue.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/04-schema-review.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/05-vcr-tests.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/06-manual-EP.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/02-Sync/07-bot-xwalk.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/prompts/03-repository-cleanup-assistant.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/settings.local.json` | - | M +2/-1 | - | - |
| `.claude/skills/documentation-audit.audit-checklist.md` | M +2/-2 | - | M +2/-2 | M +2/-2 |
| `.claude/skills/documentation-audit.openai.yaml` | M +2/-2 | - | M +2/-2 | M +2/-2 |
| `.claude/skills/documentation-audit.report-template.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.claude/skills/documentation-audit.skill.md` | M +3/-3 | - | M +3/-3 | M +3/-3 |
| `.claude/skills/mermaid-design.md` | - | M +22/-14 | M +22/-17 | - |
| `.github/workflows/contract-tests.yml` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `.github/workflows/docs.yml` | M +4/-0 | - | - | - |
| `.github/workflows/port-contracts.yml` | M +2/-2 | - | M +2/-2 | M +2/-2 |
| `.gitignore` | M +2/-1 | - | M +2/-1 | M +2/-1 |
| `Makefile` | - | - | M +1/-1 | - |
| `assets/javascripts/MERMAID_VERSION` | - | - | M +1/-1 | - |
| `assets/javascripts/download_mermaid.ps1` | - | - | M +2/-2 | - |
| `assets/javascripts/mermaid-loader.js` | - | - | M +1/-1 | - |
| `assets/stylesheets/mermaid.css` | - | - | - | M +34/-0 |
| `chrome-headless-shell/.metadata` | D +0/-5 | - | D +0/-5 | D +0/-5 |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/ABOUT` | D +0/-9 | - | D +0/-9 | D +0/-9 |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/LICENSE.headless_shell` | D +0/-37908 | - | D +0/-37908 | D +0/-37908 |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/deb.deps` | D +0/-30 | - | D +0/-30 | D +0/-30 |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/icudtl.dat` | D +-/-- | - | D +-/-- | D +-/-- |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/libvulkan.so.1` | D +-/-- | - | D +-/-- | D +-/-- |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/rpm.deps` | D +0/-92 | - | D +0/-92 | D +0/-92 |
| `chrome-headless-shell/linux-146.0.7680.31/chrome-headless-shell-linux64/v8_context_snapshot.bin` | D +-/-- | - | D +-/-- | D +-/-- |
| `docs/00-project/00-map.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `docs/00-project/agents/AGENT.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `docs/00-project/agents/CLAUDE.md` | M +3/-3 | - | M +3/-3 | M +3/-3 |
| `docs/00-project/agents/orchestration/ORCHESTRATION.md` | M +1/-1 | - | M +1/-1 | M +1/-1 |
| `docs/00-project/glossary.md` | M +1/-0 | - | M +1/-0 | M +1/-0 |
| `docs/02-architecture/00-overview.md` | M +7/-1 | - | M +7/-1 | M +7/-1 |
| `docs/02-architecture/06-diagram-policy.md` | - | - | M +4/-15 | - |
| `docs/02-architecture/architecture-diagrams.md` | - | - | M +15/-15 | - |
| `docs/02-architecture/decisions/ADR-040-diagram-governance.md` | - | M +24/-8 | M +2/-2 | - |
| `docs/02-architecture/diagrams/architecture-diagrams-prompts-v4.md` | A +392/-0 | - | - | - |
| `docs/02-architecture/diagrams/mermaid/01-full-system-component-full.mermaid` | - | - | M +8/-38 | M +160/-190 |
| `docs/02-architecture/diagrams/mermaid/04-domain-layer-class-diagram-full.mermaid` | - | - | - | M +284/-284 |
| `docs/02-architecture/diagrams/mermaid/21-activity-entity-data-flow-full.mermaid` | - | - | M +6/-22 | M +97/-113 |
| `docs/02-architecture/diagrams/mermaid/26-hexagonal-ports-adapters-full.mermaid` | - | - | M +7/-22 | M +123/-138 |
| `docs/02-architecture/diagrams/mermaid/28-composition-root-di-graph-full.mermaid` | - | - | M +10/-35 | M +91/-116 |
| `docs/02-architecture/diagrams/mermaid/29-composite-pipeline-workflow-full.mermaid` | - | - | M +6/-23 | M +91/-108 |
| `docs/02-architecture/diagrams/mermaid/30-port-adapter-mapping-full.mermaid` | - | - | M +4/-33 | M +108/-137 |
| `docs/02-architecture/diagrams/mermaid/32-single-record-journey-full.mermaid` | - | - | M +6/-16 | M +60/-70 |
| `docs/02-architecture/diagrams/mermaid/35-bootstrap-sequence-full.mermaid` | - | - | M +5/-23 | M +81/-99 |
| `docs/02-architecture/diagrams/mermaid/39-medallion-invariants-full.mermaid` | - | - | M +8/-18 | M +73/-83 |
| `docs/02-architecture/diagrams/mermaid/44-cross-provider-enrichment-full.mermaid` | - | - | M +5/-16 | M +54/-65 |
| `docs/02-architecture/diagrams/mermaid/46-yaml-config-resolution-full.mermaid` | - | - | M +8/-33 | M +83/-108 |
| `docs/02-architecture/diagrams/mermaid/png/INDEX.md` | D +0/-76 | - | D +0/-76 | D +0/-76 |
| `docs/02-architecture/diagrams/mermaid/svg/INDEX.md` | D +0/-76 | - | D +0/-76 | D +0/-76 |
| `docs/02-architecture/mmd-diagrams/00-legend.mmd` | A +54/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/_template.mmd` | - | - | M +1/-0 | M +85/-79 |
| `docs/02-architecture/mmd-diagrams/architecture/01-high-level-hexagonal.mmd` | - | M +4/-4 | M +1/-0 | M +127/-122 |
| `docs/02-architecture/mmd-diagrams/architecture/01a-hexagonal-overview.mmd` | - | M +7/-13 | - | M +57/-54 |
| `docs/02-architecture/mmd-diagrams/architecture/01b-hexagonal-domain-app.mmd` | - | M +3/-3 | - | M +37/-34 |
| `docs/02-architecture/mmd-diagrams/architecture/01c-hexagonal-infra-comp.mmd` | - | M +3/-6 | M +1/-1 | M +48/-45 |
| `docs/02-architecture/mmd-diagrams/architecture/02-layer-dependency-matrix.mmd` | - | M +2/-1 | - | M +54/-51 |
| `docs/02-architecture/mmd-diagrams/architecture/03-medallion-data-flow.mmd` | - | M +8/-10 | M +7/-6 | M +125/-103 |
| `docs/02-architecture/mmd-diagrams/architecture/03a-medallion-layers-overview.mmd` | - | M +4/-3 | - | M +35/-32 |
| `docs/02-architecture/mmd-diagrams/architecture/04-pipeline-execution-flow.mmd` | - | M +1/-0 | M +1/-1 | M +101/-98 |
| `docs/02-architecture/mmd-diagrams/architecture/05-provider-adapter-hierarchy.mmd` | - | M +3/-14 | M +1/-0 | M +110/-106 |
| `docs/02-architecture/mmd-diagrams/architecture/05a-adapter-hierarchy-base.mmd` | - | M +3/-3 | - | M +33/-30 |
| `docs/02-architecture/mmd-diagrams/architecture/05b-adapter-hierarchy-providers.mmd` | - | M +2/-2 | M +1/-1 | M +40/-37 |
| `docs/02-architecture/mmd-diagrams/architecture/06-storage-layer.mmd` | - | M +4/-10 | M +1/-0 | M +100/-96 |
| `docs/02-architecture/mmd-diagrams/architecture/06a-storage-writers.mmd` | - | - | A +65/-0 | A +68/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/06b-storage-support.mmd` | - | - | A +45/-0 | A +48/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/07-dq-system.mmd` | - | M +4/-4 | M +1/-0 | M +107/-106 |
| `docs/02-architecture/mmd-diagrams/architecture/07a-dq-analysis.mmd` | - | - | A +60/-0 | A +63/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/07b-dq-pipeline.mmd` | - | - | A +47/-0 | A +50/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/08-composite-pipeline.mmd` | - | M +7/-13 | M +3/-2 | M +136/-124 |
| `docs/02-architecture/mmd-diagrams/architecture/08a-composite-config.mmd` | - | - | A +56/-0 | A +59/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/08b-composite-execution.mmd` | - | - | A +99/-0 | A +102/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/09-observability-stack.mmd` | - | M +6/-12 | M +2/-1 | M +85/-81 |
| `docs/02-architecture/mmd-diagrams/architecture/09a-observability-app.mmd` | - | - | A +44/-0 | A +47/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/09b-observability-infra.mmd` | - | - | A +62/-0 | A +65/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/10-resilience-patterns.mmd` | - | M +5/-9 | M +2/-2 | M +74/-71 |
| `docs/02-architecture/mmd-diagrams/architecture/11-configuration-system.mmd` | - | M +3/-6 | M +1/-0 | M +112/-108 |
| `docs/02-architecture/mmd-diagrams/architecture/11a-config-loading.mmd` | - | - | A +58/-0 | A +61/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/11b-config-domain.mmd` | - | - | A +63/-0 | A +66/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/12-bootstrap-di-container.mmd` | - | M +3/-5 | M +2/-1 | M +134/-121 |
| `docs/02-architecture/mmd-diagrams/architecture/12a-bootstrap-factories.mmd` | - | M +3/-2 | M +1/-1 | M +37/-34 |
| `docs/02-architecture/mmd-diagrams/architecture/12b-bootstrap-wiring.mmd` | - | M +4/-4 | M +1/-1 | M +58/-55 |
| `docs/02-architecture/mmd-diagrams/architecture/13-port-protocol-contracts.mmd` | - | M +4/-4 | M +1/-0 | M +136/-135 |
| `docs/02-architecture/mmd-diagrams/architecture/13a-data-storage-ports.mmd` | - | M +2/-16 | - | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/architecture/13a-port-contracts-data-sources.mmd` | - | M +3/-4 | - | M +18/-18 |
| `docs/02-architecture/mmd-diagrams/architecture/13b-operational-ports.mmd` | - | M +2/-16 | M +1/-0 | M +48/-47 |
| `docs/02-architecture/mmd-diagrams/architecture/13b-port-contracts-storage.mmd` | - | M +3/-2 | - | M +23/-23 |
| `docs/02-architecture/mmd-diagrams/architecture/13c-port-contracts-observability.mmd` | - | M +3/-3 | - | M +29/-29 |
| `docs/02-architecture/mmd-diagrams/architecture/13c-validation-dq-ports.mmd` | - | M +2/-16 | - | M +50/-50 |
| `docs/02-architecture/mmd-diagrams/architecture/13d-port-contracts-services.mmd` | - | M +5/-5 | M +1/-1 | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/architecture/13e-operational-ports-domain.mmd` | - | - | A +26/-0 | A +26/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/13f-operational-ports-infra.mmd` | - | - | A +25/-0 | A +25/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/14-cli-interface-layer.mmd` | - | M +3/-9 | M +1/-0 | M +91/-87 |
| `docs/02-architecture/mmd-diagrams/architecture/14a-cli-commands.mmd` | - | - | A +60/-0 | A +63/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/14b-cli-routing.mmd` | - | - | A +62/-0 | A +65/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/15-batch-executor-internals.mmd` | - | M +6/-12 | M +2/-2 | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/architecture/16-transformer-hierarchy.mmd` | - | M +7/-9 | M +2/-1 | M +54/-50 |
| `docs/02-architecture/mmd-diagrams/architecture/16a-transformer-base.mmd` | - | - | A +50/-0 | A +50/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/16b-transformer-pub-other.mmd` | - | - | A +59/-0 | A +62/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/17-security-pii-audit.mmd` | - | M +5/-7 | M +1/-1 | M +74/-71 |
| `docs/02-architecture/mmd-diagrams/architecture/18-lock-checkpoint-shutdown.mmd` | - | M +3/-11 | M +2/-1 | M +88/-84 |
| `docs/02-architecture/mmd-diagrams/architecture/18a-lock-system.mmd` | - | - | A +57/-0 | A +60/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/18b-checkpoint-shutdown.mmd` | - | - | A +63/-0 | A +66/-0 |
| `docs/02-architecture/mmd-diagrams/architecture/png/INDEX.md` | D +0/-202 | - | D +0/-202 | D +0/-202 |
| `docs/02-architecture/mmd-diagrams/architecture/svg/INDEX.md` | D +0/-202 | - | D +0/-202 | D +0/-202 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/01-domain-ports.mmd` | M +1/-0 | M +2/-0 | - | M +252/-252 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/02-entities-aggregates.mmd` | M +1/-0 | M +2/-0 | - | M +237/-237 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/03-value-objects.mmd` | M +1/-0 | M +2/-0 | - | M +278/-278 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/04-types-enums.mmd` | M +1/-0 | M +2/-0 | - | M +231/-231 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/05-exceptions.mmd` | M +1/-0 | M +3/-1 | M +1/-1 | M +161/-161 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/06-config-classes.mmd` | M +1/-0 | M +16/-14 | M +14/-14 | M +177/-177 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/07-application-core-services.mmd` | M +1/-0 | M +2/-0 | - | M +229/-229 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/08-application-services.mmd` | M +1/-0 | M +2/-0 | - | M +198/-198 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/09-transformers.mmd` | M +1/-0 | M +2/-0 | - | M +152/-152 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/10-adapters.mmd` | M +1/-0 | M +2/-0 | - | M +225/-225 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/11-storage.mmd` | M +1/-0 | M +3/-1 | - | M +248/-248 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/12-composite-pipeline.mmd` | M +1/-0 | M +2/-0 | - | M +187/-187 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/13-domain-services.mmd` | M +1/-0 | M +2/-0 | - | M +57/-57 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/14-observability.mmd` | M +1/-0 | M +5/-3 | - | M +246/-246 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/15-extractors.mmd` | M +1/-0 | M +2/-0 | - | M +107/-107 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/16-factories-bootstrap.mmd` | M +1/-0 | M +2/-0 | M +1/-1 | M +136/-136 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/png/INDEX.md` | D +0/-100 | - | D +0/-100 | D +0/-100 |
| `docs/02-architecture/mmd-diagrams/class-diagrams/svg/INDEX.md` | D +0/-100 | - | D +0/-100 | D +0/-100 |
| `docs/02-architecture/mmd-diagrams/docs/00-diagramming-policy.md` | - | - | M +15/-274 | - |
| `docs/02-architecture/mmd-diagrams/foundation/01-full-system-component.mmd` | - | M +8/-32 | M +1/-1 | M +263/-260 |
| `docs/02-architecture/mmd-diagrams/foundation/01-high-level.mmd` | - | M +11/-12 | - | M +60/-57 |
| `docs/02-architecture/mmd-diagrams/foundation/01a-system-overview.mmd` | A +28/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/foundation/01b-system-data-pipeline.mmd` | A +33/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/foundation/01c-system-cross-cutting.mmd` | A +39/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/foundation/02-full-medallion-data-flow.mmd` | - | M +7/-11 | M +1/-1 | M +59/-56 |
| `docs/02-architecture/mmd-diagrams/foundation/03-pipeline-execution-happy-path.mmd` | - | M +2/-1 | M +1/-1 | M +87/-84 |
| `docs/02-architecture/mmd-diagrams/foundation/04-domain-layer-class-diagram.mmd` | - | M +2/-1 | - | M +344/-341 |
| `docs/02-architecture/mmd-diagrams/foundation/04-error-flow.mmd` | - | M +6/-5 | M +4/-4 | M +47/-44 |
| `docs/02-architecture/mmd-diagrams/foundation/05-layers-interaction.mmd` | - | M +7/-7 | - | M +63/-60 |
| `docs/02-architecture/mmd-diagrams/foundation/05-pipeline-lifecycle-states.mmd` | - | M +2/-1 | M +1/-1 | M +177/-174 |
| `docs/02-architecture/mmd-diagrams/foundation/06-application-layer-class-diagram.mmd` | - | M +2/-1 | M +1/-1 | M +364/-361 |
| `docs/02-architecture/mmd-diagrams/foundation/06-pipeline-execution.mmd` | - | M +2/-0 | M +3/-3 | M +64/-61 |
| `docs/02-architecture/mmd-diagrams/foundation/07-circuit-breaker-states.mmd` | - | M +2/-1 | M +1/-1 | M +67/-64 |
| `docs/02-architecture/mmd-diagrams/foundation/07-medallion-flow.mmd` | - | M +6/-4 | M +1/-1 | M +52/-49 |
| `docs/02-architecture/mmd-diagrams/foundation/08-complete-etl-workflow.mmd` | - | M +11/-10 | M +1/-1 | M +99/-99 |
| `docs/02-architecture/mmd-diagrams/foundation/08-domain-ddd.mmd` | - | M +2/-0 | M +1/-1 | M +70/-67 |
| `docs/02-architecture/mmd-diagrams/foundation/09-full-er-diagram.mmd` | - | M +2/-1 | - | M +234/-234 |
| `docs/02-architecture/mmd-diagrams/foundation/10-infrastructure-layer-class-diagram.mmd` | - | M +2/-1 | M +1/-1 | M +372/-369 |
| `docs/02-architecture/mmd-diagrams/foundation/11-lock-acquisition-sequence.mmd` | - | M +2/-1 | M +29/-29 | M +85/-82 |
| `docs/02-architecture/mmd-diagrams/foundation/12-local-deployment-architecture.mmd` | - | M +7/-9 | - | M +74/-71 |
| `docs/02-architecture/mmd-diagrams/foundation/13-domain-models-relationship.mmd` | - | M +2/-1 | - | M +399/-396 |
| `docs/02-architecture/mmd-diagrams/foundation/14-provider-health-states.mmd` | - | M +2/-1 | M +1/-1 | M +101/-98 |
| `docs/02-architecture/mmd-diagrams/foundation/15-dq-check-workflow.mmd` | - | M +11/-12 | - | M +100/-100 |
| `docs/02-architecture/mmd-diagrams/foundation/16-memory-lock-class.mmd` | - | M +2/-1 | - | M +136/-133 |
| `docs/02-architecture/mmd-diagrams/foundation/17-pipeline-hierarchy.mmd` | - | M +2/-1 | - | M +233/-233 |
| `docs/02-architecture/mmd-diagrams/foundation/18-bronze-write-sequence.mmd` | - | M +2/-1 | - | M +63/-60 |
| `docs/02-architecture/mmd-diagrams/foundation/19-delta-lake-write-sequence.mmd` | - | M +2/-1 | M +1/-1 | M +103/-100 |
| `docs/02-architecture/mmd-diagrams/foundation/20-quarantine-record-states.mmd` | - | M +2/-1 | M +1/-1 | M +122/-119 |
| `docs/02-architecture/mmd-diagrams/foundation/21-activity-entity-data-flow.mmd` | - | M +6/-13 | - | M +93/-90 |
| `docs/02-architecture/mmd-diagrams/foundation/22-client-api-request-sequence.mmd` | - | M +2/-1 | M +1/-1 | M +83/-80 |
| `docs/02-architecture/mmd-diagrams/foundation/23-silver-writer-class.mmd` | - | M +2/-1 | M +2/-68 | M +180/-243 |
| `docs/02-architecture/mmd-diagrams/foundation/24-hash-service-class.mmd` | - | M +2/-1 | - | M +70/-67 |
| `docs/02-architecture/mmd-diagrams/foundation/25-circuit-breaker-observer-class.mmd` | - | M +2/-1 | - | M +251/-248 |
| `docs/02-architecture/mmd-diagrams/foundation/26-hexagonal-ports-adapters.mmd` | - | M +8/-9 | M +5/-5 | M +115/-115 |
| `docs/02-architecture/mmd-diagrams/foundation/27-import-matrix-enforcement.mmd` | - | M +4/-3 | - | M +53/-50 |
| `docs/02-architecture/mmd-diagrams/foundation/28-composition-root-di-graph.mmd` | - | M +15/-34 | M +3/-3 | M +147/-144 |
| `docs/02-architecture/mmd-diagrams/foundation/29-composite-pipeline-workflow.mmd` | - | M +11/-32 | M +1/-1 | M +153/-150 |
| `docs/02-architecture/mmd-diagrams/foundation/30-port-adapter-mapping.mmd` | - | M +8/-26 | - | M +179/-176 |
| `docs/02-architecture/mmd-diagrams/foundation/31-pipeline-run-lifecycle.mmd` | - | M +2/-1 | M +1/-1 | M +50/-47 |
| `docs/02-architecture/mmd-diagrams/foundation/32-single-record-journey.mmd` | - | M +6/-9 | M +2/-2 | M +59/-56 |
| `docs/02-architecture/mmd-diagrams/foundation/33-cli-run-interaction.mmd` | - | M +2/-1 | M +1/-1 | M +58/-55 |
| `docs/02-architecture/mmd-diagrams/foundation/34-batch-processing-flow.mmd` | - | M +2/-1 | - | M +50/-47 |
| `docs/02-architecture/mmd-diagrams/foundation/36-architecture-principles-mindmap.mmd` | - | M +2/-1 | - | M +84/-84 |
| `docs/02-architecture/mmd-diagrams/foundation/37-cli-entry-full-chain.mmd` | - | M +6/-5 | M +2/-2 | M +57/-54 |
| `docs/02-architecture/mmd-diagrams/foundation/38-runtime-assembly-sequence.mmd` | - | M +2/-1 | M +1/-1 | M +66/-63 |
| `docs/02-architecture/mmd-diagrams/foundation/39-medallion-invariants.mmd` | - | M +7/-15 | M +1/-1 | M +73/-70 |
| `docs/02-architecture/mmd-diagrams/foundation/40-application-core-collaboration.mmd` | - | M +5/-10 | M +2/-2 | M +49/-46 |
| `docs/02-architecture/mmd-diagrams/foundation/41-error-classification-tree.mmd` | - | M +10/-29 | - | M +134/-131 |
| `docs/02-architecture/mmd-diagrams/foundation/42-pipeline-runner-class.mmd` | - | M +2/-1 | M +1/-1 | M +158/-155 |
| `docs/02-architecture/mmd-diagrams/foundation/43-fan-out-fan-in-pattern.mmd` | - | M +5/-6 | M +2/-2 | M +57/-54 |
| `docs/02-architecture/mmd-diagrams/foundation/44-cross-provider-enrichment.mmd` | - | M +5/-6 | M +5/-5 | M +55/-52 |
| `docs/02-architecture/mmd-diagrams/foundation/46-yaml-config-resolution.mmd` | - | M +8/-26 | M +4/-4 | M +128/-125 |
| `docs/02-architecture/mmd-diagrams/foundation/47-publication-merge-sources.mmd` | - | M +2/-1 | M +1/-1 | M +60/-57 |
| `docs/02-architecture/mmd-diagrams/foundation/48-composite-phase-lifecycle.mmd` | - | M +2/-1 | M +1/-1 | M +115/-112 |
| `docs/02-architecture/mmd-diagrams/foundation/49-composite-runner-class.mmd` | - | M +2/-1 | M +1/-1 | M +332/-329 |
| `docs/02-architecture/mmd-diagrams/foundation/50-exception-hierarchy.mmd` | - | M +10/-9 | M +5/-5 | M +95/-92 |
| `docs/02-architecture/mmd-diagrams/foundation/50a-exceptions-critical.mmd` | A +33/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/foundation/50b-exceptions-recoverable.mmd` | A +39/-0 | - | - | - |
