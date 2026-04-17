---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# BioETL Kubernetes Deployment Guide

> **Status:** Internal / Extended document (experimental deployment profile, non-normative for default operations).
> **Note (ADR-010):** BioETL primary deployment model is **Local-Only** (file-based,
> no Docker/Redis in runtime). See [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md).
> This Kubernetes guide is provided for **advanced/experimental use only** and is
> not the recommended deployment strategy.
> It is outside standard operational support runbooks and release flow.
> Placement note: this page lives under [Deployment & Tooling Extras](README.md),
> not under the standard operations/runbook path.

## Overview

This guide covers deploying BioETL to Kubernetes with monitoring via Prometheus and Grafana.

### Manifests Created

1. **k8s-deployment.yaml** - Core BioETL application with ConfigMap and Secrets
2. **k8s-monitoring.yaml** - Prometheus and Grafana monitoring stack
3. **k8s-networking.yaml** - Ingress, autoscaling, network policies, and quotas

---

## Prerequisites

- Kubernetes 1.20+ cluster running (EKS, GKE, AKS, or local minikube/kind)
- `kubectl` configured to access your cluster
- A container registry (Docker Hub, ECR, GCR, etc.)
- Storage provisioner (local-path, EBS, persistent volumes, etc.)
- (Optional) Ingress controller installed (nginx-ingress, traefik, etc.)
- (Optional) cert-manager for HTTPS/TLS

### Verify Prerequisites

```bash
# Check kubectl connection
kubectl cluster-info

# Verify storage class exists
kubectl get storageclass

# List default namespaces
kubectl get namespaces
```

---

## Step 1: Build and Push Container Image

First, create an optimized Dockerfile for Kubernetes (not the Cloudflare WARP one):

```bash
# Build the BioETL image
docker build -t bioetl:REPLACE_IMAGE_TAG .

# Tag for your registry (example: Docker Hub)
docker tag bioetl:REPLACE_IMAGE_TAG your-registry/bioetl:REPLACE_IMAGE_TAG

# Push to registry
docker push your-registry/bioetl:REPLACE_IMAGE_TAG
```

### Update Manifests

Edit `k8s-deployment.yaml` and change the image reference:

```yaml
image: your-registry/bioetl:REPLACE_IMAGE_TAG  # ← Update this line
imagePullPolicy: Always
```

Use the same image tag consistently in `k8s-deployment.yaml` and, if you use
the helper shell flow, set matching overrides before running it:

```bash
BIOETL_IMAGE_REGISTRY=your-registry BIOETL_IMAGE_TAG=REPLACE_IMAGE_TAG \
  scripts/ops/runtime/deploy/deploy-bioetl.sh deploy dev
```

This extended deployment subtree is still maintained as experimental material.

If using private registry, create a secret:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=your-registry \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email@example.com

# Add to deployment:
# imagePullSecrets:
# - name: regcred
```

---

## Step 2: Configure Secrets

Create and update secrets with your actual API keys:

```bash
# Create the bioetl-secrets Secret
kubectl apply -f k8s-deployment.yaml

# Edit the secret
kubectl edit secret bioetl-secrets

# Or use sealed-secrets for GitOps-friendly encryption:
# https://github.com/bitnami-labs/sealed-secrets
```

**Critical Secrets to Update:**

```yaml
BIOETL_PII_SALT_CURRENT: "YOUR-RANDOM-64-CHAR-STRING"
BIOETL_UNIPROT_API_KEY: "your-actual-key"
BIOETL_OPENALEX_EMAIL: "your@email.com"
BIOETL_SEMANTICSCHOLAR_API_KEY: "your-actual-key"
BIOETL_PUBMED_API_KEY: "your-actual-key"
BIOETL_PUBMED_EMAIL: "your@email.com"
BIOETL_CROSSREF_EMAIL: "your@email.com"
```

---

## Step 3: Create Storage Classes (if needed)

For different cloud providers:

### AWS EKS

```bash
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
EOF
```

### Google GKE

```bash
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-ssd
  replication-type: regional-pd
EOF
```

### Azure AKS

```bash
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/azure-disk
parameters:
  storageaccounttype: Premium-LRS
  kind: Managed
EOF
```

Then update manifests to use it:

```yaml
storageClassName: fast-ssd
```

---

## Step 4: Deploy BioETL Application

```bash
# Deploy core application
kubectl apply -f k8s-deployment.yaml

# Verify deployment
kubectl get deployments
kubectl get pods
kubectl get pvc

# Check pod status
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Wait for Ready State

```bash
# Watch rollout
kubectl rollout status deployment/bioetl

# Check readiness
kubectl get pods -l app=bioetl -w
```

---

## Step 5: Deploy Monitoring Stack

```bash
# Deploy Prometheus and Grafana
kubectl apply -f k8s-monitoring.yaml

# Verify monitoring deployment
kubectl get deployments prometheus grafana
kubectl get svc prometheus grafana

# Check logs
kubectl logs -f deployment/prometheus
kubectl logs -f deployment/grafana
```

---

## Step 6: Configure Ingress & Networking

### Option A: Using NGINX Ingress (Recommended)

Install NGINX ingress controller:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

Update hostnames in `k8s-networking.yaml`:

```yaml
- host: bioetl.your-domain.com
  http:
    paths:
    - path: /metrics
      backend:
        service:
          name: bioetl
          port:
            number: 8000

- host: grafana.your-domain.com
  http:
    paths:
    - path: /
      backend:
        service:
          name: grafana
          port:
            number: 3000
```

Deploy ingress:

```bash
kubectl apply -f k8s-networking.yaml
```

Get ingress IP:

```bash
kubectl get ingress bioetl-ingress
```

### Option B: Port-Forward for Testing (Development)

```bash
# Forward BioETL metrics
kubectl port-forward svc/bioetl 8000:8000 &

# Forward Grafana
kubectl port-forward svc/grafana 3000:3000 &

# Access at http://localhost:3000 (Grafana) and http://localhost:8000/metrics (BioETL)
```

---

## Step 7: Verify Deployment

```bash
# Check all resources
kubectl get all

# Test BioETL metrics endpoint
kubectl port-forward svc/bioetl 8000:8000
curl http://localhost:8000/metrics

# Test Prometheus scrape
kubectl port-forward svc/prometheus 9090:9090
# Open http://localhost:9090 → Status → Targets

# Check Grafana health
kubectl port-forward svc/grafana 3000:3000
# Open http://localhost:3000 (login: admin / password from secret)
```

---

## Scaling & Updates

### Horizontal Pod Autoscaling

The HPA in `k8s-networking.yaml` automatically scales based on CPU/memory:

```bash
kubectl get hpa
kubectl describe hpa bioetl-hpa
```

Manual scaling:

```bash
# Scale to 3 replicas
kubectl scale deployment bioetl --replicas=3

# Check status
kubectl get deployment bioetl
```

### Rolling Updates

Update the image:

```bash
kubectl set image deployment/bioetl \
  bioetl=your-registry/bioetl:REPLACE_IMAGE_TAG \
  --record

# Watch rollout
kubectl rollout status deployment/bioetl

# Rollback if needed
kubectl rollout undo deployment/bioetl
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# View logs
kubectl logs <pod-name>

# Check resource availability
kubectl top nodes
kubectl top pods
```

### Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc
kubectl describe pvc bioetl-data

# Check PV
kubectl get pv
```

### Network Connectivity

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup bioetl

# Test service connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- wget -O- http://bioetl:8000/metrics
```

### Monitoring Issues

```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090
# Navigate to http://localhost:9090/targets

# Check Grafana datasources
kubectl port-forward svc/grafana 3000:3000
# Settings → Data Sources
```

---

## Backup & Recovery

### Backup Persistent Data

```bash
# Create a snapshot of data PVC (EBS example)
aws ec2 create-snapshot \
  --volume-id vol-xxxxx \
  --description "BioETL data backup"

# For file-based backup
kubectl exec deployment/bioetl -- tar czf /tmp/backup.tar.gz /data
kubectl cp default/$(kubectl get pod -l app=bioetl -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore from Backup

```bash
# Delete old PVC
kubectl delete pvc bioetl-data

# Create new PVC
kubectl apply -f k8s-deployment.yaml

# Restore data
kubectl cp ./backup.tar.gz default/$(kubectl get pod -l app=bioetl -o jsonpath='{.items[0].metadata.name}'):/tmp/
kubectl exec deployment/bioetl -- tar xzf /tmp/backup.tar.gz -C /
```

---

## Production Checklist

- [ ] Update all image references to your registry
- [ ] Configure all API keys in bioetl-secrets
- [ ] Set resource requests/limits appropriately for your workload
- [ ] Configure storage class and PVC sizes based on data volume
- [ ] Update Ingress hostnames and enable TLS
- [ ] Install and configure ingress controller
- [ ] Set up cert-manager for certificate management
- [ ] Configure networking policies
- [ ] Set up monitoring dashboards in Grafana
- [ ] Configure alerting rules in Prometheus
- [ ] Test backup/recovery procedures
- [ ] Document runbooks for common operations
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure RBAC policies for team access
- [ ] Enable pod security policies
- [ ] Set up CI/CD pipeline for automated deployments

---

## Environment-Specific Configuration

### Development Environment

```yaml
# Reduce replicas and resources
replicas: 1
resources:
  requests:
    cpu: 100m
    memory: 256Mi
```

### Staging Environment

```yaml
replicas: 2
resources:
  requests:
    cpu: 500m
    memory: 1Gi
```

### Production Environment

```yaml
replicas: 3
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
```

---

## References

- [Kubernetes Official Docs](https://kubernetes.io/docs/)
- [Kubernetes Deployment Guide](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
- [Grafana Helm Chart](https://grafana.com/grafana/helm-charts/)
- Docker Documentation: https://docs.docker.com/reference/cli/docker/container/run/
