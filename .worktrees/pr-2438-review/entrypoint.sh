#!/bin/bash

# Start the WARP service daemon
/bin/warp-svc &
WARP_PID=$!

# Wait for daemon to start
sleep 5

# Register device and accept ToS
warp-cli registration new -- --accept-tos

# Connect
warp-cli connect

# Keep container running
tail -f /dev/null
