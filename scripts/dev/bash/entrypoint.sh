#!/bin/bash
set -e

echo "Starting Cloudflare WARP daemon..."

# Start WARP daemon and keep it running
exec warp-svc
