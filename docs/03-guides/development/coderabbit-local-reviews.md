# Local CodeRabbit review launcher

Manual multi-topic CodeRabbit reviews for local engineering work.

## Launcher

- `scripts/ops/run-coderabbit-reviews.sh` — bounded manual launcher for sequential
  CodeRabbit review topics (`architecture-boundaries`, `adapters-resilience`,
  `pipelines-determinism`, `security`, `contracts-docs-drift`).

Requires `CODERABBIT_API_KEY`. Prefer CI CodeRabbit workflow for merge gates.


## WSL residual waves (env / API auth)

Use this path for **scoped residual CLI campaigns** (epic #7688, issue #7716).
PR reviews still use the CodeRabbit **GitHub App** + `.coderabbit.yaml`.

### Prerequisites

1. WSL with CodeRabbit CLI (`coderabbit --version`, currently 0.7.x).
2. API key available as env var **or** prior login cache:
   - Env: `export CODERABBIT_API_KEY=...` (from secret store; never commit).
   - Cache: `~/.coderabbit/auth.json` after `coderabbit auth login`.
3. Repository checkout visible from WSL with clean git status.
4. Leaf scopes from `reports/quality/coderabbit/YYYYMMDD/01-scope-matrix.md` (≤300 files).

### Auth from host env into WSL

```bash
# Host has CODERABBIT_API_KEY exported (do not echo the value)
wsl -e bash -lc 'export PATH="$HOME/.local/bin:$PATH"
  export CODERABBIT_API_KEY="$CODERABBIT_API_KEY"
  coderabbit auth login --api-key "$CODERABBIT_API_KEY"
  coderabbit auth status'
```

If `coderabbit auth status` already shows `Account: API key`, re-login is optional.

### Scoped review examples

```bash
wsl -e bash -lc 'export PATH="$HOME/.local/bin:$PATH"
  repo_root="$(git rev-parse --show-toplevel)"
  cd "$repo_root"
  coderabbit review --base main --dir src/bioetl/composition --plain     | tee reports/quality/coderabbit/$(date -u +%Y%m%d)/review_S09-composition.log'
```

Half/residual scopes (S12 halves, residual domain): filter `git ls-files` and use
sparse-checkout, or review with `--dir` only when the leaf is a real directory.

### Multi-topic launcher

```bash
export CODERABBIT_API_KEY=...   # if not using auth cache
./scripts/ops/run-coderabbit-reviews.sh architecture-boundaries --base origin/main
./scripts/ops/run-coderabbit-reviews.sh all --coderabbit-only --base origin/main
```

### CI note

`.github/workflows/coderabbit.yml` runs only on trusted `push` / `workflow_dispatch`.
If Actions secret `CODERABBIT_API_KEY` is unset, the job **succeeds but skips** CLI.
Track repo secret setup under #7698.

### Artifacts

Write logs under allowlisted `reports/quality/coderabbit/**` (see `.gitignore`).
Do not raise tech-debt budgets to silence findings.
