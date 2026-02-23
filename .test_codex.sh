#!/bin/bash
KEY=$(cat /tmp/key.txt)
# Test Codex-specific endpoint
HTTP_CODE=$(curl -s -o /tmp/codex_resp.txt -w "%{http_code}" \
  https://api.openai.com/v1/responses \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","input":"say hi","max_output_tokens":10}')
echo "HTTP: $HTTP_CODE"
head -c 300 /tmp/codex_resp.txt
echo
