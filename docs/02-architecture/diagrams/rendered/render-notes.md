# Render Notes

- Mermaid CLI version in environment: `mmdc 11.12.0`.
- Browser runtime installed via Puppeteer cache at `/tmp/puppeteer`.
- 5 diagrams were copied from canonical pre-rendered PNGs because `mmdc` fails with `svg element not in render tree` on these sources in this environment.
- Affected files:
  - 04-domain-layer-class-diagram-full.mermaid
  - 06-application-layer-class-diagram-full.mermaid
  - 10-infrastructure-layer-class-diagram-full.mermaid
  - 33-cli-run-interaction-full.mermaid
  - 34-batch-processing-flow-full.mermaid
