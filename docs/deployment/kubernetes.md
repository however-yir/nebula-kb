# Kubernetes Deployment

## 1. Use Helm chart

Chart path:

- `helm/`

## 2. Prepare values

Create a custom values file, for example `values-prod.yaml`:

- set `image.repository` and `image.tag`
- replace all default passwords and API keys
- configure ingress / TLS
- configure external MySQL, Redis, and object storage if required

## 3. Install

```bash
helm upgrade --install yourrag ./helm -f values-prod.yaml -n yourrag --create-namespace
```

## 4. Health checks

```bash
kubectl get pods -n yourrag
kubectl get svc -n yourrag
kubectl logs -n yourrag deploy/yourrag
```

## 5. Production recommendations

- Add HPA for API and worker pods
- Add PodDisruptionBudget and anti-affinity
- Use managed secrets (External Secrets / Vault)
- Enable network policies and restrict egress
- Configure persistent volume backup policy
