#!/bin/bash
KEY=$(cat /tmp/key.txt)
echo "Key length: ${#KEY}"
echo "Key prefix: ${KEY:0:10}"
HTTP_CODE=$(curl -s -o /tmp/api_resp.txt -w "%{http_code}" \
  https://api.openai.com/v1/models \
  -H "Authorization: Bearer ${KEY}")
echo "HTTP: $HTTP_CODE"
head -c 200 /tmp/api_resp.txt
echo
