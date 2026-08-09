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

set -e

ACTION=${1:-deploy}
ENV=${2:-dev}
NAMESPACE="bioetl-${ENV}"

# Configuration
REGISTRY=${BIOETL_IMAGE_REGISTRY:-your-registry}
IMAGE_TAG=${BIOETL_IMAGE_TAG:-6.1.0}
CONFIG_DIR="."

echo "🚀 BioETL Kubernetes Deployment Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Action: $ACTION"
echo "Environment: $ENV"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "Image tag: $IMAGE_TAG"
echo ""

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

  create_namespace

  # Update image reference in manifests
  sed -i.bak "s|^[[:space:]]*image: .*|        image: $REGISTRY/bioetl:$IMAGE_TAG  # Updated by deploy-bioetl.sh|g" "$CONFIG_DIR/k8s-deployment.yaml"

  echo "📋 Applying manifests..."
  kubectl apply -n "$NAMESPACE" -f "$CONFIG_DIR/k8s-deployment.yaml"
  kubectl apply -n "$NAMESPACE" -f "$CONFIG_DIR/k8s-monitoring.yaml"
  kubectl apply -n "$NAMESPACE" -f "$CONFIG_DIR/k8s-networking.yaml"

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

  kubectl set image deployment/bioetl \
    -n "$NAMESPACE" \
    bioetl="$REGISTRY/bioetl:$IMAGE_TAG" \
    --record

  echo "⏳ Waiting for rollout..."
  kubectl rollout status deployment/bioetl -n "$NAMESPACE" --timeout=5m

  echo "✅ Update complete!"
  return 0
}

# Delete deployment
delete() {
  echo "🗑️  Deleting deployment..."

  read -p "Are you sure? (yes/no) " -n 3 -r
  echo
  if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    kubectl delete namespace "$NAMESPACE"
    echo "✅ Deleted!"
  else
    echo "❌ Cancelled."
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
  local service="$3"
  local local_port="$4"
  local remote_port="$5"

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
