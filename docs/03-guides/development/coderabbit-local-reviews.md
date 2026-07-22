# Local CodeRabbit review launcher

Manual multi-topic CodeRabbit reviews for local engineering work.

## Launcher

- `scripts/ops/run-coderabbit-reviews.sh` — bounded manual launcher for sequential
  CodeRabbit review topics (`architecture-boundaries`, `adapters-resilience`,
  `pipelines-determinism`, `security`, `contracts-docs-drift`).

Requires `CODERABBIT_API_KEY`. Prefer CI CodeRabbit workflow for merge gates.
