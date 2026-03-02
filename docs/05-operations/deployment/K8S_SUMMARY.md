# BioETL Kubernetes Manifests - Summary

> **Note (ADR-010):** BioETL primary deployment model is **Local-Only** (file-based,
> no Docker/Redis in runtime). See [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md).
> This Kubernetes material is provided for **advanced/experimental use only** and is
> not the recommended deployment strategy.

## Files Generated

### Core Manifests

1. **k8s-deployment.yaml** (5.4 KB)
   - Deployment: BioETL application pod with 1 replica, resource limits, probes
   - Service: ClusterIP for metrics endpoint
   - PersistentVolumeClaim: 50GB data storage
   - ConfigMap: Environment variables for pipeline configuration
   - Secret: API keys and credentials
   - ServiceAccount + RBAC: Pod access control

2. **k8s-monitoring.yaml** (5.8 KB)
   - Prometheus Deployment: Time-series metrics database
   - Prometheus Service: Exposes metrics scraping
   - Grafana Deployment: Visualization and dashboards
   - Grafana Service: LoadBalancer for external access
   - ConfigMaps: Prometheus scrape config, Grafana datasources
   - Secret: Grafana admin credentials
   - PersistentVolumeClaims: Storage for both

3. **k8s-networking.yaml** (2.8 KB)
   - Ingress: HTTPS/TLS routing for bioetl.example.com and grafana.example.com
   - HorizontalPodAutoscaler: Auto-scales 1-5 replicas on CPU/memory
   - PodDisruptionBudget: Maintains availability during cluster maintenance
   - NetworkPolicy: Restricts ingress/egress traffic
   - ResourceQuota: Namespace resource limits

### Documentation & Scripts

4. **DEPLOYMENT-GUIDE.md** (9.5 KB)
   - Step-by-step deployment instructions
   - Prerequisites and verification
   - Image building and registry setup
   - Secrets management
   - Storage class configuration (AWS/GCP/Azure)
   - Ingress setup
   - Verification procedures
   - Scaling and updates
   - Troubleshooting guide
   - Backup/recovery procedures
   - Production checklist

5. **deploy-bioetl.sh** (4.7 KB)
   - Automation script for common operations
   - Commands: deploy, update, delete, status, logs, port-forward

---

## Quick Deployment

### 1. Prepare

```bash
# Update image registry in k8s-deployment.yaml
sed -i 's|image: bioetl:6.0.0|image: YOUR-REGISTRY/bioetl:6.0.0|g' k8s-deployment.yaml

# Build and push container
docker build -t YOUR-REGISTRY/bioetl:6.0.0 .
docker push YOUR-REGISTRY/bioetl:6.0.0
```

### 2. Deploy

```bash
# Option A: Automated script
chmod +x deploy-bioetl.sh
./deploy-bioetl.sh deploy dev

# Option B: Manual kubectl
kubectl create namespace bioetl-dev
kubectl apply -n bioetl-dev -f k8s-deployment.yaml
kubectl apply -n bioetl-dev -f k8s-monitoring.yaml
kubectl apply -n bioetl-dev -f k8s-networking.yaml
```

### 3. Verify

```bash
# Check pods
kubectl get pods -n bioetl-dev

# View logs
kubectl logs -n bioetl-dev -l app=bioetl -f

# Port forward for local testing
kubectl port-forward -n bioetl-dev svc/bioetl 8000:8000
curl http://localhost:8000/metrics
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Namespace: bioetl-{dev,staging,prod}                 │   │
│  │                                                       │   │
│  │  ┌─────────────────┐         ┌──────────────────┐   │   │
│  │  │  BioETL Pod     │         │ Prometheus Pod   │   │   │
│  │  │  (Deployment)   │         │                  │   │   │
│  │  │                 │────────→│ Scrapes metrics  │   │   │
│  │  │ Python app      │         │ every 10s        │   │   │
│  │  │ :8000/metrics   │         │                  │   │   │
│  │  └────────┬────────┘         └────────┬─────────┘   │   │
│  │           │                           │             │   │
│  │  ┌────────▼────────────────────────────▼──────┐    │   │
│  │  │   Grafana Pod                              │    │   │
│  │  │   (Dashboard & Visualization)              │    │   │
│  │  │   :3000                                    │    │   │
│  │  └────────┬─────────────────────────────────┘    │   │
│  │           │                                       │   │
│  │  ┌────────┴──────────────────────────────────┐   │   │
│  │  │  PersistentVolumes                        │   │   │
│  │  │  - bioetl-data (50GB)                     │   │   │
│  │  │  - prometheus-data (20GB)                 │   │   │
│  │  │  - grafana-data (5GB)                     │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Networking                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │
│  │ Ingress      │  │ Network      │  │ Resource   │   │
│  │ Controller   │  │ Policies     │  │ Quotas     │   │
│  │ (TLS/HTTPS)  │  │ (RBAC)       │  │ (Limits)   │   │
│  └──────────────┘  └──────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Key Features

### Application Deployment
- **Multi-replica support** with HPA (scales 1-5 pods)
- **Health checks**: Liveness & readiness probes on metrics endpoint
- **Resource management**: CPU/memory requests and limits
- **Graceful shutdown**: 30-second termination grace period
- **Configuration**: Environment variables via ConfigMap
- **Secrets management**: API keys stored separately

### Monitoring Stack
- **Prometheus**: Collects metrics from BioETL endpoints
- **Grafana**: Provides dashboards for visualization
- **Automated scraping**: 10-second intervals from BioETL pods
- **Data retention**: 15 days for Prometheus, persistent for Grafana

### Networking & Security
- **Ingress**: HTTPS/TLS support for external access
- **Network Policies**: Restrict pod-to-pod communication
- **RBAC**: Service accounts with minimal permissions
- **Resource Quotas**: Namespace-level resource limits
- **Pod Disruption Budget**: High availability during maintenance

### Data Persistence
- **50GB** for application data (Bronze/Silver/Gold layers)
- **20GB** for metrics (Prometheus time-series)
- **5GB** for dashboards (Grafana)
- **Configurable storage classes** (fast-ssd, default, etc.)

---

## Configuration Reference

### Environment Variables (ConfigMap)

| Variable | Default | Purpose |
|----------|---------|---------|
| BIOETL_ENV | prod | Environment name (dev/staging/prod) |
| BIOETL_PIPELINE__BATCH_SIZE | 100 | Data batch size for processing |
| BIOETL_PIPELINE__MAX_CONCURRENT_BATCHES | 4 | Concurrent batch limit |
| BIOETL_LOG_LEVEL | INFO | Logging level |
| BIOETL_METRICS_ENABLED | true | Enable Prometheus metrics |
| BIOETL_METRICS_PORT | 8000 | Metrics HTTP server port |

### Secrets (Must Update)

| Secret | Description |
|--------|-------------|
| BIOETL_PII_SALT_CURRENT | Random 64-char string for PII hashing |
| BIOETL_UNIPROT_API_KEY | UniProt API access key |
| BIOETL_OPENALEX_EMAIL | OpenAlex polite pool email |
| BIOETL_SEMANTICSCHOLAR_API_KEY | Semantic Scholar access key |
| BIOETL_PUBMED_API_KEY | NCBI PubMed access key |
| BIOETL_CROSSREF_EMAIL | Crossref polite pool email |

### Resources (Adjustable)

```yaml
# Development
requests: {cpu: 100m, memory: 256Mi}
limits: {cpu: 500m, memory: 1Gi}

# Staging
requests: {cpu: 500m, memory: 1Gi}
limits: {cpu: 2000m, memory: 2Gi}

# Production
requests: {cpu: 1000m, memory: 2Gi}
limits: {cpu: 4000m, memory: 8Gi}
```

---

## Deployment Scenarios

### Development (Local minikube/kind)
```bash
./deploy-bioetl.sh deploy dev
kubectl port-forward -n bioetl-dev svc/grafana 3000:3000
```
Access: http://localhost:3000

### Staging (AWS EKS)
```bash
kubectl create namespace bioetl-staging
kubectl apply -n bioetl-staging -f k8s-deployment.yaml
kubectl apply -n bioetl-staging -f k8s-monitoring.yaml
# Configure ingress with cert-manager for HTTPS
```

### Production (Multi-zone, HA)
```bash
# Increase replicas
kubectl scale deployment/bioetl -n bioetl-prod --replicas=3

# Enable auto-scaling
kubectl apply -f k8s-networking.yaml

# Monitor with Prometheus/Grafana
kubectl port-forward -n bioetl-prod svc/prometheus 9090:9090
```

---

## Troubleshooting Quick Links

| Issue | Resolution |
|-------|-----------|
| Pod pending | Check: PVC status, node resources, image pull |
| Metrics 404 | Verify BIOETL_METRICS_PORT=8000 in ConfigMap |
| Grafana no data | Check Prometheus datasource, scrape targets |
| OOM Errors | Increase memory limits, check log volume |
| Storage full | Check PVC usage, run cleanup tasks |

See DEPLOYMENT-GUIDE.md for detailed troubleshooting.

---

## Next Steps

1. **Update image registry** in all manifests
2. **Configure secrets** with real API keys
3. **Set storage class** based on cloud provider
4. **Deploy** using kubectl or automated script
5. **Verify** with status and logs commands
6. **Configure ingress** with your domain
7. **Set up alerting** in Prometheus/Grafana
8. **Document runbooks** for operations team

---

## Support Resources

- Kubernetes Docs: https://kubernetes.io/docs/
- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- Docker Docs: https://docs.docker.com/reference/cli/docker/container/run/
- BioETL README: ../README.md

