#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME}/.local/bin"
curl -fsSL https://cli.coderabbit.ai/install.sh -o /tmp/coderabbit-install.sh
# Basic content checks
grep -Eq 'coderabbit|CodeRabbit' /tmp/coderabbit-install.sh
CI=1 bash /tmp/coderabbit-install.sh
export PATH="${HOME}/.local/bin:${PATH}"
command -v coderabbit
coderabbit --version
coderabbit auth status || true
