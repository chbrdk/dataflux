# DataFlux Kubernetes Deployment

## ☸️ Overview

This directory contains Kubernetes manifests for deploying DataFlux in production.

## 📁 Structure

```
k8s/
├── namespaces/            # Namespace definitions
├── configmaps/           # Configuration maps
├── secrets/              # Secret definitions
├── deployments/          # Deployment manifests
├── services/             # Service definitions
├── ingress/              # Ingress configurations
├── persistent-volumes/   # PV and PVC definitions
├── monitoring/           # Prometheus/Grafana manifests
├── rbac/                # Role-based access control
└── helm/                 # Helm charts
    ├── dataflux/         # Main DataFlux chart
    ├── monitoring/       # Monitoring stack chart
    └── values/           # Environment-specific values
```

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3.x installed

### Deploy with Helm
```bash
# Add DataFlux Helm repository
helm repo add dataflux https://charts.dataflux.io
helm repo update

# Install DataFlux
helm install dataflux dataflux/dataflux \
  --namespace dataflux \
  --create-namespace \
  --values k8s/helm/values/production.yaml

# Check deployment
kubectl get pods -n dataflux
```

### Deploy with kubectl
```bash
# Create namespace
kubectl apply -f k8s/namespaces/

# Apply configurations
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/

# Deploy services
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/

# Setup ingress
kubectl apply -f k8s/ingress/
```

## 🏗️ Architecture

### Namespaces
- **dataflux**: Main application services
- **dataflux-monitoring**: Monitoring stack
- **dataflux-storage**: Storage services

### Services
- **ingestion-service**: File upload and processing
- **query-service**: Search and retrieval
- **analysis-service**: AI content analysis
- **mcp-server**: LLM integration
- **api-gateway**: Nginx reverse proxy

### Databases
- **postgres**: Metadata storage
- **redis**: Caching layer
- **kafka**: Message queue
- **minio**: Object storage
- **weaviate**: Vector database
- **neo4j**: Graph database
- **clickhouse**: Analytics

## 📊 Resource Requirements

### Minimum Requirements
- **CPU**: 8 cores
- **Memory**: 32 GB RAM
- **Storage**: 500 GB SSD
- **Network**: 1 Gbps

### Recommended Requirements
- **CPU**: 16 cores
- **Memory**: 64 GB RAM
- **Storage**: 2 TB NVMe SSD
- **Network**: 10 Gbps

### GPU Requirements
- **Analysis Service**: NVIDIA GPU with 8GB+ VRAM
- **CUDA**: Version 11.8+
- **Driver**: Version 520+

## 🔧 Configuration

### Environment Variables
```yaml
# k8s/configmaps/dataflux-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataflux-config
  namespace: dataflux
data:
  LOG_LEVEL: "info"
  ENVIRONMENT: "production"
  POSTGRES_DB: "dataflux"
  REDIS_MAX_MEMORY: "4gb"
  KAFKA_NUM_PARTITIONS: "6"
```

### Secrets
```yaml
# k8s/secrets/dataflux-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: dataflux-secrets
  namespace: dataflux
type: Opaque
data:
  POSTGRES_PASSWORD: <base64-encoded-password>
  REDIS_PASSWORD: <base64-encoded-password>
  JWT_SECRET: <base64-encoded-secret>
  OPENAI_API_KEY: <base64-encoded-key>
```

## 🚀 Scaling

### Horizontal Pod Autoscaling
```yaml
# k8s/hpa/query-service-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: query-service-hpa
  namespace: dataflux
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: query-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaling
```yaml
# k8s/vpa/analysis-service-vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: analysis-service-vpa
  namespace: dataflux
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analysis-service
  updatePolicy:
    updateMode: "Auto"
```

## 💾 Storage

### Persistent Volumes
```yaml
# k8s/persistent-volumes/postgres-pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: fast-ssd
  hostPath:
    path: /data/postgres
```

### Storage Classes
```yaml
# k8s/storage-classes/fast-ssd.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
```

## 🌐 Networking

### Ingress Configuration
```yaml
# k8s/ingress/dataflux-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dataflux-ingress
  namespace: dataflux
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.dataflux.io
    secretName: dataflux-tls
  rules:
  - host: api.dataflux.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
```

### Service Mesh (Istio)
```yaml
# k8s/istio/virtual-service.yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: dataflux-vs
  namespace: dataflux
spec:
  hosts:
  - api.dataflux.io
  gateways:
  - dataflux-gateway
  http:
  - match:
    - uri:
        prefix: /api/v1/assets
    route:
    - destination:
        host: ingestion-service
        port:
          number: 8001
  - match:
    - uri:
        prefix: /api/v1/search
    route:
    - destination:
        host: query-service
        port:
          number: 8002
```

## 🔒 Security

### Network Policies
```yaml
# k8s/network-policies/dataflux-netpol.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dataflux-netpol
  namespace: dataflux
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: dataflux
    - podSelector:
        matchLabels:
          app: api-gateway
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: dataflux
```

### Pod Security Standards
```yaml
# k8s/pod-security/dataflux-psp.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: dataflux-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## 📊 Monitoring

### ServiceMonitor for Prometheus
```yaml
# k8s/monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dataflux-services
  namespace: dataflux
spec:
  selector:
    matchLabels:
      app: dataflux
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Grafana Dashboard ConfigMap
```yaml
# k8s/monitoring/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataflux-dashboard
  namespace: dataflux-monitoring
  labels:
    grafana_dashboard: "1"
data:
  dataflux-overview.json: |
    {
      "dashboard": {
        "title": "DataFlux Overview",
        "panels": [...]
      }
    }
```

## 🔄 CI/CD Integration

### ArgoCD Application
```yaml
# k8s/argocd/dataflux-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dataflux
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/yourusername/dataflux.git
    targetRevision: HEAD
    path: k8s/helm/dataflux
  destination:
    server: https://kubernetes.default.svc
    namespace: dataflux
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## 📋 Deployment Checklist

- [ ] Kubernetes cluster ready
- [ ] kubectl configured
- [ ] Helm installed
- [ ] Namespaces created
- [ ] ConfigMaps applied
- [ ] Secrets created
- [ ] Deployments running
- [ ] Services accessible
- [ ] Ingress configured
- [ ] SSL certificates valid
- [ ] Monitoring configured
- [ ] Logging working
- [ ] Backup strategy implemented
- [ ] Security policies applied
- [ ] Performance tested
- [ ] Documentation updated
