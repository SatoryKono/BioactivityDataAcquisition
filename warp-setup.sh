#!/bin/bash

# WARP Container Setup - Route traffic through Cloudflare WARP

echo "=== Cloudflare WARP Container Setup ==="
echo ""

# Option 1: Using the existing WARP container
echo "Option 1: Using existing WARP daemon container"
echo "Status of cloudflare-warp container:"
docker ps -a --filter "name=cloudflare-warp" --format "table {{.Names}}\t{{.Status}}"
echo ""

# Option 2: Check WARP connection status
echo "Option 2: Check WARP status"
docker exec cloudflare-warp warp-cli status 2>/dev/null || echo "Cannot check status - daemon may still be initializing"
echo ""

# Option 3: Start an app using WARP
echo "Option 3: Run a test command through WARP"
echo "Example: curl through WARP"
echo "Command: docker exec cloudflare-warp curl -I https://www.cloudflare.com"
echo ""

# Option 4: Route container traffic via WARP
echo "Option 4: Advanced setup - Route container via sidecar"
echo "Start with: docker compose -f docker-compose-warp.yml up -d"
echo ""

echo "=== WARP Configuration ==="
echo "WARP Status Command:"
echo "  docker exec cloudflare-warp warp-cli status"
echo ""
echo "WARP Proxy Mode:"
echo "  docker exec cloudflare-warp warp-cli set-mode proxy"
echo ""
echo "Connect/Disconnect WARP:"
echo "  docker exec cloudflare-warp warp-cli connect"
echo "  docker exec cloudflare-warp warp-cli disconnect"
echo ""
echo "Test connection (from host):"
echo "  curl -I https://www.cloudflare.com/cdn-cgi/trace"
echo ""
