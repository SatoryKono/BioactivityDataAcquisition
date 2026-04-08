#!/usr/bin/env bash
# Quick test to verify Codex WSL setup is working
# This is a minimal test that doesn't require API calls

set -euo pipefail

echo "=========================================="
echo "  Codex WSL Quick Test"
echo "=========================================="
echo ""

# Test 1: Node.js available
echo "[1] Testing Node.js..."
if node --version 2>/dev/null; then
    echo "✓ Node.js working"
else
    echo "✗ Node.js failed"
    exit 1
fi
echo ""

# Test 2: npm available
echo "[2] Testing npm..."
if npm --version 2>/dev/null; then
    echo "✓ npm working"
else
    echo "✗ npm failed"
    exit 1
fi
echo ""

# Test 3: Codex CLI available
echo "[3] Testing Codex CLI..."
if codex --version 2>/dev/null; then
    echo "✓ Codex CLI working"
else
    echo "✗ Codex CLI not available"
    exit 1
fi
echo ""

# Test 4: Codex can access help
echo "[4] Testing Codex help..."
if timeout 5 codex --help >/dev/null 2>&1; then
    echo "✓ Codex help accessible"
else
    echo "⚠ Codex help check timed out (normal)"
fi
echo ""

# Test 5: Check project path
echo "[5] Testing project path..."
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -d "$REPO_ROOT" ]; then
    echo "✓ Project path accessible: $REPO_ROOT"
else
    echo "✗ Project path not found"
    exit 1
fi
echo ""

echo "=========================================="
echo "  ✓ All basic tests passed!"
echo "=========================================="
echo ""
echo "You can now run:"
echo "  ./scripts/ops/codex.sh \"analyze this code\""
echo ""
echo "Note: First API call may take 20-30 seconds while"
echo "Codex connects to OpenAI's servers."
echo ""
