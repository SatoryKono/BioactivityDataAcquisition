#!/bin/bash
export OPENAI_API_KEY=$(cat /tmp/key.txt)
echo "Key: ${#OPENAI_API_KEY} chars"

# Use netrc approach
echo "machine api.openai.com" > /tmp/.netrc
echo "login apikey" >> /tmp/.netrc
echo "password $OPENAI_API_KEY" >> /tmp/.netrc

# Or use env var directly in header
curl -vsk --connect-timeout 15 --max-time 30 \
  "https://api.openai.com/v1/models" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" 2>&1 | tail -30
