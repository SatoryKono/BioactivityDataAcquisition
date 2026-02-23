#!/bin/bash
export HOME=/root
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

# Ensure DNS is cached
grep -q "api.openai.com" /etc/hosts || bash .setup_wsl_codex.sh

# Run a meaningful Codex test
timeout 90 codex exec --full-auto --json "List the Python source files in src/bioetl/domain/ and briefly describe what each does" 2>&1
echo "EXIT: $?"
