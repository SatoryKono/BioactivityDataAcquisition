#!/usr/bin/env bash
export FOO_API_KEY=synthetic
export OPENAI_API_KEY=synthetic
export OPENROUTER_API_KEY=other
echo "FOO=$FOO_API_KEY"
echo "OAI=$OPENAI_API_KEY"
echo "OR=$OPENROUTER_API_KEY"
echo "--- env ---"
env | grep -E 'FOO|OPEN' || true
echo "--- declare ---"
declare -p OPENAI_API_KEY FOO_API_KEY OPENROUTER_API_KEY || true
