#!/bin/bash
# Start Neo4j audit instance for live validation (WSL/Linux version)
# Usage: ./scripts/ops/runtime/neo4j/start-neo4j-audit.sh [--stop|--logs]

set -e

COMPOSE_FILE="docker-compose.neo4j-audit.yml"
CONTAINER_NAME="bioetl-neo4j-audit"

case "${1:-}" in
  --stop)
    echo "Stopping audit instance..."
    docker compose -f "$COMPOSE_FILE" down
    echo "Stopped."
    exit 0
    ;;
  --logs)
    echo "Showing logs..."
    docker logs "$CONTAINER_NAME" --tail 50 -f
    exit 0
    ;;
  *)
    echo "Starting Neo4j audit instance (1024m heap)..."
    docker compose -f "$COMPOSE_FILE" up -d

    echo "Waiting for startup (45 seconds)..."
    sleep 45

    if docker ps | grep -q "$CONTAINER_NAME.*healthy"; then
      echo "✅ Audit instance started successfully"
      echo ""
      echo "Connection details:"
      echo "  HTTP:  http://localhost:7475"
      echo "  Bolt:  bolt://localhost:7688"
      echo "  Auth:  neo4j / audit_secure_password"
      echo ""
      echo "To run live validation:"
      echo "  export LIVE_AUDIT_MODE=1"
      echo "  live --apply --only-complexity-layer --batch-size 5"
      echo ""
      echo "To view logs:"
      echo "  ./scripts/ops/runtime/neo4j/start-neo4j-audit.sh --logs"
      echo ""
      echo "To stop:"
      echo "  ./scripts/ops/runtime/neo4j/start-neo4j-audit.sh --stop"
    else
      echo "❌ Instance failed to start. Check logs:"
      docker logs "$CONTAINER_NAME" | tail -20
      exit 1
    fi
    ;;
esac
