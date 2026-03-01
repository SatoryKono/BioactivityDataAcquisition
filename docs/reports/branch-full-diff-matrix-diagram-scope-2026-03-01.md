# Branch Diff Matrix (Diagram Scope, vs local HEAD) — 2026-03-01

Baseline: local `TMP01-01` (`HEAD`).\
Cell format: `STATUS +added/-deleted` from `git diff HEAD..origin/<branch>`.

Total scoped files: **313**.\
CSV: `docs/reports/branch-full-diff-matrix-diagram-scope-2026-03-01.csv`.

| File | `bioetl-architecture-prompts-v3-lLJJu` | `audit-fix-diagrams-hZglG` | `audit-diagram-docs-scripts-fUJUM` | `improve-diagram-design-K2XMN` |
|---|---|---|---|---|
| `.github/workflows/docs.yml` | M +4/-0 | - | - | - |
| `assets/javascripts/MERMAID_VERSION` | - | - | M +1/-1 | - |
| `assets/javascripts/mermaid-loader.js` | - | - | M +1/-1 | - |
| `assets/stylesheets/mermaid.css` | - | - | - | M +34/-0 |
| `docs/02-architecture/06-diagram-policy.md` | - | - | M +4/-15 | - |
| `docs/02-architecture/architecture-diagrams.md` | - | - | M +15/-15 | - |
| `docs/02-architecture/decisions/ADR-040-diagram-governance.md` | - | M +24/-8 | M +2/-2 | - |
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
| `docs/02-architecture/mmd-diagrams/foundation/50c-exceptions-data-quality.mmd` | A +35/-0 | - | - | - |
| `docs/02-architecture/mmd-diagrams/foundation/png/INDEX.md` | D +0/-328 | - | D +0/-328 | D +0/-328 |
| `docs/02-architecture/mmd-diagrams/foundation/svg/INDEX.md` | D +0/-328 | - | D +0/-328 | D +0/-328 |
| `docs/02-architecture/mmd-diagrams/render.sh` | M +6/-0 | - | - | M +21/-0 |
| `docs/02-architecture/mmd-diagrams/theme/custom-dark.css` | - | - | - | A +260/-0 |
| `docs/02-architecture/mmd-diagrams/theme/custom.css` | - | - | M +9/-0 | M +66/-12 |
| `docs/02-architecture/mmd-diagrams/theme/mermaid-config.json` | - | - | M +1/-1 | M +7/-7 |
| `docs/02-architecture/mmd-diagrams/views/00-legend.mermaid` | - | M +3/-1 | - | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/views/01-full-system-component-dataflow.mermaid` | M +9/-8 | M +13/-14 | M +1/-1 | M +40/-40 |
| `docs/02-architecture/mmd-diagrams/views/01-full-system-component-domain.mermaid` | M +11/-10 | M +4/-2 | M +1/-1 | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/01-full-system-component-full.mermaid` | - | M +8/-32 | M +1/-1 | M +260/-260 |
| `docs/02-architecture/mmd-diagrams/views/01-full-system-component-infra.mermaid` | M +2/-1 | M +6/-10 | - | M +38/-38 |
| `docs/02-architecture/mmd-diagrams/views/01-full-system-component-overview.mermaid` | - | M +8/-13 | M +1/-1 | M +54/-54 |
| `docs/02-architecture/mmd-diagrams/views/01-high-level-dataflow.mermaid` | M +11/-10 | M +15/-16 | M +1/-1 | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/01-high-level-domain.mermaid` | - | M +7/-11 | - | M +63/-63 |
| `docs/02-architecture/mmd-diagrams/views/01-high-level-full.mermaid` | - | M +19/-20 | M +6/-15 | M +72/-81 |
| `docs/02-architecture/mmd-diagrams/views/01-high-level-infra.mermaid` | M +12/-11 | M +6/-10 | M +1/-1 | M +58/-58 |
| `docs/02-architecture/mmd-diagrams/views/01-high-level-overview.mermaid` | - | M +6/-10 | - | M +54/-54 |
| `docs/02-architecture/mmd-diagrams/views/02-medallion-dataflow.mermaid` | M +3/-2 | M +4/-2 | - | M +16/-16 |
| `docs/02-architecture/mmd-diagrams/views/02-medallion-domain.mermaid` | M +3/-2 | M +6/-4 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/02-medallion-full.mermaid` | - | M +11/-10 | M +3/-3 | M +49/-49 |
| `docs/02-architecture/mmd-diagrams/views/02-medallion-infra.mermaid` | M +3/-2 | M +4/-2 | - | M +24/-24 |
| `docs/02-architecture/mmd-diagrams/views/02-medallion-overview.mermaid` | M +3/-2 | M +6/-4 | - | M +27/-27 |
| `docs/02-architecture/mmd-diagrams/views/04-domain-layer-class-diagram-dataflow.mermaid` | M +9/-8 | M +12/-10 | M +1/-1 | M +36/-36 |
| `docs/02-architecture/mmd-diagrams/views/04-domain-layer-class-diagram-domain.mermaid` | M +8/-7 | M +2/-0 | - | M +34/-34 |
| `docs/02-architecture/mmd-diagrams/views/04-domain-layer-class-diagram-full.mermaid` | - | M +2/-1 | - | M +312/-312 |
| `docs/02-architecture/mmd-diagrams/views/04-domain-layer-class-diagram-infra.mermaid` | M +11/-10 | M +4/-2 | M +1/-1 | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/04-domain-layer-class-diagram-overview.mermaid` | - | M +5/-3 | - | M +50/-50 |
| `docs/02-architecture/mmd-diagrams/views/05-layers-interaction-dataflow.mermaid` | M +10/-9 | M +17/-21 | M +1/-1 | M +57/-57 |
| `docs/02-architecture/mmd-diagrams/views/05-layers-interaction-domain.mermaid` | - | M +7/-8 | - | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/views/05-layers-interaction-full.mermaid` | - | M +15/-15 | M +2/-13 | M +68/-79 |
| `docs/02-architecture/mmd-diagrams/views/05-layers-interaction-infra.mermaid` | - | M +7/-8 | - | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/views/05-layers-interaction-overview.mermaid` | M +11/-10 | M +6/-7 | M +1/-1 | M +51/-51 |
| `docs/02-architecture/mmd-diagrams/views/05-pipeline-lifecycle-states-dataflow.mermaid` | M +9/-8 | M +13/-14 | M +1/-1 | M +40/-40 |
| `docs/02-architecture/mmd-diagrams/views/05-pipeline-lifecycle-states-domain.mermaid` | - | M +8/-9 | - | M +60/-60 |
| `docs/02-architecture/mmd-diagrams/views/05-pipeline-lifecycle-states-full.mermaid` | - | M +2/-1 | M +1/-1 | M +174/-174 |
| `docs/02-architecture/mmd-diagrams/views/05-pipeline-lifecycle-states-infra.mermaid` | - | M +7/-5 | - | M +58/-58 |
| `docs/02-architecture/mmd-diagrams/views/05-pipeline-lifecycle-states-overview.mermaid` | - | M +7/-5 | - | M +46/-46 |
| `docs/02-architecture/mmd-diagrams/views/06-application-layer-class-diagram-dataflow.mermaid` | M +11/-10 | M +14/-12 | M +1/-1 | M +40/-40 |
| `docs/02-architecture/mmd-diagrams/views/06-application-layer-class-diagram-domain.mermaid` | - | M +4/-2 | - | M +50/-50 |
| `docs/02-architecture/mmd-diagrams/views/06-application-layer-class-diagram-full.mermaid` | - | M +2/-1 | M +1/-1 | M +361/-361 |
| `docs/02-architecture/mmd-diagrams/views/06-application-layer-class-diagram-infra.mermaid` | - | M +4/-2 | - | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/06-application-layer-class-diagram-overview.mermaid` | - | M +4/-5 | - | M +38/-38 |
| `docs/02-architecture/mmd-diagrams/views/07-circuit-breaker-states-dataflow.mermaid` | - | M +4/-2 | - | M +28/-28 |
| `docs/02-architecture/mmd-diagrams/views/07-circuit-breaker-states-domain.mermaid` | - | M +4/-5 | - | M +49/-49 |
| `docs/02-architecture/mmd-diagrams/views/07-circuit-breaker-states-full.mermaid` | - | M +2/-1 | M +1/-1 | M +64/-64 |
| `docs/02-architecture/mmd-diagrams/views/07-circuit-breaker-states-infra.mermaid` | - | M +4/-5 | - | M +49/-49 |
| `docs/02-architecture/mmd-diagrams/views/07-circuit-breaker-states-overview.mermaid` | - | M +4/-5 | - | M +42/-42 |
| `docs/02-architecture/mmd-diagrams/views/08-complete-etl-workflow-dataflow.mermaid` | M +10/-9 | M +11/-9 | M +1/-1 | M +30/-30 |
| `docs/02-architecture/mmd-diagrams/views/08-complete-etl-workflow-domain.mermaid` | - | M +6/-4 | - | M +47/-47 |
| `docs/02-architecture/mmd-diagrams/views/08-complete-etl-workflow-full.mermaid` | - | M +59/-58 | M +6/-59 | M +103/-156 |
| `docs/02-architecture/mmd-diagrams/views/08-complete-etl-workflow-infra.mermaid` | - | M +4/-2 | - | M +39/-39 |
| `docs/02-architecture/mmd-diagrams/views/08-complete-etl-workflow-overview.mermaid` | M +12/-11 | M +15/-13 | M +1/-1 | M +45/-45 |
| `docs/02-architecture/mmd-diagrams/views/08-domain-ddd-dataflow.mermaid` | M +11/-10 | M +15/-13 | M +1/-1 | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/08-domain-ddd-domain.mermaid` | - | M +5/-3 | M +2/-14 | M +51/-63 |
| `docs/02-architecture/mmd-diagrams/views/08-domain-ddd-full.mermaid` | - | M +15/-13 | M +3/-19 | M +72/-88 |
| `docs/02-architecture/mmd-diagrams/views/08-domain-ddd-infra.mermaid` | - | M +5/-3 | M +3/-16 | M +52/-65 |
| `docs/02-architecture/mmd-diagrams/views/08-domain-ddd-overview.mermaid` | - | M +5/-6 | M +2/-11 | M +43/-52 |
| `docs/02-architecture/mmd-diagrams/views/10-infrastructure-layer-class-diagram-dataflow.mermaid` | M +12/-11 | M +16/-17 | M +1/-1 | M +46/-46 |
| `docs/02-architecture/mmd-diagrams/views/10-infrastructure-layer-class-diagram-domain.mermaid` | - | M +5/-6 | - | M +51/-51 |
| `docs/02-architecture/mmd-diagrams/views/10-infrastructure-layer-class-diagram-full.mermaid` | - | M +2/-1 | M +1/-1 | M +369/-369 |
| `docs/02-architecture/mmd-diagrams/views/10-infrastructure-layer-class-diagram-infra.mermaid` | - | M +5/-6 | - | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/10-infrastructure-layer-class-diagram-overview.mermaid` | - | M +5/-6 | - | M +47/-47 |
| `docs/02-architecture/mmd-diagrams/views/12-local-deployment-architecture-dataflow.mermaid` | M +12/-11 | M +15/-16 | M +1/-1 | M +42/-42 |
| `docs/02-architecture/mmd-diagrams/views/12-local-deployment-architecture-domain.mermaid` | - | M +5/-6 | M +2/-18 | M +55/-71 |
| `docs/02-architecture/mmd-diagrams/views/12-local-deployment-architecture-full.mermaid` | - | M +11/-12 | M +8/-27 | M +76/-95 |
| `docs/02-architecture/mmd-diagrams/views/12-local-deployment-architecture-infra.mermaid` | - | M +4/-5 | - | M +49/-49 |
| `docs/02-architecture/mmd-diagrams/views/12-local-deployment-architecture-overview.mermaid` | - | M +5/-6 | - | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/14-provider-health-states-dataflow.mermaid` | - | M +6/-4 | - | M +39/-39 |
| `docs/02-architecture/mmd-diagrams/views/14-provider-health-states-domain.mermaid` | - | M +4/-5 | - | M +52/-52 |
| `docs/02-architecture/mmd-diagrams/views/14-provider-health-states-full.mermaid` | - | M +2/-1 | M +1/-1 | M +98/-98 |
| `docs/02-architecture/mmd-diagrams/views/14-provider-health-states-infra.mermaid` | - | M +5/-6 | - | M +56/-56 |
| `docs/02-architecture/mmd-diagrams/views/14-provider-health-states-overview.mermaid` | - | M +5/-6 | M +3/-19 | M +50/-66 |
| `docs/02-architecture/mmd-diagrams/views/15-dq-check-workflow-dataflow.mermaid` | - | M +6/-7 | - | M +37/-37 |
| `docs/02-architecture/mmd-diagrams/views/15-dq-check-workflow-domain.mermaid` | - | M +4/-2 | - | M +46/-46 |
| `docs/02-architecture/mmd-diagrams/views/15-dq-check-workflow-full.mermaid` | - | M +11/-12 | M +7/-7 | M +103/-103 |
| `docs/02-architecture/mmd-diagrams/views/15-dq-check-workflow-infra.mermaid` | - | M +6/-7 | - | M +54/-54 |
| `docs/02-architecture/mmd-diagrams/views/15-dq-check-workflow-overview.mermaid` | - | M +6/-7 | - | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/21-activity-entity-data-flow-dataflow.mermaid` | - | M +4/-2 | - | M +25/-25 |
| `docs/02-architecture/mmd-diagrams/views/21-activity-entity-data-flow-domain.mermaid` | - | M +2/-0 | - | M +37/-37 |
| `docs/02-architecture/mmd-diagrams/views/21-activity-entity-data-flow-full.mermaid` | - | M +7/-10 | M +5/-21 | M +98/-114 |
| `docs/02-architecture/mmd-diagrams/views/21-activity-entity-data-flow-infra.mermaid` | - | M +2/-0 | - | M +37/-37 |
| `docs/02-architecture/mmd-diagrams/views/21-activity-entity-data-flow-overview.mermaid` | - | M +2/-0 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/26-hexagonal-ports-adapters-dataflow.mermaid` | - | M +4/-2 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/26-hexagonal-ports-adapters-domain.mermaid` | - | M +4/-2 | - | M +46/-46 |
| `docs/02-architecture/mmd-diagrams/views/26-hexagonal-ports-adapters-full.mermaid` | - | M +7/-6 | M +4/-4 | M +128/-128 |
| `docs/02-architecture/mmd-diagrams/views/26-hexagonal-ports-adapters-infra.mermaid` | - | M +4/-2 | - | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/26-hexagonal-ports-adapters-overview.mermaid` | - | M +4/-2 | - | M +36/-36 |
| `docs/02-architecture/mmd-diagrams/views/28-composition-root-di-graph-dataflow.mermaid` | M +14/-13 | M +17/-18 | M +2/-14 | M +34/-46 |
| `docs/02-architecture/mmd-diagrams/views/28-composition-root-di-graph-domain.mermaid` | M +20/-19 | M +5/-6 | M +2/-20 | M +52/-70 |
| `docs/02-architecture/mmd-diagrams/views/28-composition-root-di-graph-full.mermaid` | - | M +15/-34 | M +3/-3 | M +144/-144 |
| `docs/02-architecture/mmd-diagrams/views/28-composition-root-di-graph-infra.mermaid` | M +20/-19 | M +5/-9 | M +2/-20 | M +52/-70 |
| `docs/02-architecture/mmd-diagrams/views/28-composition-root-di-graph-overview.mermaid` | - | M +6/-5 | M +1/-1 | M +43/-43 |
| `docs/02-architecture/mmd-diagrams/views/29-composite-pipeline-workflow-dataflow.mermaid` | M +11/-10 | M +15/-19 | M +1/-1 | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/29-composite-pipeline-workflow-domain.mermaid` | M +23/-22 | M +24/-22 | M +2/-23 | M +43/-64 |
| `docs/02-architecture/mmd-diagrams/views/29-composite-pipeline-workflow-full.mermaid` | - | M +11/-32 | M +1/-1 | M +150/-150 |
| `docs/02-architecture/mmd-diagrams/views/29-composite-pipeline-workflow-infra.mermaid` | M +23/-22 | M +26/-27 | M +2/-23 | M +51/-72 |
| `docs/02-architecture/mmd-diagrams/views/29-composite-pipeline-workflow-overview.mermaid` | - | M +4/-3 | - | M +19/-19 |
| `docs/02-architecture/mmd-diagrams/views/30-port-adapter-mapping-dataflow.mermaid` | M +7/-6 | M +4/-2 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/30-port-adapter-mapping-domain.mermaid` | M +11/-10 | M +4/-2 | M +1/-1 | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/30-port-adapter-mapping-full.mermaid` | - | M +8/-26 | - | M +176/-176 |
| `docs/02-architecture/mmd-diagrams/views/30-port-adapter-mapping-infra.mermaid` | M +11/-10 | M +4/-2 | M +1/-1 | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/30-port-adapter-mapping-overview.mermaid` | - | M +5/-7 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/31-pipeline-run-lifecycle-dataflow.mermaid` | M +15/-14 | M +19/-20 | M +2/-15 | M +39/-52 |
| `docs/02-architecture/mmd-diagrams/views/31-pipeline-run-lifecycle-domain.mermaid` | - | M +9/-8 | M +1/-1 | M +64/-64 |
| `docs/02-architecture/mmd-diagrams/views/31-pipeline-run-lifecycle-full.mermaid` | - | M +2/-1 | M +1/-1 | M +47/-47 |
| `docs/02-architecture/mmd-diagrams/views/31-pipeline-run-lifecycle-infra.mermaid` | - | M +9/-31 | - | M +96/-96 |
| `docs/02-architecture/mmd-diagrams/views/31-pipeline-run-lifecycle-overview.mermaid` | - | M +9/-11 | M +1/-1 | M +53/-53 |
| `docs/02-architecture/mmd-diagrams/views/32-single-record-journey-dataflow.mermaid` | - | M +3/-2 | - | M +25/-25 |
| `docs/02-architecture/mmd-diagrams/views/32-single-record-journey-domain.mermaid` | - | M +6/-5 | - | M +49/-49 |
| `docs/02-architecture/mmd-diagrams/views/32-single-record-journey-full.mermaid` | - | M +18/-21 | M +6/-16 | M +60/-70 |
| `docs/02-architecture/mmd-diagrams/views/32-single-record-journey-infra.mermaid` | - | M +4/-3 | - | M +41/-41 |
| `docs/02-architecture/mmd-diagrams/views/32-single-record-journey-overview.mermaid` | - | M +5/-4 | - | M +39/-39 |
| `docs/02-architecture/mmd-diagrams/views/33-cli-run-interaction-dataflow.mermaid` | - | M +6/-8 | - | M +48/-48 |
| `docs/02-architecture/mmd-diagrams/views/33-cli-run-interaction-domain.mermaid` | - | M +5/-7 | - | M +64/-64 |
| `docs/02-architecture/mmd-diagrams/views/33-cli-run-interaction-full.mermaid` | - | M +2/-1 | M +1/-1 | M +61/-61 |
| `docs/02-architecture/mmd-diagrams/views/33-cli-run-interaction-infra.mermaid` | - | M +6/-8 | - | M +68/-68 |
| `docs/02-architecture/mmd-diagrams/views/33-cli-run-interaction-overview.mermaid` | - | M +6/-5 | - | M +53/-53 |
| `docs/02-architecture/mmd-diagrams/views/34-batch-processing-flow-dataflow.mermaid` | M +18/-17 | M +22/-23 | M +2/-18 | M +42/-58 |
| `docs/02-architecture/mmd-diagrams/views/34-batch-processing-flow-domain.mermaid` | - | M +7/-6 | - | M +59/-59 |
| `docs/02-architecture/mmd-diagrams/views/34-batch-processing-flow-full.mermaid` | - | M +2/-1 | - | M +51/-51 |
| `docs/02-architecture/mmd-diagrams/views/34-batch-processing-flow-infra.mermaid` | - | M +7/-9 | - | M +59/-59 |
| `docs/02-architecture/mmd-diagrams/views/34-batch-processing-flow-overview.mermaid` | M +21/-20 | M +25/-26 | M +2/-21 | M +48/-67 |
| `docs/02-architecture/mmd-diagrams/views/35-bootstrap-sequence-dataflow.mermaid` | M +12/-11 | M +2/-0 | M +1/-1 | M +34/-34 |
| `docs/02-architecture/mmd-diagrams/views/35-bootstrap-sequence-domain.mermaid` | M +22/-21 | M +2/-0 | M +2/-22 | M +42/-62 |
| `docs/02-architecture/mmd-diagrams/views/35-bootstrap-sequence-full.mermaid` | - | M +5/-4 | - | M +82/-82 |
| `docs/02-architecture/mmd-diagrams/views/35-bootstrap-sequence-infra.mermaid` | M +22/-21 | M +2/-0 | M +2/-22 | M +42/-62 |
| `docs/02-architecture/mmd-diagrams/views/35-bootstrap-sequence-overview.mermaid` | M +16/-15 | M +2/-0 | M +2/-16 | M +31/-45 |
| `docs/02-architecture/mmd-diagrams/views/36-architecture-principles-mindmap-dataflow.mermaid` | M +12/-11 | M +17/-21 | M +1/-1 | M +50/-50 |
| `docs/02-architecture/mmd-diagrams/views/36-architecture-principles-mindmap-domain.mermaid` | M +12/-11 | M +5/-3 | M +1/-1 | M +54/-54 |
| `docs/02-architecture/mmd-diagrams/views/36-architecture-principles-mindmap-full.mermaid` | - | M +2/-1 | - | M +84/-84 |
| `docs/02-architecture/mmd-diagrams/views/36-architecture-principles-mindmap-infra.mermaid` | M +6/-5 | M +5/-3 | - | M +42/-42 |
| `docs/02-architecture/mmd-diagrams/views/36-architecture-principles-mindmap-overview.mermaid` | - | M +6/-7 | M +3/-13 | M +50/-60 |
| `docs/02-architecture/mmd-diagrams/views/39-medallion-invariants-dataflow.mermaid` | M +10/-9 | M +11/-9 | M +1/-1 | M +30/-30 |
| `docs/02-architecture/mmd-diagrams/views/39-medallion-invariants-domain.mermaid` | M +15/-14 | M +16/-14 | M +2/-15 | M +35/-48 |
| `docs/02-architecture/mmd-diagrams/views/39-medallion-invariants-full.mermaid` | - | M +17/-25 | M +3/-13 | M +73/-83 |
| `docs/02-architecture/mmd-diagrams/views/39-medallion-invariants-infra.mermaid` | M +15/-14 | M +18/-19 | M +2/-15 | M +43/-56 |
| `docs/02-architecture/mmd-diagrams/views/39-medallion-invariants-overview.mermaid` | M +12/-11 | M +13/-11 | M +1/-1 | M +37/-37 |
| `docs/02-architecture/mmd-diagrams/views/41-error-classification-tree-dataflow.mermaid` | M +10/-9 | M +14/-15 | M +1/-1 | M +42/-42 |
| `docs/02-architecture/mmd-diagrams/views/41-error-classification-tree-domain.mermaid` | M +17/-16 | M +21/-22 | M +2/-17 | M +49/-64 |
| `docs/02-architecture/mmd-diagrams/views/41-error-classification-tree-full.mermaid` | - | M +10/-29 | - | M +131/-131 |
| `docs/02-architecture/mmd-diagrams/views/41-error-classification-tree-infra.mermaid` | M +17/-16 | M +20/-18 | M +2/-17 | M +45/-60 |
| `docs/02-architecture/mmd-diagrams/views/41-error-classification-tree-overview.mermaid` | - | M +6/-5 | - | M +38/-38 |
| `docs/02-architecture/mmd-diagrams/views/44-cross-provider-enrichment-dataflow.mermaid` | M +10/-9 | M +13/-14 | M +1/-1 | M +38/-38 |
| `docs/02-architecture/mmd-diagrams/views/44-cross-provider-enrichment-domain.mermaid` | M +17/-16 | M +4/-2 | M +2/-17 | M +45/-60 |
| `docs/02-architecture/mmd-diagrams/views/44-cross-provider-enrichment-full.mermaid` | - | M +5/-4 | M +5/-16 | M +54/-65 |
| `docs/02-architecture/mmd-diagrams/views/44-cross-provider-enrichment-infra.mermaid` | M +17/-16 | M +4/-2 | M +2/-17 | M +45/-60 |
| `docs/02-architecture/mmd-diagrams/views/44-cross-provider-enrichment-overview.mermaid` | M +11/-10 | M +4/-5 | M +1/-1 | M +43/-43 |
| `docs/02-architecture/mmd-diagrams/views/46-yaml-config-resolution-dataflow.mermaid` | M +5/-4 | M +9/-7 | - | M +32/-32 |
| `docs/02-architecture/mmd-diagrams/views/46-yaml-config-resolution-domain.mermaid` | M +5/-4 | M +5/-6 | - | M +40/-40 |
| `docs/02-architecture/mmd-diagrams/views/46-yaml-config-resolution-full.mermaid` | - | M +8/-26 | M +1/-1 | M +116/-116 |
| `docs/02-architecture/mmd-diagrams/views/46-yaml-config-resolution-infra.mermaid` | M +5/-4 | M +6/-7 | - | M +44/-44 |
| `docs/02-architecture/mmd-diagrams/views/46-yaml-config-resolution-overview.mermaid` | M +5/-4 | M +5/-3 | - | M +35/-35 |
| `docs/02-architecture/mmd-diagrams/views/48-composite-phase-lifecycle-dataflow.mermaid` | M +14/-13 | M +18/-22 | M +2/-14 | M +38/-50 |
| `docs/02-architecture/mmd-diagrams/views/48-composite-phase-lifecycle-domain.mermaid` | - | M +4/-6 | - | M +55/-55 |
| `docs/02-architecture/mmd-diagrams/views/48-composite-phase-lifecycle-full.mermaid` | - | M +2/-1 | M +1/-1 | M +112/-112 |
| `docs/02-architecture/mmd-diagrams/views/48-composite-phase-lifecycle-infra.mermaid` | - | M +5/-10 | - | M +59/-59 |
| `docs/02-architecture/mmd-diagrams/views/48-composite-phase-lifecycle-overview.mermaid` | M +15/-14 | M +4/-2 | M +2/-15 | M +38/-51 |
| `docs/02-architecture/mmd-diagrams/views/50-exception-hierarchy-dataflow.mermaid` | M +9/-8 | M +13/-11 | M +1/-1 | M +40/-40 |
| `docs/02-architecture/mmd-diagrams/views/50-exception-hierarchy-domain.mermaid` | - | M +5/-6 | M +2/-20 | M +57/-75 |
| `docs/02-architecture/mmd-diagrams/views/50-exception-hierarchy-full.mermaid` | - | M +12/-11 | M +7/-7 | M +98/-98 |
| `docs/02-architecture/mmd-diagrams/views/50-exception-hierarchy-infra.mermaid` | M +23/-22 | M +5/-6 | M +2/-23 | M +55/-76 |
| `docs/02-architecture/mmd-diagrams/views/50-exception-hierarchy-overview.mermaid` | - | M +5/-3 | M +3/-17 | M +48/-62 |
| `docs/02-architecture/mmd-diagrams/views/png/INDEX.md` | D +0/-940 | - | D +0/-940 | D +0/-940 |
| `docs/02-architecture/mmd-diagrams/views/svg/INDEX.md` | D +0/-940 | - | D +0/-940 | D +0/-940 |
| `mkdocs.yml` | M +18/-8 | - | M +0/-8 | M +0/-8 |
| `scripts/add_svg_text_fallback.py` | - | - | M +15/-9 | - |
| `scripts/check_diagram_quality_gates.py` | - | - | M +9/-3 | - |
| `scripts/extract_diagram_params.py` | - | A +2113/-0 | - | - |
| `scripts/fix_diagram_links.py` | - | - | M +35/-19 | - |
| `scripts/lint_diagrams.py` | M +27/-0 | - | M +71/-12 | M +71/-12 |
| `scripts/reindex_linkstyles.py` | - | - | - | A +180/-0 |
| `scripts/uniform_diagram_sizes.py` | - | - | M +1/-1 | - |
