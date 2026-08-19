#!/bin/bash
# BioETL Kubernetes Deployment Script.
#
# Provides quick-start deployment capabilities for BioETL on Kubernetes.
# Supports multiple environments and deployment actions with proper validation.
#
# Usage:
#   bash scripts/ops/runtime/deploy/deploy-bioetl.sh [action] [environment]
#
# Actions:
#   deploy    Deploy application (create namespace + apply manifests)
#   update    Update container image
#   delete    Delete deployment and namespace
#   status    Show deployment status
#   logs      Stream logs from pods
#   port-forward   Forward port to service
#
# Environments:
#   dev       Development environment
#   staging   Staging environment
#   prod      Production environment
#
# Examples:
#   # Deploy to development
#   bash scripts/ops/runtime/deploy/deploy-bioetl.sh deploy dev
#
#   # Update staging deployment
#   bash scripts/ops/runtime/deploy/deploy-bioetl.sh update staging
#
#   # Check production status
#   bash scripts/ops/runtime/deploy/deploy-bioetl.sh status prod
#
#   # Stream logs from bioetl pods
#   bash scripts/ops/runtime/deploy/deploy-bioetl.sh logs dev bioetl
#
# Environment Variables:
#   BIOETL_IMAGE_REGISTRY    Container registry (default: your-registry)
#   BIOETL_IMAGE_TAG         Image tag (default: 6.1.0)
#
# Dependencies:
#   - kubectl (Kubernetes CLI)
#   - k8s-deployment.yaml (Kubernetes deployment manifest)
#   - k8s-monitoring.yaml (Kubernetes monitoring manifest)
#   - k8s-networking.yaml (Kubernetes networking manifest)
#
# See Also:
#   - Kubernetes deployment documentation
#   - Infrastructure deployment guides

set -euo pipefail

ACTION=${1:-deploy}
ENV=${2:-dev}
NAMESPACE="bioetl-${ENV}"

# Configuration
REGISTRY=${BIOETL_IMAGE_REGISTRY:-your-registry}
IMAGE_TAG=${BIOETL_IMAGE_TAG:-6.1.0}

# Kubernetes manifests live under docs/05-operations/deployment/ (repo-relative),
# not at the repository root. Resolve the directory from this script location so
# the deploy/update paths work regardless of the caller's CWD. Override with
# BIOETL_K8S_MANIFEST_DIR when manifests are staged elsewhere.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"
CONFIG_DIR="${BIOETL_K8S_MANIFEST_DIR:-${REPO_ROOT}/docs/05-operations/deployment}"

# Set DRY_RUN=1 to validate/plan without mutating the cluster.
DRY_RUN="${DRY_RUN:-0}"

echo "🚀 BioETL Kubernetes Deployment Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Action: $ACTION"
echo "Environment: $ENV"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "Image tag: $IMAGE_TAG"
echo ""

# Fail fast when the expected manifests are missing under CONFIG_DIR.
require_manifests() {
  local missing=0 manifest
  for manifest in k8s-deployment.yaml k8s-monitoring.yaml k8s-networking.yaml; do
    if [[ ! -f "${CONFIG_DIR}/${manifest}" ]]; then
      echo "❌ Missing manifest: ${CONFIG_DIR}/${manifest}" >&2
      missing=1
    fi
  done
  if [[ "${missing}" -ne 0 ]]; then
    echo "   Set BIOETL_K8S_MANIFEST_DIR to the directory containing the k8s-*.yaml files." >&2
    return 1
  fi
  return 0
}

# Create namespace if it doesn't exist
create_namespace() {
  if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "📁 Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
  fi
  return 0
}

# Deploy application
deploy() {
  echo "📦 Starting deployment..."

  require_manifests

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "🧪 DRY_RUN=1: client-side manifest validation only (no cluster changes)."
    kubectl apply -n "$NAMESPACE" --dry-run=client \
      -f "$CONFIG_DIR/k8s-deployment.yaml" \
      -f "$CONFIG_DIR/k8s-monitoring.yaml" \
      -f "$CONFIG_DIR/k8s-networking.yaml"
    echo "✅ Dry-run validation complete."
    return 0
  fi

  create_namespace

  # Render the pinned image into a temp copy so the tracked manifest under
  # docs/** is never mutated in place (keeps the deploy idempotent + clean tree).
  local rendered
  rendered="$(mktemp)"
  sed "s|^[[:space:]]*image: .*|        image: $REGISTRY/bioetl:$IMAGE_TAG  # Updated by deploy-bioetl.sh|g" \
    "$CONFIG_DIR/k8s-deployment.yaml" > "$rendered"

  echo "📋 Applying manifests..."
  kubectl apply -n "$NAMESPACE" -f "$rendered"
  kubectl apply -n "$NAMESPACE" -f "$CONFIG_DIR/k8s-monitoring.yaml"
  kubectl apply -n "$NAMESPACE" -f "$CONFIG_DIR/k8s-networking.yaml"
  rm -f "$rendered"

  echo "⏳ Waiting for deployment to be ready..."
  kubectl rollout status deployment/bioetl -n "$NAMESPACE" --timeout=5m

  echo "✅ Deployment complete!"
  echo ""
  echo "📊 Access points:"
  # Cluster-internal service DNS only (not a public clear-text edge).
  echo "  - Metrics: http://bioetl.${ENV}.internal:8000/metrics"  # NOSONAR - internal cluster DNS
  echo "  - Prometheus: kubectl port-forward -n $NAMESPACE svc/prometheus 9090:9090"
  echo "  - Grafana: kubectl port-forward -n $NAMESPACE svc/grafana 3000:3000"
  return 0
}

# Update image
update() {
  echo "🔄 Updating image..."

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "🧪 DRY_RUN=1: would set image to $REGISTRY/bioetl:$IMAGE_TAG (skipped)."
    return 0
  fi

  # --record is deprecated; record the change cause via an explicit annotation.
  kubectl set image deployment/bioetl \
    -n "$NAMESPACE" \
    bioetl="$REGISTRY/bioetl:$IMAGE_TAG"
  kubectl annotate deployment/bioetl -n "$NAMESPACE" \
    "kubernetes.io/change-cause=deploy-bioetl.sh update ${REGISTRY}/bioetl:${IMAGE_TAG}" \
    --overwrite

  echo "⏳ Waiting for rollout..."
  kubectl rollout status deployment/bioetl -n "$NAMESPACE" --timeout=5m

  echo "✅ Update complete!"
  return 0
}

# Delete deployment
delete() {
  echo "🗑️  Deleting deployment (namespace: $NAMESPACE)..."

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "🧪 DRY_RUN=1: would delete namespace $NAMESPACE (skipped)."
    return 0
  fi

  # Extra gate for production: refuse unless explicitly acknowledged.
  if [[ "$ENV" == "prod" && "${BIOETL_CONFIRM_PROD:-0}" != "1" ]]; then
    echo "❌ Refusing to delete a prod namespace without BIOETL_CONFIRM_PROD=1." >&2
    return 1
  fi

  # Require the exact namespace name to avoid accidental data loss.
  local reply
  read -r -p "Type the namespace to confirm deletion (${NAMESPACE}): " reply
  echo
  if [[ "$reply" == "$NAMESPACE" ]]; then
    kubectl delete namespace "$NAMESPACE"
    echo "✅ Deleted!"
  else
    echo "❌ Cancelled (input did not match ${NAMESPACE})."
  fi
  return 0
}

# Show status
status() {
  echo "📊 Deployment Status"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  echo ""
  echo "🔹 Pods:"
  kubectl get pods -n "$NAMESPACE" -l app=bioetl

  echo ""
  echo "🔹 Deployments:"
  kubectl get deployments -n "$NAMESPACE"

  echo ""
  echo "🔹 Services:"
  kubectl get svc -n "$NAMESPACE"

  echo ""
  echo "🔹 Persistent Volumes:"
  kubectl get pvc -n "$NAMESPACE"

  echo ""
  echo "🔹 Resources:"
  kubectl top nodes
  kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo "  (Metrics not available yet)"

  echo ""
  echo "🔹 Recent Events:"
  kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -5
  return 0
}

# Show logs
logs() {
  local component="${3:-bioetl}"
  echo "📝 Logs for $component in $NAMESPACE"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ "$component" = "all" ]]; then
    kubectl logs -n "$NAMESPACE" -l app=bioetl -f --max-log-requests=10
  else
    kubectl logs -n "$NAMESPACE" -l app="$component" -f
  fi
  return 0
}

# Port forwarding
port_forward() {
  local service="${3:-}"
  local local_port="${4:-}"
  local remote_port="${5:-}"

  if [[ -z "$service" || -z "$local_port" || -z "$remote_port" ]]; then
    echo "❌ Usage: deploy-bioetl.sh port-forward <env> <service> <local_port> <remote_port>" >&2
    return 1
  fi

  echo "🔗 Port forwarding $service..."
  echo "   Local: $local_port → Remote: $remote_port"

  kubectl port-forward -n "$NAMESPACE" "svc/$service" "$local_port:$remote_port"
  return 0
}

# Execute based on action
case "$ACTION" in
  deploy)
    deploy
    ;;
  update)
    update
    ;;
  delete)
    delete
    ;;
  status)
    status
    ;;
  logs)
    logs "$@"
    ;;
  port-forward)
    port_forward "$@"
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo ""
    echo "Available actions:"
    echo "  deploy         - Deploy application (create namespace + apply manifests)"
    echo "  update         - Update container image"
    echo "  delete         - Delete deployment and namespace"
    echo "  status         - Show deployment status"
    echo "  logs           - Stream logs from pods"
    echo "  port-forward   - Forward port to service"
    echo ""
    echo "Usage examples:"
    echo "  ./deploy-bioetl.sh deploy dev"
    echo "  ./deploy-bioetl.sh status staging"
    echo "  ./deploy-bioetl.sh logs prod bioetl"
    echo "  ./deploy-bioetl.sh port-forward prod grafana 3000 3000"
    echo ""
    echo "Optional environment overrides:"
    echo "  BIOETL_IMAGE_REGISTRY=my-registry"
    echo "  BIOETL_IMAGE_TAG=6.1.0"
    exit 1
    ;;
esac
