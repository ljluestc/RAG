# Runbook: Pod Crash Loop

## Overview
This runbook guides operators through diagnosing and resolving Kubernetes pods stuck in CrashLoopBackOff.

## Symptoms
- Pod status: `CrashLoopBackOff` or `Error`
- `kubectl get pods` shows `RESTARTS` count increasing
- Application fails to start or exits immediately after start

## Prerequisites
- `kubectl` configured with cluster access
- Appropriate RBAC permissions to view pods, logs, events

## Procedure

### Step 1: Inspect Pod Status
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:
- `Last State` and `Reason` in container status
- `Exit Code` (e.g., 1, 137 for OOM)
- Resource limits and requests

### Step 2: Check Container Logs
```bash
kubectl logs <pod-name> -n <namespace> --previous
kubectl logs <pod-name> -n <namespace> -c <container-name>
```

The `--previous` flag shows logs from the crashed container instance.

### Step 3: Common Causes and Fixes

| Cause | Fix |
|-------|-----|
| OOMKilled (exit 137) | Increase memory limits or fix memory leak |
| Liveness probe failure | Adjust probe thresholds or fix startup time |
| Missing config/secret | Verify ConfigMap/Secret exists and is mounted |
| Init container failure | Check init container logs |
| Image pull error | Verify image exists and imagePullSecrets |

### Step 4: Verify Fix
```bash
kubectl get pod <pod-name> -n <namespace> -w
# Wait for Running status with 0 restarts
```

## Escalation
If the issue persists after 30 minutes of troubleshooting, escalate to platform team. Include:
- Pod describe output
- Previous container logs
- Recent events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`

## References
- Kubernetes docs: Pod lifecycle
- Internal: SRE playbook #42
