#!/bin/bash
# Codex wrapper with fixed PATH to avoid .local/bin/env issues

# Set clean PATH without problematic directories
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Run codex with original arguments
/usr/local/bin/codex "$@"